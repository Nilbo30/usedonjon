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
| 2 | Table des compétences + XP (`skills.py`) | ✅ fait |
| 3 | Pipeline de stats ; suppression du niveau global de run | ✅ fait |
| 4 | Profondeur récompensée : 30 étages, XP et monstres à l'échelle | ✅ fait |
| 5 | Fin de run + `RunSummary` | ✅ fait |
| 6 | `Meta` + sauvegarde JSON ; la boucle est bouclée | ✅ fait |
| 7 | Le refuge : un lieu où l'on marche, avec son coffre | ✅ fait |
| 8 | L'orbe : remonter au refuge avec ses acquis | ✅ fait |
| 9 | L'arbre des talents : le jeu entier se déverrouille | ✅ fait |
| 10 | Familles et classes de créatures ; ce qu'on apprend, le donjon l'apprend | ✅ fait |
| 11 | L'archer : le tir, et ce qu'il change au déplacement | ✅ fait |
| 12 | L'esquive : encaisser ou se dérober, deux runs différents | ✅ fait |
| 13 | Le butin des créatures, et la compétence « Chance » | ✅ fait |
| 14 | Retours de partie : sept bugs, pierres, nœuds répétables, exploration | ✅ fait |
| 15 | Le lot interface : fiches justes, bulle, action unique, stèle, piles | ✅ fait |

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
tant que le méta ne l'a pas débloqué. Il ramène au refuge, et non à l'étage 1. Il ne rend ni PV ni satiété : l'utiliser à
l'agonie reste un pari.

**Conséquence assumée :** le donjon passe à 30 étages. Un donjon qu'on termine
en un passage ne laisserait nulle part où aller après un usage de l'orbe. Le run
se juge donc à l'étage le plus profond atteint (`RunSummary.deepest`, suivi
séparément de `depth` puisque l'orbe fait revenir à 1).

### Étape 6 — la boucle, telle qu'elle tourne

**Conversion.** `XP méta = niveaux de compétences × (1 + 0,1 × (étage − 1))`,
l'étage étant le plus profond du passage en cours. C'est ce facteur qui fera de
l'orbe un pari : mourir plus haut qu'avant rapportera moins, même mieux
entraîné.

| Scénario | Niveaux | Facteur | Méta |
|---|---|---|---|
| Mort au 12, sans orbe | 20 | ×2,1 | 42 |
| Orbe au 12, mort au 8 | 26 | ×1,7 | 44 |
| Orbe au 12, poussé au 16 | 30 | ×2,5 | 75 |

**Qui parle à qui.** `Game` ignore toujours l'existence de `Meta` — un test
lit le source de `game.py` pour s'en assurer. C'est `Session` (session.py) qui
fait le lien : elle construit la `RunConfig` depuis le méta, et encaisse le
`RunSummary` à la fin. Les interfaces ne connaissent qu'elle.

**Sauvegarde** : `~/.usedonjon/meta.json`. Un fichier absent, corrompu ou
partiel donne une progression neuve plutôt qu'un plantage. Les modes `--script`
et `--auto` n'y touchent jamais : ce sont des outils de test, ils n'ont pas à
faire progresser un joueur.

**Rythme mesuré**, campagne de 40 runs enchaînés par le bot :

| Runs | Étage moyen atteint |
|---|---|
| 1-10 | 5,0 |
| 11-20 | 6,8 |
| 21-30 | 6,7 |
| 31-40 | 7,3 (record : 11) |

Le premier niveau global tombe après deux runs, le huitième après quarante.
La courbe monte puis s'aplatit — c'est le moment où l'orbe et les déblocages
devront prendre le relais.

### Étapes 7 et 8 — le refuge, le coffre, l'orbe

**Le refuge est un étage comme un autre**, pas un menu : même carte, même
déplacement, même souris. Ce qui le distingue tient dans sa `RunConfig` —
`is_hub`, pas de faim, pas de monstres. Ajouter un marchand plus tard sera
poser quelque chose dans cette pièce.

**La `Session` possède le héros.** C'est le changement d'architecture qu'a
demandé le refuge : `Game` accepte un joueur au lieu d'en fabriquer un, ce qui
lui permet de traverser refuge et donjon avec son sac, ses compétences et ce
qu'il a identifié. Une vie = un héros ; une descente = un `Game`.

Trois façons de clore une partie, trois suites :

| Fin | Ce qu'on garde | Méta |
|---|---|---|
| Mort / victoire | rien (sauf le coffre) | oui, sur la descente qui vient de finir |
| Orbe (`retour`) | tout : sac, compétences, identifications | **non** |
| Escalier du refuge | — | — |

**L'orbe** est un objet trouvé à partir de l'étage 4. Il clôt la descente et
renvoie au refuge. Comme chaque descente est un `Game` neuf, la profondeur
repart de 1 — le pari est structurel, pas une règle ajoutée : la mort suivante
ne comptera que la nouvelle descente. Il ne rend ni PV ni satiété.

**Le coffre** vit dans `Meta` (donc sur disque) : huit places, les objets y
survivent à la mort avec leur bonus. C'est la seule matière qui traverse.

