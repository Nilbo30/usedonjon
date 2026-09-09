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


@behaviour("archer")
def _archer(game, monster):
    """Tire dès qu'il t'a dans sa ligne, et se décale d'un pas pour t'y mettre.

    Une tourelle immobile se contourne et cesse d'exister ; celui-ci cherche
    l'alignement, ce qui rend les couloirs dangereux et apprend à casser sa
    ligne. Il ne tire jamais à travers un des siens — se mettre derrière une
    autre créature est donc un abri réel.
    """
    joueur = game.player
    direction = _direction_de_tir(game, monster.pos, joueur)
    if direction:
        game.tirer(monster, direction)
        return
    if game.can_attack(monster, joueur):
        game.attack(monster, joueur)      # au contact il se défend, mal
        return
    if _sees_player(game, monster) and _se_placer(game, monster):
        return
    _chasseur(game, monster)


def _direction_de_tir(game, depuis, cible):
    """La direction où tirer pour toucher la cible depuis cette case, ou None."""
    from .game import PORTEE_TIR

    for direction in ALL_DIRS:
        _pos, touche = game.ligne_de_tir(depuis, direction, PORTEE_TIR)
        if touche is cible:
            return direction
    return None


def _se_placer(game, monster):
    """Un pas de côté qui donne une ligne de tir, s'il y en a un."""
    for direction in ALL_DIRS:
        case = add(monster.pos, direction)
        if not game.level.walkable(case) or game.actor_at(case):
            continue
        if _direction_de_tir(game, case, game.player):
            return game.try_move(monster, direction)
    return False


def _wander(game, monster):
    dirs = list(ALL_DIRS)
    game.rng.shuffle(dirs)
    for d in dirs:
        if game.level.walkable(add(monster.pos, d)) and game.try_move(monster, d):
            return
    game.pass_turn(monster)
