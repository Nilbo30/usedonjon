"""Le hub : le refuge entre deux descentes.

C'est un étage comme un autre — même carte, même déplacement, même souris —
mais sans monstre, sans faim et sans escalier de retour. Ajouter un marchand ou
une forge, plus tard, sera poser quelque chose dans cette pièce, pas construire
une interface.
"""

from . import tiles
from .config import RunConfig
from .dungeon import Level, Room

LARGEUR, HAUTEUR = 25, 13


def config(base=None):
    """La config d'un séjour au hub : rien de ce qui menace n'y opère."""
    base = base or RunConfig()
    return base.replace(is_hub=True, hunger_enabled=False,
                        monsters_per_floor=(0, 0), items_per_floor=(0, 0),
                        traps_per_floor=(0, 0), spawn_interval=10 ** 9)


def generer():
    """Une salle unique : un coffre à gauche, l'escalier du donjon à droite."""
    level = Level(LARGEUR, HAUTEUR)
    salle = Room(2, 2, LARGEUR - 4, HAUTEUR - 4)
    level.rooms.append(salle)
    for pos in salle.cells():
        level.set_tile(pos, tiles.FLOOR)

    level.chest = (salle.x + 2, salle.y + salle.h // 2)
    level.set_tile(level.chest, tiles.CHEST)

    level.stairs = (salle.x + salle.w - 3, salle.y + salle.h // 2)
    level.set_tile(level.stairs, tiles.STAIRS)

    level.explored |= set(level.walkable_cells())
    for x in range(LARGEUR):
        for y in range(HAUTEUR):
            level.explored.add((x, y))
    return level


def depart(level):
    """Où le héros apparaît en arrivant : au milieu, entre les deux."""
    return (LARGEUR // 2, HAUTEUR // 2)