Détail savoureux : l'orbe étant un parchemin, il arrive **non identifié**.
Le reconnaître est en soi une étape.

### Étape 9 — l'arbre déverrouille le jeu

La progression linéaire a été remplacée par un **arbre de talents** (tree.py),
et l'idée est allée plus loin que des bonus chiffrés : **le jeu entier se
déverrouille**. La première vie se joue dans un couloir vide où l'on meurt de
faim ; l'équipement, les créatures, les objets au sol, le coffre du refuge,
l'orbe — tout se gagne un nœud à la fois.

Ce qui rend la chose viable, mesuré :

| État du jeu | XP par vie |
|---|---|
| Donjon vide | 4,5 |
| + monstres | 6,0 |
| + kit de départ | 14,0 |
| + objets au sol | 15,9 |

**Chaque déblocage augmente le débit**, donc accélère le suivant : c'est le
moteur d'un incrémental, et il sort des données plutôt que d'une règle.

Deux choses que la mesure a dictées :

- une vie vide dure 124 tours, soit **~40 secondes** en clic-déplacement — le
  prologue est une vignette, pas une corvée. Le déplacement automatique à la
  souris, fait bien avant, sauve cette idée sans qu'on l'ait cherché ;
- **les créatures viennent avant l'équipement**, et non l'inverse. J'avais
  d'abord conclu le contraire en lisant mal ma propre mesure : les monstres sans
  arme rapportent 6 XP contre 4,5 à vide, c'est-à-dire *plus*, et j'avais retenu
  « on meurt à l'étage 3 » pour en déduire « c'est pire ». Une campagne complète
  a tranché : l'ouverture va aussi vite dans les deux sens (Fouille à la vie 9),
  mais l'ordre inverse est absurde à jouer — on obtient une épée sans rien à
  frapper. Le danger d'abord, sa réponse ensuite ; les deux vies à mains nues
  entraînent le pugilat, qui existe depuis l'étape 2.

**Échelle des prix** : 3 · 12 · 35 · 90 · 220, calée sur les 4,2 XP de la
première mort — le premier talent tombe dès la première vie. Un test le
verrouille, sinon le jeu s'ouvrirait sur deux vies vides avant le moindre choix.

**Rythme observé** : Estomac (vie 1) · Constitution (2) · Besace (4) ·
**Créatures** (6) · **Barda** (8) · **Fouille** (9), puis accélération.

**Comment on ajoute du contenu**, désormais : un nœud dans `tree.py`, et un
`unlock="..."` sur les objets concernés. Les baguettes seront deux lignes de
données. `RunConfig()` construite à la main garde tout — c'est le chemin du
méta, et lui seul, qui verrouille.

**L'affichage est un éventail**, pas une liste. Le centre porte l'XP
disponible, chaque branche s'ouvre en rayons, et un nœud s'éloigne du centre
d'un cran par prérequis.

Rien n'est placé à la main, et c'est un découpage emboîté : une branche reçoit
une part de l'ouverture proportionnelle à la place qu'il lui faut — son rang le
plus chargé, ramené à son rayon — puis, *dans* cette part, un nœud prend le
centre de la sienne et ses enfants se partagent cette même part au prorata de
leurs feuilles. Un enfant ne peut donc pas sortir du secteur de son parent :
**aucun trait ne se croise à l'intérieur d'une branche**, par construction.

Restent les prérequis qui traversent l'éventail — Barda derrière Créatures, la
voie du retour derrière Grimoires *et* le coffre. Ceux-là dépendent de l'ordre
des branches, et l'ordre a été cherché plutôt que deviné : sur les 720
permutations possibles, plusieurs donnent zéro croisement, et
`Survie · Monde vivant · Équipement · Le refuge · Profond · Trouvailles` est
celle qui garde en plus l'ordre où le joueur découvre les trois premières.

Trois tests le tiennent : les ronds ne se touchent pas, aucun trait n'en croise
un autre (si ça tombe après l'ajout d'un nœud, c'est `BRANCHES` qu'il faut
revoir), et `len(places) == len(ARBRE)` — un nœud rangé dans une branche absente
de `BRANCHES` disparaîtrait sans bruit.

**Rupture de sauvegarde assumée** : `Meta.level` et `BONUS` ont disparu au
profit de `xp` / `xp_totale` / `noeuds`. Les anciennes sauvegardes repartent de
zéro. Un talent inconnu dans un fichier (version antérieure ou future) est
ignoré plutôt que fatal.

### Étape 10 — familles, classes, et le couplage qui les paie

Le bestiaire était une liste de six blocs figés où le « Sorcier bleu » portait
à la fois son espèce, ses chiffres, son comportement et son nom. Il devient un
croisement à deux axes :

* la **famille** — animal, humanoïde, homoncule — dit ce qu'est la créature :
  son allure, les étages où on la croise, et bientôt ses forces et faiblesses ;
* la **classe** — rôdeur, erratique, embusqué, guerrier, blindé — dit ce qu'elle
  fait : son comportement (`ai.py`) et le talent qui la réveille.

