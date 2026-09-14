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
