"""Interface terminal (curses). Elle ne fait qu'appeler les commandes de Game.

Aucune règle de jeu ici : l'UI lit l'état et envoie des `cmd_*`. On peut donc
brancher une autre interface (web, pygame) sans toucher au moteur.
"""

import curses

from .game import DEAD, PLAYING, WON, Game
from .geom import DIRECTIONS
from .script import MOVE_KEYS

LOG_LINES = 5
HELP = [
    "hjkl / yubn / flèches : se déplacer et attaquer",
    ",  ramasser      >  descendre l'escalier      .  attendre",
    "i  inventaire     c  compétences             q  quitter",
    "?  aide",
    "",
    "Dans l'inventaire : lettre de l'objet puis",
    "  u utiliser   e équiper   t lancer   d poser   échap annuler",
]

ARROWS = {
    curses.KEY_LEFT: DIRECTIONS["w"],
    curses.KEY_RIGHT: DIRECTIONS["e"],
    curses.KEY_UP: DIRECTIONS["n"],
    curses.KEY_DOWN: DIRECTIONS["s"],
}

COLOR_OF_GLYPH = {
    "@": 1, "*": 2, "?": 2, "%": 2, "(": 2, ")": 2, "[": 2, ">": 3, "^": 4,
}


def run(seed=None, max_depth=5):
    curses.wrapper(lambda stdscr: _main(stdscr, seed, max_depth))


def _main(stdscr, seed, max_depth):
    curses.curs_set(0)
    _init_colors()
    game = Game(seed=seed, max_depth=max_depth)
    message = None
    while True:
        _draw(stdscr, game, message)
        message = None
        if game.state != PLAYING:
            stdscr.getch()
            return
        key = stdscr.getch()
        try:
            char = chr(key)
        except ValueError:
            char = ""
        if char in ("q", "Q"):
            return
        if char == "?":
            _overlay(stdscr, "Aide", HELP)
            continue
        if char == "i":
            message = _inventory_flow(stdscr, game)
            continue
        if char == "c":
            _overlay(stdscr, "Compétences de ce run", _skill_lines(game))
            continue
        if key in ARROWS:
            game.cmd_move(ARROWS[key])
            continue
        if char in MOVE_KEYS:
            game.cmd_move(MOVE_KEYS[char])
        elif char == ".":
            game.cmd_wait()
        elif char == ",":
            game.cmd_pickup()
        elif char == ">":
            game.cmd_descend()


def _skill_lines(game):
    lignes = [f"{nom:<16} niv. {niveau:<3} {acquis}/{requis}"
              for nom, niveau, acquis, requis in game.skill_lines()]
    return lignes or ["Tu n'as encore rien pratiqué."]


def _init_colors():
    if not curses.has_colors():
        return
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)     # héros
    curses.init_pair(2, curses.COLOR_YELLOW, -1)   # objets
    curses.init_pair(3, curses.COLOR_GREEN, -1)    # escalier
    curses.init_pair(4, curses.COLOR_RED, -1)      # pièges et monstres
    curses.init_pair(5, curses.COLOR_WHITE, -1)


def _attr(glyph, is_monster):
    if not curses.has_colors():
        return curses.A_NORMAL
    if is_monster:
        return curses.color_pair(4) | curses.A_BOLD
    pair = COLOR_OF_GLYPH.get(glyph)
    if pair:
        return curses.color_pair(pair) | (curses.A_BOLD if glyph == "@" else 0)
    return curses.A_NORMAL


def _draw(stdscr, game, message=None):
    stdscr.erase()
    height, width = stdscr.getmaxyx()
    _addstr(stdscr, 0, 0, game.status_line()[: width - 1], curses.A_REVERSE)

    monster_positions = {m.pos for m in game.monsters()}
    for y, row in enumerate(game.render()):
        if y + 1 >= height - LOG_LINES - 1:
            break
        for x, glyph in enumerate(row):
            if x >= width - 1 or glyph == " ":
                continue
            _addch(stdscr, y + 1, x, glyph, _attr(glyph, (x, y) in monster_positions))

    log_top = max(1, height - LOG_LINES - 1)
    for offset, line in enumerate(game.log.tail(LOG_LINES)):
        _addstr(stdscr, log_top + offset, 0, line[: width - 1])

    footer = message or {
        PLAYING: "? aide   i inventaire   c compétences   q quitter",
        DEAD: "Tu es mort. Une touche pour quitter.",
        WON: "Victoire ! Une touche pour quitter.",
    }[game.state]
    _addstr(stdscr, height - 1, 0, footer[: width - 1], curses.A_REVERSE)
    stdscr.refresh()


def _inventory_flow(stdscr, game):
    """Affiche le sac, laisse choisir un objet puis une action."""
    player = game.player
    if not player.inventory:
        return "Ton sac est vide."
    lines = []
    for index, item in enumerate(player.inventory):
        marks = []
        if item is player.weapon:
            marks.append("équipée")
        if item is player.shield:
            marks.append("équipé")
        suffix = f"  <{', '.join(marks)}>" if marks else ""
        lines.append(f"{chr(ord('a') + index)}) {item.name}{suffix}")
    _overlay(stdscr, "Sac — choisis une lettre (échap pour fermer)", lines, wait=False)
    key = stdscr.getch()
    if key in (27, -1):
        return None
    slot = key - ord("a")
    if not 0 <= slot < len(player.inventory):
        return "Pas d'objet à cette lettre."
    item = player.inventory[slot]
    _overlay(stdscr, item.name,
             ["u) utiliser / lire / manger", "e) équiper ou ranger",
              "t) lancer (puis une direction)", "d) poser", "échap) annuler"],
             wait=False)
    action = stdscr.getch()
    action_char = chr(action) if 0 <= action < 256 else ""
    if action_char == "u":
        game.cmd_use(slot)
    elif action_char == "e":
        game.cmd_equip(slot)
    elif action_char == "d":
        game.cmd_drop(slot)
    elif action_char == "t":
        _overlay(stdscr, f"Lancer {item.name}", ["Direction ? (hjkl / yubn / flèches)"],
                 wait=False)
        key = stdscr.getch()
        direction = ARROWS.get(key)
        if direction is None and 0 <= key < 256:
            direction = MOVE_KEYS.get(chr(key))
        if direction is None:
            return "Jet annulé."
        game.cmd_throw(slot, direction)
    return None


def _overlay(stdscr, title, lines, wait=True):
    height, width = stdscr.getmaxyx()
    box_w = min(width - 2, max(len(title), *(len(l) for l in lines or [""])) + 4)
    box_h = min(height - 2, len(lines) + 4)
    top = max(0, (height - box_h) // 2)
    left = max(0, (width - box_w) // 2)
    win = curses.newwin(box_h, box_w, top, left)
    win.box()
    try:
        win.addstr(0, 2, f" {title[: box_w - 6]} ", curses.A_BOLD)
        for index, line in enumerate(lines[: box_h - 3]):
            win.addstr(index + 2, 2, line[: box_w - 4])
    except curses.error:
        pass
    win.refresh()
    if wait:
        stdscr.getch()


def _addstr(win, y, x, text, attr=curses.A_NORMAL):
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


def _addch(win, y, x, char, attr=curses.A_NORMAL):
    try:
        win.addch(y, x, char, attr)
    except curses.error:
        pass
