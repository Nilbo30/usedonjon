"""L'arbre des talents : c'est lui qui déverrouille le jeu, morceau par morceau.

La première vie se joue dans un couloir vide où l'on meurt de faim. Tout le
reste — l'équipement, les créatures, les objets au sol, le coffre du refuge —
se gagne un nœud à la fois. Chaque déblocage augmente ce qu'une vie rapporte,
donc accélère le suivant : c'est le moteur.

Un nœud porte trois choses, et une seule table à éditer pour ajouter du
contenu :

* `effets` — des nombres qui s'ajoutent à la `RunConfig` (+25 de ventre) ;
* `reglages` — des valeurs qui la remplacent (le kit de départ, les cadences) ;
* `unlocks` — des drapeaux que la génération consulte (« grimoires ») ;
* `objets` — ce qui s'ajoute au sac de départ ;
* `classes` — les classes de créatures que le nœud réveille (voir monsters.py) ;
* `repetitions` — combien de fois on peut le reprendre (1 par défaut). Les
  effets d'un nœud repris s'additionnent d'eux-mêmes : le cumul lit la liste
  des achats, pas un ensemble ;
* `facteur_cout` — de combien son prix grimpe à chaque reprise.

Ce dernier point est une règle du jeu, pas un détail : **ce que le héros
apprend, le donjon l'apprend aussi**. Le nœud qui te donne une épée fait venir
les créatures qui se battent au contact, celui qui te donne un bouclier fait
apparaître ce qui encaisse. On n'achète donc jamais des monstres — on achète un
outil, et la menace qu'il éveille est ce qui rendra le suivant désirable.

Ajouter les baguettes, plus tard, sera : un nœud ici, un `unlock="baguettes"`
sur les objets concernés. Le moteur ne bouge pas.
"""

#: Ce qu'une partie vaut avant tout déblocage : un donjon nu.
BASE_VERROUILLEE = {
    # Le donjon s'achète par tranches de dix étages, et chaque tranche
    # franchie fait monter les créatures d'un cran (voir `palier_scaling`) :
    # ouvrir la suite du donjon doit se sentir au premier pas.
    "max_depth": 10,
    "monsters_per_floor": (0, 0),
    "items_per_floor": (0, 0),
    "traps_per_floor": (0, 0),
    "spawn_interval": 10 ** 9,
    "starting_kit": (),
}


class Noeud:
    def __init__(self, key, name, cost, description, branche="", parents=(),
                 effets=None, reglages=None, unlocks=(), objets=(), classes=(),
                 repetitions=1, facteur_cout=1):
        self.key = key
        self.name = name
        self.cost = cost
        self.description = description
        self.branche = branche
        self.parents = tuple(parents)
        self.effets = dict(effets or {})       # additifs
        self.reglages = dict(reglages or {})   # absolus
        self.unlocks = tuple(unlocks)
        self.objets = tuple(objets)            # s'ajoutent au sac de départ
        self.classes = tuple(classes)          # créatures réveillées
        self.repetitions = repetitions         # combien de fois on peut le reprendre
        self.facteur_cout = facteur_cout       # de combien le prix grimpe à chaque reprise

    def accessible(self, acquis):
        return all(parent in acquis for parent in self.parents)

    def reste_a_prendre(self, acquis):
        """Combien de fois ce nœud peut encore être acheté."""
        return self.repetitions - list(acquis).count(self.key)

    def prix(self, acquis=()):
        """Ce que coûte la prochaine reprise : le prix grimpe à chaque fois.

        Sans cela, un nœud répétable serait une aubaine : payer quatre fois
        trois XP pour cent points de ventre ne vaudrait aucune hésitation.
        """
        return round(self.cost
                     * self.facteur_cout ** list(acquis).count(self.key))

    def __repr__(self):
        return f"<Noeud {self.key} {self.cost} XP>"


ARBRE = {}


def _enregistrer(*noeuds):
    for noeud in noeuds:
        ARBRE[noeud.key] = noeud


