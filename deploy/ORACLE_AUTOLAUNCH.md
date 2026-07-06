# Auto-lancement d'une VM Oracle Free (retry capacité + notif Telegram)

Oracle Free est souvent "out of capacity". Ce script retente en boucle (et tente
plusieurs shapes gratuits) jusqu'à ce qu'une VM démarre, puis t'envoie une notif
Telegram avec l'IP.

## Setup unique (~5 min)

### 1. Installer le SDK Oracle
```
pip install oci
```

### 2. Créer une clé API Oracle (la console génère tout pour toi)
1. Console Oracle → en haut à droite, ton **avatar** → **My profile**
2. Menu de gauche → **API keys** → **Add API key**
3. Laisse **"Generate API key pair"** → **Download private key** (garde le fichier)
4. **Add** → Oracle affiche un encadré **"Configuration file preview"** : clique **Copy**
5. Crée le fichier `C:\Users\User\.oci\config` et **colle** ce contenu dedans.
6. Dans ce fichier, la ligne `key_file=` doit pointer vers la clé privée téléchargée,
   par ex. :
   ```
   key_file=C:\Users\User\.oci\oci_api_key.pem
   ```
   (déplace/renomme la clé privée téléchargée à cet emplacement.)

> Le `config` ressemble à ça (valeurs déjà remplies par Oracle) :
> ```
> [DEFAULT]
> user=ocid1.user.oc1..xxxx
> fingerprint=aa:bb:cc:...
> tenancy=ocid1.tenancy.oc1..xxxx
> region=eu-paris-1
> key_file=C:\Users\User\.oci\oci_api_key.pem
> ```

### 3. Renseigner la config du script
1. Copie `deploy/oracle_autolaunch.config.example.json`
   → `deploy/oracle_autolaunch.config.json`
2. Mets le chemin de ta **clé SSH publique** (le `.pub` téléchargé au moment de la
   création d'instance) dans `ssh_public_key_path`.
   - Si tu n'as pas de `.pub`, génère-en une :
     `ssh-keygen -t rsa -b 2048 -f C:\Users\User\.ssh\automontage` → utilise
     `automontage.pub`.

### 4. Lancer
Double-clic sur **`oracle_autolaunch.bat`** (ou `python deploy/oracle_autolaunch.py`).
Garde la fenêtre ouverte : il retente toutes les 3 min. Dès qu'une VM démarre :
- il écrit l'IP dans `deploy/oracle_instance.json`
- il t'envoie une **notif Telegram** ✅

Ensuite, dis-moi "la VM est prête" → je déploie le service 24/7 dessus.

## Notes
- La notif passe par **Telegram** (Instagram ne permet pas de s'auto-notifier
  gratuitement). Token lu depuis `~/.automontage/settings.json`.
- Le script ne supprime rien. Il réutilise un réseau public existant, sinon il
  crée VCN + passerelle + sous-réseau (SSH 22 ouvert).
- Sécurité : ne commite jamais `~/.oci/config`, la clé privée, ni
  `oracle_autolaunch.config.json` (chemins locaux). Le `.gitignore` les exclut.