Les chiffres restent écrits à la main, créature par créature : un bestiaire se
règle à l'oreille, pas au produit de deux multiplicateurs. Les axes portent le
sens, pas l'arithmétique. La bascule a été vérifiée à l'empreinte : md5
identique sur huit parties scriptées, `4fde85d8bf3105dd3f0e5c8d648f2f5f`.

**La règle du couplage**, et c'est elle qui vaut l'étape : *ce que le héros
apprend, le donjon l'apprend aussi*. Un nœud ne vend jamais des monstres — il
vend un outil, et la classe qu'il réveille vient avec.

| Le nœud donne | Le donjon apprend |
|---|---|
| l'épée | le **guerrier** — frappe fort, on choisit ses combats |
| le bouclier | le **blindé** — encaisse, il faut frapper plus fort ou fuir |
| les herbes | l'**embusqué** — frappe puis se retire pour souffler |

Cela répond à une question posée pendant la conception : *si le rat est
l'ennemi le plus facile, qu'est-ce qui empêche de ne jamais acheter le reste ?*
Trois réponses, dans l'ordre de force :

1. **On n'achète pas les monstres**, donc on ne peut pas les refuser sans
   refuser sa propre puissance.
2. **Le donjon ne s'adoucit pas** : quand aucune créature réveillée n'habite un
   étage, `table_for_depth` rappelle les plus proches au lieu de vider l'étage,
   et `_scale_to_depth` les met à niveau. Sans ce repli, ne rien débloquer
   serait la stratégie optimale — un donjon désert où l'on descend encaisser le
   multiplicateur de profondeur.
3. **Le revenu plafonne** : la monnaie du méta est la somme des niveaux de
   compétences, et une classe qu'on n'a jamais réveillée est une compétence
   qu'on ne pratique pas.

**Le critère d'acceptation** est chiffré : après chaque achat, l'XP par vie doit
monter. Il a immédiatement condamné deux nœuds.

| État | XP/vie |
|---|---|
| donjon vide | 4,5 |
| + créatures | 5,8 |
| + l'épée | 8,7 |
| + le bouclier | 11,6 |
| + nourriture | 24,0 |

« Faune variée » (23,1 → 21,3) ne donnait rien au joueur : rien qu'une densité
de monstres plus forte. **Supprimé** — sous cette grammaire, aucun nœud n'a le
droit de n'apporter que du danger. Sa classe d'embusqués est passée aux herbes,
dont elle est le miroir. « Butin », qui promettait un contenu inexistant, est
sorti de l'arbre en attendant l'étape 11.

**Deux leçons de méthode**, plus utiles que les chiffres :

*L'instrument avant la conclusion.* Les nœuds d'objets semblaient tous faire
reculer l'XP. Vérification faite, **le bot ne s'équipait jamais** : il ramassait
l'épée en fer et continuait à cogner avec celle en bois. Mesurer « Armurerie »
avec ce bot-là, c'était mesurer sa cécité. Corrigé (`_a_mieux_en_main`).

*Le bruit avant le signal.* Même corrigé, la série semblait reculer trois fois
de suite. Avec 80 parties et une marge d'erreur, la vérité est plus plate :
21,0 ± 1,2 → 19,6 ± 0,9 → 18,8 ± 1,0 → 19,9 ± 0,9. **Ces écarts ne sont pas
significatifs** ; j'avais lu du bruit comme du signal, exactement le travers que
je m'étais promis d'éviter. Reste un effet réel : chaque famille d'objets
débloquée diluait la nourriture dans un nombre de trouvailles constant —
acheter du contenu faisait mourir de faim. Chaque famille ajoute désormais
+1 trouvaille par étage, ce qui a demandé que les effets sachent s'additionner
terme à terme (`Meta._somme`).

**« Nourriture » plutôt que « Fouille ».** Le nœud qui ouvre les trouvailles
porte désormais son objet : les vivres passent derrière un verrou `vivres`, et
les flèches derrière `projectiles` — leur nœud à elles, qui accueillera la
classe des archers (*tu apprends à lancer, le donjon aussi*). C'est le seul
nœud de l'arbre qui n'amène aucune menace : un répit assumé.

Ce découpage a révélé un défaut bien plus grave que ceux d'avant, invisible
tant que la nourriture n'était pas verrouillée : **la part de nourriture dans
le tirage s'effondre à mesure qu'on débloque des familles** — 100 %, puis 26 %
avec les herbes, puis 11,7 % une fois tout ouvert. Trois vivres par étage
devenaient moins d'un. Le +1 trouvaille par famille ne compensait rien du tout ;
acheter du contenu affamait. Corrigé d'abord par une garantie : un vivre posé d'office à chaque étage. Ça
marchait, et c'était **trop mécanique** — « il y a toujours un onigiri quelque
part » se sent en jouant, et un étage doit pouvoir être avare. La garantie est
donc statistique et non plus par étage : **la nourriture ne descend jamais sous
30 % du tirage**, quel que soit le nombre de familles ouvertes. C'est un
plancher, pas une part fixe — quand peu de choses sont débloquées, les vivres
gardent la part plus large qui leur revient naturellement (100 % au début, 54 %
avec les projectiles).