_enregistrer(
    # --- Survie : ce qui existe dès le premier pas ------------------------
    Noeud("estomac", "Estomac solide", 3,
          "+25 de ventre au départ. Se reprend, de plus en plus cher.",
          branche="Survie", repetitions=4, facteur_cout=3,
          effets={"max_fullness": 25}),
    Noeud("constitution", "Constitution", 3,
          "+5 points de vie au départ. Se reprend, de plus en plus cher.",
          branche="Survie", repetitions=4, facteur_cout=3,
          effets={"start_hp": 5}),
    Noeud("endurance", "Endurance", 12,
          "La marche creuse 8 % de moins. Se reprend, de plus en plus cher.",
          branche="Survie", parents=("estomac",), repetitions=3,
          facteur_cout=3, effets={"endurance": 0.08}),
    Noeud("besace", "Besace", 12, "+2 places dans le sac.",
          branche="Survie", parents=("estomac",), effets={"inventory_size": 2}),
    Noeud("second_souffle", "Second souffle", 220,
          "Une fois par descente, le coup fatal ne l'est pas : tu te relèves "
          "à mi-vie.",
          branche="Survie", parents=("constitution",),
          effets={"reanimations": 1}),

    # --- Équipement : la réponse au problème posé par les créatures -------
    # Ce nœud fait naître le monde vivant : on ne l'achète pas pour se voir
    # offrir une épée — on l'achète pour qu'il y en ait, et il vient avec les
    # créatures qui savent s'en servir. Un nœud qui n'apporterait que du danger
    # ne serait jamais pris ; celui-ci arme le donjon et le joueur du même
    # geste, à lui d'aller la chercher.
    Noeud("epee", "L'épée", 12,
          "Des épées traînent dans le donjon — et des créatures qui savent "
          "s'en servir : ce qui rôdait se met à frapper pour de bon.",
          branche="Équipement", parents=("nourriture",), unlocks=("epees",),
          classes=("guerrier",)),
    Noeud("bouclier", "Le bouclier", 12,
          "Des boucliers apparaissent au sol. Le donjon se protège aussi : "
          "des créatures blindées, difficiles à entamer.",
          branche="Équipement", parents=("epee",),
          unlocks=("boucliers",), classes=("blinde",)),
    Noeud("affutage", "Affûtage", 12,
          "+1 en attaque. Se reprend, de plus en plus cher.",
          branche="Équipement", parents=("epee",), repetitions=3,
          facteur_cout=3, effets={"start_attack": 1}),
    Noeud("cuirasse", "Cuirasse", 12,
          "+1 en défense. Se reprend, de plus en plus cher.",
          branche="Équipement", parents=("bouclier",), repetitions=3,
          facteur_cout=3, effets={"start_defense": 1}),

    # --- Monde vivant : d'abord le danger, l'équipement viendra après -----
    Noeud("pieges", "Pièges", 12,
          "Le sol devient traître. Les créatures marchent dessus aussi : "
          "un piège repéré est une arme.",
          branche="Monde vivant", parents=("nourriture",),
          reglages={"traps_per_floor": (1, 3)}),

    Noeud("butin", "Butin", 35,
          "Les créatures vaincues laissent parfois quelque chose : leur arme, "
          "leur pitance. Ce qu'on ramasse ainsi aiguise l'œil.",
          branche="Monde vivant", parents=("nourriture",), unlocks=("butin",)),

    # --- Trouvailles : ce qui traîne par terre ----------------------------
    # Et voilà pourquoi le premier nœud du jeu peuple déjà le donjon : ce que
    # tu apportes, le donjon le sent. Sans cela il existait un état — des
    # vivres, aucun monstre — où l'on traversait le donjon à pied sans risque,
    # et le multiplicateur de profondeur payait cette promenade mieux que le
    # jeu réel : 44 XP par vie contre 16.
    Noeud("nourriture", "Nourriture", 3,
          "Des vivres apparaissent au sol, et un pour la route. Mais l'odeur "
          "attire les bêtes : le donjon n'est plus désert.",
          branche="Trouvailles", unlocks=("vivres",), objets=("onigiri",),
          classes=("rodeur", "erratique"),
          reglages={"items_per_floor": (2, 4),
                    "monsters_per_floor": (3, 6), "spawn_interval": 30}),
    Noeud("exploration", "Sens de l'orientation", 12,
          "Le héros sait explorer un étage tout seul : il s'arrête dès que "
          "quelque chose bouge, ou qu'il a fini.",
          branche="Trouvailles", unlocks=("exploration",)),
    Noeud("auto_repas", "Repas automatique", 35,
          "Le ventre presque vide, le héros mange sa réserve sans qu'on le "
          "lui dise.",
          branche="Trouvailles", parents=("exploration",),
          unlocks=("auto_repas",)),
    Noeud("auto_soin", "Soin automatique", 90,
          "La vie basse, le héros porte une herbe à sa bouche sans qu'on le "
          "lui dise.",
          branche="Trouvailles", parents=("auto_repas", "herbes"),
          unlocks=("auto_soin",)),
    Noeud("herbes", "Herbes", 35,
          "Herbes et graines rejoignent les trouvailles. Le donjon apprend "
          "aussi à souffler : des créatures frappent puis se retirent.",
          branche="Trouvailles", parents=("nourriture",), unlocks=("herbes",),
          classes=("embusque",), effets={"items_per_floor": (1, 1)}),
    Noeud("projectiles", "Projectiles", 35,
          "Des pierres à lancer traînent au sol : de quoi frapper sans "
          "s'approcher. Le donjon apprend à viser aussi : on te tire dessus "
          "de loin — et un archer abattu laisse ses flèches.",
          branche="Trouvailles", parents=("nourriture",),
          unlocks=("projectiles",), classes=("archer",),
          effets={"items_per_floor": (1, 1)}),
    Noeud("grimoires", "Grimoires", 35,
          "Les parchemins rejoignent les trouvailles — non identifiés.",
          branche="Trouvailles", parents=("nourriture",), unlocks=("grimoires",),
          effets={"items_per_floor": (1, 1)}),
    Noeud("rien_ne_se_perd", "Rien ne se perd", 35,
          "Une chance sur dix de récupérer le projectile qui a touché. "
          "Se reprend trois fois.",
          branche="Trouvailles", parents=("projectiles",), repetitions=3,
          effets={"recuperation_projectile": 0.10}),
    Noeud("intuition", "Intuition", 90,
          "Le premier parchemin ramassé de chaque vie est reconnu d'emblée.",
          branche="Trouvailles", parents=("grimoires",), unlocks=("intuition",)),
    Noeud("abondance", "Abondance", 220, "Deux trouvailles de plus par étage.",
          branche="Trouvailles", parents=("herbes",),
          effets={"items_per_floor": (2, 2)}),

    # --- Le refuge --------------------------------------------------------
    Noeud("coffre", "Le coffre", 35,
          "Un coffre au refuge : ce qu'on y laisse survit à la mort.",
          branche="Le refuge", parents=("nourriture",), unlocks=("coffre",)),
    Noeud("grand_coffre", "Grand coffre", 90, "+4 places dans le coffre.",
          branche="Le refuge", parents=("coffre",), effets={"coffre_places": 4}),
    Noeud("voie_du_retour", "La voie du retour", 90,
          "L'orbe de retour apparaît à partir du quatrième étage : on remonte "
          "avec son butin, et le coffre sert enfin à quelque chose.",
          branche="Le refuge", parents=("coffre",), unlocks=("orbe",)),

    # --- Profond ----------------------------------------------------------
    Noeud("profondeurs", "Les profondeurs", 35,
          "Dix étages de plus. Ce qui les habite est d'un autre calibre : "
          "passé le dixième, les créatures changent de classe.",
          branche="Profond", parents=("epee",),
          reglages={"max_depth": 20}),
    Noeud("abysses", "Les abysses", 90,
          "Dix étages encore, et la même marche à franchir. Peu remontent.",
          branche="Profond", parents=("profondeurs",),
          reglages={"max_depth": 30}),

)

#: Effets qui ne concernent pas la partie mais la progression elle-même.
EFFETS_META = {"coffre_places"}

#: Ordre d'affichage des branches, de la gauche vers la droite de l'éventail.
#: Il n'a aucun effet sur le jeu, mais il décide des croisements : un nœud dont
#: le prérequis vit dans une autre branche tire un trait par-dessus tout ce qui
#: les sépare. Cet ordre-ci n'en laisse aucun (un test le vérifie) ; les trois
#: premières suivent l'ordre où le joueur les découvre. Un croisement subsiste :
#: aucun ordre n'en donne moins, l'arbre ayant désormais plus de liens qui
#: traversent qu'une seule permutation ne peut en démêler.
BRANCHES = ("Survie", "Équipement", "Profond", "Monde vivant", "Le refuge",
            "Trouvailles")


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
    return [noeud for noeud in ARBRE.values()
            if noeud.reste_a_prendre(acquis) > 0 and noeud.accessible(acquis)]


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
