"""Évènements d'action : ce que le héros vient de faire.

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
| `monstre_vaincu` | `monstre` (Actor), `arme` (Item ou None), `distance`        |
| `ramassage`      | `objet`                                                     |
| `pose`           | `objet`                                                     |
| `usage_objet`    | `objet`, `categorie`                                        |
| `equipement`     | `objet`, `categorie`, `equipe` (True si porté, False rangé) |
| `jet`            | `objet`, `cible` (Actor ou None), `direction`               |
| `descente`       | `etage` (le nouvel étage)                                   |

`arme` vaut None à mains nues : c'est volontaire, une compétence « pugilat »
pourra s'y accrocher sans rien changer ici.
"""

PAS = "pas"
ATTENTE = "attente"
COUP = "coup"
MONSTRE_VAINCU = "monstre_vaincu"
RAMASSAGE = "ramassage"
POSE = "pose"
USAGE_OBJET = "usage_objet"
EQUIPEMENT = "equipement"
JET = "jet"
DESCENTE = "descente"

#: Tous les évènements que le moteur sait émettre, pour vérifier les tables.
NOMS = (PAS, ATTENTE, COUP, MONSTRE_VAINCU, RAMASSAGE, POSE, USAGE_OBJET,
        EQUIPEMENT, JET, DESCENTE)


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

    def of(self, nom):
        return [e for e in self.events if e.nom == nom]

    def count(self, nom):
        return sum(1 for e in self.events if e.nom == nom)

    def clear(self):
        self.events.clear()

    def __len__(self):
        return len(self.events)
