# Journal

Le récit du projet : chaque étape, ses mesures, et surtout les **changements
d'avis**. On y ajoute, on n'y corrige jamais — une mesure qui a fait revenir
sur une décision vaut plus que la décision elle-même, et elle ne vaut que
collée à son contexte.

L'état courant, lui, est dans `plan.md`, qui pointe ici.

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

### Le dernier trait en travers

Il restait un croisement, et il était visible : « Herbes » est le second
prérequis du soin automatique, et son trait traversait toute la branche des
trouvailles pour aller le rejoindre — en coupant au passage celui qui relie les
projectiles à « Rien ne se perd ».

Jusqu'ici un seul levier décidait des croisements, l'ordre de `tree.BRANCHES`.
Il ne pouvait rien ici : les deux traits vivent dans la même branche, où l'ordre
vient du rangement par prix puis par nom — « Herbes » avant « Projectiles »,
alphabétiquement, alors que le soin automatique l'attend de l'autre côté.

D'où un second levier, de la même nature : le champ `ordre` d'un nœud, qui le
départage avant le prix. « Herbes » prend `ordre=1` et passe donc après les
projectiles, contre la frontière de la sous-branche où vit le soin automatique.
Le trait est devenu court, et **l'éventail ne compte plus aucun croisement**.

Le test qui vérifiait jusqu'ici que `BRANCHES` était le moins mauvais ordre
possible en exige maintenant zéro, et nomme les deux traits fautifs quand il
tombe : il y a désormais deux leviers à bouger, et aucun des deux ne touche au
jeu.

### Étape 16 — la monnaie du méta devient l'XP investie

#### Le défaut

`RunSummary` convertissait **la somme des niveaux de compétences** en XP méta.
Les courbes étant géométriques (`growth` autour de 1,5), cette somme croît
logarithmiquement avec ce qui est réellement pratiqué, quand le danger, lui,
croît par marches (×2,32 au dixième étage, ×4,63 au vingtième). Trois symptômes
du même défaut :

1. **Le plateau** — le gain d'une vie tournait autour de 35 quoi qu'on fasse,
   noté deux fois dans ce document.
2. **Le papillonnage était optimal** — les premiers crans de chaque compétence
   sont les moins chers ; en effleurer douze rapportait plus que d'en
   approfondir trois.
3. **Tous les crans pesaient pareil** — un cran de marche valait un cran
   d'épée. C'est le défaut qu'Oblivion avait et que Skyrim a corrigé.

#### Le correctif

`SkillSet` tient un compteur de **toute l'XP versée** depuis le début de la
vie, niveaux franchis ou non. C'est lui que `RunSummary` emporte, et c'est lui
que `meta.valeur_du_run` multiplie par la profondeur. Trois lignes de moteur.

Les niveaux restent affichés — sur la fiche, dans le bilan, dans les records.
Ils se lisent ; ils ne s'achètent plus.

#### Ce que ça a donné

Trois configurations, 60 vies de bot chacune, avant et après :

| ouvert | XP/vie avant | XP/vie après |
|---|---|---|
| donjon vide | 4,3 ± 0,1 | 221,5 ± 4,1 |
| + Nourriture | 19,7 ± 1,2 | 433,7 ± 34,4 |
| arbre complet | 54,5 ± 4,0 | 1 936,9 ± 180,6 |

Et le gain suit enfin l'effort. Arbre complet, 60 vies rangées par étage
atteint :

| étage atteint | tours | XP avant | XP après |
|---|---|---|---|
| 1-4 | 256 | 19,6 | 416 |
| 5-8 | 455 | 37,8 | 1 117 |
| 9-12 | 650 | 59,1 | 2 017 |
| 13-16 | 881 | 75,5 | 3 108 |
| 17+ | 844 | 84,8 | 3 645 |

Avant, descendre trois fois plus profond rapportait 4,3 fois plus. Après, 8,8
fois. C'est la fin du plateau : le risque et la récompense montent ensemble.

#### La correction que la mesure a imposée au raisonnement

Le raisonnement de départ disait : « le coût de chaque cran **est** sa
pondération, elle est donc tirée des courbes déjà écrites ». L'identité
comptable est vraie — l'XP versée vaut exactement la somme des coûts des crans
franchis — mais **les courbes n'y entrent pour rien**, et il faut le dire parce
que ça décide de la suite :

```
base=25 growth=1,55  ->  niveau  6   XP versée 600
base= 5 growth=1,50  ->  niveau 10   XP versée 600
base= 1 growth=3,00  ->  niveau  6   XP versée 600
```

Six cents actions valent six cents XP quelle que soit la courbe. Ce que la
monnaie compte, c'est le **nombre d'actions**, pondéré par la profondeur. La
courbe ne décide plus que du nombre de crans que ces actions achètent.

Conséquence mesurée, et c'est la vraie question ouverte de cette étape :

| compétence | part des niveaux (avant) | part de l'XP versée (après) | et si on divisait par `base` |
|---|---|---|---|
| Marche | 17,5 % | **60,0 %** | 25,7 % |
| Récupération | 12,8 % | 13,7 % | 14,7 % |
| Combat | 13,7 % | 10,0 % | 13,5 % |
| Esquive | 10,8 % | 3,7 % | 13,1 % |
| Bouclier | 10,3 % | 5,6 % | 10,1 % |
| Épée | 7,3 % | 2,6 % | 5,5 % |

La marche passe de 17,5 % à 60 % de la monnaie. Ce n'est pas un accident : un
run fait ~600 pas et ~30 coups. L'ancienne monnaie **normalisait** cette
différence de fréquence par les courbes — `marche` coûte 25 XP le premier cran
contre 5 pour `epee` précisément parce qu'« avec une XP fixe par action,
marcher monte neuf fois plus vite qu'épée » (voir les mesures de référence
plus haut). La nouvelle monnaie jette cette normalisation.

Le garde-fou de fond tient toujours : le budget de marche d'une vie reste
exactement la nourriture qu'elle trouve. Mais le sens a changé — l'XP méta dit
maintenant « combien de temps tu as tenu, et jusqu'où », pas « ce que tu as
fait ». **Décision en attente.** La correction, si on la veut, tient en une
ligne et elle est chiffrée dans la dernière colonne : compter `XP versée /
base` par compétence, c'est-à-dire l'effort en « premiers crans équivalents ».
Elle rend la normalisation sans ajouter de table — `base` existe déjà — et
garde tout le reste de l'étape intact : le gain reste linéaire en actions, le
papillonnage reste neutre, les crans gardent leur poids. Seule la marche
retombe de 60 % à 26 %.

#### Le recalage des prix

L'échelle n'a pas été simplement multipliée : elle a aussi été **aplatie**. La
nouvelle monnaie fait moins grossir les gains d'une vie à l'autre — ouvrir la
nourriture double le revenu là où elle le quintuplait — donc les marches hautes
devaient se rapprocher.

| | avant | après |
|---|---|---|
| échelle | 3 · 12 · 35 · 90 · 220 | 150 · 350 · 800 · 1600 · 3200 |
| rapports | 1 : 4 : 12 : 30 : 73 | 1 : 2,3 : 5,3 : 11 : 21 |

Rythme d'ouverture, 12 parties de 15 vies, avant → après : premier talent
vie 1,0 → 1,0 · « Nourriture » vie 2,8 → 2,8 · « L'épée » vie 5,6 → 5,2 ·
talents pris en 15 vies 20,8 → 18,8. Le milieu de l'arbre s'ouvre un cheveu
plus lentement, et c'est attendu : le bot meurt vers l'étage 10, là où la
nouvelle monnaie récompense surtout ceux qui descendent plus bas.

Trois recalages d'échelle ont été essayés avant celui-ci (×50 tel quel, puis
deux aplatissements intermédiaires) ; les mesures sont dans l'historique.

#### Le critère du plan, revérifié

« Après chaque achat, l'XP par vie doit monter. » Vingt achats dans l'ordre où
le bot les prend, 40 vies chacun, écart-type de la moyenne à l'appui :

```
donjon vide                   220 ±     5
+ Nourriture                  438 ±    45     +218  (4,8 σ)
+ Estomac solide              435 ±    52       -3  (0,0 σ)
+ Endurance                   503 ±    53      +69  (0,9 σ)
+ Besace                      503 ±    53       +0  (0,0 σ)
+ Constitution                656 ±    58     +152  (1,9 σ)
+ L'épée                      630 ±    50      -26  (0,3 σ)
+ Le bouclier                 711 ±    61      +82  (1,0 σ)
+ Affûtage                    762 ±    56      +51  (0,6 σ)
+ Cuirasse                    696 ±    56      -66  (0,8 σ)
+ Pièges                      729 ±    61      +33  (0,4 σ)
+ Sens de l'orientation       729 ±    61       +0  (0,0 σ)
+ Butin                       958 ±    86     +229  (2,2 σ)
+ Repas automatique           988 ±    86      +30  (0,2 σ)
+ Herbes                     1048 ±    80      +60  (0,5 σ)
+ Projectiles                1119 ±   119      +70  (0,5 σ)
+ Grimoires                  1404 ±   128     +285  (1,6 σ)
+ Le coffre                  1404 ±   128       +0  (0,0 σ)
+ Les profondeurs            1572 ±   163     +168  (0,8 σ)
+ Soin automatique           1562 ±   158      -10  (0,0 σ)
+ La voie du retour          1460 ±   156     -101  (0,5 σ)
```

Aucun recul ne franchit la barre des deux sigma — le plus fort est à 0,8 σ.
Le critère tient, et « L'épée » et « Projectiles », les deux nœuds qu'on
surveillait depuis l'étape précédente, ne penchent plus (−0,3 σ et +0,5 σ).

Trois nœuds bougent d'exactement **zéro** : « Besace », « Sens de
l'orientation » et « Le coffre ». Ce n'est pas un prix faux, c'est
l'instrument : le bot ne remplit jamais son sac, a sa propre exploration, et ne
dépose rien au refuge. Ces trois-là ne sont pas mesurables par lui — à retenir
avant d'en conclure quoi que ce soit sur leur prix.

#### Effets de bord traités

- **Le rond des talents** portait des prix à deux chiffres ; il en porte
  quatre. Le rayon passe de 13 à 16 et la police du prix se choisit **à la
  mesure**, pas au nombre de chiffres — un test vérifie que chaque prix de
  l'arbre, reprises comprises, tient dans son rond.
