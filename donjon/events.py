"""Évènements : ce qui vient de se passer, en deux familles.

C'est le socle de l'XP par action. Le moteur ne sait pas ce qu'est une
compétence ; il annonce simplement « le héros a fait un pas », « le héros a
porté un coup avec cette arme ». Les auditeurs branchés sur `Game.listeners`
décident quoi en faire — demain la table des compétences, aujourd'hui un
simple enregistreur pour les tests.

Un évènement n'est émis **que si l'action a réellement eu lieu** (un tour
consommé). Une commande refusée n'annonce rien.

Contrat des évènements — les clés listées sont toujours présentes :

| nom              | données                                                    |
|------------------|------------------------------------------------------------|
| `pas`            | `depart`, `arrivee`, `diagonale`                            |
| `attente`        | —                                                           |
| `coup`           | `arme` (Item ou None), `cible` (Actor), `touche`, `degats`  |
| `coup_recu`      | `bouclier` (Item ou None), `source` (Actor), `degats`        |
| `monstre_vaincu` | `monstre` (Actor), `arme` (Item ou None), `distance`        |
| `ramassage`      | `objet`                                                     |
| `pose`           | `objet`                                                     |
| `usage_objet`    | `objet`, `categorie`                                        |
| `equipement`     | `objet`, `categorie`, `equipe` (True si porté, False rangé) |
| `jet`            | `objet`, `cible` (Actor ou None), `direction`               |
| `descente`       | `etage` (le nouvel étage)                                    |
| `repos`          | `pv` (points de vie regagnés en se reposant)                 |

`arme` vaut None à mains nues : c'est volontaire, une compétence « pugilat »
s'y accroche sans rien changer ici. Même logique pour `bouclier`.

`repos` n'est émis que lorsque l'attente soigne réellement : patienter à pleine
vie n'entraîne rien.

`coup_recu` est le seul évènement d'action que le héros ne déclenche pas
lui-même : on apprend à parer en encaissant. Les coups portés *par* les
monstres sur d'autres monstres, eux, n'émettent aucune **action**.

## Les faits d'effet

Seconde famille, ajoutée à l'étape 17.3. Là où une action dit « le héros vient
de frapper », un fait dit **« sept points de vie viennent d'être retirés à
X »** — la conséquence, pas le geste.

| nom | données |
|-----------------|--------------------------------------------------------|
| `soin_recu` | `cible`, `points`, `source` |
| `degats_subis` | `cible`, `degats`, `source` |
| `ventre_change` | `cible`, `ecart` (négatif quand la faim creuse) |
| `statut_pose` | `cible`, `statut`, `tours`, `source` |
| `pv_max_gagne` | `cible`, `points`, `source` |

Deux différences avec les actions, et elles sont voulues :

* **Un fait est émis quel que soit l'acteur.** Un piège qui tue une créature,
  un monstre qui en soigne un autre : tout passe. C'est la moitié de l'intérêt
  du bus — « quand une créature meurt, soigne » doit marcher même quand le
  héros n'y est pour rien. Les règles d'XP, elles, gardent leur filtre sur le
  héros : l'équilibrage mesuré ne bouge pas.
* **Un fait précède toujours la mort qu'il cause.** `game.blesser` publie, puis
  le point d'appel vérifie la mort. Un auditeur voit donc les dégâts avant
  `monstre_vaincu`, jamais l'inverse.

`source` vaut l'acteur, l'objet ou rien du tout — un piège n'a pas d'auteur.
Comme pour `arme`, c'est volontaire : une règle s'y accroche sans rien changer
ici.

Les cinq faits sont émis depuis les cinq seules méthodes qui touchent aux
jauges (`Game.soigner`, `blesser`, `nourrir`, `poser_statut`, `gagner_pv_max`),
et **seulement quand quelque chose a réellement changé** : soigner un héros
déjà au maximum n'annonce rien, comme une commande refusée n'annonce rien.
"""

PAS = "pas"
ATTENTE = "attente"
COUP = "coup"
COUP_RECU = "coup_recu"
MONSTRE_VAINCU = "monstre_vaincu"
RAMASSAGE = "ramassage"
POSE = "pose"
USAGE_OBJET = "usage_objet"
EQUIPEMENT = "equipement"
JET = "jet"
DESCENTE = "descente"
REPOS = "repos"
BUTIN = "butin"

# --- les faits d'effet : ce qui vient d'arriver à quelqu'un ---------------
SOIN_RECU = "soin_recu"
DEGATS_SUBIS = "degats_subis"
VENTRE_CHANGE = "ventre_change"
STATUT_POSE = "statut_pose"
PV_MAX_GAGNE = "pv_max_gagne"

#: Ce que le héros vient de faire.
ACTIONS = (PAS, ATTENTE, COUP, COUP_RECU, MONSTRE_VAINCU, RAMASSAGE, POSE,
           USAGE_OBJET, EQUIPEMENT, JET, DESCENTE, REPOS, BUTIN)

#: Ce qui vient d'arriver à quelqu'un, héros ou non.
FAITS = (SOIN_RECU, DEGATS_SUBIS, VENTRE_CHANGE, STATUT_POSE, PV_MAX_GAGNE)

#: Tous les évènements que le moteur sait émettre, pour vérifier les tables.
NOMS = ACTIONS + FAITS


class Event:
    """Un fait de jeu : un nom et des données. Volontairement passif."""

    __slots__ = ("nom", "donnees")

    def __init__(self, nom, donnees=None):
        self.nom = nom
        self.donnees = donnees or {}

    def get(self, cle, defaut=None):
        return self.donnees.get(cle, defaut)

    def __getitem__(self, cle):
        return self.donnees[cle]

    def __repr__(self):
        details = ", ".join(f"{k}={v!r}" for k, v in self.donnees.items())
        return f"<{self.nom} {details}>"


class Recorder:
    """Auditeur qui garde tout : sert aux tests et au débogage d'équilibrage.

        game.listeners.append(recorder)
    """

    def __init__(self):
        self.events = []

    def __call__(self, game, event):
        self.events.append(event)

    def noms(self):
        return [e.nom for e in self.events]

    def actions(self):
        """Les noms des seules actions — ce que le héros vient de faire.

        Les faits d'effet s'intercalent partout depuis l'étape 17.3 : marcher
        creuse le ventre, donc un `pas` est toujours suivi d'un
        `ventre_change`. Un test qui parle d'actions doit le dire.
        """
        return [e.nom for e in self.events if e.nom in ACTIONS]

    def faits(self):
        """Les noms des seuls faits d'effet — ce qui vient d'arriver à quelqu'un."""
        return [e.nom for e in self.events if e.nom in FAITS]

    def of(self, nom):
        return [e for e in self.events if e.nom == nom]

    def count(self, nom):
        return sum(1 for e in self.events if e.nom == nom)

    def clear(self):
        self.events.clear()

    def __len__(self):
        return len(self.events)
