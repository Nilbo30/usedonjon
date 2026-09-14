# Chantier — le bus de déclencheurs généralisé

Audit, plan et décisions ouvertes. **Aucune ligne de moteur n'a été écrite.**

Trois décisions déjà prises :

1. **Un seul mécanisme** pour les bonus passifs et les effets qui agissent.
2. **Les règles portées par les talents passent par `RunConfig`** — `Game` ne
   lira jamais `Meta`, la frontière tient telle quelle.
3. **Les constantes de `game.py`** (`ESQUIVE_MAX`, `PORTEE_TIR`, le plancher de
   faim…) sont **hors périmètre** : une étape à part, plus tard.

---

# a. Audit

## L'état des lieux, chiffré

| | où | combien |
|---|---|---|
| évènements émis | `game.py` | 20 points d'émission, 13 noms |
| auditeurs | `Game.listeners` | 1 (`skills.Trainer`) |
| bonus chiffrés (`skills.EFFETS`) | 4 fichiers | 11 noms, **13 points de lecture** |
| effets qui agissent (`@effect`) | `items.py` | 13 fonctions |
| effets de piège (`@trap`) | `traps.py` | 3 fonctions |
| **mutations d'état** (`heal`, `take_damage`, `add_status`, `fullness`) | `game.py`, `items.py`, `traps.py`, `entities.py` | **19 sites** |

Ces 19 sites sont le vrai périmètre du point 1. Ce n'est pas « treize
fonctions » : c'est tout endroit qui change un PV, un ventre ou un statut.

---

## Point 1 — les effets émettent des évènements

### Ce qui existe

`Game.notify(nom, **donnees)` diffuse sur `Game.listeners`. `Event` est passif,
`Recorder` enregistre pour les tests. Les fonctions `@effect` et `@trap`
reçoivent déjà `game` en premier argument : **elles peuvent publier dès
aujourd'hui**, sans rien changer à leur signature.

### Ce qui manque

**Une seconde famille d'évènements.** Le contrat d'`events.py` est explicite :
les évènements décrivent « ce que le héros vient de faire », et « les coups
portés par les monstres sur d'autres monstres n'émettent rien ». Ce sont des
**actions du héros**. Il faut à côté des **faits d'effet** — « 7 PV rendus à X
par Y » — émis quel que soit l'acteur.

**Un point d'émission qui ne s'oublie pas.** C'est le point dur :

```python
class Actor:
    def heal(self, amount): ...        # aucune référence à game
    def take_damage(self, amount): ... # aucune référence à game
```

`Actor` ne connaît pas `Game`. Les 19 sites de mutation l'appellent de
l'extérieur. Deux voies :

- **publier au point d'appel** — 19 endroits à ne pas oublier, et un oubli est
  silencieux : l'effet marche, mais rien ne l'écoute. Le pire genre de bug.
- **faire passer toute mutation par le moteur** — `game.soigner(cible, n,
  source=…)`, `game.blesser(...)`, `game.nourrir(...)`, `game.poser_statut(...)`.
  `Actor` reste bête, le moteur devient le seul à toucher aux PV, et il publie
  au seul endroit possible.

**Je recommande la seconde**, et elle se garde par un test de source — le
projet en a déjà un du même genre (`test_le_moteur_ignore_le_meta` lit le
source de `game.py`). Ici : `\.heal(` et `\.take_damage(` interdits hors de
`game.py`.

### Ce qui risque de casser

**Pas ce que je croyais.** Je pensais trouver un `check_death` appelé de façon
incohérente selon les sites. Vérification faite, les six sites de dégâts
appellent tous `check_death` juste après. Le repliement dans `game.blesser()`
est donc une simplification, pas un changement d'ordre.

Le seul écart réel : `notify` tombe **avant** `check_death` sur deux sites (le
coup au contact, le tir) et il n'y a pas de `notify` du tout sur les quatre
autres. Une fois replié, la règle devient uniforme — le fait d'effet précède
toujours la mort qu'il cause. C'est un choix, il est bon, et il ne se voit pas
aujourd'hui puisque personne n'écoute.

`Trainer` filtre par nom : des noms neufs sont inertes. « Aucun changement de
comportement tant qu'aucune règle n'écoute » est donc tenable — à condition
qu'aucun nouveau nom ne collide avec les treize existants.

---

## Point 2 — porteur générique

### Ce qui existe

Un seul porteur, et il est câblé en dur : `Trainer` lit `game.player.skills`,
et le filtre d'équipement est `player.families()`. `RunConfig` est déjà le
canal méta → run et sait porter des données arbitraires (`unlocks` et
`classes` sont des `frozenset`).

### Ce qui manque

**La table « quel évènement concerne quels porteurs ».** C'est la vraie
spécification du point 2, et elle est plus subtile qu'elle n'en a l'air, parce
qu'une réponse naïve fait exploser le coût.

Ma proposition tient en une phrase : **les porteurs concernés sont ceux que
l'évènement nomme — source et cible — plus leur équipement, plus l'étage, plus
le run.**