Résultat une fois tout ouvert : 0,81 vivre par étage en moyenne, et **39 % des
étages n'en portent aucun**. La faillite disparaît, la peur reste.

| État | avant | après le plancher |
|---|---|---|
| épée + bouclier | 11,9 ± 0,4 | 11,9 ± 0,4 |
| + nourriture | 24,0 ± 1,3 | 24,0 ± 1,3 |
| + projectiles | 27,5 ± 1,4 | 27,5 ± 1,4 |
| + herbes | 23,3 ± 1,4 | 24,8 ± 1,3 |
| + grimoires | 20,9 ± 1,1 | 24,5 ± 1,2 |
| + armurerie | 20,6 ± 1,0 | 27,2 ± 1,4 |
| + abondance | — | 28,4 ± 1,4 |

La règle passe l'épreuve du temps long : la part n'est pas un poids réglé à la
main mais une proportion recalculée sur le tirage du moment, donc elle tient à
1, 5, 50 ou 200 familles d'objets ajoutées (test à l'appui). Deux limites à
garder en tête : elle ne protège **que** la nourriture — si un autre objet
devenait vital, il lui faudrait son propre plancher, et la forme générale serait
une table `{catégorie: part minimale}` — et elle suppose que les vivres à venir
portent bien la catégorie `FOOD`, faute de quoi ils compteraient comme de la
dilution.

Un détour instructif au passage : une part *fixe* de 30 % faisait chuter l'état
« + projectiles » de 27,5 à 21,9, parce qu'à deux objets débloqués la part
naturelle des vivres (54 %) est bien supérieure au seuil. Une règle qui protège
doit être un plancher, jamais un plafond déguisé.

Plus aucun recul ne survit à la marge d'erreur, « Abondance » compris : la
question laissée ouverte plus haut se referme, et sa cause était la même.

Le bot lance désormais ses flèches sur une cible alignée (`_tir_possible`) : la
même précaution que pour l'équipement, prise avant de mesurer un talent de
projectiles plutôt qu'après.

**Rythme observé** : Estomac (vie 1) · Constitution (2) · Besace (4,3) ·
Créatures (6,3) · **L'épée** (8,3) · **Le bouclier** (9,5) · Nourriture (10,7).
C'est l'ordre du bot, qui prend toujours le moins cher : un joueur qui voit que
« Nourriture » double son revenu la prendra bien plus tôt. Le choix existe,
c'est ce qui compte.

### Étape 11 — l'archer

La première créature qui peut te toucher **sans t'approcher**. Elle arrive avec
le nœud « Projectiles », qui te donne les flèches : *tu apprends à lancer, le
donjon aussi*. Un arc viendra plus tard comme amélioration de ce nœud — les
objets à lancer, eux, restent : les retirer priverait le héros de sa seule
réponse à distance et casserait le miroir.

**Le comportement** : il tire dès que tu es sur sa ligne (huit directions,
portée 7), et sinon **se décale d'un pas pour t'y mettre**. Une tourelle
immobile se contourne et cesse d'exister ; celui-ci rend les couloirs
dangereux et apprend à casser l'alignement. Il ne tire jamais à travers un des
siens, donc **se mettre derrière une autre créature est un abri réel**.

Le moteur y gagne une seule fonction, `ligne_de_tir`, partagée par le jet du
héros et le tir des créatures — et comme elle s'arrête au premier acteur, la
créature qui passe devant prend le trait à ta place.

**Ce que la mesure a corrigé** : à sa fréquence naturelle, l'archer mangeait
tout le gain de son nœud.

| fréquence à l'étage 5 | XP/vie |
|---|---|
| 21 % des apparitions | 22,9 ± 1,1 |
| 15 % | 23,6 ± 1,3 |
| **11 %** | **25,0 ± 1,3** |
| 9 % | 26,4 ± 1,4 |

Le nœud sans archers valait 27,5 ; le donjon sans le nœud, 24,0. Retenu : 11 %,
soit un archer croisé régulièrement sans qu'il occupe le donjon. Aucune de ces
paires n'est significative prise seule — c'est la **monotonie de la série** qui
tranche, pas un écart isolé.

### Étape 12 — l'esquive, et deux façons de traverser un run

La compétence qui accompagne l'archer, mais elle vaut de près comme de loin :
elle annule un coup entièrement, quelle qu'en soit la provenance.

**Elle est le pendant exact de « épée / pugilat », côté défense.** Le jeu avait
déjà la moitié du mécanisme : ce qu'on porte décide de ce qu'on apprend. Le
bras nu ouvre donc `shield_skill = "esquive"` comme la main vide ouvre
`weapon_skill = "pugilat"` — aucun nouveau rouage, une ligne dans `entities.py`
et deux règles symétriques :

```python
Regle(events.COUP_RECU, "bouclier", si=lambda e: e["bouclier"] is not None),
Regle(events.COUP_RECU, "esquive",  si=lambda e: e["bouclier"] is None),
```

