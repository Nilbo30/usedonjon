"""L'arbre des talents : c'est lui qui déverrouille le jeu, morceau par morceau.

La première vie se joue dans un couloir vide où l'on meurt de faim. Tout le
reste — l'équipement, les créatures, les objets au sol, le coffre du refuge —
se gagne un nœud à la fois. Chaque déblocage augmente ce qu'une vie rapporte,
donc accélère le suivant : c'est le moteur.

Un nœud porte trois choses, et une seule table à éditer pour ajouter du
contenu :

* `effets` — des nombres qui s'ajoutent à la `RunConfig` (+25 de ventre) ;
* `reglages` — des valeurs qui la remplacent (le kit de départ, les cadences) ;
* `unlocks` — des drapeaux que la génération consulte (« grimoires »).

Ajouter les baguettes, plus tard, sera : un nœud ici, un `unlock="baguettes"`
sur les objets concernés. Le moteur ne bouge pas.
"""

#: Ce qu'une partie vaut avant tout déblocage : un donjon nu.
BASE_VERROUILLEE = {
    "monsters_per_floor": (0, 0),
    "items_per_floor": (0, 0),
    "traps_per_floor": (0, 0),
    "spawn_interval": 10 ** 9,
    "starting_kit": (),
}


class Noeud:
    def __init__(self, key, name, cost, description, branche="", parents=(),
                 effets=None, reglages=None, unlocks=()):
        self.key = key
        self.name = name
        self.cost = cost
        self.description = description
        self.branche = branche
        self.parents = tuple(parents)
        self.effets = dict(effets or {})       # additifs
        self.reglages = dict(reglages or {})   # absolus
        self.unlocks = tuple(unlocks)

    def accessible(self, acquis):
        return all(parent in acquis for parent in self.parents)

    def __repr__(self):
        return f"<Noeud {self.key} {self.cost} XP>"


ARBRE = {}


def _enregistrer(*noeuds):
    for noeud in noeuds:
        ARBRE[noeud.key] = noeud