- **« On ne gagne rien au refuge »** tient toujours, et mieux qu'avant : le
  multiplicateur vaut zéro, `SkillSet.gain` refuse une XP nulle, donc rien
  n'est même versé. Un test le vérifie maintenant sur l'XP versée et plus
  seulement sur les niveaux, parce qu'une XP dormant sous le seuil d'un niveau
  rapporterait aujourd'hui elle aussi.
- **Rupture de sauvegarde** assumée : une sauvegarde d'avant garde ses talents
  et son solde, mais ce solde ne vaut plus grand-chose face aux nouveaux prix.
  Rien ne plante.

### Étape 17 — les effets deviennent des réactions (proposition)

Les deux formes possibles, confrontées aux onze effets existants, sont dans
`docs/effets-reactions.md`. Rien n'est codé : le choix revient au joueur, et la
migration se fera à comportement identique.

Ce que l'inventaire a appris avant même de choisir : les onze effets font
**treize points de lecture**, et ce nombre ne grandit pas avec le contenu — il
grandit avec le nombre d'endroits où le moteur calcule un nombre. Trois des
treize portent une **borne** (le plancher de la faim, les plafonds d'esquive et
de butin) qui n'est pas une somme : c'est le détail qui départage les deux
formes.


### Étape 17.0 — un filet qu'il a fallu mesurer avant d'y croire

Le chantier du bus de déclencheurs repose entièrement sur une promesse : « à
comportement identique ». Sans preuve, c'est une intention. D'où le filet : des
parties rejouées à graine fixe, et une empreinte md5 de l'état à chaque
commande. L'empreinte porte sur l'**état**, jamais sur les messages —
reformuler une phrase du journal ne doit pas casser le filet, changer un dégât
doit le casser.

**Première version : huit vies de bot. Elle ne servait à rien.** Porter
`ESQUIVE_MAX` de 0,55 à 0,90 ne cassait *aucune* des huit empreintes. Un filet
qui ne mord pas est pire que pas de filet : il donne la confiance sans la
garantie.

L'inventaire des évènements a dit pourquoi :

| évènement | sur les huit vies |
|---|---|
| `pas` | 1 620 |
| `coup` | 138 |
| `pose` | **0** |
| `jet` | **1** |
| `butin` | 5 |
| `equipement` | 6 |

Le bot ne pose jamais rien, ne lance presque jamais et ne déséquipe pas. Tout
un pan du moteur n'était pas couvert — et rien ne l'aurait dit.

**Ce que le bot ne fait pas, il faut le faire exprès.** Sept scènes contrôlées
sont venues s'ajouter : le jet, l'équipement, les objets, les pièges, et
surtout **l'esquive, le butin et la faim**.

Ces trois dernières méritent leur nom. Le moteur a exactement trois bornes — le
plancher du creusement (`max(0.25, …)`), le plafond d'esquive, le plafond de
butin — et ce sont **précisément les trois que l'étape 17.1 va convertir en
interceptions**. Aucune vie de bot ne les atteint : il faut un héros à dix
niveaux d'esquive, vingt de chance ou trente de marche pour que la borne
décide. Sans ces scènes, l'étape la plus risquée du chantier aurait avancé sans
protection là où elle est la plus risquée.

Le filet final : **quinze parties, 2 300 pas, tous les évènements du moteur au
moins une fois**, et deux tests qui gardent cette propriété — l'un exige que
chaque évènement apparaisse, l'autre que les commandes rares apparaissent
plusieurs fois, parce qu'une occurrence unique ne couvre qu'un chemin sur
plusieurs. Un troisième vérifie que les trois bornes sont réellement franchies.

Sensibilité re-mesurée après coup, en déplaçant les constantes d'un pour cent :

| constante déplacée de 1 % | empreintes cassées |
|---|---|
| `ESQUIVE_MAX` | 1 (la scène de l'esquive) |
| `DEGATS_A_DISTANCE` | 1 |
| `PORTEE_TIR` (+1 case) | 2 |
| `CHANCE_BUTIN_MAX` | 0 |

**La limite, dite honnêtement :** le filet attrape toute modification
structurelle, et les écarts d'un pour cent sur les chemins qu'il échantillonne
beaucoup. Il ne garantit pas d'attraper un écart d'un pour cent sur une
probabilité rarement tirée — `CHANCE_BUTIN_MAX` n'est franchi qu'une vingtaine
de fois dans tout le corpus. Le même plafond déplacé de moitié, lui, casse
l'empreinte : vérifié.

### Étape 17.1 — l'interception : le moteur pose des questions

Les treize points de lecture ne sont plus des expressions arithmétiques. Le
moteur ne lit plus « le bonus d'attaque » : il **demande** combien vaut
l'attaque, et ce qui sait répondre répond.

```python
# avant
int(self.base_attack + equipement + self.bonus("attaque"))

# après
int(questions.demander(questions.ATTAQUE, self.base_attack + equipement,
                       porteur=self, arme=self.weapon))
```

Trois choses changent, et la troisième est la raison du chantier :

1. Les compétences répondent toujours, par une table de onze lignes qui relie
   chaque effet à la question qu'il alimente. Aucun des onze n'a été réécrit.
2. Une **interception** peut modifier la réponse en route, en données :
   `@intercepte(ATTAQUE)` et rien d'autre.
3. La question **porte son contexte** — qui frappe, qui encaisse, avec quoi.
   C'est ce que `porteur.bonus("attaque")` ne pouvait pas dire, et c'est ce
   qu'il faut pour les affinités de matière du chantier 3.

#### Nommer la question d'après la quantité, pas d'après le bonus

Le choix qui décide de la lisibilité de tout le reste. « Endurance » ne
s'ajoute pas à une question « endurance » : elle se **retire** de la question
« faim ». On intercepte donc « la faim », pas « l'endurance » — ce qu'on veut
changer, pas le moyen par lequel on le changeait jusqu'ici.

#### Deux garanties, tenues par le code

**L'ordre est déterministe sans table de priorités.** Deux passes : tout ce qui
ajoute, puis tout ce qui multiplie, puis le bornage. À l'intérieur d'une passe
l'ordre n'existe pas, l'addition et la multiplication étant commutatives. Un
test le vérifie en déclarant le multiplicateur *avant* l'addition.

**Une interception ne peut rien déclencher.** Elle ne reçoit pas le `Game` : il
n'y a aucune cascade possible au milieu d'un calcul de dégâts. Ce n'est pas une
règle de discipline, c'est une propriété de structure — et c'est elle qui
dispensera les questions du garde-fou de l'étape 17.4.

#### Une quatrième borne, trouvée en route

L'audit comptait trois bornes. Il y en a **quatre** : `max(1, brut)` sur
l'intervalle de repos avait été manqué. Et le corpus d'empreintes ne l'atteignait
pas non plus — il montait à sept niveaux de récupération là où il en faut huit.
D'où une seizième partie, « le repos », et un test qui vérifie que les quatre
bornes sont réellement franchies par le corpus. Une borne qu'aucune partie
n'atteint n'est pas protégée : on peut la déplacer sans qu'une empreinte bouge.

#### Ce que le filet a attrapé

Une seule régression, et aucun autre test ne l'aurait vue : **`20` devenu
`20.0`**. `resultat()` multipliait systématiquement par un facteur valant 1.0,
ce qui transformait tous les entiers en flottants — et « PV 20/20.0 » sur la
fiche du héros est déjà un changement de comportement. Les seize empreintes ont
toutes cassé d'un coup, les repères étaient identiques, et le message l'a dit :
*« les repères sont les mêmes mais la trace diffère »*. Correction : ne pas
multiplier quand personne n'a déclaré de multiplicateur.

C'est exactement ce pour quoi l'étape 17.0 existait.

#### Ce que ça coûte

Campagne de 25 vies, arbre complet, **14 629 tours des deux côtés** — ce qui est
déjà une preuve d'identité de plus :

| | durée | par tour |
|---|---|---|
| avant | 9,87 s | 0,674 ms |
| après | 10,51 s | 0,718 ms |

**+6,5 %.** Une allocation d'objet par nombre calculé, et l'attaque du héros est
recalculée à chaque coup. C'est le prix annoncé dans la comparaison des deux
formes, et il est payé.

> **Correction, étape 17.4 :** ces +6,5 % étaient du **bruit**. Mesuré une seule
> fois, sur une machine dont la dispersion atteint ±18 % à code identique. La
> reprise en cinq passes ne trouve aucun écart. Voir « la mesure de coût était
> du bruit » plus bas.

370 tests, dont dix-huit neufs sur les questions — les cinq effets témoins du
brief, l'ordre des passes, le bornage, et le test qui compte : une interception
déclarée en données change bien `joueur.attack`, sans qu'une ligne de moteur
ait bougé.

### Étape 17.2 — cinq portes, et le moteur seul à les franchir

Dix-huit endroits changeaient un PV, un ventre ou un statut. Ils convergent
maintenant vers cinq méthodes de `Game` :

```python
game.soigner(cible, points, source=…)
game.blesser(cible, degats, source=…)
game.nourrir(cible, points)          # les deux sens, bornes comprises
game.poser_statut(cible, nom, tours, source=…)
game.gagner_pv_max(cible, points, source=…)
```

C'est une étape qui ne se voit pas du tout en jouant, et c'est exactement le
but : `Actor` ne connaît pas le jeu, donc `heal` et `take_damage` ne peuvent
rien annoncer. Sans cette convergence, l'étape 17.3 devrait publier aux
dix-huit points d'appel — et **un oubli y serait silencieux** : l'effet
marcherait, mais rien ne l'écouterait.

Un **test de source** l'interdit désormais : hors de `entities.py` (qui les
définit) et de `game.py` (seul autorisé à les appeler), aucun module ne peut
toucher `.heal(`, `.take_damage(`, `.add_status(`, `.fullness` ou
`.base_max_hp`. Le garde a été vérifié en réintroduisant volontairement un
appel direct dans `traps.py` : il tombe.

#### La correction que l'audit méritait

L'audit disait, après vérification, que replier `check_death` dans `blesser`
était « une simplification, pas un changement d'ordre ». **C'était faux.** Les
six sites de dégâts appellent bien `check_death` juste après, mais deux d'entre
eux — le coup au contact et le tir ennemi — glissent un `say` et un `notify`
entre les deux. Replier avancerait la mort du monstre **avant** l'évènement du
coup qui l'a tué, déplaçant `monstre_vaincu` dans le flux.