**Comment elle monte** : en encaissant sans bouclier — et surtout **en se
déplaçant sous la menace**, un monstre à portée ou un archer qui te tient dans
sa ligne. La première source seule ne suffisait pas : on n'apprend pas à se
dérober en encaissant, puisque encaisser est ce qui tue. La seconde récompense
le déplacement plutôt que l'endurance, ce qui est exactement le geste qu'on veut
apprendre au joueur.

**Le pari a fallu le construire, pas le déclarer.** Premier réglage : 16,1
XP/vie au bras nu contre 27,3 avec bouclier. Le pari n'existait pas — je
comparais « bouclier + compétence » à « compétence seule », alors qu'une esquive
doit remplacer *l'objet* : un bouclier en fer donne +6 de défense dès qu'on le
ramasse, quand la compétence plafonnait au niveau 1,2.

| réglage | bras nu | niveau atteint |
|---|---|---|
| 0,03/niveau, plafond 40 % | 16,1 ± 1,1 | 1,2 |
| 0,05, et l'XP en bougeant | 21,8 ± 1,4 | 3,8 |
| 0,07, plafond 50 % | 22,1 ± 1,3 | 3,9 |
| **0,09, plafond 55 %** | **24,4 ± 1,7** | 4,0 |

Contre 27,3 ± 1,5 pour le bouclier : **89 %**. Pas la parité — le bouclier
trouvé reste meilleur, et c'est juste — mais une vraie autre façon de jouer.

**Une fuite attrapée au passage** : la règle « bouger sous la menace » ne
regardait pas le bras. Le run avec bouclier entraînait donc l'esquive sans
jamais s'en servir, et comme le méta compte la somme des niveaux, il gagnait de
l'XP pour une compétence morte — 27,3 → 32,8. Une compétence qui monte sans
servir est de l'inflation, pas de la progression.

### Étape 13 — le butin, et la chance qui s'y entretient

Le nœud « Butin » revient dans l'arbre, cette fois avec quelque chose derrière.
La table tient sur les deux axes du bestiaire, comme prévu de longue date :

> **la classe lâche son outil, la famille lâche sa matière.**

L'archer laisse ses flèches, le guerrier son épée, le blindé sa plaque,
l'embusqué son parchemin de téléportation ; l'animal laisse de la viande,
l'humanoïde ses provisions, l'homoncule une herbe de vie. Douze créatures, deux
tables de quatre lignes, et chaque famille ou classe ajoutée remplit ses cases
toute seule.

**Une créature ne peut jamais lâcher ce que le donjon n'a pas ouvert.** L'archer
laisse ses flèches précisément parce que le talent qui l'a réveillé est celui
qui met des flèches au sol : la boucle se referme sur elle-même. Un gobelin tué
par un joueur qui n'a pas « Nourriture » ne laisse pas de vivres.

**La compétence « Chance »** monte en trouvant du butin et augmente la chance
d'en trouver : elle s'entretient de ce qu'elle produit. C'est la première
boucle positive du jeu, donc la première à devoir être plafonnée — le moteur
borne le tirage à 60 %, sans quoi un run chanceux le deviendrait de plus en
plus. Premier réglage : elle atteignait le niveau 0,3 en moyenne, c'est-à-dire
qu'elle n'existait pas. Recalée (base 2, +3 % par niveau), elle atteint 1,0 en
moyenne et 3 dans les bons runs.

| | XP/vie |
|---|---|
| sans « Butin » | 27,3 ± 1,5 |
| avec « Butin » | **32,7 ± 1,7** |

### Étape 14 — ce qu'une vraie partie a révélé

Vingt retours après une première session complète. Sept bugs corrigés d'un
coup, dont un qui coûtait cher : **un talent acheté au refuge ne s'appliquait
qu'à la vie suivante**. Le héros n'est créé qu'une fois par vie, et « Affûtage »
ne touchait que le suivant — on payait pour la vie d'après. Les autres : un
message d'accueil qui promettait un coffre non gagné, des créatures qui
apparaissaient dans le champ de vision, un archer qui chargeait au corps à
corps, une chauve-souris qui renonçait à mordre une fois sur trois, les pièges
présents avant leur talent, et une console noire derrière la fenêtre sous
Windows.

**Les pierres remplacent les flèches** comme projectile de base : lancer une
flèche à main nue n'a pas de sens. La flèche reste, avec un **poids de tirage
nul** — elle n'apparaît donc jamais au sol, seulement dans le butin d'un
archer. C'est le mécanisme le plus simple pour un objet qui ne se trouve que
sur un cadavre, et il ne demande aucun code.

**Les nœuds répétables.** `Noeud(repetitions=3)` : le cumul lit la liste des
achats et non un ensemble, donc les effets s'additionnent d'eux-mêmes. « Rien ne
se perd » (10 % de récupérer le projectile qui touche) se reprend trois fois, et
l'éventail affiche « 1/3 » dans le rond au lieu d'une coche.

