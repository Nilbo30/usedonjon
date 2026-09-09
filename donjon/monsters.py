"""Bestiaire : de la donnée pure. Une entrée = une créature.

`depth` (min, max) définit à quels étages l'espèce peut apparaître,
`behaviour` choisit l'IA (voir ai.py).
"""

SPECIES = [
    {
        "key": "mamel", "name": "Mamel", "glyph": "m",
        "hp": 8, "attack": 4, "defense": 1, "exp": 3,
        "depth": (1, 4), "weight": 20, "behaviour": "chasseur",
    },
    {
        "key": "rat", "name": "Rat des cavernes", "glyph": "r",
        "hp": 10, "attack": 5, "defense": 1, "exp": 4,
        "depth": (1, 5), "weight": 18, "behaviour": "chasseur",
    },
    {
        "key": "chauve_souris", "name": "Chauve-souris", "glyph": "b",
        "hp": 9, "attack": 4, "defense": 0, "exp": 5, "speed": 150,
        "depth": (2, 7), "weight": 14, "behaviour": "erratique",
    },
    {
        "key": "gobelin", "name": "Gobelin", "glyph": "g",
        "hp": 16, "attack": 8, "defense": 3, "exp": 9,
        "depth": (3, 8), "weight": 16, "behaviour": "chasseur",
    },
    {
        "key": "golem", "name": "Golem de pierre", "glyph": "G",
        "hp": 30, "attack": 12, "defense": 7, "exp": 22, "speed": 60,
        "depth": (5, 99), "weight": 10, "behaviour": "chasseur",
    },
    {
        "key": "sorcier", "name": "Sorcier bleu", "glyph": "s",
        "hp": 14, "attack": 9, "defense": 2, "exp": 15,
        "depth": (6, 99), "weight": 12, "behaviour": "peureux",
    },
]


def table_for_depth(depth):
    """[(espèce, poids)] des créatures pouvant apparaître à cet étage."""
    return [
        (s, s["weight"])
        for s in SPECIES
        if s["depth"][0] <= depth <= s["depth"][1]
    ] or [(SPECIES[0], 1)]