`blesser` ne replie donc rien : elle retire des PV, un point. La simplification
était tentante et elle aurait cassé la promesse de l'étape. C'est le deuxième
chiffre de l'audit que le code contredit, après les « trois bornes » qui
étaient quatre.

#### Une cinquième porte, trouvée en écrivant le test

L'audit parlait de « PV, ventre, statuts ». `base_max_hp` n'est aucun des trois
— et c'est pourtant bien un changement de PV, celui de l'herbe de vie. Sans
`gagner_pv_max`, l'étape 17.3 n'aurait rien eu à publier pour elle. C'est le
test de source qui l'a fait apparaître, en cherchant ce qu'il devait interdire.

#### Ce que ça coûte

Rien de mesurable : 0,709 ms par tour contre 0,718 après l'étape 17.1, sur la
même campagne de 25 vies. Et **14 629 tours des deux côtés**, pour la troisième
fois — une preuve d'identité de plus, gratuite.

377 tests. Les seize empreintes n'ont pas bougé d'un caractère.

### Étape 17.3 — les cinq portes publient

Les cinq méthodes qui touchent aux jauges annoncent maintenant ce qu'elles
viennent de faire. C'est une seconde famille d'évènements, à côté des treize
actions existantes :

| nom | données |
|---|---|
| `soin_recu` | `cible`, `points`, `source` |
| `degats_subis` | `cible`, `degats`, `source` |
| `ventre_change` | `cible`, `ecart` |
| `statut_pose` | `cible`, `statut`, `tours`, `source` |
| `pv_max_gagne` | `cible`, `points`, `source` |

La différence n'est pas cosmétique. Une **action** dit « le héros vient de
frapper » ; un **fait** dit « sept points de vie viennent d'être retirés à X ».
La conséquence, pas le geste.

#### Les deux règles qui donnent leur sens aux faits

**Un fait est émis quel que soit l'acteur.** C'est la décision prise avant de
commencer, et elle renverse une ligne du contrat d'`events.py` : « les coups
portés par les monstres sur d'autres monstres n'émettent rien ». Ça reste vrai
des actions ; c'est maintenant faux des faits. Sans ça, « quand une créature
meurt, soigne » ne marcherait que sur ses propres victimes — et un piège qui
achève un monstre ne déclencherait rien. Les règles d'XP, elles, gardent leur
filtre sur le héros : l'équilibrage mesuré ne bouge pas d'un point.

**Un fait ne part que si quelque chose a changé.** Soigner un héros déjà au
maximum n'annonce rien, et reposer un statut plus court que celui en place non
plus. C'est la même règle que pour les actions — une commande refusée
n'annonce rien — et elle évite au futur bus un flot de « il ne s'est rien
passé ».

Le fait porte **ce qui est réellement arrivé**, pas ce qui était demandé :
soigner de 99 quand il en manque 3 annonce 3.

#### Ce que les six tests cassés ont appris

Six tests d'`events.py` sont tombés d'un coup — et les seize empreintes, elles,
n'ont pas bougé. C'est exactement le bon signal : le **jeu** est identique,
seuls des tests qui énuméraient le flux complet voyaient les nouveaux noms
s'intercaler. Marcher creuse le ventre, donc un `pas` est désormais toujours
suivi d'un `ventre_change`.

Leur intention était « voici les actions attendues », pas « voici tout ce qui
passe sur le bus ». Le `Recorder` sait maintenant le dire : `actions()` et
`faits()` à côté de `noms()`. Un seul test a changé de sens plutôt que de
forme — celui du coup entre monstres, qui affirme désormais les deux moitiés de
la décision : aucune action, mais le fait part.

#### Ce que ça coûte

| | par tour |
|---|---|
| avant 17.1 | 0,674 ms |
| après 17.1 | 0,718 ms |
| après 17.2 | 0,709 ms |
| après 17.3 | 0,715 ms |

Rien de neuf : le chantier entier tient dans les +6 % payés par l'interception.
Et **14 629 tours à chaque mesure**, pour la quatrième fois.

> **Correction, étape 17.4 :** ce tableau n'a aucune valeur. Chacune de ses
> lignes est une mesure unique, et le bruit de la machine les recouvre toutes.

Volume émis sur 25 vies, à garder en tête pour l'étape 17.5 — c'est ce que la
collecte des porteurs devra traverser :

```
ventre_change  15 003      degats_subis  2 433
soin_recu       2 413      statut_pose     116
pv_max_gagne       14
```

`ventre_change` domine largement : environ un par tour, la faim creusant à
chaque pas. Si le coût de 17.5 dérape, c'est là qu'il faudra regarder d'abord.

383 tests, dont six neufs sur les faits. Les seize empreintes sont intactes
pour la quatrième étape d'affilée.

### Étape 17.4 — deux garde-fous qui n'ont encore rien à garder

Un auditeur a le droit d'agir, donc d'émettre à son tour. « Tuer soigne » plus
« être soigné blesse » plus « être blessé peut tuer » ferme la boucle. Deux
garde-fous, tous deux en données :

- **la profondeur de chaîne** — `RunConfig.profondeur_max_chaine`, à 8. Au-delà,
  l'évènement n'est pas émis. Dans `RunConfig` et pas en dur, pour qu'un talent
  puisse un jour l'ouvrir ;
- **le plafond par règle et par tour** — `Regle.max_par_tour`, à `None` partout.
  Le compteur ne garde qu'un tour, donc rien ne s'accumule sur mille tours.

#### Ce qu'ils gardent aujourd'hui : rien, et c'est mesuré

Aucune règle n'agit encore. Mesurée sur trois vies complètes puis sur deux
autres en test permanent, **la profondeur de chaîne maximale vaut un**. Un test
l'affirme et échouera le jour où ça changera — c'est lui qui fera remarquer que
les garde-fous commencent à servir, plutôt que de le laisser arriver en
silence.

Un garde-fou préventif est exactement le genre de mécanisme que ce projet a
appris à se méfier d'ajouter avant son contenu. D'où la contrepartie : le
prouver en le faisant mordre. `Boucleur`, trois lignes, se mord la queue —
soigné il blesse, blessé il soigne. Sans garde-fou il tourne jusqu'à la pile ;
avec, il s'arrête exactement à la profondeur déclarée, et la coupure s'écrit au
journal. Vérifié aussi à l'envers, en désarmant la coupure : six tests sur dix
tombent immédiatement.

Une coupure **se voit** : au journal et dans `chaines_coupees`. Un garde-fou
silencieux est pire que la boucle qu'il coupe — on déboguerait un effet qui
« marche une fois sur deux ».

#### La mesure de coût était du bruit — les trois étapes précédentes incluses

En mesurant cette étape, le chiffre est tombé *sous* celui d'avant le chantier.
Un gain impossible : on a ajouté un test et un `try/finally` par évènement.
Alors j'ai mesuré trois fois le même code :

```
0,626   0,606   0,535 ms/tour
```

**±18 % de dispersion à code identique.** Toutes les mesures de coût de ce
chantier étaient des passes uniques : elles ne mesuraient pas le code, elles
mesuraient la charge de la machine à cet instant. Les « +6,5 % » de l'étape
17.1 n'existaient pas.

Reprise proprement, cinq passes par version, comparées sur la médiane et le
minimum — la version d'avant le chantier reconstruite dans un
`git worktree` pour que les deux tournent dans les mêmes conditions :

| | min | médiane | max |
|---|---|---|---|
| avant 17.1 | 0,594 | **0,607** | 0,618 |
| après 17.4 | 0,536 | **0,589** | 0,621 |

Les plages se recouvrent entièrement. **Le chantier entier — interception,
convergence des mutations, publication des faits, garde-fous — ne coûte rien de
mesurable.** L'allocation d'un objet `Question` par nombre calculé se perd dans
le reste.

C'est la discipline du projet appliquée à moi-même : ne jamais croire un signal
qu'on n'a mesuré qu'une fois. Elle avait déjà servi contre « trois régressions
d'affilée » qui étaient plates à une barre d'erreur près ; elle vient de servir
contre un coût que j'avais annoncé trois fois.

393 tests, dont dix sur les garde-fous. Les seize empreintes sont intactes pour
la cinquième étape d'affilée.

### Étape 17.5 — le porteur générique

Jusqu'ici un seul objet pouvait réagir à un évènement : le héros, par sa table
de compétences, câblée en dur dans `skills.Trainer`. Une règle peut désormais
être **portée** par n'importe quoi — une créature, une arme au poing, l'étage,
le run entier — et le moteur va la chercher là où elle est.

```python
Regle(events.MONSTRE_VAINCU, lambda d: d.jeu.soigner(d.porteur, 2))
```

#### La spécification tient en une phrase

**Les porteurs concernés sont ceux que l'évènement nomme, plus leur équipement,
plus l'étage, plus le run.** Avec une addition au contrat : pour une **action**,
le héros est toujours concerné, puisqu'une action est par définition la sienne
— c'est ce qui permet à une paire de bottes de réagir à un simple pas.

La ligne qui compte est celle qui manque : **un objet posé par terre ne porte
rien tant qu'on ne le touche pas.** Sans elle, chaque pas balaierait
l'inventaire de l'étage. Un test pose vingt cailloux au sol et vérifie qu'un
pas ne concerne personne.

#### Un porteur est tout ce qui a un champ `regles`

Pas un seul `isinstance` dans `regles.py`, donc aucun import d'`entities` ni
d'`items` — c'est ce qui garde le fichier hors du cycle d'imports, et ça rend
le mécanisme ouvert : poser `regles` sur une nouvelle sorte d'objet suffit à la
rendre porteuse. Cinq l'ont reçu : `Actor`, `ItemType`, `Level`, `RunConfig`,
et `tree.Noeud`.

Les règles d'un objet vivent sur son **type**, jamais sur l'exemplaire. C'est
ce qui rend le coffre indolore : il n'y stocke qu'une clé et reconstruit
l'objet depuis le catalogue. Le jour où un enchantement sera propre à un
exemplaire, il faudra l'écrire dans l'entrepôt — noté, pas fait.

#### La frontière tient sans rien changer

Une règle de talent passe par `RunConfig.regles`, produit par `Meta._cumul()`.
`Game` lit `config.regles` et jamais `Meta` : le test de source qui interdit
`Meta` dans `game.py` continue de garantir la frontière tout seul, sans une
ligne de plus.

#### Ce que cette étape ne fait pas, et pourquoi