**L'exploration automatique** devient un talent — l'automatisation est la
signature du genre incrémental, autant qu'elle s'achète. Le moteur choisit la
destination (`prochaine_exploration` : ce qui traîne d'abord, la frontière de
l'inconnu ensuite, l'escalier en dernier), l'interface anime, exactement comme
le déplacement au clic. Elle s'arrête à la première chose qui mérite une
décision.

Un bug pris dans mon propre code au passage : elle visait des objets **pas
encore découverts**, donc injoignables, et abandonnait au lieu de passer à la
frontière. Elle explore maintenant 78 → 207 cases en une trentaine de pas.

**Reste ouvert** : l'XP par vie tourne toujours autour de 35 quoi qu'on fasse —
le gain ne raconte pas la descente. Le joueur continue de jouer pour cerner ce
qui devrait être récompensé.

### Étape 15 — le lot interface

Six retours de jouabilité, tous venus de la même partie.

**La fiche mentait.** Un onigiri annonçait « rend 50 points de ventre » alors
que le moteur en rendait 55 avec Cuisine au niveau 2 : la note était un texte
figé. Elle porte désormais un trou (`{n}`) et l'objet sait calculer sa valeur
dans *ces* mains (`puissance_pour`). Un test vérifie l'essentiel : le chiffre
annoncé est celui que l'effet applique.

**Le panneau du sac sautait sous le curseur** parce que sa hauteur dépendait de
la longueur de la fiche. La fiche devient une bulle posée à côté de la ligne
survolée ; le panneau ne dépend plus que du nombre d'objets.

**Un bouton d'action au lieu de quatre.** Ramasser / Descendre / Coffre /
Attendre étaient quatre boutons dont trois éteints en permanence. Un seul
demeure, dont le libellé dit ce qu'il fera ici — et il partage sa logique avec
le clic sur le héros, qui faisait déjà ce travail.

