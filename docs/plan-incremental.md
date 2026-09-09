# Plan : donjon mystère incrémental

Document de référence pour la transformation du roguelike en hybride
roguelike / incrémental. À relire au début de chaque session de travail.

## Les trois couches

1. **Le donjon** (fait) — roguelike classique : étages générés, permadeath,
   faim, objets, tour par tour.
2. **XP par action** — pas de niveau global de personnage, mais une XP séparée
   par compétence (marcher, épée, hache, pyromancie, potions…), gagnée à
   l'usage réel.
3. **Prestige** — à la mort, les compétences sont perdues ; un niveau global
   permanent monte, améliore les runs suivants et débloque des mécaniques.

## La frontière run / méta

```
Meta  ──(lu au lancement)──>  RunConfig  ──(injectée)──>  Game
 ▲                                                          │
 └──────────(mis à jour à un seul endroit)── RunSummary ────┘
```

- **`Meta`** — persiste : niveau global, XP globale, déblocages, statistiques
  cumulées, options. Sérialisé en JSON.
- **`RunConfig`** (`donjon/config.py`, fait) — dérivée du méta au lancement,
  immuable pendant le run : réglages, stats de départ, kit, tables autorisées.
- **`Game`** — état de run, intégralement détruit à la mort.

**La règle qui tient tout : `Game` ne connaît que `RunConfig`, jamais `Meta`.**
Et `Meta` n'est modifié qu'à la fin d'un run. Sans cette règle, du code de run
finira par lire le méta au milieu d'un combat et la frontière sera perdue.

| Détruit à la mort | Survit |
|---|---|
| Niveaux et XP de compétences | Niveau global, XP globale |
| Inventaire, équipement | Déblocages acquis |
| PV, faim, statuts | Statistiques cumulées, records |
| Étage, carte, monstres, journal | Options |

## Décisions prises

| Question | Choix |
|---|---|
| Niveau global du personnage | **Il disparaît** — les compétences remplacent toute la progression de run (étape 3) |
| Gain d'XP | **Fixe par action**, sans rendement décroissant ni garde-fou anti-farm |
| Effet d'un niveau | **Bonus de stats continus** (épée +N dégâts, marche → faim ralentie…) |
| Fin de run | **Mort seule** (ou fond du donjon atteint) — pas d'extraction volontaire |

### Pourquoi pas de garde-fou anti-farm

Tourner en rond pour farmer « marcher » est déjà puni par la faim : mesuré sur
120 parties, un étage rapporte ~18 points de ventre (0,37 onigiri en moyenne)
et en coûte ~26. **Le budget d'XP de marche d'un run est exactement le total de
nourriture qu'il trouve.** Le levier d'équilibrage est donc un poids dans
`items.py` et une taille de jauge dans `RunConfig` — deux nombres en données,
aucune règle dans le moteur.

Conséquence pour la couche 3 : « jauge de faim plus grande » ne vend pas du
confort, elle vend **du temps de progression**.

Réserve connue : le jour où une compétence « nourriture » ou un bonus de
prestige rendra la nourriture abondante, le farm redeviendra rentable. Ce sera
alors une récompense assumée, à garder en tête en écrivant ces tables.

## Étapes

| # | Étape | État |
|---|---|---|
| 0 | `RunConfig` : les réglages deviennent des données injectées | ✅ fait |
| 1 | Bus d'évènements d'action (`events.py`) | ✅ fait |
| 2 | Table des compétences + XP (`skills.py`) | ✅ fait |
| 3 | Pipeline de stats ; suppression du niveau global de run | ✅ fait |
| 4 | Fin de run + `RunSummary` | à faire |
| 5 | `Meta` + sauvegarde JSON ; la boucle est bouclée | à faire |
| 6 | Déblocages en table | à faire |

Chaque étape laisse le jeu lançable et jouable.

### Étapes 2 et 3 — livrées ensemble