Les **interceptions** gardent leur registre global : elles ne sont pas encore
portées. La raison est structurelle, et c'est une conséquence directe de
l'étape 17.1 — une question ne reçoit délibérément pas le `Game`, ce qui
interdit toute cascade au milieu d'un calcul de dégâts. Or l'étage et le run ne
se trouvent qu'à partir du `Game`.

Ce n'est pas un manque pour le chantier 3 : les porteurs d'une question se
limitent à ce qu'elle nomme déjà — le porteur, son arme, sa cible — et c'est
exactement ce qu'il faut pour « l'argent mord la chair ».

#### Le coût, mesuré autrement

C'était l'inconnue de l'étape : `ventre_change` part environ une fois par tour,
et chacun traverse maintenant une collecte de porteurs.

Premier essai, cinq passes par version en blocs : 0,595 avant le chantier,
0,639 après 17.4, **0,596 après 17.5**. Incohérent — 17.5 contient tout ce que
17.4 contient, plus une collecte. Ce n'était pas une mesure, c'était la dérive
de la machine entre trois blocs.

Repris en **entrelaçant** les passes — A, B, C, A, B, C… — pour que la dérive
frappe les trois versions également, sept fois chacune :

| | min | médiane | max |
|---|---|---|---|
| avant le chantier | 0,518 | **0,578** | 0,601 |
| après 17.4 | 0,533 | **0,572** | 0,614 |
| après 17.5 | 0,540 | **0,573** | 0,621 |

Les médianes sont indiscernables. Les minima — la mesure la moins polluée —
laissent deviner quelques pour cent, pas davantage. **Le chantier entier, la
collecte des porteurs comprise, ne coûte rien de mesurable.**

L'entrelacement est la leçon de méthode de cette étape : mesurer trois
versions en blocs, c'est mesurer trois moments de la machine.

406 tests, dont treize sur les règles portées. Les seize empreintes sont
intactes pour la sixième étape d'affilée — et cette fois c'est le mécanisme
le plus invasif du chantier qui ne les a pas touchées.

### Étape 17.6 — le bâton de flammes, et le compte exact

Le test de validation du chantier : écrire le premier bâton de pyromancie
**uniquement en données**, et signaler ce que ça demande au moteur. C'est
l'information qui était cherchée, pas le bâton.

#### La tentative en données seules, et ce qu'elle a heurté

Écrite avant de toucher à quoi que ce soit, elle donne quatre points, et pas
un de moins :

| ce qui manquait | pourquoi |
|---|---|
| **une direction à l'usage** | ni `cmd_use(slot)` ni `Item.use(game, user)` n'en prennent — l'effet ne sait pas où viser |
| **une portée par objet** | `PORTEE_TIR` est une constante de module, aucun champ par objet |
| **des charges** | `quantite` compte des exemplaires et `plus` est un bonus : un bâton à cinq charges n'est pas cinq bâtons |
| **une question pour les dégâts d'un sort** | sinon l'affinité du feu n'a nulle part où se poser |

Et un cinquième en écrivant le cône :

| **une primitive de visée en zone** | `ligne_de_tir` s'arrête au premier acteur : c'est ce qu'il faut pour une flèche, jamais pour une flamme |

Plus un sixième, dans l'interface et non le moteur : le mode de visée existait
pour le jet, il lui manquait de savoir vers quoi l'envoyer. **Une ligne.**

#### Ce que ça dit, et ce que ça ne dit pas

**La généralisation n'a pas raté**, et le critère « si ça demande de toucher au
moteur » aurait donné un faux négatif — c'était la mise en garde du départ.
Regardons ce que chaque point a coûté :

- trois des cinq sont des **champs de données** (`portee`, `largeur`,
  `charges`) : une ligne de déclaration chacun, zéro logique ;
- un est un **troisième registre** (`on_aim`), à côté des deux qui existaient
  déjà (`on_use`, `on_hit`). Le moteur a gagné une forme d'objet, pas un cas
  particulier : le prochain bâton, la prochaine baguette, le prochain cor de
  chasse n'en coûteront aucune ;
- un est une **question de plus**, exactement la frontière annoncée à l'étape
  17.1 — « une question par endroit où un nombre se calcule », et il y en a
  maintenant douze ;
- un est de la **géométrie**. Aucun bus d'évènements ne fabrique « tous les
  acteurs dans ce cône » ; c'était la prédiction de l'audit, et c'est le seul
  point que les données ne pouvaient pas couvrir. Acheté une fois, il servira
  à tout ce qui frappe en zone.

Ce qui a tenu en données, en revanche, est ce qui compte : **l'effet entier est
dans le registre `@effect`**, comme les treize qui le précèdent. Et la
compétence « Pyromancie » n'a demandé qu'une entrée au catalogue plus le champ
`skill` de l'objet — la règle `@objet` sur l'usage fait le reste, sans une
règle nouvelle ni une ligne de moteur. C'est la promesse du projet depuis
l'étape 2, et elle tient encore.

#### Prouvé, pas livré

Le bâton est **verrouillé** : aucun nœud n'ouvre « batons », donc il
n'apparaît nulle part. C'était un test de mécanisme, pas une livraison de
contenu — l'accrocher à l'arbre est une décision avec son équilibrage à
mesurer.

Le test qui vérifie que tout verrou d'objet est donné par un talent l'a
immédiatement attrapé. Plutôt que de l'affaiblir — ce qui aurait laissé passer
du contenu réellement injoignable — `tree.VERROUS_EN_ATTENTE` nomme la dette et
sa raison, et un second test exige qu'elle disparaisse de la liste le jour où
le nœud arrive.

420 tests, dont treize sur le bâton. Les seize empreintes sont intactes pour la
septième étape d'affilée : du contenu verrouillé ne change rien à une partie.

### Le bâton rejoint l'arbre — et une mesure qui se dégonfle

Le nœud **« Les bâtons »** ouvre la famille, derrière « Grimoires » : la magie
s'approfondit, on lit avant de brûler. Prix 800, comme ses quatre voisins qui
ouvrent une famille d'objets (Herbes, Projectiles, Grimoires, Butin) — il en
ouvre une, il coûte comme eux.

`VERROUS_EN_ATTENTE` est vide : la dette posée à l'étape 17.6 est soldée, et le
test qui exige qu'elle disparaisse quand le nœud arrive a fait son travail.

#### Le bot d'abord, la mesure ensuite

`_baton_possible` : le bot n'allume le bâton que pour **au moins deux cibles**,
ou pour une seule dont l'échange coup pour coup lui serait défavorable, et il
choisit la direction qui touche le plus de monde. Cinq charges : le brûler sur
un rat ne mesurerait rien.

C'est la leçon payée deux fois — le bot qui ne s'équipait pas, le bot qui ne
lisait pas — appliquée **avant** de mesurer et non après. Il s'en sert dix fois
sur douze vies.

#### La mesure, et ce qu'elle ne dit pas

| | XP/vie | étage |
|---|---|---|
| arbre sans les bâtons | 1 954 ± 130 | 9,59 ± 0,37 |
| arbre complet | 2 149 ± 173 | 10,16 ± 0,38 |

+195 XP par vie, soit **+0,9 σ**. Le critère du plan tient — l'XP monte après
l'achat, rien ne recule — mais **l'effet n'est pas mesurable au-dessus de la
barre du projet**.

Et voici le vrai enseignement : la même mesure à 40 vies donnait +707 XP,
**+1,86 σ**. Presque la barre. À 100 vies il n'en reste que la moitié. C'est la
deuxième fois en deux étapes qu'un chiffre mesuré une seule fois se dégonfle
quand on le regarde mieux, après les « +6,5 % » de coût qui n'existaient pas.

La raison est visible dans le jeu : à poids 4 et profondeur minimale 3, le
bâton apparaît **moins d'une fois par vie**. Le nœud n'achète pas une
puissance, il achète une rencontre rare. C'est très shirenien, et ça rend le
nœud difficile à évaluer au bot. À revoir en jouant.

#### Deux entorses assumées, et elles se disent

**Le nœud ne réveille aucune classe de créatures.** La règle du fichier est
qu'un nœud qui donne un outil fait venir ceux qui savent s'en servir — le
donjon apprend ce que le héros apprend. « Grimoires » l'enfreignait déjà ;
« Les bâtons » l'enfreint aussi. La magie du donjon attend sa classe, le mage,
et la bâcler en recoloriant un archer ne vaut rien. C'est écrit dans `tree.py`,
au-dessus des deux nœuds concernés.

**Deux empreintes sur seize ont été regénérées** : les deux parties qui
achètent tout l'arbre achètent désormais le bâton. Les quatorze autres n'ont
pas bougé d'un caractère — c'est la preuve que seul le contenu neuf a bougé.

#### Un plancher de couverture qui descend, et pourquoi

Le corpus est passé de quinze butins à neuf : le bot, sachant brûler, tue
autrement et donc ailleurs. Le plancher descend de dix à huit.

Baisser une barre parce que le chiffre a baissé est exactement ce qu'une barre
existe pour empêcher — alors j'ai d'abord cherché à restaurer la couverture, en
densifiant la scène du butin. Ça a échoué, et l'échec apprend quelque chose sur
le jeu : **dans une mêlée serrée, la moitié du butin ne tombe jamais**, parce
que la case porte déjà ce qu'a lâché le mort précédent. Six kills sur douze
dans ce cas. Une scène dense ne peut donc pas produire plus de butin qu'une
scène clairsemée.

Le chemin reste exercé neuf fois, le plancher le garde à huit, et la raison est
écrite à côté du chiffre.

422 tests.

### Étape 18 — l'effort, et la marche qui redescend de 60 % à 26 %

L'étape 16 avait remplacé la somme des niveaux par l'XP de compétences versée,
et la mesure avait immédiatement montré le défaut de la nouvelle monnaie :

```
base=25 growth=1,55  ->  niveau  6   XP versée 600
base= 5 growth=1,50  ->  niveau 10   XP versée 600
```

**Les courbes s'y annulaient.** L'XP versée comptait des *actions*, rien
d'autre — un run se résumait à son nombre de pas. La marche ramassait 60 % de
la monnaie parce qu'on fait six cents pas pour trente coups, là où l'ancienne
monnaie normalisait cette fréquence par les courbes elles-mêmes.

#### La correction tenait bien en une ligne

`SkillSet.effort()` : l'XP versée à chaque compétence, **divisée par le coût de
son premier cran**. Une unité d'effort, c'est « un premier cran de cette
compétence-là », quelle qu'elle soit. Vingt-cinq pas valent une unité, comme
cinq coups d'épée ou deux butins trouvés.

