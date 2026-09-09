"""Mode sans interface : jouer une partie depuis une chaîne de commandes.

Sert à tester vite et de façon déterministe (mêmes appels que l'UI) :

    python -m donjon --seed 42 --script "lllj,>"

Langage de commandes :
    h j k l y u b n   déplacement (gauche/bas/haut/droite + diagonales)
    .                 attendre
    ,                 ramasser
    >                 descendre l'escalier
    U<slot>           utiliser / lire / manger l'objet
    E<slot>           équiper ou déséquiper
    D<slot>           poser
    T<slot><dir>      lancer l'objet dans une direction
    #                 le reste de la ligne est un commentaire

Les commandes d'objet sont en MAJUSCULES pour ne pas entrer en conflit avec les
déplacements en diagonale (« u » = haut-droite, « U » = utiliser).

Les emplacements (<slot>) vont de « a » à « l » comme dans l'inventaire.
"""

from .geom import DIRECTIONS

MOVE_KEYS = {
    "h": DIRECTIONS["w"], "l": DIRECTIONS["e"],
    "j": DIRECTIONS["s"], "k": DIRECTIONS["n"],
    "y": DIRECTIONS["nw"], "u": DIRECTIONS["ne"],
    "b": DIRECTIONS["sw"], "n": DIRECTIONS["se"],
}


class ScriptError(ValueError):
    pass


def slot_index(char):
    index = ord(char.lower()) - ord("a")
    if index < 0:
        raise ScriptError(f"emplacement invalide : {char!r}")
    return index


def tokenize(source):
    """Découpe la source en commandes (chaque commande = 1 à 3 caractères)."""
    text = "".join(line.split("#")[0] for line in source.splitlines())
    text = "".join(text.split())          # les espaces ne sont que du confort
    tokens = []
    i = 0
    while i < len(text):
        char = text[i]
        if char in MOVE_KEYS or char in ".,>":
            tokens.append((char,))
            i += 1
        elif char in "UED":
            if i + 1 >= len(text):
                raise ScriptError(f"« {char} » attend un emplacement")
            tokens.append((char, text[i + 1]))
            i += 2
        elif char == "T":
            if i + 2 >= len(text):
                raise ScriptError("« T » attend un emplacement puis une direction")
            tokens.append((char, text[i + 1], text[i + 2]))
            i += 3
        else:
            raise ScriptError(f"commande inconnue : {char!r}")
    return tokens


def run_command(game, token):
    """Exécute une commande déjà découpée. Renvoie True si un tour est passé."""
    char = token[0]
    if char in MOVE_KEYS:
        return game.cmd_move(MOVE_KEYS[char])
    if char == ".":
        return game.cmd_wait()
    if char == ",":
        return game.cmd_pickup()
    if char == ">":
        return game.cmd_descend()
    if char == "U":
        return game.cmd_use(slot_index(token[1]))
    if char == "E":
        return game.cmd_equip(slot_index(token[1]))
    if char == "D":
        return game.cmd_drop(slot_index(token[1]))
    if char == "T":
        direction = MOVE_KEYS.get(token[2])
        if direction is None:
            raise ScriptError(f"direction de jet invalide : {token[2]!r}")
        return game.cmd_throw(slot_index(token[1]), direction)
    raise ScriptError(f"commande non gérée : {token!r}")


def run_script(game, source, on_step=None):
    """Joue toute la partition. `on_step(game, token, acted)` après chaque commande."""
    from .game import PLAYING
    for token in tokenize(source):
        if game.state != PLAYING:
            break
        acted = run_command(game, token)
        if on_step:
            on_step(game, token, acted)
    return game