_enregistrer(
    # --- Survie : ce qui existe dès le premier pas ------------------------
    Noeud("estomac", "Estomac solide", 3, "+25 de ventre au départ.",
          branche="Survie", effets={"max_fullness": 25}),
    Noeud("constitution", "Constitution", 3, "+5 points de vie au départ.",
          branche="Survie", effets={"start_hp": 5}),
    Noeud("besace", "Besace", 12, "+2 places dans le sac.",
          branche="Survie", parents=("estomac",), effets={"inventory_size": 2}),
    Noeud("ventre_ogre", "Ventre d'ogre", 35, "+40 de ventre.",
          branche="Survie", parents=("estomac",), effets={"max_fullness": 40}),
    Noeud("endurci", "Endurci", 35, "+10 points de vie.",
          branche="Survie", parents=("constitution",), effets={"start_hp": 10}),
    Noeud("second_souffle", "Second souffle", 220, "+20 points de vie.",
          branche="Survie", parents=("endurci",), effets={"start_hp": 20}),

    # --- Équipement : la réponse au problème posé par les créatures -------
    Noeud("barda", "Barda", 12,
          "Tu pars avec une épée, un bouclier et un onigiri.",
          branche="Équipement", parents=("creatures",),
          reglages={"starting_kit": ("epee_bois", "bouclier_bois", "onigiri")}),
    Noeud("affutage", "Affûtage", 35, "+1 en attaque.",
          branche="Équipement", parents=("barda",), effets={"start_attack": 1}),
    Noeud("cuirasse", "Cuirasse", 35, "+1 en défense.",
          branche="Équipement", parents=("barda",), effets={"start_defense": 1}),

    # --- Monde vivant : d'abord le danger, l'équipement viendra après -----
    Noeud("creatures", "Créatures", 12,
          "Le donjon se peuple : monstres et pièges. Tu n'as que tes poings — "
          "cogner entraîne le pugilat.",
          branche="Monde vivant",
          reglages={"monsters_per_floor": (3, 6), "traps_per_floor": (1, 3),
                    "spawn_interval": 30}),
    Noeud("butin", "Butin", 35,
          "Les créatures vaincues laissent parfois quelque chose.",
          branche="Monde vivant", parents=("creatures",), unlocks=("butin",)),
    Noeud("faune", "Faune variée", 90,
          "Des espèces plus nombreuses, et un donjon plus habité.",
          branche="Monde vivant", parents=("creatures",),
          reglages={"monsters_per_floor": (4, 8), "spawn_interval": 22}),

    # --- Trouvailles : ce qui traîne par terre ----------------------------
    Noeud("fouille", "Fouille", 12,
          "Des objets apparaissent au sol : vivres et projectiles.",
          branche="Trouvailles", reglages={"items_per_floor": (2, 4)}),
    Noeud("herbes", "Herbes", 35,
          "Herbes et graines rejoignent les trouvailles.",
          branche="Trouvailles", parents=("fouille",), unlocks=("herbes",)),
    Noeud("grimoires", "Grimoires", 35,
          "Les parchemins rejoignent les trouvailles — non identifiés.",
          branche="Trouvailles", parents=("fouille",), unlocks=("grimoires",)),
    Noeud("intuition", "Intuition", 90,
          "Le premier parchemin ramassé de chaque vie est reconnu d'emblée.",
          branche="Trouvailles", parents=("grimoires",), unlocks=("intuition",)),
    Noeud("armurerie", "Armurerie", 90,
          "Armes et boucliers se trouvent aussi dans le donjon.",
          branche="Trouvailles", parents=("fouille",), unlocks=("armurerie",)),
    Noeud("abondance", "Abondance", 220, "Deux trouvailles de plus par étage.",
          branche="Trouvailles", parents=("herbes",),
          reglages={"items_per_floor": (4, 6)}),

    # --- Le refuge --------------------------------------------------------
    Noeud("coffre", "Le coffre", 35,
          "Un coffre au refuge : ce qu'on y laisse survit à la mort.",
          branche="Le refuge", parents=("fouille",), unlocks=("coffre",)),
    Noeud("grand_coffre", "Grand coffre", 90, "+4 places dans le coffre.",
          branche="Le refuge", parents=("coffre",), effets={"coffre_places": 4}),

    # --- Profond ----------------------------------------------------------
    Noeud("voie_du_retour", "La voie du retour", 220,
          "L'orbe de retour apparaît à partir du quatrième étage.",
          branche="Profond", parents=("grimoires", "coffre"),
          unlocks=("orbe",)),
)

#: Effets qui ne concernent pas la partie mais la progression elle-même.
EFFETS_META = {"coffre_places"}

#: Ordre d'affichage des branches.
BRANCHES = ("Survie", "Équipement", "Monde vivant", "Trouvailles",
            "Le refuge", "Profond")


def par_branche():
    """Les nœuds groupés par branche, dans l'ordre d'affichage."""
    groupes = {branche: [] for branche in BRANCHES}
    for noeud in ARBRE.values():
        groupes.setdefault(noeud.branche, []).append(noeud)
    for noeuds in groupes.values():
        noeuds.sort(key=lambda n: (n.cost, n.name))
    return [(branche, groupes[branche]) for branche in BRANCHES
            if groupes.get(branche)]


def disponibles(acquis):
    """Les nœuds qu'on pourrait acheter maintenant, prix mis à part."""
    return [noeud for cle, noeud in ARBRE.items()
            if cle not in acquis and noeud.accessible(acquis)]


def profondeurs():
    """Le rang de chaque nœud : le plus long chemin qui y mène.

    C'est ce qui l'éloigne du centre dans l'éventail — les nœuds sans prérequis
    au premier rang, leurs enfants au deuxième. Se recalcule tout seul quand on
    ajoute un nœud.
    """
    rangs = {}

    def rang(cle):
        if cle not in rangs:
            parents = ARBRE[cle].parents
            rangs[cle] = 1 + max((rang(parent) for parent in parents),
                                 default=-1)
        return rangs[cle]

    return {cle: rang(cle) for cle in ARBRE}
