"""Les règles portées : « quand ceci arrive à ce porteur, fais cela ».

Jusqu'ici un seul objet pouvait réagir à un évènement : le héros, par sa table
de compétences, câblée en dur dans `skills.Trainer`. Une règle peut désormais
être **portée** par n'importe quoi — une créature, une arme au poing, l'étage,
le run entier — et le moteur va la chercher là où elle est.

    Regle(events.MONSTRE_VAINCU, lambda d: d.jeu.soigner(d.porteur, 2))

## Qui est concerné par quoi

C'est la vraie spécification de cette étape, et une réponse naïve ferait
exploser le coût. Celle-ci tient en une phrase : **les porteurs concernés sont
ceux que l'évènement nomme, plus leur équipement, plus l'étage, plus le run.**

| porteur | concerné par |
|---|---|
| une créature | tout évènement qui la nomme (`cible`, `source`, `monstre`…) |
| le héros | **toute action** — une action est par contrat la sienne |
| un objet équipé | tout évènement qui nomme son porteur |
| un objet nommé | l'évènement qui le nomme (`arme`, `objet`, `bouclier`) |
| l'étage, le run | tout |

La ligne qui compte est celle qui manque : **un objet posé par terre ne porte
rien tant qu'on ne le touche pas.** Sans elle, chaque pas balaierait
l'inventaire de l'étage et le coût par évènement grandirait avec le nombre
d'objets au sol.

## Ce qu'est un porteur

Tout ce qui a un attribut `regles`. Aucun `isinstance` ici, donc aucun import
d'`entities` ni d'`items` : c'est ce qui évite un cycle, et ça rend le
mécanisme ouvert — poser `regles` sur une nouvelle sorte d'objet suffit à la
rendre porteuse.

## Ce que cette étape ne fait pas

Les **interceptions** (voir questions.py) gardent leur registre global : elles
ne sont pas encore portées. La raison est structurelle et vient de l'étape
17.1 — une question ne reçoit délibérément pas le `Game`, c'est ce qui interdit
toute cascade au milieu d'un calcul de dégâts. Or l'étage et le run ne se
trouvent qu'à partir du `Game`. Les porteurs d'une question se limitent donc à
ce qu'elle nomme déjà, et c'est exactement ce dont le chantier 3 a besoin :
l'arme au poing face à la famille de la créature.
"""

from . import events


class Declenchement:
    """Ce qu'une règle reçoit : le fait, le porteur, et de quoi agir.

    Le pendant de `questions.Question` pour l'autre famille de noms. Même
    forme d'appel — une règle prend un seul argument et lit `porteur` dessus —
    mais celui-ci porte le `Game`, parce qu'une règle a le droit d'agir.
    """

    __slots__ = ("jeu", "evenement", "porteur")

    def __init__(self, jeu, evenement, porteur):
        self.jeu = jeu
        self.evenement = evenement
        self.porteur = porteur

    @property
    def nom(self):
        return self.evenement.nom

    def get(self, cle, defaut=None):
        return self.evenement.get(cle, defaut)

    def __getitem__(self, cle):
        return self.evenement[cle]

    def __repr__(self):
        return f"<déclenchement {self.evenement.nom} sur {self.porteur!r}>"


class Regle:
    """« Quand cet évènement arrive à mon porteur, fais ça. »

    `action` prend un seul argument, le `Declenchement`. `si` est un prédicat
    sur ce même objet. `max_par_tour` plafonne les déclenchements d'un même
    tour — le garde-fou de l'étape 17.4, ici aussi.
    """

    def __init__(self, evenement, action, si=None, max_par_tour=None,
                 etiquette=""):
        if evenement not in events.NOMS:
            raise ValueError(f"évènement inconnu : {evenement!r}")
        self.evenement = evenement
        self.action = action
        self.si = si
        self.max_par_tour = max_par_tour
        self.etiquette = etiquette or getattr(action, "__name__", "règle")

    def __repr__(self):
        return f"<Regle {self.etiquette} sur {self.evenement}>"


class PlafondParTour:
    """Compte les déclenchements d'un tour, et les oublie au suivant.

    Partagé avec `skills.Trainer` : sans ça, deux compteurs identiques
    dériveraient l'un de l'autre.
    """

    def __init__(self):
        self._tour = None
        self._compte = {}

    def autorise(self, regle, tour):
        if regle.max_par_tour is None:
            return True
        if tour != self._tour:
            self._tour, self._compte = tour, {}
        fois = self._compte.get(id(regle), 0)
        if fois >= regle.max_par_tour:
            return False
        self._compte[id(regle)] = fois + 1
        return True


def _ajouter(porteurs, vus, objet):
    """Retient un porteur une seule fois, dans l'ordre où on le rencontre."""
    if objet is None or id(objet) in vus:
        return
    if getattr(objet, "regles", None):
        porteurs.append(objet)
    vus.add(id(objet))


def _ajouter_acteur(porteurs, vus, acteur):
    """Une créature, et ce qu'elle a en main : l'arme porte ses propres règles."""
    if acteur is None:
        return
    _ajouter(porteurs, vus, acteur)
    _ajouter(porteurs, vus, getattr(acteur, "weapon", None))
    _ajouter(porteurs, vus, getattr(acteur, "shield", None))


def porteurs_concernes(jeu, evenement):
    """Les porteurs que cet évènement regarde, sans doublon et dans l'ordre.

    L'ordre est celui du parcours — héros, puis ce que l'évènement nomme, puis
    l'étage, puis le run — donc stable d'une partie à l'autre. Deux règles ne
    peuvent pas se disputer la priorité par hasard.
    """
    porteurs, vus = [], set()
    if evenement.nom in events.ACTIONS:
        # Par contrat, une action est celle du héros : c'est ce qui permet à
        # une paire de bottes de réagir à un simple pas.
        _ajouter_acteur(porteurs, vus, jeu.player)
    for valeur in evenement.donnees.values():
        # `alive` distingue une créature de tout le reste, sans importer
        # `entities` — c'est ce qui garde ce fichier hors du cycle.
        if hasattr(valeur, "alive"):
            _ajouter_acteur(porteurs, vus, valeur)
        else:
            _ajouter(porteurs, vus, valeur)
    _ajouter(porteurs, vus, jeu.level)
    _ajouter(porteurs, vus, jeu.config)
    return porteurs


class Distributeur:
    """L'auditeur qui porte les règles jusqu'à leur porteur.

    Branché sur `Game.listeners` à côté de `skills.Trainer`. Tant qu'aucun
    porteur ne déclare de règle, il ne fait rien — et c'est le cas aujourd'hui.
    """

    def __init__(self):
        self.plafond = PlafondParTour()

    def __call__(self, jeu, evenement):
        for porteur in porteurs_concernes(jeu, evenement):
            for regle in porteur.regles:
                if regle.evenement != evenement.nom:
                    continue
                declenchement = Declenchement(jeu, evenement, porteur)
                if regle.si and not regle.si(declenchement):
                    continue
                if not self.plafond.autorise(regle, jeu.turn):
                    continue
                regle.action(declenchement)
