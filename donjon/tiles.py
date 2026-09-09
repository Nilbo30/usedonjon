"""Types de cases : une valeur + ses propriétés (simple table de données).

Ajouter un terrain (eau, herbes hautes, sable mouvant...) = une entrée ici.
"""

WALL = "wall"
FLOOR = "floor"
CORRIDOR = "corridor"
STAIRS = "stairs"

PROPERTIES = {
    #            glyphe, traversable, bloque la vue
    WALL:     {"glyph": "#", "walkable": False, "opaque": True},
    FLOOR:    {"glyph": ".", "walkable": True,  "opaque": False},
    CORRIDOR: {"glyph": ".", "walkable": True,  "opaque": False},
    STAIRS:   {"glyph": ">", "walkable": True,  "opaque": False},
}


def glyph(tile):
    return PROPERTIES[tile]["glyph"]


def walkable(tile):
    return PROPERTIES[tile]["walkable"]


def opaque(tile):
    return PROPERTIES[tile]["opaque"]