def autoplay(game, steps=200, on_step=None):
    """Bot bête mais fonctionnel : mange, se soigne, tape, et fonce à l'escalier.

    Sert de test de robustesse rapide : des centaines de tours joués sans
    exception, avec une graine fixe donc reproductibles.
    """
    from . import path
    from .game import PLAYING
    from .geom import chebyshev, step_toward

    for _ in range(steps):
        if game.state != PLAYING:
            break
        player = game.player
        # `can_attack` et non la simple adjacence : une cible en diagonale
        # derrière un coin de mur est hors d'atteinte, et s'acharner dessus
        # ferait tourner le bot dans le vide sans consommer de tour.
        adjacent = [m for m in game.monsters() if game.can_attack(player, m)]
        bloques = [m for m in game.monsters()
                   if chebyshev(m.pos, player.pos) == 1
                   and not game.can_attack(player, m)]
        if adjacent:
            acted = game.cmd_move(step_toward(player.pos, adjacent[0].pos))
        elif bloques:
            acted = _se_replacer(game, bloques[0])
        elif _tir_possible(game) is not None:
            slot, direction = _tir_possible(game)
            acted = game.cmd_throw(slot, direction)
        elif _a_mieux_en_main(game) is not None:
            acted = game.cmd_equip(_a_mieux_en_main(game))
        elif player.hp <= player.max_hp // 3 and _find(game, "herbe_soin") is not None:
            acted = game.cmd_use(_find(game, "herbe_soin"))
        elif player.fullness <= 25 and _find(game, "onigiri") is not None:
            acted = game.cmd_use(_find(game, "onigiri"))
        elif (player.hp < player.max_hp * 0.8 and player.fullness > 30
              and not game.monsters_visible()):
            acted = game.cmd_rest()          # souffler tant que le ventre suit
        elif game.level.items.get(player.pos) is not None:
            acted = game.cmd_pickup()
        elif not game.monsters_visible() and _objet_proche(game, path):
            acted = _seek(game, path, _objet_proche(game, path))
        elif player.pos == game.level.stairs:
            acted = game.cmd_descend()
        else:
            acted = _seek(game, path, game.level.stairs)
        if not acted:
            acted = game.cmd_wait()      # jamais de tour perdu : pas de blocage
        if on_step:
            on_step(game, ("auto",), acted)
    return game


def _tir_possible(game, portee=6):
    """(slot, direction) pour lancer une flèche sur une cible alignée, sinon None.

    Le bot ne lançait rien : mesurer un talent de projectiles avec lui, c'était
    mesurer sa cécité. Il vise en ligne droite, la portée d'un jet.
    """
    from .geom import ALL_DIRS, add

    slot = _find(game, "fleche")
    if slot is None:
        return None
    for direction in ALL_DIRS:
        pos = game.player.pos
        for _ in range(portee):
            pos = add(pos, direction)
            if not game.level.walkable(pos):
                break
            cible = game.actor_at(pos)
            if cible is not None:
                if not cible.is_player:
                    return slot, direction
                break
    return None


def _a_mieux_en_main(game):
    """Le slot d'un équipement meilleur que celui porté, sinon None.

    Sans ça le bot ramasse l'épée en fer et continue à cogner avec celle en
    bois : toute mesure sur l'armement mesurerait sa cécité, pas le jeu.
    """
    from . import items as items_mod

    player = game.player
    porte = {items_mod.WEAPON: player.weapon, items_mod.SHIELD: player.shield}
    for index, objet in enumerate(player.inventory):
        if objet.category not in porte:
            continue
        actuel = porte[objet.category]
        if objet is not actuel and objet.power > (actuel.power if actuel else 0):
            return index
    return None


def _find(game, key):
    for index, item in enumerate(game.player.inventory):
        if item.type.key == key:
            return index
    return None


def _objet_proche(game, path, portee=14):
    """L'objet connu le plus proche s'il vaut le détour, sinon None.

    Sans ça le bot ne ramasse que ce qu'il piétine, et toute mesure sur
    l'économie des objets ne dit rien du jeu — seulement de sa trajectoire.
    """
    if len(game.player.inventory) >= game.player.max_items:
        return None
    connus = [pos for pos in game.level.items if pos in game.level.explored]
    if not connus:
        return None
    bloques = {m.pos for m in game.monsters()}
    meilleur, distance = None, portee + 1
    for pos in connus:
        chemin = path.find_path(game.level, game.player.pos, pos, bloques,
                                allowed=game.level.explored)
        if chemin is not None and len(chemin) < distance:
            meilleur, distance = pos, len(chemin)
    return meilleur


def _se_replacer(game, cible):
    """Contourner un coin de mur pour pouvoir frapper la cible au tour suivant."""
    from .geom import ALL_DIRS, add, chebyshev

    for direction in ALL_DIRS:
        if not game.can_step(game.player, direction):
            continue
        depuis = add(game.player.pos, direction)
        vers_cible = (cible.pos[0] - depuis[0], cible.pos[1] - depuis[1])
        if (chebyshev(depuis, cible.pos) == 1
                and not game.corner_blocked(depuis, vers_cible)):
            return game.cmd_move(direction)
    return False


def _seek(game, path, goal):
    """Un pas vers `goal` via le BFS, sinon un pas au hasard (anti-blocage)."""
    from .geom import ALL_DIRS

    blocked = {a.pos for a in game.actors if a.alive and a is not game.player}
    direction = path.step_along(game.level, game.player.pos, goal, blocked)
    if direction and game.cmd_move(direction):
        return True
    for direction in game.rng.shuffle(list(ALL_DIRS)):
        if game.can_step(game.player, direction):
            return game.cmd_move(direction)
    return game.cmd_wait()
