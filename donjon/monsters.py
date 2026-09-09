"""Bestiaire : deux axes et une table.

La **famille** dit ce qu'est la créature — son allure, les étages où on la
croise, et bientôt ses forces et ses faiblesses. La **classe** dit ce qu'elle
fait : son comportement (voir ai.py), sa façon d'attaquer, et le talent qui la
réveille dans le donjon.

Une créature est une case de ce croisement : (animal, guerrier) est le rat
enragé, (mort-vivant, archer) sera l'archer squelette. La profondeur décide de
la famille — les animaux en haut, les homoncules tout en bas — et l'arbre des
talents décide des classes : `unlock` sur une classe se lit comme les autres
verrous du jeu. Ce que le héros apprend, le donjon l'apprend aussi.

Les chiffres restent écrits à la main, créature par créature : un bestiaire se
règle à l'oreille, pas au produit de deux multiplicateurs. Les deux axes
portent le sens, pas l'arithmétique.

Les créatures ne donnent pas d'XP : on progresse en agissant, pas en tuant
(voir skills.py).
"""

#: Ce qu'est la créature. `forme` et `couleur` servent d'allure par défaut.
FAMILLES = {
    "animal": {
        "nom": "Animal", "couleur": "#b07a52", "forme": "rond",
        "note": "Bêtes du haut du donjon : nombreuses, peu dangereuses seules.",
    },
    "humanoide": {
        "nom": "Humanoïde", "couleur": "#4fae86", "forme": "rond",
        "note": "Elles se battent avec des outils — les tiens, souvent.",
    },
    "homoncule": {
        "nom": "Homoncule", "couleur": "#8a8fa8", "forme": "carre",
        "note": "Créatures fabriquées : chair assemblée, pierre et métal.",
    },
}

#: Ce que fait la créature. `unlock` : le drapeau qui la réveille, s'il en faut
#: un. Sans `unlock`, la classe est là dès que le donjon est peuplé.
CLASSES = {
    "rodeur": {
        "nom": "Rôdeur", "behaviour": "chasseur",
        "note": "Vient au contact, sans finesse.",
    },
    "erratique": {
        "nom": "Erratique", "behaviour": "erratique",
        "note": "Se déplace n'importe comment : impossible à anticiper.",
    },
    "embusque": {
        "nom": "Embusqué", "behaviour": "peureux",
        "note": "Frappe et recule dès qu'elle est blessée.",
    },
    "guerrier": {
        "nom": "Guerrier", "behaviour": "chasseur",
        "note": "Frappe fort : on choisit ses combats.",
    },
    "archer": {
        "nom": "Archer", "behaviour": "archer",
        "note": "Te vise de loin dès que tu es sur sa ligne : casse l'alignement.",
    },
    "blinde": {
        "nom": "Blindé", "behaviour": "chasseur",
        "note": "Encaisse tout, mais lentement : frapper plus fort, ou fuir.",
    },
}

