# usedonjon — petit donjon mystère

Un roguelike « Mystery Dungeon » (type *Shiren le vagabond*) volontairement
minimal : tour par tour, étages générés aléatoirement, faim, objets à lancer,
escalier à trouver. Écrit en **Python 3, sans aucune dépendance**, pour pouvoir
tester une idée en quelques secondes et faire grossir les mécaniques ensuite.

![Aperçu du jeu](docs/apercu.png)

## Jouer

```bash
python3 -m donjon                # fenêtre graphique (tkinter, fourni avec Python)
python3 -m donjon --seed 42      # partie reproductible
python3 -m donjon --depth 10     # raccourcir le donjon (30 étages par défaut)
python3 -m donjon --tile 26      # cases plus grandes
python3 -m donjon --tui          # version terminal (ASCII, curses)
python3 -m donjon --meta         # voir sa progression permanente
python3 -m donjon --no-save      # jouer sans toucher à la sauvegarde
```

### À la souris

Tout se joue au clic, sans rien connaître du clavier :

- **clic sur une case voisine** : s'y déplacer, ou attaquer ce qui s'y trouve ;
- **clic plus loin** : le héros s'y rend tout seul (chemin calculé par le BFS de
  `path.py`, uniquement à travers ce qu'il a déjà vu) et s'arrête dès qu'un
  monstre apparaît, qu'il est blessé ou qu'il marche sur quelque chose ;
- **clic sur le héros** : ramasser l'objet sous lui, descendre l'escalier, ou
  attendre un tour selon la situation — les consommables, eux, se ramassent
  tout seuls en marchant dessus ;
- **bouton « Se reposer »** : patienter jusqu'à guérison, au prix du ventre —
  l'attente s'interrompt seule si un monstre paraît ;
- **survol** : une étiquette décrit la case (nom et PV du monstre, objet, piège) ;
- **clic droit** : annuler le déplacement en cours ou fermer un panneau ;
- les **boutons en bas à droite** (Ramasser, Descendre, Attendre, Sac, Aide) et
  le **sac** sont entièrement cliquables — y compris viser un jet en cliquant
  la cible.

![Le sac à la souris](docs/sac.png)

Les compétences se consultent d'un clic ou avec `c` :

![Les compétences](docs/competences.png)

### Au clavier

Les **flèches** (ou `hjkl` + `yubn`, ou le pavé numérique) pour se déplacer et
attaquer, `,` ramasser, `>` descendre, `.` attendre, `i` sac, `?` aide,
`q` quitter. Dans le sac : la lettre de l'objet, puis `u` utiliser, `e` équiper,
`t` lancer (puis une direction), `d` poser. Après la partie, `R` relance une
nouvelle descente.

Il y a deux affichages pour le même moteur : la fenêtre graphique (`gui.py`,
formes dessinées à la main, prête à recevoir des sprites PNG) et le terminal
(`ui.py`, ASCII). Aucun des deux ne contient de règle de jeu.

### Sous Windows

**Le plus simple : double-clique `jouer.bat`.** Il se place tout seul dans le
bon dossier et lance le jeu — pas de ligne de commande, et pas d'erreur
« No module named donjon ».

En ligne de commande, `python -m donjon` suffit aussi, à condition d'être dans
le dossier **qui contient** le dossier `donjon` (celui où se trouve ce README).
Si tu vois `No module named donjon`, tape `dir` : tu dois voir `donjon` et
`README.md` dans la liste ; sinon, descends d'un cran avec `cd`.

tkinter est livré avec l'installeur officiel de python.org, donc rien à
installer. Seul le mode `--tui` demande en plus `pip install windows-curses`.

Sur Mac et Linux, `./jouer.sh` fait la même chose.

## Tester vite

Tout le jeu est pilotable sans interface : l'UI et les tests appellent les
mêmes fonctions `Game.cmd_*`.

```bash
python3 -m unittest discover -s tests      # la suite complète (~3 s, 47 tests)
python3 -m donjon --seed 7 --script "lljj,>" --frames   # rejouer une partition
python3 -m donjon --seed 7 --auto 500 --reveal          # bot + carte dévoilée
```

Langage de script : `hjklyubn` déplacement, `.` attendre, `,` ramasser,
`>` escalier, `U<slot>` utiliser, `E<slot>` équiper, `D<slot>` poser,
`T<slot><dir>` lancer, `#` commentaire. Les emplacements vont de `a` à `l`
(majuscules pour les objets afin de ne pas gêner `u` = diagonale haut-droite).

