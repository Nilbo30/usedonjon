"""IA des monstres : une fonction par comportement, choisie par `behaviour`."""

from . import path
from .geom import ALL_DIRS, add, chebyshev, step_toward

BEHAVIOURS = {}


def behaviour(name):
    def wrap(fn):
        BEHAVIOURS[name] = fn
        return fn
    return wrap


def take_turn(game, monster):
    fn = BEHAVIOURS.get(monster.behaviour, BEHAVIOURS["chasseur"])
    fn(game, monster)


def _sees_player(game, monster):
    player = game.player
    room = game.level.room_at(monster.pos)
    if room and room.contains(player.pos):
        return True
    return chebyshev(monster.pos, player.pos) <= 1


def _approach(game, monster, target_pos):
    """Un pas vers la cible : chemin calculé, puis replis gloutons si bloqué."""
    blocked = {a.pos for a in game.actors if a.alive and a is not monster}
    blocked.discard(target_pos)
    options = []
    routed = path.step_along(game.level, monster.pos, target_pos, blocked)
    if routed:
        options.append(routed)
    wanted = step_toward(monster.pos, target_pos)
    options.append(wanted)
    if wanted[0] and wanted[1]:
        options += [(wanted[0], 0), (0, wanted[1])]
    for d in options:
        if d != (0, 0) and game.try_move(monster, d):
            return True
    return False


@behaviour("chasseur")
def _chasseur(game, monster):
    player = game.player
    if game.can_attack(monster, player):
        game.attack(monster, player)
        return
    if _sees_player(game, monster):
        monster.target_pos = player.pos
    if monster.target_pos:
        if _approach(game, monster, monster.target_pos):
            if monster.pos == monster.target_pos:
                monster.target_pos = None
            return
        monster.target_pos = None
    _wander(game, monster)


@behaviour("erratique")
def _erratique(game, monster):
    """Vole n'importe comment : une fois sur deux, direction aléatoire."""
    player = game.player
    if game.can_attack(monster, player) and game.rng.chance(0.7):
        game.attack(monster, player)
        return
    if game.rng.chance(0.5):
        _wander(game, monster)
        return
    _chasseur(game, monster)


@behaviour("peureux")
def _peureux(game, monster):
    """Frappe puis recule : garde ses distances quand il est blessé."""
    player = game.player
    dist = chebyshev(monster.pos, player.pos)
    if monster.hp < monster.max_hp // 2 and dist <= 2:
        away = step_toward(player.pos, monster.pos)
        if game.try_move(monster, away):
            return
    if game.can_attack(monster, player):
        game.attack(monster, player)
        return
    _chasseur(game, monster)


def _wander(game, monster):
    dirs = list(ALL_DIRS)
    game.rng.shuffle(dirs)
    for d in dirs:
        if game.level.walkable(add(monster.pos, d)) and game.try_move(monster, d):
            return
    game.pass_turn(monster)
