#!/usr/bin/env python3
"""Auto-lancement d'une instance Oracle Cloud Always Free.

Oracle Free est en "out of capacity" la plupart du temps sur les shapes gratuits.
Ce script RETENTE en boucle (et tente plusieurs shapes) jusqu'à ce qu'une
capacité se libère. Dès que l'instance démarre, il récupère l'IP publique et
envoie une notif Telegram.

Pré-requis (setup unique) :
  1. pip install oci
  2. Une clé API Oracle dans ~/.oci/config  (voir deploy/ORACLE_AUTOLAUNCH.md)
  3. deploy/oracle_autolaunch.config.json renseigné (chemin clé SSH publique...)

Lancement :
  python deploy/oracle_autolaunch.py
(ou double-clic sur oracle_autolaunch.bat)

Le script est SANS effet de bord destructeur : il ne fait que LIRE l'état et
CRÉER (réseau si absent + instance). Il s'arrête dès qu'une instance tourne.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse

try:
    import oci
except ImportError:
    print("[ERREUR] Le SDK Oracle n'est pas installé. Fais d'abord :")
    print("    pip install oci")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "oracle_autolaunch.config.json")
RESULT_PATH = os.path.join(HERE, "oracle_instance.json")
SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".automontage", "settings.json")

# Codes/erreurs qui signifient "réessaie plus tard" (capacité, throttling).
_RETRYABLE = ("out of host capacity", "out of capacity", "outofcapacity",
              "too many requests", "internalerror")


# --------------------------------------------------------------------------- #
# Notifications (Telegram — instantané sur ton téléphone)
# --------------------------------------------------------------------------- #
def _telegram(msg):
    """Envoie un message Telegram via le bot déjà configuré. Best-effort."""
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            s = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        s = {}
    token, chat = s.get("telegram_bot_token"), s.get("telegram_chat_id")
    if not (token and chat):
        print("[notif] Telegram non configuré — message non envoyé :", msg)
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat, "text": msg}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15)
    except Exception as e:                                    # pragma: no cover
        print("[notif] échec envoi Telegram :", e)


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"[ERREUR] Config absente : {CONFIG_PATH}")
        print("Copie oracle_autolaunch.config.example.json -> oracle_autolaunch.config.json")
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    pub = cfg.get("ssh_public_key_path", "")
    if not pub or not os.path.exists(pub):
        print(f"[ERREUR] Clé SSH publique introuvable : {pub!r}")
        print("Renseigne 'ssh_public_key_path' (le fichier .pub téléchargé d'Oracle).")
        sys.exit(1)
    with open(pub, encoding="utf-8") as f:
        cfg["_ssh_public_key"] = f.read().strip()
    return cfg


# --------------------------------------------------------------------------- #
# Découverte des ressources (AD, image, sous-réseau)
# --------------------------------------------------------------------------- #
def pick_availability_domain(identity, compartment):
    ads = identity.list_availability_domains(compartment).data
    if not ads:
        raise RuntimeError("Aucun availability domain trouvé.")
    return ads[0].name


def pick_image(compute, compartment, shape, os_name, os_version):
    """OCID de la dernière image Ubuntu compatible avec le shape (l'arch est
    gérée automatiquement par le filtre shape)."""
    images = compute.list_images(
        compartment, operating_system=os_name,
        operating_system_version=os_version, shape=shape,
        sort_by="TIMECREATED", sort_order="DESC").data
    if not images:
        raise RuntimeError(
            f"Aucune image {os_name} {os_version} pour le shape {shape}.")
    return images[0].id


def ensure_public_subnet(net, compartment, ssh_cidr="0.0.0.0/0"):
    """Renvoie l'OCID d'un sous-réseau public. En réutilise un s'il existe,
    sinon crée VCN + Internet Gateway + route + sécurité (SSH 22) + subnet."""
    # 1) réutiliser un subnet existant si présent
    subnets = net.list_subnets(compartment).data
    for sn in subnets:
        if not getattr(sn, "prohibit_public_ip_on_vnic", True):
            print(f"[reseau] sous-réseau public réutilisé : {sn.display_name}")
            return sn.id

    print("[reseau] aucun sous-réseau public — création du VCN complet…")
    netc = oci.core.VirtualNetworkClientCompositeOperations(net)

    vcn = netc.create_vcn_and_wait_for_state(
        oci.core.models.CreateVcnDetails(
            cidr_block="10.0.0.0/16", compartment_id=compartment,
            display_name="automontage-vcn"),
        [oci.core.models.Vcn.LIFECYCLE_STATE_AVAILABLE]).data

    igw = netc.create_internet_gateway_and_wait_for_state(
        oci.core.models.CreateInternetGatewayDetails(
            compartment_id=compartment, vcn_id=vcn.id, is_enabled=True,
            display_name="automontage-igw"),
        [oci.core.models.InternetGateway.LIFECYCLE_STATE_AVAILABLE]).data

    rt = netc.create_route_table_and_wait_for_state(
        oci.core.models.CreateRouteTableDetails(
            compartment_id=compartment, vcn_id=vcn.id,
            display_name="automontage-rt",
            route_rules=[oci.core.models.RouteRule(
                destination="0.0.0.0/0", network_entity_id=igw.id)]),
        [oci.core.models.RouteTable.LIFECYCLE_STATE_AVAILABLE]).data

    sl = netc.create_security_list_and_wait_for_state(
        oci.core.models.CreateSecurityListDetails(
            compartment_id=compartment, vcn_id=vcn.id,
            display_name="automontage-sl",
            egress_security_rules=[oci.core.models.EgressSecurityRule(
                protocol="all", destination="0.0.0.0/0")],
            ingress_security_rules=[oci.core.models.IngressSecurityRule(
                protocol="6", source=ssh_cidr,  # 6 = TCP
                tcp_options=oci.core.models.TcpOptions(
                    destination_port_range=oci.core.models.PortRange(
                        min=22, max=22)))]),
        [oci.core.models.SecurityList.LIFECYCLE_STATE_AVAILABLE]).data

    subnet = netc.create_subnet_and_wait_for_state(
        oci.core.models.CreateSubnetDetails(
            compartment_id=compartment, vcn_id=vcn.id,
            cidr_block="10.0.0.0/24", display_name="automontage-subnet",
            route_table_id=rt.id, security_list_ids=[sl.id],
            prohibit_public_ip_on_vnic=False),
        [oci.core.models.Subnet.LIFECYCLE_STATE_AVAILABLE]).data
    print(f"[reseau] sous-réseau public créé : {subnet.display_name}")
    return subnet.id


# --------------------------------------------------------------------------- #
# Lancement avec retry sur capacité
# --------------------------------------------------------------------------- #
def _is_retryable(err):
    msg = (str(getattr(err, "message", "")) + " " + str(err)).lower()
    return any(k in msg for k in _RETRYABLE)


def build_launch_details(cfg, attempt, ad, compartment, image_id, subnet_id):
    shape = attempt["shape"]
    details = oci.core.models.LaunchInstanceDetails(
        availability_domain=ad,
        compartment_id=compartment,
        shape=shape,
        display_name=cfg.get("display_name", "automontage"),
        source_details=oci.core.models.InstanceSourceViaImageDetails(image_id=image_id),
        create_vnic_details=oci.core.models.CreateVnicDetails(
            subnet_id=subnet_id, assign_public_ip=True),
        metadata={"ssh_authorized_keys": cfg["_ssh_public_key"]},
    )
    # Les shapes "Flex" (Ampere A1) exigent ocpus + mémoire.
    if "Flex" in shape:
        details.shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus=float(attempt.get("ocpus", 1)),
            memory_in_gbs=float(attempt.get("memory_gb", 6)))
    return details


def get_public_ip(compute, net, compartment, instance_id):
    atts = compute.list_vnic_attachments(compartment, instance_id=instance_id).data
    for a in atts:
        vnic = net.get_vnic(a.vnic_id).data
        if vnic.public_ip:
            return vnic.public_ip
    return None


def main(once=False):
    cfg = load_config()
    oci_cfg = oci.config.from_file()  # ~/.oci/config, profil DEFAULT
    oci.config.validate_config(oci_cfg)
    compartment = cfg.get("compartment_id") or oci_cfg["tenancy"]

    identity = oci.identity.IdentityClient(oci_cfg)
    compute = oci.core.ComputeClient(oci_cfg)
    net = oci.core.VirtualNetworkClient(oci_cfg)

    retry_s = int(cfg.get("retry_seconds", 180))
    attempts = cfg.get("attempts") or []
    if not attempts:
        print("[ERREUR] 'attempts' vide dans la config.")
        sys.exit(1)

    print("[oracle] préparation (AD, image, réseau)…")
    # Tolérance au 401/429/5xx (clé API fraîchement ajoutée = propagation lente) :
    # on retente le setup jusqu'à ce que l'auth passe, au lieu de planter.
    ad = subnet_id = None
    for setup_try in range(120):
        try:
            ad = pick_availability_domain(identity, compartment)
            subnet_id = ensure_public_subnet(net, compartment)
            for a in attempts:
                a["_image_id"] = pick_image(compute, compartment, a["shape"],
                                            a.get("os", "Canonical Ubuntu"),
                                            a.get("os_version", "22.04"))
                print(f"[oracle] tentative prévue : {a['shape']}  (image OK)")
            break
        except oci.exceptions.ServiceError as e:
            if e.status in (401, 429) or 500 <= e.status < 600:
                print(f"[oracle] setup : {e.status} {e.code} — clé en propagation ? "
                      f"retry 60s ({setup_try + 1})", flush=True)
                time.sleep(60)
            else:
                raise
    else:
        print("[ERREUR] auth toujours KO après ~2h — vérifier la clé API.")
        return 1

    if not once:   # en mode --once (GitHub, toutes les 30 min) on évite le spam
        _telegram("🟡 AutoMontage : recherche de capacité Oracle lancée. "
                  "Je te préviens dès que le serveur est prêt.")

    compute_c = oci.core.ComputeClientCompositeOperations(compute)
    cycle = 0
    while True:
        cycle += 1
        for a in attempts:
            shape = a["shape"]
            try:
                print(f"[oracle] cycle {cycle} — tentative {shape}…", flush=True)
                details = build_launch_details(cfg, a, ad, compartment,
                                               a["_image_id"], subnet_id)
                resp = compute_c.launch_instance_and_wait_for_state(
                    details, [oci.core.models.Instance.LIFECYCLE_STATE_RUNNING])
                inst = resp.data
                ip = get_public_ip(compute, net, compartment, inst.id)
                with open(RESULT_PATH, "w", encoding="utf-8") as f:
                    json.dump({"instance_id": inst.id, "shape": shape,
                               "public_ip": ip, "display_name": inst.display_name},
                              f, ensure_ascii=False, indent=2)
                print(f"[oracle] ✅ INSTANCE PRÊTE — {shape} — IP {ip}")
                _telegram(
                    f"✅ AutoMontage : serveur Oracle PRÊT !\n"
                    f"Shape : {shape}\nIP : {ip}\n"
                    f"Reviens me dire 'la VM est prête' pour que je déploie.")
                return 0
            except oci.exceptions.ServiceError as e:
                if _is_retryable(e):
                    print(f"[oracle]   pas de capacité ({e.status}) — on retente.")
                    continue
                print(f"[oracle] ERREUR non-récupérable : {e}")
                _telegram(f"⚠️ AutoMontage : erreur Oracle non gérée : {e.code} "
                          f"— le script s'arrête, regarde la console.")
                return 1
        if once:                       # mode GitHub Actions : 1 run = 1 cycle
            print("[oracle] run unique terminé — pas de capacité ce coup-ci.")
            return 0
        print(f"[oracle] aucune capacité ce cycle — pause {retry_s}s…", flush=True)
        time.sleep(retry_s)


if __name__ == "__main__":
    sys.exit(main(once="--once" in sys.argv))