Aucune table nouvelle : `base` existe depuis l'étape 2, et c'est précisément là
que le raisonnement avait été fait — « avec une XP fixe par action, marcher
monte neuf fois plus vite qu'épée. C'est ce qui a dicté les courbes. »

| compétence | niveaux (avant 16) | XP versée (16) | effort (18) |
|---|---|---|---|
| **Marche** | 17,5 % | **60,0 %** | **25,7 %** |
| Récupération | 12,8 % | 13,7 % | 14,9 % |
| Combat | 13,7 % | 10,0 % | 12,5 % |
| Bouclier | 10,3 % | 5,6 % | 11,2 % |
| Esquive | 10,8 % | 3,7 % | 10,5 % |
| Épée | 7,3 % | 2,6 % | 4,2 % |

La prédiction chiffrée de l'étape 16 disait 25,7 %. Mesuré : 25,7 %.

#### Ce que ça ne défait pas

`base` est un **diviseur constant par compétence** : il ne touche pas à la
géométrie des courbes. Le sixième cran d'épée coûte toujours sept fois le
premier, en effort comme en XP brute. Donc tout ce que l'étape 16 avait gagné
tient : le plateau reste tombé, le gain reste linéaire en actions, et un cran
arraché vaut toujours plus qu'un cran offert. Trois tests le disent.

#### Deux chiffres, et un seul s'échange

`total_xp()` reste l'XP brute — ce qui s'est passé dans la partie, et c'est
elle qui figure dans les empreintes. `effort()` est la monnaie. L'interface
montre la monnaie, parce qu'afficher un nombre qui n'est pas celui qu'on
dépense n'aide personne.

**Les seize empreintes n'ont pas bougé d'un caractère.** C'est la preuve la
plus nette qu'on pouvait donner : cette étape ne touche qu'à la **conversion**,
et le donjon lui-même est exactement le même.

#### L'échelle, recalée pour la seconde fois — et en sens inverse

L'étape 16 avait dû **aplatir** l'échelle. L'étape 18 la **redresse**, plus
raide que jamais, et pour une raison mesurée : le revenu d'une vie grandit
maintenant **×27** entre le couloir vide et l'arbre complet, là où il
grandissait ×8,7.

| | avant 16 | 16 | 18 |
|---|---|---|---|
| échelle | 3 · 12 · 35 · 90 · 220 | 150 · 350 · 800 · 1600 · 3200 | **6 · 30 · 100 · 280 · 700** |
| rapports | 1:4:12:30:73 | 1:2,3:5,3:11:21 | **1:5:17:47:117** |
| XP/vie, donjon vide | 4,3 | 221,5 | 8,8 |
| XP/vie, arbre complet | 54,5 | 1 937 | 240 |

Rythme mesuré sur douze parties de quinze vies : premier talent vie **1,0**,
« Nourriture » vie **2,8**, « L'épée » vie 5,7, et **20,9 talents en quinze
vies** — exactement la valeur d'avant l'étape 16 (20,8).

#### Le critère du plan, revérifié de bout en bout

Vingt et un achats, 40 vies chacun. Aucun recul ne franchit la barre des deux
sigma ; le plus fort est à 1,0 σ. De 8,8 à 140 XP par vie.

#### Ce que la mesure signale, et que je ne corrige pas

Avec l'échelle redressée, la branche magique sort de l'horizon du bot :
« Grimoires » à la vie 14 pour trois parties sur douze, et **« Les bâtons »
jamais pris en quinze vies**. C'est la conséquence assumée d'une échelle plus
raide — et le bot meurt vers l'étage 10, là où la nouvelle monnaie récompense
surtout ceux qui descendent plus bas. Un humain qui joue mieux y arrivera plus
tôt. À confirmer en jouant, pas au bot.

425 tests, dont trois neufs sur l'effort.

## Étape 19.1 — la matière, et ce qu'elle ne donne jamais

Le chantier 3 coupe l'arme en deux : la **forme** dit *comment on frappe* et
porte les chiffres, la **matière** dit *sur quoi ça mord* et ne porte aucun
chiffre d'attaque. Cette étape pose l'axe entier avec deux formes seulement —
épée et bouclier — parce que l'axe est ce qui se mesure, et que les trois
autres formes n'ajouteront pas une ligne de moteur.

### Sept lignes de données, dix objets

Les quatre équipements écrits à la main ont disparu. À leur place :

```python
FORMES   = {"epee": {...,"attaque": 5}, "bouclier": {...,"attaque": 5}}
MATIERES = {"bois":   {"poids": 10, "profondeur": 1},
            "bronze": {"poids":  7, "profondeur": 2},
            "fer":    {"poids":  5, "profondeur": 4},
            "argent": {"poids":  3, "profondeur": 5},
            "obsidienne": {"poids": 2, "profondeur": 7}}
```

Deux formes × cinq matières = **dix objets**, dépliés par `_equipements()`.
Les clés restent `epee_bois`, `bouclier_fer` — ce qui n'a rien cassé du kit de
départ ni de la table de butin. Le jour où les trois autres formes arrivent,
ce sont vingt objets pour deux lignes de plus.

`MATIERES` n'a pas de champ `attaque`, et un test refuse qu'on lui en ajoute
un : c'est le verrou du chantier. Une matière qui donnerait de l'attaque brute
ferait gagner l'épée en bois entraînée contre l'épée en argent trouvée le jour
même, et la boucle du butin mourrait.

### La rencontre : matière contre famille

`donjon/affinites.py`, quinze nombres et **zéro ligne de moteur** :

|  | animal | humanoïde | homoncule |
|---|---|---|---|
| bois | 1,0 | 1,0 | 0,7 |
| bronze | 1,1 | 1,0 | 0,9 |
| fer | 1,0 | 1,1 | **1,3** |
| argent | **1,3** | 1,2 | 0,8 |
| obsidienne | 1,2 | **1,3** | 1,0 |

Une seule interception, sur la question `ATTAQUE` ouverte à l'étape 17.1. Elle
porte les deux moitiés du coup : l'arme de celui qui frappe mord la famille
d'en face, le bouclier de celui qui encaisse repousse la famille de celui qui
frappe. La moitié défensive vit sur `ATTAQUE` et non sur `DEFENSE` parce que
`Actor.defense` est une **propriété**, lue sans savoir qui attaque ; lui
apprendre l'attaquant coûtait une ligne de moteur pour un effet gratuit ici.
C'est écrit dans le fichier, pas seulement ici.

Hors combat il n'y a personne en face : la fiche du héros affiche l'attaque
nue. Afficher ×1,3 serait un mensonge d'affichage.

### Le pivot coûte, et personne ne l'a écrit

Le brief interdisait d'ajouter un coût artificiel au changement d'arme — pas
de malus, pas de temps d'adaptation. Il n'y en a pas. Le coût vient de deux
faits déjà présents dans le jeu :

* les animaux peuplent les étages 1 à 7, les homoncules 8 et au-delà. Une
  matière forte contre le vivant est donc **automatiquement faible en
  profondeur** ;
* chaque coup crédite **deux** compétences, la forme et la matière. Changer de
  matière, c'est repartir de zéro sur une courbe pendant que l'autre reste
  haute.

`Actor.attaque_contre(cible)` est remontée sur la classe de base : les
monstres posent désormais la même question que le héros, ce qui était la
condition pour que le bouclier du héros voie la famille de celui qui frappe.

### Ce qui garde la boucle du butin en vie

La compétence de matière donne +1 d'attaque par niveau — c'est sa courbe, et
c'est ce qui fait le prix du pivot. Le danger était qu'elle finisse par
écraser l'affinité. Elle ne le peut pas, et pas grâce à un plafond : la
compétence **s'ajoute** avant que l'affinité ne **multiplie**. Maîtriser une
matière qui glisse, c'est voir sa maîtrise glisser avec elle.

Le chiffre : contre un homoncule, l'épée en bois rattrape l'épée en fer neuve
à **26 de compétence « Bois »** — pour un héros d'étage 8 déjà monté en
« Épée » et en « Combat ». Le bot, sur douze campagnes de quinze vies, plafonne
à **4**. La marge est de six fois. Le test, lui, tient la structure et non la
marge, parce que la marge bougera et que la structure, non.

### Mesures

Douze campagnes de quinze vies, puis trente, mêmes graines des deux côtés,
comparaison appariée vie par vie.

| | avant | après | écart |
|---|---|---|---|
| effort/vie (180 vies) | 43,63 | 44,22 | +0,6 (0,4 σ) |
| étage atteint (180 vies) | 7,33 | 7,02 | −0,31 (1,8 σ) |
| effort/vie (**450 vies**) | 43,09 | 45,64 | **+2,54 (2,3 σ)** |
| étage atteint (**450 vies**) | 7,24 | 7,17 | −0,07 (0,7 σ) |

**Pour la troisième fois en trois étapes, une mesure se dégonfle en doublant
l'échantillon** : le recul d'étage à 1,8 σ tombe à 0,7 σ. Et la hausse
d'effort fait l'inverse, de 0,4 σ à 2,3 σ. La règle du projet — ne rien croire
sous deux sigma — a encore protégé d'une conclusion fausse, dans les deux sens.

Ce qui reste : **+6 % d'effort par vie**, au-dessus de la barre. L'explication
tient en deux faits — l'épée de départ est passée de 3 à 5 d'attaque (la forme
donne le chiffre, et il est unique), et chaque emplacement porte maintenant
deux courbes au lieu d'une. Je ne recale pas l'échelle des prix aujourd'hui :
l'étape suivante ajoute trois formes et déplacera le même nombre. Recaler deux
fois, c'est recaler à l'aveugle.

### Ce que cette étape ne mesure pas, et le dit

La distribution des matières en fin de vie, sur 450 vies :

    bois 289 · bronze 76 · fer 19 · argent 13 · obsidienne 3

**Ce chiffre ne dit rien du jeu.** Toutes les formes frappent à 5 : le bot
choisit son équipement sur `power`, donc il ne voit plus aucune différence
entre une épée en bois et une épée en argent et garde ce qu'il a. C'est
exactement ce que sa propre docstring redoutait — « toute mesure sur
l'armement mesurerait sa cécité, pas le jeu » — pour une raison neuve.

Le brief l'avait prévu : « le bot devra apprendre à décider d'un pivot. S'il ne
sait pas le faire, **il ne mesure rien**. » C'est le travail de l'étape 19.3,
et jusque-là les deux mesures qui comptent — distribution des matières, nombre
de pivots par vie — restent en attente.