Une graine fixe rejoue exactement la même partie : les tests de régression
comparent simplement les journaux et les cartes.

Les tests d'interface (clavier et souris) construisent une vraie fenêtre et lui
envoient des évènements ; ils s'ignorent tout seuls si tkinter ou un écran
manquent, donc la suite reste verte sur un serveur sans affichage.

## Ce qui est déjà là

| Mécanique | État |
|---|---|
| 30 étages générés (salles + couloirs), escalier | ✅ |
| XP et monstres qui montent avec la profondeur | ✅ |
| Bilan de fin de run (étage record, tours, compétences, cause) | ✅ |
| Progression permanente : un arbre de talents qui déverrouille le jeu | ✅ |
| Un refuge où l'on marche, avec un coffre qui traverse la mort | ✅ |
| L'orbe de retour : remonter avec ses acquis, sans gagner de méta | ✅ |
| Visibilité « salle entière », mémoire de la carte | ✅ |
| Combat au tour par tour, diagonales bloquées par les angles de murs | ✅ |
| Compétences : on progresse dans ce qu'on pratique | ✅ |
| Faim (ventre), mort de faim | ✅ |
| Repos : s'arrêter convertit le ventre en PV, trois fois mieux qu'en marchant | ✅ |
| Objets : herbes, parchemins, nourriture, armes, boucliers, flèches | ✅ |
| Jet d'objets sur les monstres | ✅ |
| Statuts (endormi, confus, paralysé) avec durée | ✅ |
| Pièges cachés | ✅ |
| Fiches d'objets au survol (effet, compétence entraînée) | ✅ |
| Parchemins non identifiés tant qu'on ne les a pas essayés | ✅ |
| Consommables ramassés en marchant dessus | ✅ |
| Vitesses différentes (rapide / lent) | ✅ |
| Trois IA (chasseur, erratique, peureux) + pathfinding | ✅ |
| Jeu complet à la souris (clic, déplacement auto, survol, boutons) | ✅ |

## Équilibrage de départ

