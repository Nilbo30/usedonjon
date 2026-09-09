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
| 13 | Le butin des créatures | à faire |

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
