# Textes d'intro — format « Sélection rafale » (style LMDLS)

Livrable : **tous les textes d'intro (hooks)** pour les 20 photos préparées, rangées ici
sous `intro_01.jpg` → `intro_20.jpg`. Données machine dans [`intros.json`](intros.json).
Règles du format : [spec](../../../../docs/superpowers/specs/2026-07-07-format-selection-rafale-lmdls-design.md).

## Comment lire

Le hook est une **pile de lignes centrée** qui apparaît **ligne par ligne (~0,8 s/ligne)** sur
la photo fixe, puis reste ~1,7 s avant la rafale produits. Code couleur :

- **blanc** = texte normal (mots de structure)
- 🟡 **jaune** = adjectif hype + mot-punch (`meilleurs`, `incroyables`, `sous-cotés`, `absolument`, `ne connaît`)
- 🔴 **badge rouge** = dernier chip temporel (`cet été`) sur pastille arrondie
- *part N* = petit, blanc, sous la pile

`part N` = numéro dans la **série** (même produit) → effet « suite », les gens reviennent voir la suivante.

---

## Les 20 hooks (1 par photo)

| Photo | Produit héros | Texte d'intro complet | Série · part |
|-------|---------------|-----------------------|--------------|
| **intro_01** | polo rugby rayé vert | Les 🟡meilleurs polos à avoir 🟡absolument 🔴cet été · *part 1* | polos · 1 |
| **intro_02** | t-shirt rayé jaune | Les t-shirts 🟡incroyables que presque personne 🟡ne connaît · *part 1* | t-shirts · 1 |
| **intro_03** | Nike Dunk jaunes | Les 🟡meilleures sneakers à avoir 🟡absolument 🔴cet été · *part 1* | sneakers · 1 |
| **intro_04** | t-shirt rayé jaune | Les t-shirts 🟡incroyables que presque personne 🟡ne connaît · *part 2* | t-shirts · 2 |
| **intro_05** | veste varsity noire | Les vestes 🟡sous-cotées que presque personne 🟡ne connaît · *part 1* | vestes · 1 |
| **intro_06** | t-shirt jaune LIVE FAST | Les t-shirts 🟡incroyables que presque personne 🟡ne connaît · *part 3* | t-shirts · 3 |
| **intro_07** | surchemise rayée rose | Les chemises 🟡incroyables que presque personne 🟡ne connaît · *part 1* | chemises · 1 |
| **intro_08** | short cargo camo | Les cargos 🟡sous-cotés que presque personne 🟡ne connaît · *part 1* | cargos · 1 |
| **intro_09** | maillot de foot bleu #19 | Les 🟡meilleurs maillots à avoir 🟡absolument 🔴cet été · *part 1* | maillots · 1 |
| **intro_10** | polo bleu marine + jorts | Les 🟡meilleurs polos à avoir 🟡absolument 🔴cet été · *part 2* | polos · 2 |
| **intro_11** | cargo blanc destroy | Les cargos 🟡sous-cotés que presque personne 🟡ne connaît · *part 2* | cargos · 2 |
| **intro_12** | maillot lacrosse jaune | Les 🟡meilleurs maillots à avoir 🟡absolument 🔴cet été · *part 2* | maillots · 2 |
| **intro_13** | sweat manches longues CASA | Les sweats 🟡incroyables que presque personne 🟡ne connaît · *part 1* | sweats · 1 |
| **intro_14** | polo rugby rayé vert | Les 🟡meilleurs polos à avoir 🟡absolument 🔴cet été · *part 3* | polos · 3 |
| **intro_15** | maillot foot US #55 | Les 🟡meilleurs maillots à avoir 🟡absolument 🔴cet été · *part 3* | maillots · 3 |
| **intro_16** | hoodie marron + bandana | Les hoodies 🟡incroyables que presque personne 🟡ne connaît · *part 1* | hoodies · 1 |
| **intro_17** | t-shirt gris | Les t-shirts 🟡incroyables que presque personne 🟡ne connaît · *part 4* | t-shirts · 4 |
| **intro_18** | hoodie vert LIVE FAST | Les hoodies 🟡incroyables que presque personne 🟡ne connaît · *part 2* | hoodies · 2 |
| **intro_19** | veste coach verte | Les vestes 🟡sous-cotées que presque personne 🟡ne connaît · *part 2* | vestes · 2 |
| **intro_20** | t-shirt blanc imprimé | Les t-shirts 🟡incroyables que presque personne 🟡ne connaît · *part 5* | t-shirts · 5 |

---

## Découpage ligne par ligne (pour l'animation)

Chaque bloc = une pile ; chaque tiret = une ligne révélée à ~0,8 s d'intervalle.

**Modèle A — « best-of saison »** (intro_01, 03, 09, 10, 12, 14, 15)
```
Les
meilleurs        🟡
{produit}
à avoir
absolument       🟡
cet été          🔴 badge
part N           (petit)
```

**Modèle B — « secret / sous-coté »** (intro_02, 04, 05, 06, 07, 08, 11, 13, 16, 17, 18, 19, 20)
```
Les
{produit}
incroyables      🟡   (ou : sous-cotés 🟡)
que presque
personne
ne connaît       🟡
part N           (petit)
```

---

## Banque pour générer à l'infini (au-delà des 20)

**Produits** (accord genre à respecter) :
`t-shirts, maillots, polos, sweats, hoodies, vestes, chemises, cargos, jeans, jorts, sneakers, casquettes, sacs`
→ féminins : `vestes, chemises, sneakers, casquettes` (→ *meilleures*, *sous-cotées*).

**Adjectifs hype** : `incroyables · sous-cotés · que personne ne porte · introuvables · qui changent tout`
**Superlatif** : `meilleurs / meilleures`
**Périodes (badge rouge)** : `cet été · cette saison · en 2026 · à la rentrée`
**Squelettes** :
- `Les {sup} {produit} à avoir absolument {période}`
- `Les {produit} {adj} que presque personne ne connaît`
- `Les {produit} {adj} qu'il te faut {période}`

**Variante 60 s « choix »** (multi-produits, CTA commentaire) :
```
Les meilleurs {produit} du moment
Choisis ton préféré
part 1
```
→ enchaîner 4–5 produits, la caption change à chaque produit, hook « Choisis ton préféré ».

---

## Notes

- Accents : le repo tourne en fr ; ici les hooks sont écrits **avec** accents pour l'affichage.
  `intros.json` est volontairement sans accents (sécurité encodage) — le renderer réinjecte les accents à l'affichage.
- Numérotation `part N` = par série. En repostant, incrémenter la même série pour créer l'effet feuilleton.
- Mapping `intro_NN.jpg` → hash source d'origine : voir champ `src` dans `intros.json`.
