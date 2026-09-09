"""Outils partagés par les tests : une partie propre et contrôlable."""

from donjon.entities import Monster
from donjon.game import Game
from donjon.monsters import SPECIES


def sandbox(seed=1, max_depth=5):
    """Une partie sans monstres, objets ni pièges : on place ce qu'on teste."""
    game = Game(seed=seed, max_depth=max_depth)
    game.actors = [game.player]
    game.level.items.clear()
    game.level.traps.clear()
    game.player.pos = _open_spot(game)
    game.player.energy = 100
    return game


def _open_spot(game):
    """Une case de salle avec au moins un voisin libre dans chaque direction."""
    for room in game.level.rooms:
        if room.w >= 3 and room.h >= 3:
            return (room.x + 1, room.y + 1)
    return game.player.pos


def species(key):
    for entry in SPECIES:
        if entry["key"] == key:
            return entry
    raise KeyError(key)


def place_monster(game, pos, key="mamel", **overrides):
    data = dict(species(key))
    data.update(overrides)
    monster = Monster(data)
    monster.pos = pos
    game.actors.append(monster)
    return monster