#: Une entrée = une case du croisement. `depth` (min, max) borne les étages,
#: `weight` pèse le tirage ; `color` et `shape` ne servent qu'à l'affichage et
#: retombent sur ceux de la famille.
BESTIAIRE = [
    {
        "key": "mamel", "name": "Mamel", "glyph": "m",
        "famille": "animal", "classe": "rodeur",
        "hp": 8, "attack": 4, "defense": 1,
        "depth": (1, 4), "weight": 20, "color": "#7fd06b",
    },
    {
        "key": "rat", "name": "Rat des cavernes", "glyph": "r",
        "famille": "animal", "classe": "rodeur",
        "hp": 10, "attack": 5, "defense": 1,
        "depth": (1, 5), "weight": 18,
    },
    {
        "key": "chauve_souris", "name": "Chauve-souris", "glyph": "b",
        "famille": "animal", "classe": "erratique",
        "hp": 9, "attack": 4, "defense": 0, "speed": 150,
        "depth": (2, 7), "weight": 14, "color": "#9b6fd0", "shape": "pointu",
    },
    {
        "key": "rat_enrage", "name": "Rat enragé", "glyph": "r",
        "famille": "animal", "classe": "guerrier",
        "hp": 14, "attack": 8, "defense": 2,
        "depth": (2, 6), "weight": 12, "color": "#c2603f",
    },
    {
        "key": "tatou", "name": "Tatou cuirassé", "glyph": "t",
        "famille": "animal", "classe": "blinde",
        "hp": 18, "attack": 5, "defense": 6, "speed": 80,
        "depth": (3, 7), "weight": 10, "color": "#9c8b6a", "shape": "carre",
    },
    {
        "key": "limace", "name": "Limace cracheuse", "glyph": "l",
        "famille": "animal", "classe": "archer",
        "hp": 12, "attack": 7, "defense": 1, "speed": 90,
        # Rare à dessein : à 21 % des apparitions, l'archer coûtait plus que
        # son nœud ne rapporte (22,9 contre 24,0 XP/vie). À 11 %, il se croise
        # assez pour enseigner sa leçon sans occuper le donjon.
        "depth": (3, 7), "weight": 5, "color": "#8fd0a8",
    },
    {
        "key": "gobelin", "name": "Gobelin", "glyph": "g",
        "famille": "humanoide", "classe": "rodeur",
        "hp": 16, "attack": 8, "defense": 3,
        "depth": (3, 8), "weight": 16,
    },
    {
        "key": "brute_gobeline", "name": "Brute gobeline", "glyph": "B",
        "famille": "humanoide", "classe": "guerrier",
        "hp": 22, "attack": 11, "defense": 4,
        "depth": (5, 10), "weight": 12, "color": "#3e8f6d",
    },
    {
        "key": "arbaletrier", "name": "Arbalétrier gobelin", "glyph": "a",
        "famille": "humanoide", "classe": "archer",
        "hp": 15, "attack": 9, "defense": 3,
        "depth": (5, 10), "weight": 5, "color": "#6fae8f",
    },
    {
        "key": "tas_de_chair", "name": "Tas de chair", "glyph": "c",
        "famille": "homoncule", "classe": "rodeur",
        "hp": 40, "attack": 9, "defense": 2, "speed": 80,
        "depth": (9, 99), "weight": 8, "color": "#c07a86", "shape": "rond",
    },
    {
        "key": "automate", "name": "Automate de métal", "glyph": "A",
        "famille": "homoncule", "classe": "blinde",
        "hp": 34, "attack": 11, "defense": 10, "speed": 70,
        "depth": (10, 99), "weight": 9, "color": "#a8b0bd",
    },
    {
        "key": "golem", "name": "Golem de pierre", "glyph": "G",
        "famille": "homoncule", "classe": "guerrier",
        "hp": 30, "attack": 12, "defense": 7, "speed": 60,
        "depth": (8, 99), "weight": 10,
    },
    {
        "key": "sorcier", "name": "Sorcier bleu", "glyph": "s",
        "famille": "humanoide", "classe": "embusque",
        "hp": 14, "attack": 9, "defense": 2,
        "depth": (6, 99), "weight": 12, "color": "#5b8ad0",
    },
]


def _composer(entree):
    """Une entrée complétée par sa famille et sa classe.

    C'est la seule forme que le reste du jeu manipule : `Monster` y lit son
    comportement sans savoir qu'il vient de la classe.
    """
    famille = FAMILLES[entree["famille"]]
    classe = CLASSES[entree["classe"]]
    espece = dict(entree)
    espece.setdefault("color", famille["couleur"])
    espece.setdefault("shape", famille["forme"])
    espece["behaviour"] = classe["behaviour"]
    return espece


#: Le bestiaire résolu, dans l'ordre de la table : c'est lui qu'on tire.
SPECIES = [_composer(entree) for entree in BESTIAIRE]


def table_for_depth(depth, classes=None):
    """[(espèce, poids)] des créatures pouvant apparaître à cet étage.

    `classes` limite le tirage aux classes réveillées ; `None` les autorise
    toutes — le moteur, le bot et les tests jouent au bestiaire complet.

    Quand aucune créature réveillée n'habite cet étage, **on ne vide pas
    l'étage** : on rappelle les plus proches, que `_scale_to_depth` mettra à
    niveau. Sans ça, ne rien débloquer rendrait le donjon plus sûr — et refuser
    les talents deviendrait la meilleure stratégie.
    """
    autorisees = [espece for espece in SPECIES
                  if classes is None or espece["classe"] in classes]
    ici = [(espece, espece["weight"]) for espece in autorisees
           if espece["depth"][0] <= depth <= espece["depth"][1]]
    if ici or not autorisees:
        return ici

    def ecart(espece):
        bas, haut = espece["depth"]
        return max(bas - depth, depth - haut, 0)

    proche = min(ecart(espece) for espece in autorisees)
    return [(espece, espece["weight"]) for espece in autorisees
            if ecart(espece) == proche]
