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
| Fin de run | **Mort seule** — pas d'extraction volontaire ; le fond du donjon (étage 30) reste une victoire, hors de portée sans progression |
| Source du niveau global | **Les niveaux de compétences** accumulés dans le run |
| Effet du niveau global | **Une table fixe de bonus** — même progression pour tous |
| Objets qui survivent | **Un entrepôt**, dans un hub accessible après la mort |

### Pourquoi pas de garde-fou anti-farm

Tourner en rond pour farmer « marcher » est déjà puni par la faim : mesuré sur
120 parties, un étage rapporte ~18 points de ventre (0,37 onigiri en moyenne)
et en coûte ~26. **Le budget d'XP de marche d'un run est exactement le total de
nourriture qu'il trouve.** Le levier d'équilibrage est donc un poids dans
`items.py` et une taille de jauge dans `RunConfig` — deux nombres en données,
aucune règle dans le moteur.

*Correctif de méthode :* ces 18 points par étage sont ce que le donjon **fait
apparaître**, pas ce qu'un joueur ramasse. Le bot ne ramassait longtemps que ce
qu'il piétinait, ce qui rendait toute mesure sur l'économie des objets muette.
Il fait maintenant un détour vers l'objet connu le plus proche ; doubler ou
tripler le poids de l'onigiri ne change toujours rien à ses résultats, ce qui
suggère que le mur est ailleurs (le combat) — à confirmer en jouant.

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
| 4 | Profondeur récompensée : 30 étages, XP et monstres à l'échelle | ✅ fait |
| 5 | Fin de run + `RunSummary` | ✅ fait |
| 6 | `Meta` + sauvegarde JSON ; la boucle est bouclée | à faire |
| 7 | Le hub après la mort (bilan, méta, « nouveau run ») | à faire |
| 8 | L'orbe (soft reset) et l'entrepôt | à faire |
| 9 | Déblocages en table | à faire |

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

## Les deux boucles

```
        ┌──────────── run ────────────┐
        │  descendre, pratiquer,      │
        │  monter ses compétences     │
        └──────┬───────────────┬──────┘
               │ mort          │ orbe (soft reset)
               ▼               ▼
        niveau global      étage 1, on garde
        + entrepôt         objets ET niveaux
        (tout est perdu)   (aucun gain de méta)
```

**L'orbe, façon R Key d'Isaac.** On repart au premier étage en conservant
objets et niveaux de compétences : les étages du haut deviennent triviaux et on
descend plus bas qu'au tour précédent. Le prix : **aucune progression du niveau
global**. C'est un soft reset dans le run, imbriqué dans le hard reset qu'est la
mort.

Ce choix est architecturalement gratuit : le run ne se termine pas, il
redémarre. Rien à sérialiser, et `Meta` reste alimenté uniquement par la mort —
la frontière tient sans effort.

L'orbe est un objet trouvé dans le donjon, rare et plutôt profond, invisible
tant que le méta ne l'a pas débloqué. Il ne rend ni PV ni satiété : l'utiliser à
l'agonie reste un pari.

**Conséquence assumée :** le donjon passe à 30 étages. Un donjon qu'on termine
en un passage ne laisserait nulle part où aller après un usage de l'orbe. Le run
se juge donc à l'étage le plus profond atteint (`RunSummary.deepest`, suivi
séparément de `depth` puisque l'orbe fait revenir à 1).

## Règles fixées en cours de route

**Descendre paie.** L'XP par action est multipliée par
`1 + 0.15 × (étage − 1)` : à l'étage 11, une même action rapporte 2,5 fois plus.
Sans ça, le méta venant des niveaux de compétences, la stratégie optimale
serait de tourner en rond au premier étage jusqu'à épuiser l'estomac, mourir, et
recommencer — sans aucun risque. Les monstres s'endurcissent en parallèle
(`monster_scaling`, +6 % par étage), sans quoi le bestiaire, qui s'arrête à
l'étage 8, laisserait 22 étages sans difficulté.

Mesuré : le bot atteint l'étage 6 en médiane, 8 au mieux, sur 120 graines. Il
reste donc 22 étages de marge pour ce que la progression permanente ouvrira.

**Le repos.** Deux vitesses de régénération : 1 PV tous les 8 tours en agissant,
tous les 3 tours à l'arrêt (`RunConfig.regen_interval` et
`rest_regen_interval`). S'arrêter convertit donc la nourriture en PV près de
trois fois mieux que marcher — c'est ce qui fait du repos une décision et pas
un raccourci clavier. La commande `cmd_rest` patiente jusqu'à guérison et
s'interrompt d'elle-même (guéri, blessé, affamé, monstre en vue) ; elle refuse
même de commencer si un monstre est visible. La compétence `récupération`,
entraînée uniquement quand le repos soigne réellement, raccourcit l'intervalle
de repos — jamais celui de la marche.

*Première intention corrigée en route :* j'avais d'abord accéléré la
régénération globale (1 PV / 4 tours). Mesure faite, le bot ne se reposait
jamais — il guérissait déjà en marchant, donc « s'arrêter pour se soigner »
n'était pas une technique. D'où les deux vitesses.

**Ce que ça vaut, mesuré :** à profondeur 5, le bot gagne 78 fois sur 120 en se
reposant contre 81 en s'en privant. Le repos reste donc **défavorable à qui
court après l'escalier** : la nourriture est l'horloge du run, et acheter des PV
avec raccourcit la descente plus que les PV ne la sécurisent. C'est un outil de
détresse, pas une routine — ce qui se défend (Shiren aussi fait payer le repos
cher), mais si on veut en faire une routine, le levier est l'abondance de
nourriture, pas le taux de régénération.

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
