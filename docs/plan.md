# Plan : donjon mystère incrémental

L'état courant, la frontière, les contraintes. À relire au début de chaque
session de travail. Le récit — comment on y est arrivé, ce qu'on a mesuré, ce
sur quoi on est revenu — est dans `journal.md`, et chaque étape ci-dessous y
renvoie.

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
| Source de l'XP permanente | **Les niveaux de compétences** accumulés dans le run |
| Emploi de l'XP | **Un arbre de talents** : on choisit, les choix sont définitifs |
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
| 2 | [Table des compétences + XP (`skills.py`)](journal.md#étapes-2-et-3--livrées-ensemble) | ✅ fait |
| 3 | [Pipeline de stats ; suppression du niveau global de run](journal.md#étapes-2-et-3--livrées-ensemble) | ✅ fait |
| 4 | Profondeur récompensée : 30 étages, XP et monstres à l'échelle | ✅ fait |
| 5 | Fin de run + `RunSummary` | ✅ fait |
| 6 | [`Meta` + sauvegarde JSON ; la boucle est bouclée](journal.md#étape-6--la-boucle-telle-quelle-tourne) | ✅ fait |
| 7 | [Le refuge : un lieu où l'on marche, avec son coffre](journal.md#étapes-7-et-8--le-refuge-le-coffre-lorbe) | ✅ fait |
| 8 | [L'orbe : remonter au refuge avec ses acquis](journal.md#étapes-7-et-8--le-refuge-le-coffre-lorbe) | ✅ fait |
| 9 | [L'arbre des talents : le jeu entier se déverrouille](journal.md#étape-9--larbre-déverrouille-le-jeu) | ✅ fait |
| 10 | [Familles et classes de créatures ; ce qu'on apprend, le donjon l'apprend](journal.md#étape-10--familles-classes-et-le-couplage-qui-les-paie) | ✅ fait |
| 11 | [L'archer : le tir, et ce qu'il change au déplacement](journal.md#étape-11--larcher) | ✅ fait |
| 12 | [L'esquive : encaisser ou se dérober, deux runs différents](journal.md#étape-12--lesquive-et-deux-façons-de-traverser-un-run) | ✅ fait |
| 13 | [Le butin des créatures, et la compétence « Chance »](journal.md#étape-13--le-butin-et-la-chance-qui-sy-entretient) | ✅ fait |
| 14 | [Retours de partie : sept bugs, pierres, nœuds répétables, exploration](journal.md#étape-14--ce-quune-vraie-partie-a-révélé) | ✅ fait |
| 15 | [Le lot interface : fiches justes, bulle, action unique, stèle, piles](journal.md#étape-15--le-lot-interface) | ✅ fait |
| 16 | [La monnaie du méta devient l'XP investie, et non la somme des niveaux](journal.md#étape-16--la-monnaie-du-méta-devient-lxp-investie) | ✅ fait |
| 17 | [Le bus de déclencheurs : tout contenu devient de la donnée](journal.md#étape-170--un-filet-quil-a-fallu-mesurer-avant-dy-croire) | ✅ fait |
| 18 | [La monnaie devient l'effort : un pas ne vaut plus un coup](journal.md#étape-18--leffort-et-la-marche-qui-redescend-de-60--à-26-) | ✅ fait |
| 19 | [L'arme devient forme × matière](journal.md#étape-191--la-matière-et-ce-quelle-ne-donne-jamais) | ✅ fait |
| 20 | [Dix retours de partie, et l'éventail qui ne peut plus grandir](journal.md#étape-20--dix-retours-de-partie-dont-un-qui-bloque-tout-le-reste) | ✅ fait |
| 21 | [La stèle se promène, et l'arbre se découvre](journal.md#étape-21--la-stèle-se-promène-et-larbre-se-découvre) | ✅ fait |
| 22 | [Les matières s'achètent, et ce que ça coûte au pivot](journal.md#étape-22--les-matières-sachètent-et-ce-que-ça-coûte-au-pivot) | ✅ fait |

Chaque étape laisse le jeu lançable et jouable.

### Étape 17 — le bus de déclencheurs

L'audit, le plan en six temps et les décisions ouvertes sont dans
[`chantier-declencheurs.md`](chantier-declencheurs.md) ; les deux formes
comparées avant de choisir sont dans
[`effets-reactions.md`](effets-reactions.md).

| | | |
|---|---|---|
| 17.0 | [Le filet : seize parties, seize empreintes](journal.md#étape-170--un-filet-quil-a-fallu-mesurer-avant-dy-croire) | ✅ fait |
| 17.1 | [L'interception : les treize points de lecture deviennent des questions](journal.md#étape-171--linterception--le-moteur-pose-des-questions) | ✅ fait |
| 17.2 | [Toute mutation passe par le moteur](journal.md#étape-172--cinq-portes-et-le-moteur-seul-à-les-franchir) | ✅ fait |
| 17.3 | [Ces méthodes publient](journal.md#étape-173--les-cinq-portes-publient) | ✅ fait |
| 17.4 | [Les garde-fous](journal.md#étape-174--deux-garde-fous-qui-nont-encore-rien-à-garder) | ✅ fait |
| 17.5 | [Le porteur générique](journal.md#étape-175--le-porteur-générique) | ✅ fait |
| 17.6 | [Le bâton de pyromancie : cinq points de moteur, et pourquoi](journal.md#étape-176--le-bâton-de-flammes-et-le-compte-exact) | ✅ fait |
| 17.7 | [Le bâton rejoint l'arbre](journal.md#le-bâton-rejoint-larbre--et-une-mesure-qui-se-dégonfle) | ✅ fait |

### Étape 19 — forme × matière

La forme dit *comment on frappe* et porte les chiffres ; la matière dit *sur
quoi ça mord* et n'en porte **aucun**. Le pivot ne coûte rien d'artificiel : il
coûte parce que les familles se répartissent en profondeur et que chaque coup
entraîne deux compétences.

| | | |
|---|---|---|
| 19.1 | [L'axe des matières : deux formes, cinq matières](journal.md#étape-191--la-matière-et-ce-quelle-ne-donne-jamais) | ✅ fait |
| 19.2 | [Les trois autres formes, et le coût d'un coup](journal.md#étape-192--les-trois-autres-formes-et-le-coût-dun-coup) | ✅ fait |
| 19.3 | [Le bot apprend à pivoter, et la mesure répond autre chose](journal.md#étape-193--le-bot-apprend-à-pivoter-et-la-mesure-répond-autre-chose) | ✅ fait |

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
tant que le méta ne l'a pas débloqué. Il ramène au refuge, et non à l'étage 1. Il ne rend ni PV ni satiété : l'utiliser à
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

## Retours de partie intégrés

- **Parchemins non identifiés.** Leur apparence est tirée au sort à chaque run
  (`items.Registre`) ; les essayer les identifie pour tous les exemplaires du
  run. C'est de l'état de run, donc perdu à la mort. Rendre une identification
  permanente serait un champ dans `Meta` — à décider quand les potions
  arriveront, elles suivront le même chemin (une ligne dans `APPARENCES`).
- **Consommables ramassés au passage**, sans coûter de tour. L'équipement reste
  un choix délibéré, pour ne pas encombrer le sac.
- **Prochain avantage affiché**, pour les compétences comme pour le niveau
  global : les tables savaient déjà ce qu'elles donnaient, il suffisait de le
  dire.
- **Le sac s'efface pendant la visée**, sinon on ne voit pas où l'on lance.
- Les largeurs de panneaux sont mesurées par la police et non estimées au
  nombre de caractères — c'est ce qui faisait déborder les chiffres.

## Dette assumée

- `bouclier` s'entraîne en encaissant : c'est le seul évènement (`coup_recu`)
  que le héros ne déclenche pas lui-même. Assumé — on apprend à parer en se
  faisant frapper.
- Aucune compétence de magie n'existe encore : le jeu n'a ni bâton ni sort.
  Pyromancie et cryomancie viendront avec le contenu correspondant, chacune
  en une entrée de table.

## L'éventail, et la place qu'il lui reste

Il a été bloqué net à l'étape 20 : 27 nœuds, 1,6 pixel de marge, et un
vingt-huitième le faisait déborder. L'étape 21 l'a rouvert par un **zoom pur**
(les deux rayons multipliés par 1,5, seule transformation qui aère sans changer
un seul angle) et un **déplacement à la souris**, l'éventail étant désormais
plus grand que la fenêtre.

Les quatre nœuds de matière ont repris ces huit nœuds dès l'étape 22, et le
test de marge a fait son travail : il a échoué **avant** que deux ronds se
touchent, en disant quoi faire. Facteur monté à 1,75, huit nœuds de marge à
nouveau. C'est la boucle telle qu'elle doit tourner — quand ils ne suffiront
plus, c'est ce facteur qu'il faudra monter, et le commentaire de
`TALENT_RAYON_DERNIER` porte la table de ce que chaque cran coûte en
lisibilité.

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
- Toute refonte du moteur qui se dit « à comportement identique » doit laisser
  les **seize empreintes** de `tests/test_empreintes.py` intactes. Les
  regénérer sans dire pourquoi dans le journal, c'est retirer le filet.
- Un filet se mesure avant qu'on s'y fie : la première version des empreintes
  ne couvrait ni la pose, ni le jet, ni aucune des quatre bornes du moteur.
- **Un instrument se vérifie avant qu'on lise ses chiffres.** Le bot est
  l'instrument de mesure du projet : tant qu'il ne sait pas faire une chose, il
  ne mesure rien de cette chose — il mesure sa propre cécité. Douze tests
  tiennent sa décision d'armement (`tests/test_pivot.py`) avant qu'on croie un
  seul chiffre de distribution des matières.
- **Un écart sous deux sigma n'existe pas, et se dégonfle en doublant
  l'échantillon.** Quatre fois de suite, un écart mesuré entre 1,7 et 1,9 σ
  est retombé sous 1,3 σ en doublant le nombre de vies. Une mesure unique ne
  vaut jamais une décision.