Des compétences sans effet ne se testent pas, et « bonus de stats continus »
n'a de sens qu'avec le pipeline. Les compétences remplacent donc le niveau
global dans le même mouvement : c'était le plus petit incrément cohérent.

Ce qui a disparu : `player.level`, `player.exp`, `exp_threshold`, `grant_exp`
et le champ `exp` du bestiaire. On ne progresse plus en tuant.

**Comment ajouter du contenu, désormais :**

| Ajout | Ce qu'il faut écrire |
|---|---|
| Une famille d'arme (hache) | une entrée dans `CATALOGUE` + `skill="hache"` sur les objets |
| Une compétence sur du contenu existant | une entrée dans `CATALOGUE` + une `Regle` |
| Un objet d'une catégorie connue | rien : la compétence est déduite de la catégorie |
| Un **nouveau type de bonus** | une entrée dans `EFFETS` **et** un point de lecture dans le moteur |

Seule la dernière ligne coûte du code — c'est la frontière assumée du système,
et les effets sont volontairement peu nombreux (8).

**Équilibrage après la bascule**, bot à profondeur 5, 120 graines : 77 % de
victoires contre 83 % avant. Les compétences remplacent donc à peu près les
bonus de l'ancien niveau global, en un peu plus dur. Niveaux gagnés par run
(médiane 7) : marche 2,5 · combat 2,2 · épée 1,3 · bouclier 0,7 · le reste
proche de zéro.

Les compétences rares (cuisine, herboristerie, parchemins, jet) ne montent
quasiment pas parce que le bot n'utilise presque pas d'objets. À revoir quand
un humain aura joué : c'est peut-être le bot qui joue mal, pas la courbe qui
est fausse.

### Mesures de référence (avant l'étape 2)

Mesuré sur 40 parties complètes, une partie émet en moyenne :

| évènement | par partie |
|---|---|
| `pas` | 156 |
| `coup` | 17 |
| `monstre_vaincu` | 9,5 |
| `descente` | 6 |
| `usage_objet` | 1,9 |
| `ramassage` | 0,7 |

Avec une XP fixe par action, « marcher » monte environ **neuf fois plus vite**
qu'« épée ». C'est ce qui a dicté les courbes : `marche` coûte 25 XP le premier
niveau, `epee` seulement 5.

## Règles fixées en cours de route

**Diagonales et angles de murs.** Une diagonale n'est franchissable — ni en
déplacement, ni en coup — que si les deux cases orthogonales sont libres. La
règle vaut pour le héros comme pour les monstres. Coût mesuré au bot :
83 victoires sur 120 contre 92 sans la règle, à graines identiques. Le bot y
perd parce qu'il ignore une cible qu'il ne peut pas frapper et continue sa
route en encaissant ; un joueur humain, lui, y gagne un outil défensif (rompre
le contact en passant un coin) que le bot n'exploite pas.

## Dette assumée

- `bouclier` s'entraîne en encaissant : c'est le seul évènement (`coup_recu`)
  que le héros ne déclenche pas lui-même. Assumé — on apprend à parer en se
  faisant frapper.
- Aucune compétence de magie n'existe encore : le jeu n'a ni bâton ni sort.
  Pyromancie et cryomancie viendront avec le contenu correspondant, chacune
  en une entrée de table.

## Question encore ouverte

**Un objet peut-il survivre à la mort ?** (entrepôt façon Shiren, relique
choisie à chaque mort). Ne bloque rien avant l'étape 5. Hypothèse de travail :
rien ne survit sauf le méta. L'ajouter plus tard = un champ dans `Meta` et une
ligne dans `RunConfig`.

## Contraintes permanentes

- Tout est piloté par des données : ajouter « archerie » doit être une ligne
  dans une table, jamais une modification du moteur. Idem pour les bonus de
  prestige et les déblocages.
- Une action peut créditer plusieurs compétences à la fois.
- Pas de refonte globale : on avance par incréments sur l'existant.
- Le jeu reste jouable après chaque étape.