| porteur | concerné par |
|---|---|
| une créature | tout évènement qui la nomme comme source ou cible |
| un objet équipé | tout évènement qui nomme son porteur |
| un objet au sol | **seulement** les évènements qui le nomment (ramassage, pose, on le foule) |
| l'étage | tout évènement du run |
| le run | tout évènement du run |

La ligne qui compte est la troisième. Sans elle, chaque pas balaie l'inventaire
de l'étage et le coût par évènement devient proportionnel au nombre d'objets au
sol. Un objet au sol ne porte rien tant qu'on ne le touche pas.

### Ce qui risque de casser

- **La frontière** — réglée : `RunConfig.regles`, produit par `Meta._cumul()`
  depuis les nœuds de l'arbre. Le test de source qui interdit `Meta` dans
  `game.py` continue de la garantir tout seul.
- **Le coût.** `notify` passe d'une boucle sur un auditeur à « collecter les
  porteurs, puis boucler ». Six cents pas par vie, quarante vies par campagne,
  une dizaine de campagnes par décision : c'est mesurable, donc à **mesurer**,
  pas à supposer.
- **La sérialisation.** Une règle portée par le *type* d'objet ne pose aucun
  problème : le coffre stocke `{cle, plus, nombre}` et reconstruit depuis le
  catalogue. Une règle propre à une *instance* — un enchantement — devrait être
  écrite dans l'entrepôt. À noter maintenant, à ne pas faire maintenant.

---

## Point 3 — interception

### Ce qui existe

**Rien.** Les treize points de lecture sont des expressions arithmétiques
écrites à la main :

```python
int(self.base_attack + equipement + self.bonus("attaque"))   # entities.py:152
max(0.25, creuse - player.bonus("endurance"))                # game.py:278
min(ESQUIVE_MAX, defenseur.bonus("esquive"))                 # game.py:504
```

### Ce qui manque

L'objet « effet en route » : une valeur, son contexte, ses bornes. Et la
conversion des treize points.

**La difficulté est les bornes.** Trois des treize en portent une, et ce ne
sont pas des sommes : le plancher de faim à 0,25, `ESQUIVE_MAX`,
`CHANCE_BUTIN_MAX`. Comme les constantes restent hors périmètre (décision 3),
l'objet effet prendra sa borne en argument au point de lecture. Le jour où on
déménagera les constantes, ce sera une ligne par point, sans retoucher au
mécanisme.

### Ce qui risque de casser

**L'ordre.** Décision proposée : deux passes — tout ce qui ajoute, puis tout ce
qui multiplie, puis le bornage. À l'intérieur d'une passe, l'ordre n'existe pas,
parce que l'addition et la multiplication sont commutatives. C'est ce qui rend
l'ordre déterministe **sans table de priorités à maintenir**.

**La contamination.** Une interception ne doit pas pouvoir émettre — sinon on
rouvre les cascades là où on n'en veut surtout pas, dans un calcul de dégâts.
Ça doit être garanti par le code, pas par la discipline : l'objet effet ne
reçoit pas `game`.

---

## Point 4 — garde-fous

### Ce qui existe

Rien, et c'est normal : aucune chaîne n'est possible aujourd'hui. C'est le
point 1 qui crée le besoin — avant lui, un garde-fou n'aurait rien à garder.

### Ce qui manque

- une profondeur maximale de chaîne évènement → effet → évènement ;
- un plafond de déclenchements par règle et par tour.

En données, comme demandé : le plafond par tour est un champ de la règle
(`max_par_tour`), la profondeur est un champ de `RunConfig` — donc réglable par
le méta comme le reste, et pas un nombre dans le moteur.

### Ce qui risque de casser

**Un garde-fou silencieux est pire que la boucle qu'il coupe.** Si une chaîne
est tronquée sans que ça se voie, on débogue un effet qui « marche une fois sur
deux ». Décision proposée : la coupure écrit au journal, et **la suite de tests
échoue si une chaîne est coupée pendant son exécution** — en test, une coupure
est un bug, pas une protection.

---

# b. Le plan, en étapes jouables

Chaque étape laisse le jeu lançable et la suite verte. L'ordre est celui du
risque croissant, et il diffère de celui du brief : l'interception d'abord
parce qu'elle est la plus petite et la seule qui améliore le jeu à elle seule ;
le porteur générique en dernier parce qu'il est le plus gros et qu'il ne se
voit pas.

### Étape 0 — le filet

Figer les empreintes md5 de huit parties scriptées, en test permanent de la
suite. C'est le filet des étapes 1 à 5 ; sans lui, « à comportement identique »
est une intention, pas une preuve.

*Test :* huit graines rejouées, empreintes comparées à des valeurs enregistrées.
*Jouable :* rien ne change.

### Étape 1 — l'interception (point 3)

Les treize points de lecture deviennent des questions nommées. Aucune règle
n'intercepte encore.