De même dans le sac : « Utiliser » et « Équiper » fusionnent en une action
évidente (un onigiri se mange, une épée s'équipe), accessible au **double-clic**.

**Une stèle des talents dans le refuge.** L'arbre n'était accessible que par un
bouton ; il a maintenant un objet dans la pièce, comme le coffre — et il est là
dès la première vie, parce qu'un joueur qui ne voit pas la stèle ne sait pas
que l'arbre existe.

**Les munitions s'empilent** (« une pierre ×7 »), plafonnées à 99 pour que le
sac ne devienne pas infini. Lancer n'en détache qu'une, le coffre garde la pile
entière. Le bug de conception s'est révélé dans un test qui bouclait sans fin :
`while add_item(...)` ne terminait plus, puisqu'une pile accepte toujours un
exemplaire de plus. C'est exactement ce que le plafond corrige.

### Deux bugs de la stèle, et une fuite d'XP

**Bloquant** : le panneau des talents se rouvrait dès qu'on le fermait. La règle
disait « si le héros est sur la stèle, ouvrir » — vraie tant qu'on piétine la
case, donc refermer relançait l'ouverture au tour suivant, sans issue. Elle dit
maintenant « **en arrivant** sur la stèle » : la fenêtre retient la case dont
elle a déjà ouvert le panneau et l'oublie quand on s'en éloigne. Le coffre avait
le même défaut, dormant.

**Le refuge entraînait.** Marcher au refuge montait la compétence de marche, et
comme la monnaie du méta est la somme des niveaux, on pouvait acheter l'arbre en
faisant des ronds dans une pièce sans faim ni monstre — le farm exact que le
multiplicateur de profondeur était censé rendre absurde. `xp_multiplier()`
renvoie désormais **zéro** au refuge : on y dépense, on n'y gagne pas.

### Retours de partie, deuxième salve

**Le trajet à la souris s'arrêtait devant les portes** — et la cause était plus
large qu'une porte. Le calcul de chemin exemptait la case d'arrivée de *toutes*
les vérifications, occupation **et** géométrie, pour permettre de viser un
monstre. Le dernier pas pouvait donc couper l'angle d'un mur, le moteur le
refusait ensuite, et le héros restait planté sans explication : **10 962 cases
concernées** sur 200 étages. La géométrie est désormais séparée du reste et ne
souffre aucune exception.

Deux tests ont chuté au passage, et tous deux parce que le correctif améliore le
jeu : un monstre bloqué derrière un angle sait maintenant faire le tour (le test
comptait sur son incapacité), et le compteur de tours du bot retarde d'un cran
sur l'horloge d'énergie (le test traquait la mauvaise grandeur — c'est l'action
refusée qui trahit un bot qui tourne à vide, pas l'horloge).

**Les pâtés de couloir.** Deux tracés en L qui se recouvrent laissaient une
flaque de couloir large de deux cases — 35 sur 200 étages. Un dégraissage rend
au mur la case dont personne n'a besoin, en vérifiant à chaque fois que l'étage
reste d'un seul tenant.

**Les nœuds de statistiques deviennent répétables**, avec un prix qui grimpe :
`facteur_cout=3` donne 3, 9, 27, 81 XP pour quatre reprises. « Ventre d'ogre »
et « Endurci » disparaissent — ils n'étaient que la deuxième marche d'un
escalier que le nœud sait maintenant monter seul. Sans cette montée du prix, un
nœud répétable serait une aubaine sans hésitation.

**« Second souffle » devient une vraie réanimation** : une fois par descente, le
coup fatal ne l'est pas et l'on se relève à mi-vie. La réserve voyage avec le
héros, donc traverse le refuge et se perd avec lui.

**« Nourriture » passe de 12 à 3 XP.** La première vie est un couloir vide où
l'on meurt de faim : sa réponse doit être à portée de la première mort. Le
rythme s'en trouve transformé — Nourriture à la vie 2,8 au lieu de 10,7, et
toute l'ouverture suit.

### Le donjon qui payait le vide

Trois retours, dont un qui a fait tomber un pan du dessin.

**« Créatures » n'avait aucune raison d'être acheté.** C'était le seul nœud qui
n'offrait rien : il ajoutait du danger et attendait qu'on le paie. Il disparaît,
et **« L'épée »** prend sa place — mais elle ne donne plus d'épée : elle en fait
**apparaître** dans le donjon, avec les créatures qui savent s'en servir. Le
nœud arme le monde et le joueur du même geste, à lui d'aller la chercher.
« Armurerie » disparaît du même coup : c'est l'épée qui ouvre les épées, le
bouclier qui ouvre les boucliers.

**La faim ne tuait plus.** Avec la seule nourriture débloquée, elle occupait
100 % du tirage — trois onigiri par étage pour trente tours de ventre dépensés.
Le plancher de nourriture reçoit donc un **plafond** (35 %) : au-delà, les
places au sol restent vides. Un donjon où l'on n'a rien débloqué est un donjon
pauvre, pas un garde-manger. La puissance de l'onigiri n'a pas bougé : c'était
la quantité, pas la portion.

**Et l'idée qui a tout simplifié : la nourriture attire les bêtes.** Le premier
nœud du jeu peuple donc déjà le donjon — l'odeur des vivres réveille ce qui
rôde. Cela supprime l'**état** qui causait tout le reste : il n'existe plus de
moment où l'on a de quoi manger et rien à craindre. « L'épée » n'apporte plus
que sa classe de guerriers, et exige « Nourriture » : on ne peut pas armer des
créatures avant qu'il y en ait.

Sous cette forme, la série est monotone **avec ou sans** fond de donjon (13,8
contre 14,0) : le remède de la profondeur n'est donc plus un correctif. Il reste
comme dessin, et il a pris sa forme définitive — **le donjon s'achète par
tranches de dix étages** : dix au départ, « Les profondeurs » en ouvre dix de
plus, « Les abysses » dix encore.

Et chaque tranche franchie fait **une marche**, pas une pente : au-delà du
dixième étage les créatures gagnent d'un coup 45 %, et autant au vingt-et-
unième. Ouvrir la suite du donjon doit se sentir au premier pas, pas au dixième.

| étage | créatures |
|---|---|
| 10 | ×1,54 |
| **11** | **×2,32** |
| 20 | ×3,10 |
| **21** | **×4,63** |
| 30 | ×5,76 |

Ces deux nœuds sont hors de portée du bot, qui meurt vers l'étage 5 : aucune
campagne ne peut donc dire s'ils sont bien prix. C'est un test unitaire qui
tient la marche — le premier étage d'une tranche doit coûter plus cher que
trois étages de pente.

**Le défaut que tout cela corrigeait, pour mémoire.** « Nourriture » à 3 XP rendait le donjon vide *survivable* : le bot le
traversait jusqu'à l'étage 26 sans rencontrer âme qui vive, et le multiplicateur
de profondeur payait 44 XP par vie — contre 16 une fois les créatures
réveillées. **Le jeu payait pour éviter son propre contenu.**

Deux remèdes essayés :

| remède | vide | avec l'épée |
|---|---|---|
| faim +25 % par étage | 11,6 | 13,1 |
| **fond du donjon à 8 étages** | **9,9** | **14,7** |

La faim aggravée marchait, mais elle rendait la profondeur invivable pour tout
le monde, y compris pour qui joue bien. Le fond du donjon est la bonne poignée :
**l'escalier ne descend qu'à l'étage 8 tant qu'on ne l'a pas ouvert**, et trois
nœuds (« La descente », « Les abysses », « Le fond ») repoussent la limite. Ils
paient par construction, puisque tout le multiplicateur de profondeur est
derrière — mais pas tout de suite : le bot meurt vers l'étage 5, donc « La
descente » ne rapporte encore rien. C'est un nœud qu'on achète quand on sait
enfin atteindre le fond, et c'est très bien ainsi.

Une faim qui se creuse de 5 % par étage reste, plus douce, pour que la
profondeur demande des vivres sans les exiger.

**Le repas automatique** rejoint l'automatisation : ventre presque vide, le
héros mange sa réserve sans qu'on le lui dise. Il ne coûte pas de tour — ce
qu'on achète, c'est de ne plus y penser — et il crédite la cuisine comme un
repas ordinaire, l'automatisation ne devant pas coûter de progression.

**Un croisement dans l'éventail est devenu inévitable** : l'arbre a plus de
liens qui traversent qu'une permutation ne peut en démêler. Le test ne réclame
donc plus zéro, il vérifie que l'ordre retenu **vaut le meilleur possible**, en
essayant les 720 permutations — et il nomme l'ordre gagnant s'il en trouve un.

### L'instrument avait des lacunes, pas le jeu

Le bot mourait vers l'étage 9 avec l'arbre entier acheté, et l'on pouvait
croire à un mur de difficulté. Le diagnostic dit autre chose. Son sac **au
moment de mourir** :

```
parchemin_teleport · herbe_vie · onigiri · epee_bois · epee_fer
onigiri · onigiri · parchemin_panique · bouclier_fer
```

Il mourait en tenant sa téléportation et son parchemin de panique, sans avoir
lu un seul parchemin de sa vie, en portant une herbe de vie jamais mangée, et
en frappant tout ce qui passait — y compris un automate qui le tue en 5 coups
quand il lui en faut 8. **Ce n'était pas la puissance qui lui manquait, c'était
le jugement**, et une lacune de l'instrument se lit exactement comme un défaut
du jeu.

Quatre réflexes appris :

* **compter avant de frapper** — `hp/dégâts` des deux côtés, et l'on ne
  s'arrête pas pour ce qu'on ne peut pas battre ;
* **fuir vers l'escalier** plutôt que vers nulle part : fuir, c'est descendre ;
* **lire un parchemin** quand l'échange est perdu et la vie basse — les connus
  d'abord, n'importe lequel à bout de souffle, ce qui est aussi la façon dont
  on identifie un parchemin ;
* **manger l'herbe de vie**, et le ventre creux, ne plus se détourner que pour
  ce qui se mange : il mourait de faim en allant chercher une troisième épée.

| | avant | après |
|---|---|---|
| étage atteint (arbre complet) | 9,1 | **10,4** |
| étage maximum | 13 | **19** |
| palier de l'étage 11 franchi | jamais | **32 vies sur 60** |
| parchemins lus par vie | 0 | 3,3 |

Le premier palier est enfin franchi une fois sur deux : les nœuds de
profondeur deviennent mesurables.

**Mais changer l'instrument change toutes les mesures**, et il faut le dire :
les chiffres d'ouverture des étapes précédentes ont bougé. La série monte
toujours dans l'ensemble, avec deux nœuds qui penchent du mauvais côté sans
franchir la barre — « L'épée » (−1,8, soit 1,6 σ) et « Projectiles » (−3,6,
soit 1,9 σ) sur 120 parties chacun. Sous deux sigma, je ne rejoue pas les
chiffres : c'est précisément l'erreur que la série des « trois reculs » m'avait
apprise.

### Dix retours de plus, et un bug de comptage

**« Combat » montait sans combattre** : abattre une créature d'un caillou
créditait la carrure de 3 XP, parce que la règle du monstre vaincu ne regardait
pas la distance — que l'évènement portait pourtant déjà. Une ligne, mais elle
faussait aussi mes campagnes.

**Le coffre ne servait à rien sans l'orbe** : on n'y dépose que ce qu'on
rapporte, et l'orbe coûtait 220 XP derrière deux prérequis dont un sans rapport
(les grimoires). « La voie du retour » descend à 90, rejoint la branche du
refuge et n'exige plus que le coffre : les deux nœuds se prennent ensemble et
s'expliquent l'un l'autre. Ça règle du même coup le trait qui traversait
l'éventail — le nœud était accroché à l'autre bout de l'arbre.

**Les nœuds répétables affichent leur prix** et non plus le compte des
reprises : ce qu'on veut savoir devant un rond, c'est ce qu'il coûte
maintenant. Le compte reste en bas, dans la fiche.

**Affûtage et Cuirasse** passent de 35 XP pour +1 à des reprises à 12, 36, 108 :
un point d'attaque valait mal une marche entière de l'échelle.

**La faim a enfin un levier** : « Endurance » (12 XP, trois reprises) enlève 8 %
au coût de chaque pas. C'était la demande la plus concrète — « pas moyen de
descendre sans s'affamer ».

**Deux automatismes de plus** : la première arme et le premier bouclier trouvés
s'équipent d'eux-mêmes (ramasser une épée en cognant du poing n'était le choix
de personne), et le **soin automatique** rejoint le repas automatique, à 30 %
de vie.

**Deux corrections d'interface** : les étiquettes de la carte ne s'affichent
plus sous un panneau ouvert, et l'exploration automatique **rend la main quand
l'escalier paraît** — c'est une nouvelle, au joueur d'en décider. Elle ne
s'arrête pas si l'escalier était déjà en vue au départ : c'est le passage de
« pas vu » à « vu » qui compte.

Effet cumulé sur le bot, arbre complet : étage **12,3** en moyenne au lieu de
10,4, maximum **27** au lieu de 19, et la faim ne tue plus que 18 fois sur 40
au lieu de 21.

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
