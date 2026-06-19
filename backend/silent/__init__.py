"""Silent Content Engine — pipeline de génération de vidéos sans voix-off.
Architecture : ContentStrategy -> Policy -> VideoRecipe (immuable) -> Renderer -> Store.
Le Policy est le SEUL système de décision (cf docs/superpowers/specs/2026-06-19-silent-content-engine-design.md).
"""