### Les empreintes

Neuf des seize ont bougé, et c'est du contenu assumé, pas une dérive. Cinq
partitions sur huit : l'épée de départ est passée de 3 à 5 d'attaque, donc
toute scène où le héros tient une arme a changé d'état. Les trois autres — le
jet, les objets, les pièges — n'ont pas bougé d'un caractère, le héros n'y
frappant personne. Quatre parties sur huit, dont les deux qui achètent
l'arbre entier.

446 tests, dont vingt et un neufs sur les matières.

## Étape 19.2 — les trois autres formes, et le coût d'un coup

L'axe des matières était posé, mais il ne croisait qu'une seule arme. Cette
étape ajoute la **dague**, la **lance** et la **hache** : cinq formes × cinq
matières font **vingt-cinq équipements** à partir de douze lignes de données.

### Ce que porte une forme

| forme | attaque | cadence | portée | part |
|---|---|---|---|---|
| dague | 3 | 70 | 1 | 0,35 |
| épée | 5 | 100 | 1 | 0,30 |
| lance | 4 | 100 | **2** | 0,20 |
| hache | 8 | 160 | 1 | 0,15 |
| bouclier | 5 | — | — | 1,0 |

`cadence` est l'énergie que coûte un coup, 100 étant le tour plein : la dague
frappe 1,43 fois plus souvent que l'épée, la hache 1,6 fois moins. Ramenés à
cent d'énergie, les quatre valent 4,3 · 5,0 · 4,0 · 5,0 — la lance paie sa
portée, la dague paie le droit d'agir souvent.

### La part, qui n'a l'air de rien

`poids` n'est pas un poids de tirage mais une **part** : les quatre formes de
mêlée se partagent 1,0. Sans ça, passer d'une forme à quatre multipliait par
quatre le poids total des armes dans la table de butin, et le donjon se serait
couvert d'épées au détriment des herbes et des vivres. Une refonte de
l'équipement aurait refait, discrètement, l'économie des objets.

La mesure le confirme : **211 armes portées en fin de vie avant, 211 après**.
La part donne au passage une rareté à chaque forme, gratuitement.

### Deux points de moteur, et pourquoi ils sont deux

**Le coût du coup.** `attack` dépensait `ACTION_COST` en dur. Il pose
maintenant la question `COUT_COUP`, dont la valeur de départ est la cadence de
l'arme. C'est une question et non une lecture directe pour que le jour où un
talent veut accélérer les coups, il le fasse en données — la machinerie de
l'étape 17.1 sert telle quelle.

Son plancher est la **cinquième borne** du moteur, et la seule que le corpus
des empreintes n'atteint pas : elle n'existe que pour qu'une interception
maladroite ne rende jamais un coup gratuit, ce qui ferait boucler le jeu. Elle
est déclarée comme telle dans `questions.demander`, plutôt que passée sous
silence.

**La portée.** `attack` se coupe en deux : `_cibles_du_coup` dit *qui* est
touché, `_porter_le_coup` fait ce que faisait l'ancien corps. Le coût est payé
une fois par attaque, l'esquive se joue cible par cible — deux créatures
alignées ne se dérobent pas ensemble.

La géométrie, elle, n'a **rien coûté** : `acteurs_dans_la_zone`, écrite à
l'étape 17.6 pour le souffle du bâton, fait exactement ce qu'il faut. C'est la
première fois qu'une primitive de moteur écrite pour un contenu resserve telle
quelle pour un autre.

### Une décision de jeu, prise contre la lettre du brief

Le brief disait « portée ». J'ai fait **traverser** la lance plutôt que
frapper à deux cases. La raison est un piège que la seconde forme créait : le
coup se donne en avançant sur la case d'à côté, donc une lance qui attaque à
deux cases **empêche de marcher vers une créature**. On ne peut plus
s'approcher, plus fuir en diagonale autour d'elle, plus rien. Ce n'est pas une
portée, c'est une malédiction.

En traversant, la lance garde tout ce que la portée promettait — la meilleure
arme des couloirs, qui sont partout — sans toucher au déplacement. Un test
garde cette propriété explicitement.

### Le bot a dû réapprendre à choisir

`_a_mieux_en_main` comparait les `power` bruts. C'était juste tant que toutes
les armes coûtaient un tour plein ; avec la hache à 8 pour 160 d'énergie, le
bot l'aurait prise à tous les coups et « le bot préfère la hache » n'aurait
rien dit du jeu. Il compare maintenant la valeur **pour cent d'énergie**.

Ce n'est pas encore choisir sa matière — ça, c'est l'étape 19.3, et c'est la
seule qui rendra lisibles les deux mesures qui comptent.

### Mesures

Soixante campagnes de quinze vies, mêmes graines des deux côtés, comparaison
appariée vie par vie, contre l'étape 19.1.

| | avant | après | |
|---|---|---|---|
| effort/vie | 43,89 | 43,54 | −0,35 (0,6 σ) |
| étage atteint | 7,18 | 7,13 | −0,06 (1,3 σ) |

**Neutre**, ce qui est le bon résultat pour un ajout de contenu : trois formes
de plus ne doivent pas déplacer l'économie, seulement ouvrir des façons de
jouer. À 450 vies l'étage disait 1,7 σ ; à 900 il dit 1,3. Quatrième fois qu'un
écart se dégonfle en doublant l'échantillon, et je commence à croire que c'est
une propriété de la mesure et non une série de coïncidences.

Formes portées en fin de vie, sur 900 vies :

    épée 126 · dague 126 · hache 112 · lance 60

La hache sort au-dessus de sa rareté (0,15 de part pour 25 % des armes
portées) : le bot la garde dès qu'il la trouve, puisqu'elle égale l'épée à
énergie constante. La lance reste sous la sienne, le bot ne sachant pas qu'un
couloir double sa valeur. Les deux écarts sont lisibles, et aucun n'est un bug.

### Les empreintes

**Quatre parties sur seize ont bougé, et zéro partition.** Exactement les
quatre qui achètent « Les armes ». Les douze autres n'ont pas frémi — la
cadence d'une épée vaut 100, c'est-à-dire l'ancien coût, et c'est la preuve la
plus nette qu'on pouvait donner que le coût du coup ne change rien là où il n'y
a rien à changer.

462 tests, dont seize neufs sur les formes.

## Étape 19.3 — le bot apprend à pivoter, et la mesure répond autre chose

Le brief le disait sans détour : « le bot devra apprendre à décider d'un pivot.
**S'il ne sait pas le faire, il ne mesure rien.** » Cette étape lui apprend,
prouve qu'il a appris, puis mesure. La réponse n'est pas celle qu'attendait la
question, et c'est tout l'intérêt.

### Ce que « décider d'un pivot » veut dire

Comparer des `power`, c'est choisir une arme comme on choisit un nombre.
Décider d'un pivot, c'est répondre à trois questions que le jeu pose déjà :

1. **qu'est-ce que je vais croiser ici ?** `_familles_attendues` lit la table
   de l'étage, pondérée. Le bot juge sur la population et non sur la créature
   qu'il a sous le nez : sinon il changerait d'arme à chaque rencontre, ce qui
   n'est pas un pivot mais un tic.
2. **qu'est-ce que ma matière leur fait ?** `_mordant_moyen` croise cette
   population avec la table des affinités.
3. **qu'est-ce que je perds en lâchant ce que je tiens ?** La compétence de
   matière ne vaut que l'objet en main — mais elle vaut aussi le **bouclier**.
   Lâcher l'épée en argent quand le bras porte de l'argent ne coûte rien. Un
   bot qui l'ignore surestime le prix du pivot et ne pivote jamais.

Plus une marge de 10 % : chaque échange coûte un tour, et sans marge deux armes
à un pour cent l'une de l'autre se relaieraient à chaque étage.

**Zéro ligne de moteur.** Le bot apprend à lire ce qui était déjà écrit.

### Vérifier l'instrument avant de croire ses chiffres

Douze tests (`tests/test_pivot.py`) tiennent la décision dans les cinq
situations qui comptent : il prend l'argent en haut, le fer en bas, il pivote
quand l'étage change de peuple, il **ne** pivote **pas** quand sa compétence
d'argent est haute — et il pivote quand même si le bouclier garde l'argent.
Coupez les affinités, sept tombent ; coupez la lecture des compétences, un
tombe. L'instrument mord.

### Ce que l'instrument a révélé de mes propres chiffres

Le bot lucide s'est mis à prendre la dague partout. Il avait raison : **une
cadence multiplie l'attaque entière**, carrure et compétences comprises, pas la
seule puissance de l'arme. J'avais calé les cadences de l'étape 19.2 sur la
puissance seule, ce qui était faux.

| attaque hors arme | dague 70 | épée 100 | hache 160 |
|---|---|---|---|
| 2 | 7,1 | 7,0 | 6,2 |
| 12 | **21,4** | 17,0 | 12,5 |
| 25 | **40,0** | 30,0 | 20,6 |

La dague gagnait dès le deuxième point d'attaque, et l'écart explosait. Cadences
recalées — dague **85**, hache **130** — et les trois formes se relaient :

| attaque hors arme | dague | épée | hache |
|---|---|---|---|
| 4 | 8,2 | 9,0 | **9,2** |
| 8 | 12,9 | **13,0** | 12,3 |
| 20 | **27,1** | 25,0 | 21,5 |

La hache tant qu'on frappe faible, l'épée le temps d'apprendre, la dague quand
la carrure fait le gros du travail. Les bases de compétence suivent (dague 6,
hache 4). C'est une correction de l'étape précédente, pas une trouvaille : le
chiffre était faux et l'outil neuf l'a montré en trois campagnes.

Formes portées en fin de vie, 900 vies, contre leur rareté au tirage :

| | dague | épée | lance | hache |
|---|---|---|---|---|
| trouvées | 35 % | 30 % | 20 % | 15 % |
| portées | 35 % | 26 % | 16 % | 23 % |

Aucune forme ne domine : la distribution portée suit la distribution trouvée.
C'est le meilleur résultat possible pour un axe d'équilibre.

### Les mesures du brief

Comparaison à cadences identiques des deux côtés — **bot aveugle contre bot
lucide**, seule la décision change. 60 campagnes de 15 vies, appariées.

