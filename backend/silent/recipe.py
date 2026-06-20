"""VideoRecipe : IR de production immuable. Toute la chaîne converge ici.
`validate` applique les invariants I2/I3/R3 ; échec => ValueError (R1: pas de
fallback silencieux)."""
from dataclasses import dataclass
from backend.config import SILENT
from backend.silent import registry


@dataclass(frozen=True)
class VideoRecipe:
    mechanic: str
    layout: str
    hook: str
    content_angle: str
    assets: tuple        # tuple => immuable
    duration: float
    font: str
    accent: str          # couleur ASS, ex "&H0000FFFF&"
    text_anim: str       # "fade" | "pop"
    seed: int
    music: str = None    # chemin du bed musical (optionnel) — décidé par le Policy


def validate(recipe):
    """Vérifie tous les invariants structurels avant émission (R3)."""
    m = registry.MECHANICS.get(recipe.mechanic)
    if m is None:
        raise ValueError(f"unknown mechanic: {recipe.mechanic!r}")            # I2
    if recipe.layout not in m["layouts"]:
        raise ValueError(
            f"layout {recipe.layout!r} not allowed for mechanic "
            f"{recipe.mechanic!r} (allowed: {m['layouts']})")                  # I3
    if len(recipe.assets) != m["asset_count"]:
        raise ValueError(
            f"asset count {len(recipe.assets)} != required "
            f"{m['asset_count']} for {recipe.mechanic!r}")                     # I2
    if not (SILENT["min_duration"] <= recipe.duration <= SILENT["max_duration"]):
        raise ValueError(
            f"duration {recipe.duration} out of range "
            f"[{SILENT['min_duration']}, {SILENT['max_duration']}]")           # I2
    return recipe