*Test :* empreintes identiques · un test par effet témoin (`attaque`,
`endurance`, `esquive`, `chance`, `regeneration`) sur la valeur lue · **un test
qui déclare une interception en données et vérifie qu'elle mord** — sinon on
aura construit un mécanisme sans preuve qu'il sert.
*Jouable :* identique.

### Étape 2 — toute mutation passe par le moteur

`game.soigner`, `game.blesser`, `game.nourrir`, `game.poser_statut`. Les 19
sites convergent. **Aucune émission encore** : c'est l'étape la plus risquée,
elle est isolée exprès pour que les empreintes désignent le coupable.

*Test :* empreintes identiques · test de source interdisant `.heal(` et
`.take_damage(` hors de `game.py`.
*Jouable :* identique.

### Étape 3 — ces méthodes publient (point 1)

La seconde famille d'évènements. Aucune règle n'écoute.

*Test :* empreintes identiques · un `Recorder` voit les faits d'effet dans
l'ordre attendu, et voit le fait **avant** la mort qu'il cause.
*Jouable :* identique.

### Étape 4 — les garde-fous (point 4)

*Test :* une règle de test qui boucle volontairement se coupe à la profondeur
déclarée · un plafond par tour est respecté · la suite échoue si une coupure
survient hors des tests qui la provoquent.
*Jouable :* identique.

### Étape 5 — le porteur générique (point 2)

`RunConfig.regles`, et la collecte des porteurs selon la table ci-dessus.

*Test :* une règle portée par un objet **équipé** ne se déclenche que porté ·
une règle portée par le run se déclenche toujours · une règle portée par un
objet **au sol** ne se déclenche pas quand on passe à côté · le test de source
`Meta` tient toujours · **une mesure du coût** : temps d'une campagne de 40
vies avant et après.
*Jouable :* identique, et pour la première fois du contenu devient possible.

### Étape 6 — le test de validation : le bâton de pyromancie

En deux temps, pour que le résultat soit lisible :

**6a — cible unique.** Portée, charges, dégâts de feu. Si ça demande une seule
ligne de moteur, la généralisation a raté et c'est l'information cherchée.

**6b — cibles multiples.** Le cône. Là, une primitive de visée manquera — « tous
les acteurs dans ce cône » n'existe nulle part. Ce n'est pas un effet, c'est de
la géométrie, et aucun bus n'en fabrique. On l'achètera une fois, consciemment,
et elle servira ensuite à tout ce qui frappe en zone.

---

# c. Décisions encore ouvertes

Trois, toutes de design, avec ma recommandation.

### 1 · Les faits d'effet sont-ils émis même sans le héros ?

`events.py` dit aujourd'hui, noir sur blanc, que les coups entre monstres
n'émettent rien. Si un piège tue une créature, « quand une créature meurt,
soigne » doit-il se déclencher ?

**Je recommande oui** — c'est la moitié de l'intérêt du chantier — **et que les
règles d'XP gardent leur filtre existant** (`si=` sur le héros). L'équilibrage
mesuré ne bouge pas, le contenu s'ouvre. Le contrat d'`events.py` sera réécrit
pour dire que les deux familles n'ont pas la même portée.

### 2 · Les monstres portent-ils des règles dès l'étape 5 ?

Si oui, « l'archer squelette est faible à la lumière » devient des données, et
c'est exactement le système espèce × classe qu'on a construit. Mais toute la
table du bestiaire devient porteuse, et le coût monte.

**Je recommande oui, et de le mesurer à l'étape 5** plutôt que de s'en priver
par précaution.

### 3 · Le ventre et les statuts passent-ils aussi par le moteur ?

L'étape 2 peut ne router que les PV, ou les quatre mutations. Router les quatre
coûte à peine plus et évite d'y revenir.

**Je recommande les quatre.** Je peux trancher seul si tu ne dis rien.

---

# d. La scission du plan — proposition, non faite

`docs/plan-incremental.md` fait **1 150 lignes**. Il sert deux usages qui se
gênent : dire où on en est, et dire comment on y est arrivé.

Proposition :

- **`plan.md`** — l'état courant, la frontière run/méta, les contraintes
  permanentes, le tableau des étapes, la façon d'ajouter du contenu. Ce qu'on
  relit au début d'une session. Court, et toujours à jour.
- **`journal.md`** — chronologique : chaque étape, ses mesures, et surtout les
  **changements d'avis**. On y ajoute, on n'y corrige jamais.

Une réserve, et elle décide de la forme : les changements d'avis sont la partie
la plus précieuse du document, et ils sont aujourd'hui **collés** à la décision
qu'ils renversent. « Le donjon qui payait le vide », « l'instrument avait des
lacunes », la correction sur les courbes de l'étape 16 : séparés de leur
contexte, ils deviennent des anecdotes.

Donc : le journal reste strictement chronologique, et `plan.md` **pointe
dedans** — chaque ligne du tableau des étapes renvoie à son entrée. Sinon on
garde l'état courant et on perd la raison de l'état courant, ce qui est le
contraire du but.

**Rien n'est scindé tant que tu n'as pas dit oui.**