| | bot aveugle | bot lucide | |
|---|---|---|---|
| effort/vie | 43,77 | 42,77 | −1,00 (2,2 σ) |
| étage atteint | 7,14 | 7,13 | 0,2 σ |
| **pivots/vie** | 0,109 | 0,117 | 0,7 σ |

Matières portées en fin de vie :

| | bois | bronze | fer | argent | obsidienne |
|---|---|---|---|---|---|
| bot aveugle | 536 | 208 | 35 | 24 | 9 |
| bot lucide | 480 | 220 | **52** | **39** | 8 |

### Ce que ça dit, et ce que ça ne dit pas

**Le bot choisit mieux ses matières** : +49 % de fer, +63 % d'argent, −10 % de
bois. L'axe est enfin visible dans une mesure. C'était le but de l'étape.

**Il ne pivote pas plus souvent.** 0,109 contre 0,117, sous la barre. Et le
chiffre du bot aveugle n'était pas nul : il changeait de matière **par
accident**, en changeant d'arme pour d'autres raisons. Le pivot délibéré n'est
pas plus fréquent que le pivot accidentel.

Le brief avait prévu deux lectures : « zéro = le creux est trop profond, cinq =
ça n'existe pas ». Aucune des deux ne s'applique. La vraie raison est ailleurs,
et elle se lit dans le tableau des populations :

| étage | animal | humanoïde | homoncule | meilleure matière |
|---|---|---|---|---|
| 1–7 | 100 → 39 % | 0 → 61 % | **0 %** | argent |
| 8 | 0 % | 82 % | 18 % | obsidienne / fer |
| 10 | 0 % | 52 % | 48 % | **fer** |
| 11+ | 0 % | 31 % | 69 % | **fer** |

La bascule des familles commence à l'étage **8**. Le bot meurt en moyenne à
**7,1**. Sur 900 vies, celles qui atteignent l'étage 8 pivotent presque deux
fois plus (0,207 contre 0,109), et celles qui s'arrêtent avant ne pivotent
**jamais** — pas une seule fois.

Autrement dit : **le donjon s'arrête avant que le pivot ait une raison
d'exister.** Ce n'est ni un creux trop profond ni un pivot inexistant, c'est un
horizon trop court. Le mécanisme est juste, prouvé par douze tests ; il lui
manque des étages.

Je ne le corrige pas ici. Trois leviers existent — faire remonter les
homoncules, ouvrir « Les profondeurs » plus tôt, ou rendre la survie plus
longue — et ce sont trois décisions de jeu, pas une correction de code.

### Une dernière chose, désagréable et vraie

Le bot lucide gagne **moins d'effort** (−1,00, 2,2 σ). Ce n'est pas une
régression : il se bat mieux, donc il frappe moins de fois, et la monnaie
compte les coups. C'est une propriété connue de l'effort depuis l'étape 18 —
mais c'est la première fois qu'on la voit pénaliser le fait de **bien jouer**.
À garder en tête le jour où l'on jugera un talent défensif.

474 tests, dont douze neufs sur le pivot. Une seule empreinte a bougé :
« pièges », la seule vie assez longue pour porter deux armes de matières
différentes en même temps.

## Étape 20 — dix retours de partie, dont un qui bloque tout le reste

Dix remarques après une vraie partie. Sept sont traitées, une est déjà vraie,
une est une décision à prendre, et la dernière s'est heurtée à un mur qu'il
vaut mieux connaître : **l'éventail des talents est plein**.

### Ce qui est corrigé

**Un bouton qui rouvre ce qui est ouvert le referme.** Le clavier basculait
déjà — « c » ouvre les compétences, « c » les referme — les boutons, eux, ne
faisaient qu'ouvrir. Cliquer deux fois sur « Compétences » ne faisait rien, et
il fallait deviner qu'on sortait par Échap ou par le clic droit.

**L'XP à dépenser est affichée.** Il y a deux monnaies et on n'en voyait
qu'une : à gauche l'effort de la descente en cours, et c'est tout. Le trésor de
guerre ne se lisait qu'au centre de l'éventail — donc il fallait mourir,
remonter au refuge et ouvrir la stèle pour savoir ce qu'on pouvait s'offrir.
Il s'affiche maintenant en haut à droite, en permanence.

**L'exploration ne ramasse plus les armes.** Elle allait les chercher une par
une et le sac finissait plein d'épées qu'on n'avait pas choisies. Or le moteur
avait déjà tranché ailleurs : `_gerer_objet_au_sol` ramasse les consommables au
passage et **laisse l'équipement au sol**, parce qu'emporter une arme est une
décision. L'exploration automatique contredisait sa propre règle.

Elle fait maintenant ce que le retour demandait, mot pour mot : elle s'arrête
la première fois qu'une arme entre dans le champ, la nomme, et rend la main. Si
le joueur repart sans s'en occuper, elle ne l'arrêtera plus — c'est la même
mémoire que celle de l'escalier, et c'est ce qu'« ignorer » veut dire.

**Viser s'achète.** Le nœud « Projectiles » ne faisait que poser des pierres au
sol ; le geste, lui, était offert dès la première vie. Un héros qui n'a jamais
appris à viser n'a pas à savoir lancer une herbe à la figure d'un rat. Le
talent ouvre maintenant les deux d'un coup — de quoi lancer, et de quoi
apprendre à le faire.

**Le donjon profond est moins monotone.** « Trop de golems de pierre à partir
de l'étage 8 » : c'était vrai, et pire que ça.

| | avant | après |
|---|---|---|
| espèces à l'étage 8 | 5 | **6** |
| espèces à l'étage 11 | **4** | 7 |
| espèces à l'étage 13 | 4 | 6 |
| part du golem, étages 8-13 | 18 à 26 % | **10 à 16 %** |

Passé l'étage 10 le bestiaire tombait à quatre espèces et n'en rebougeait plus
jamais : gobelins et arbalétriers s'arrêtaient au dixième, et il ne restait que
les trois homoncules et le sorcier. Quatre changements de données :

* le golem pèse **6** au lieu de 10 — la créature la plus lente et la plus dure
  du jeu ne doit pas être une rencontre sur cinq ;
* le tas de chair arrive à l'étage **8** au lieu de 9, et pèse 10 : la famille
  des homoncules se présente par sa face molle en même temps que par son mur ;
* gobelin jusqu'au **11**, brute gobeline et arbalétrier jusqu'au **13** — le
  moteur sait déjà les mettre à niveau (`_scale_to_depth`), il n'y avait aucune
  raison de les retirer.

Deux tests neufs gardent la propriété, et ils gardent une **forme** et non un
chiffre : aucun étage du milieu ne tient sur moins de cinq espèces, aucune
créature n'y dépasse 30 % des rencontres. Les étages 1-2 en sont exclus (deux
bêtes, c'est une mise en bouche) et le fond du donjon aussi (il ne reste que
les homoncules, et c'est tout l'intérêt).

Un troisième test a dû être **réécrit plutôt que réparé** : il figeait « plus
de 50 % d'homoncules à l'étage 11 », un réglage. Il mesure maintenant une
pente — plus on descend, plus la chair cède au fabriqué — et la pente, elle, ne
doit jamais s'inverser.

### Le mur : l'éventail des talents est plein

Le retour demandait que les matières se cachent derrière des talents. C'est
écrit, mesuré, et **repris** : les quatre nœuds n'entrent pas dans l'éventail.

La preuve est nette. L'éventail tient 27 nœuds avec **1,6 pixel** de marge :
les deux plus proches, « Repas automatique » et « Herbes », sont à 39,6 px pour
un minimum de 38. J'ai ajouté **un seul nœud vide** pour voir : 37,1 px. Le
test des ronds tombe.

Ce n'est pas un problème de réglage. J'ai cherché sur quatre leviers — rayon du
dernier anneau (325 → 415), ouverture (160° → 172°), étirement de l'ellipse
(1,3 à 2,0), rayon des ronds (16 → 15), et jusqu'à donner aux matières leur
propre branche. Chaque combinaison déplace le problème sans le résoudre : élargir
les anneaux desserre les paires radiales et resserre les paires angulaires, et
inversement. Le minimum n'est jamais repassé au-dessus de 38.

**L'arbre ne peut plus grandir avant que sa mise en page soit refaite.** C'est
une étape à part entière, et c'est maintenant le premier obstacle sur la route
de tout ce qui viendra — pas seulement des matières.

Ce que la mesure a dit avant que je reprenne le travail, et qui servira le jour
où l'éventail aura de la place :

| | matières trouvées en fin de vie | pivots/vie |
|---|---|---|
| sans verrou (19.3) | bois 480 · bronze 220 · fer 52 · argent 39 · obsidienne 8 | 0,117 |
| échelle 30/100/280/700 | bois 556 · bronze 194 · fer 13 · **rien d'autre** | 0,062 |
| échelle 6/30/100/280 | bois 494 · bronze 211 · fer 57 · argent 12 | 0,087 |

**Verrouiller les matières les rend plus rares, pas plus désirables** — et le
pivot, déjà fragile, tombe de moitié à la première échelle. Si le verrou revient
un jour, ce sera avec l'échelle basse, et en sachant ce qu'il coûte.

### Un bonus : une liste recopiée à la main qui ne l'est plus

`TOUT_DEBLOQUE` — ce que le bot et les tests ont d'ouvert — était une liste de
quatorze chaînes recopiées à la main depuis l'arbre. Le jour des quatre nœuds,
elle s'est désynchronisée immédiatement : le bot jouait à un donjon où les
matières n'existaient pas. Un test l'a vu, mais **le voir après coup n'est pas
la même chose que de ne pas pouvoir se tromper**. Elle se lit maintenant dans
l'arbre.

### Mesures

Soixante campagnes de quinze vies, appariées, contre l'étape 19.3.

| | avant | après | |
|---|---|---|---|
| effort/vie | 42,77 | 43,70 | +0,93 (1,8 σ) |
| étage atteint | 7,13 | 7,17 | +0,04 (1,1 σ) |
| pivots/vie | 0,117 | 0,108 | 1,3 σ |

Rien ne franchit la barre. Le sens est celui qu'on attendait : moins de golems,
c'est un peu plus de survie, donc un peu plus d'effort — et un peu, ici, veut
dire pas assez pour être sûr.

Quatre empreintes sur seize ont bougé, dont deux qui descendent **plus bas**
qu'avant. C'est l'effet recherché.

487 tests, dont dix-huit neufs.

### Annotation à l'étape 20, écrite après coup