Repère mesuré avec le bot (`autoplay`, qui fonce vers l'escalier sans farmer) :

| Profondeur | Issue du bot sur 200 graines |
|---|---|
| 5 étages (défaut) | ~83 % de victoires |
| 10 étages | mort systématique, le plus souvent aux étages 6-8 |

Autrement dit : un joueur qui combat et fouille doit pouvoir descendre bien plus
bas qu'un bot pressé. C'est la base à faire bouger quand on ajustera les tables
de `monsters.py` et les réglages en tête de `game.py`.

## Architecture

```
donjon/
  config.py     RunConfig : réglages d'une partie (canal vers le futur méta)
  events.py     évènements d'action (socle de l'XP par compétence)
  skills.py     catalogue des compétences, règles de gain, bonus
  run.py        RunSummary : le bilan d'un run terminé
  tree.py       l'arbre des talents : tout le contenu déverrouillable
  meta.py       progression permanente et sa sauvegarde JSON
  session.py    le lien entre les runs (le seul endroit méta + partie)
  rng.py        hasard centralisé et graine → parties reproductibles
  geom.py       positions et 8 directions
  tiles.py      types de cases (table de propriétés)
  dungeon.py    génération d'étage, champ de vision
  path.py       BFS (IA, bot de test, déplacement à la souris)
  entities.py   Actor / Player / Monster, PV, statuts, énergie
  items.py      objets = données + effets enregistrés
  monsters.py   bestiaire = données pures
  traps.py      pièges = données + effets
  ai.py         un comportement = une fonction enregistrée
  game.py       état, ordonnanceur, API d'actions (cmd_*)
  script.py     partitions de commandes + bot (tests rapides)
  gui.py        fenêtre tkinter, souris et clavier (aucune règle de jeu)
  ui.py         affichage curses (aucune règle de jeu)
  __main__.py   CLI
```

Deux choix structurent la suite :

1. **Ordonnanceur à énergie.** Chaque acteur gagne `speed` points par tour de
   monde et agit à 100. Une action pourra coûter 50 (attaque rapide) ou 200
   (incantation) sans toucher au reste.
2. **UI découplée du moteur.** `game.py` n'importe ni `gui.py` ni `ui.py` : les
   trois affichages (fenêtre, terminal, aucun) appellent les mêmes `cmd_*`.
   C'est ce qui a permis d'ajouter la fenêtre graphique sans toucher une seule
   règle de jeu.

## Ajouter du contenu

**Un monstre** — une entrée dans `donjon/monsters.py` :

```python
{"key": "ninja", "name": "Ninja", "glyph": "n", "hp": 18, "attack": 10,
 "defense": 4, "exp": 14, "depth": (4, 99), "weight": 10, "behaviour": "peureux",
 "color": "#d0c05b", "shape": "pointu"}
```

`glyph` sert au terminal, `color` et `shape` (`rond`, `carre`, `pointu`) à la
fenêtre graphique — les deux derniers sont facultatifs.

**Un objet** — un effet + une entrée dans `donjon/items.py` :

```python
@effect("jet_gel")
def _jet_gel(game, thrower, target, item):
    target.add_status("paralysé", 8)
    game.say(f"{target.name} est pris dans la glace.")
    return True

ItemType("baguette_gel", "baguette de gel", "/", SCROLL, weight=6, on_hit="jet_gel")
```

**Une compétence** — une entrée dans `donjon/skills.py`, plus une règle disant
quel évènement la nourrit :

```python
Skill("hache", "Hache", base=5, scope=EQUIPEMENT, effects={"attaque": 2})
```

Une arme de cette famille se déclare avec `skill="hache"` dans `items.py` : la
règle `"@arme"` fait le reste, le moteur n'est pas touché. Un objet d'une
catégorie déjà connue (herbe, parchemin…) hérite automatiquement de sa
compétence.

**Un comportement d'IA** — une fonction décorée dans `donjon/ai.py` :

```python
@behaviour("voleur")
def _voleur(game, monster):
    ...   # vole un objet puis fuit vers l'escalier
```

**Un piège** — même schéma dans `donjon/traps.py`.

## Le refuge et les deux boucles

La partie s'ouvre dans un **refuge** : une petite salle où l'on marche, avec un
coffre et l'escalier du donjon. Ce qu'on laisse dans le coffre survit à la mort.

Deux boucles s'y imbriquent :

- **mourir** — on perd sac et compétences, mais le niveau global monte, et les
  descentes suivantes partent mieux équipées ;
- **l'orbe de retour**, trouvée à partir de l'étage 4 — on remonte au refuge
  avec tout, sac et compétences comprises, mais la descente ne rapporte
  **aucune** progression permanente et la profondeur repart de zéro. On est plus
  fort pour descendre plus bas, à condition d'y arriver vraiment.

## L'arbre des talents

Le jeu **se déverrouille**. La première vie se joue dans un couloir vide où
l'on meurt de faim : pas d'arme, pas de monstre, rien au sol. Mourir rapporte
de l'XP permanente — les niveaux de compétences du run multipliés par la
profondeur atteinte — et cette XP s'échange contre des talents, au refuge.

L'équipement, les créatures, les objets, les herbes, les parchemins, le coffre,
l'orbe : chacun est un nœud à acheter, avec ses prérequis. Les choix sont
définitifs. Chaque déblocage augmente ce qu'une vie rapporte, donc accélère le
suivant.

![L'arbre des talents](docs/talents.png)

Ajouter du contenu, c'est un nœud dans `tree.py` et un `unlock="..."` sur les
objets concernés — le moteur ne bouge pas. La sauvegarde vit dans
`~/.usedonjon/meta.json`.

## Où va le projet

Le jeu évolue vers un hybride roguelike / incrémental. Les compétences sont en
place — on progresse dans ce qu'on pratique, marcher entraîne la marche et
frapper entraîne l'arme en main — et la suite est le prestige — à la mort les compétences sont perdues, un niveau global permanent
monte et débloque des mécaniques. Le plan détaillé, la frontière entre état de
run et état permanent, et les décisions déjà prises sont dans
[`docs/plan-incremental.md`](docs/plan-incremental.md).

## Pistes pour la suite

- Objets non identifiés (herbes de couleur, parchemins au nom inconnu)
- Marmites / fusion d'objets, malédictions, objets scellés
- Monstres qui se transforment en objets, alliés, montures
- Missions à contraintes (sans objet, étages spéciaux, salles de monstres)
- Sauvegarde de partie (l'état est déjà sérialisable sans effort)
- Coût d'action variable (attaques rapides, incantations lentes)
- Sprites PNG dans la fenêtre (le dessin passe déjà par une fonction par forme)