La mesure de l'étape 20 disait « rien ne franchit la barre » sur 900 vies.
Relancée sur **1800**, l'effort par vie passe à **+0,96 (2,4 σ)** : elle
franchit la barre. C'est la première fois qu'un écart **grandit** avec
l'échantillon au lieu de se dégonfler — quatre fois de suite, c'était
l'inverse. L'entrée d'origine n'est pas corrigée, elle est annotée : elle
disait vrai de ce qu'elle avait mesuré.

Le sens reste celui qu'on attendait et la taille est petite : moins de golems,
c'est +2 % d'effort par vie. Rien à recaler ; simplement, c'est un effet réel
et non du bruit.

## Étape 21 — la stèle se promène, et l'arbre se découvre

L'étape 20 s'était arrêtée sur un mur : l'éventail des talents tenait 27 nœuds
avec 1,6 pixel de marge, et un vingt-huitième le faisait déborder quel qu'il
soit. Deux changements le lèvent, et ils ne se ressemblent pas : l'un rend la
place, l'autre décide de ce qu'on montre.

### Le zoom pur, la seule piste qui marchait

Quatre leviers avaient été essayés à l'étape 20 — ouverture, étirement, rayon
des ronds, branche dédiée — et chacun desserrait les paires radiales en
resserrant les angulaires, ou l'inverse. Le cinquième marche, et pour une
raison qu'on peut écrire :

La part d'ouverture que réclame une branche vaut `TALENT_ESPACEMENT / rayon`,
puis tout est normalisé sur les 160° de l'éventail. **Multiplier les deux
rayons par le même facteur divise donc tous les besoins par ce facteur, et la
normalisation les rattrape** : les angles ne bougent pas d'un degré, seules les
distances grandissent. C'est un zoom, au sens strict — la seule transformation
qui aère sans redessiner.

Reste que l'éventail dépasse alors de la fenêtre. D'où la seconde moitié : **on
le promène à la souris**.

Le facteur est un compromis, mesuré :

| facteur | écart minimal | nœuds de marge | visibles d'un coup |
|---|---|---|---|
| 1,0 | 40 px | **0** | 27 / 27 |
| **1,5** | **59 px** | **8** | **13 / 27** |
| 1,75 | 69 px | 12 | 9 / 27 |
| 2,0 | 79 px | 16 | 6 / 27 |

1,5 garde la moitié de l'arbre lisible sans bouger la souris. Le jour où huit
nœuds ne suffiront plus, c'est ce nombre qu'il faudra monter — et la table dit
ce qu'il en coûtera.

### Un clic qui attend le relâchement

Glisser part d'un appui, et un appui sur un rond achetait le talent. On aurait
voulu déplacer l'arbre, on aurait acheté « Les abysses », et **les choix sont
définitifs**. Un talent s'achète donc maintenant au **relâchement**, et
seulement si la souris n'a pas voyagé de plus de cinq pixels entre les deux.
Deux tests le tiennent : glisser depuis un rond ne doit rien acheter, et un
frisson de souris de deux pixels doit rester un clic.

C'est aussi ce qui a fait bouger tous les tests d'achat de talent : ils
cliquaient d'un appui. Ils passent par un `cliquer()` qui appuie **puis**
relâche — ce qu'un vrai clic a toujours été.

### Découper à la main, faute de mieux

Le canevas de tkinter ne découpe rien : un rond tiré trop haut allait se
dessiner par-dessus la barre de vie, et un trait de talent traversait le
bandeau. La première version avait exactement ce défaut, et elle se voyait au
premier coup d'œil sur une capture.

Trois réponses, dans cet ordre : un rond hors cadre ne se dessine pas ; un
trait est **découpé au rectangle** (Liang-Barsky, quatre bornes le long du
segment) ; le cœur de l'éventail s'efface quand il n'a plus la place. Le cadre
commence sous la légende des branches et s'arrête au-dessus de la ligne de
lecture, avec la marge qu'il faut au **nom** posé au-dessus du rond.

### Les nœuds cachés

Un talent ne se montre plus tant que son prérequis n'est pas pris. On voit donc
toujours exactement ce qu'on peut viser, et le reste se découvre en montant.
Au premier lancement, ce sont les **quatre racines** — Estomac solide,
Constitution, Nourriture, Sens de l'orientation — et rien d'autre.

Une exception, qui n'en est pas une : un nœud **acquis** reste visible même
quand il n'a plus rien à donner. Un arbre qui efface ce qu'on a payé serait
cruel.

Ouvrir la stèle la **recadre** sur ce qui est visible. Sans ça, une première
partie ouvrirait l'arbre sur du vide : les racines sont en bas de l'éventail,
et tout le reste est caché.

### Ce que les tests gardent, maintenant

Le test « tous les nœuds tiennent dans le cadre » n'avait plus de sens : le
cadre est plus petit que l'arbre, exprès. Il est remplacé par deux autres, qui
disent ce qui compte vraiment depuis qu'on déplace la vue :

* **chaque talent peut être amené sous les yeux** — aucun n'est hors
  d'atteinte, quel que soit le déplacement permis ;
* **l'éventail ne peut pas être emporté hors de l'écran** — on en garde un bon
  tiers sur chaque axe, et pas le strict minimum : l'éventail est un arc, les
  coins de sa boîte sont vides, et n'en garder qu'un pixel revenait à pouvoir
  tirer l'arbre jusqu'à ne plus montrer qu'un coin sans un seul rond dedans.

Et surtout un test neuf, celui qui manquait le jour du mur : **l'éventail garde
de la place pour grandir**. Il ajoute six nœuds fictifs et vérifie que ça tient
encore. « Deux ronds se touchent » arrive trop tard — il dit qu'on a débordé,
pas qu'on allait déborder. Celui-ci échoue avant, et son message dit quoi
faire.

### Un piège d'outillage, noté parce qu'il m'a eu

Pendant la recherche du bon facteur, trois mesures d'affilée ont donné le même
chiffre pour trois réglages différents. Ce n'était pas le code : Python
relisait un `__pycache__` périmé, les réécritures du fichier tombant dans la
même seconde que la précédente. La comparaison des facteurs ci-dessus a été
refaite caches vidés. **Un banc de mesure qui ne varie pas quand on change le
réglage ne confirme rien : il est cassé.**

494 tests, dont sept neufs sur la stèle.

## Étape 22 — les matières s'achètent, et ce que ça coûte au pivot

L'étape 20 avait écrit les quatre nœuds de matière et dû les reprendre :
l'éventail ne tenait pas un nœud de plus. L'étape 21 lui a rendu de la place.
Ils reviennent, avec **l'échelle basse**, et la mesure qui va avec.

### Un objet peut réclamer deux talents

C'est le seul point de moteur, et il tenait dans le croisement : une arme est
une **forme** et une **matière**, donc deux verrous, pas un. `ItemType.unlock`
devient un n-uplet — une chaîne seule reste acceptée, c'est le cas de tout le
reste du contenu — et les deux filtres (butin au sol, butin des créatures)
deviennent une inclusion d'ensembles.

    epee_bois   →  ('epees',)
    epee_fer    →  ('epees', 'fer')

Le kit de départ est intact : le bois n'a pas de verrou. C'est aussi la matière
qui ne mord rien de particulier et qui glisse sur le fabriqué — ce qu'on trouve
quand on n'a rien appris.

### L'échelle basse, et pourquoi elle n'est pas un cadeau

| | bronze | fer | argent | obsidienne |
|---|---|---|---|---|
| échelle haute (essayée) | 30 | 100 | 280 | 700 |
| **échelle basse (retenue)** | **6** | **30** | **100** | **280** |

À l'échelle haute, le fer ne se prenait presque jamais dans l'horizon d'un
joueur et l'argent jamais : le changement d'arme tombait de 0,117 à 0,062 par
vie. **Verrouiller une matière la rend déjà plus rare ; il ne faut donc pas,
en plus, la rendre chère.** C'est une décision de jeu prise sur trois mesures,
pas un réglage au jugé.

### Ce que le verrou coûte quand même

Soixante campagnes de quinze vies, appariées, contre l'étape 21.

| | avant | après | |
|---|---|---|---|
| effort/vie | 43,70 | 42,83 | 1,6 σ |
| étage atteint | 7,17 | 7,10 | 1,6 σ |
| **pivots/vie** | **0,108** | **0,087** | **2,2 σ** |

Matières portées en fin de vie :

| | bois | bronze | fer | argent | obsidienne |
|---|---|---|---|---|---|
| avant | 482 | 210 | 55 | 42 | 8 |
| après | 494 | 211 | 57 | **12** | **0** |

Le fer et le bronze survivent au verrou ; **l'argent perd les trois quarts et
l'obsidienne disparaît**. Le changement d'arme perd un cinquième, au-dessus de
la barre des deux sigma — c'est la seule des trois mesures qui bouge vraiment,
et c'est exactement celle qu'on savait menacée.

Ce n'est pas une régression : c'est le prix annoncé, payé, et mesuré. Un joueur
qui va plus loin que les quinze vies du bot finira par prendre l'obsidienne —
c'est la même situation que « Les bâtons », jamais pris dans cet horizon et
pourtant bien vivant pour qui joue mieux. **Mais il faut le savoir, et ne pas
se raconter que verrouiller du contenu le met en valeur : ça le raréfie.**

### L'éventail a rendu ses huit nœuds, et on les a repris

Quatre de plus, et le test de marge de l'étape 21 a fait exactement son
travail : il a échoué **avant** que deux ronds se touchent, en disant quoi
faire. Le facteur passe de 1,5 à **1,75**, et la table du commentaire est
refaite sur l'arbre tel qu'il est (31 nœuds) :

| facteur | écart minimal | nœuds de marge | visibles d'un coup |
|---|---|---|---|
| 1,5 | 49 px | 4 | 19 / 31 |
| **1,75** | **58 px** | **8** | **14 / 31** |
| 2,0 | 66 px | 11 | 9 / 31 |

On revient au même profil qu'hier : huit nœuds d'avance, près de la moitié de
l'arbre lisible sans bouger la souris. Le garde-fou a coûté une ligne et a
évité une séance entière de tâtonnement — c'est ce que valait le test.

### Les empreintes

**Deux sur seize.** Celles qui achètent l'épée, donc le bronze, donc un donjon
qui ne sert plus le même équipement. Les six autres vies et les huit partitions
n'ont pas frémi : le bois n'a jamais eu de verrou.

494 tests, dont cinq neufs sur les verrous de matière.
