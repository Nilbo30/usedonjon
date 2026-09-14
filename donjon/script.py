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
    """Bot d'essai : il mange, se soigne, frappe, fuit ce qui le dépasse, lit
    un parchemin quand il n'a plus le choix, et fonce à l'escalier.

    Il sert de test de robustesse — des centaines de tours sans exception, à
    graine fixe donc reproductibles — et d'instrument de mesure. À ce titre
    ses lacunes comptent : ce qu'il ne sait pas faire, aucune campagne ne peut
    l'évaluer.
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
        redoutables = [m for m in adjacent if _echange_perdant(game, m)]
        if redoutables and _urgence(game):
            # Mourir avec sa téléportation en poche est le travers du bot
            # bête : quand l'échange est perdu et la vie basse, on lit.
            acted = game.cmd_use(_parchemin_de_secours(game))
        elif redoutables and not _acculé(game):
            acted = _fuir(game, path)        # on ne s'arrête pas pour ce qu'on
        elif adjacent:                        # ne peut pas battre : on descend
            acted = game.cmd_move(step_toward(player.pos, adjacent[0].pos))
        elif _find(game, "herbe_vie") is not None:
            acted = game.cmd_use(_find(game, "herbe_vie"))   # PV définitifs
        elif bloques:
            acted = _se_replacer(game, bloques[0])
        elif _baton_possible(game) is not None:
            slot, direction = _baton_possible(game)
            acted = game.cmd_use(slot, direction)
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


def _echange_perdant(game, monstre):
    """L'échange coup pour coup tourne-t-il à notre désavantage ?

    Le bot frappait tout ce qui passait à sa portée, y compris un automate qui
    le tue en cinq coups quand il lui en faut huit. Compter, c'est déjà jouer.
    """
    joueur = game.player
    inflige = max(1.0, joueur.attack - monstre.defense * 0.7)
    encaisse = max(1.0, monstre.attack - joueur.defense * 0.7)
    return monstre.hp / inflige > joueur.hp / encaisse


def _urgence(game):
    """Vie basse et parchemin en poche : le moment de s'en servir."""
    joueur = game.player
    return (joueur.hp <= joueur.max_hp * 0.4
            and _parchemin_de_secours(game) is not None)


def _parchemin_de_secours(game):
    """Le slot d'un parchemin qui sort d'un mauvais pas, ou None.

    On préfère ce qu'on connaît ; à bout de souffle, on lit n'importe quoi —
    c'est ce que fait un joueur, et c'est ainsi qu'on identifie un parchemin.
    """
    from . import items as items_mod

    joueur = game.player
    for cle in ("parchemin_teleport", "parchemin_panique"):
        slot = _find(game, cle)
        if slot is not None and joueur.inventory[slot].identifie:
            return slot
    if joueur.hp > joueur.max_hp * 0.25:
        return None
    for index, objet in enumerate(joueur.inventory):
        if objet.category == items_mod.SCROLL and not objet.identifie:
            return index
    return None


def _acculé(game):
    """Aucune case libre où reculer : autant frapper."""
    from .geom import ALL_DIRS, add

    for direction in ALL_DIRS:
        case = add(game.player.pos, direction)
        if game.can_step(game.player, direction) and not game.actor_at(case):
            return False
    return True


def _fuir(game, path):
    """Continuer vers l'escalier sans s'arrêter pour ce qu'on ne peut pas battre."""
    if game.player.pos == game.level.stairs:
        return game.cmd_descend()
    return _seek(game, path, game.level.stairs)


def _baton_possible(game):
    """(slot, direction) pour un souffle de flammes qui vaut une charge, sinon None.

    Cinq charges par bâton : le brûler sur un rat ne mesure rien. Le bot ne
    l'allume que pour au moins deux cibles, ou pour une seule dont l'échange
    coup pour coup lui serait défavorable. Il choisit la direction qui touche
    le plus de monde.

    Sans ça, une campagne sur le nœud « Les bâtons » mesurerait sa cécité — le
    bot ne s'équipait pas, le bot ne lisait pas, et les deux fois la mesure
    était muette avant qu'on le lui apprenne.
    """
    from .geom import ALL_DIRS

    slot = _find(game, "baton_flammes")
    if slot is None:
        return None
    baton = game.player.inventory[slot]
    meilleure, combien = None, 0
    for direction in ALL_DIRS:
        cibles = [acteur for acteur
                  in game.acteurs_dans_la_zone(game.player.pos, direction,
                                               baton.type.portee,
                                               baton.type.largeur)
                  if not acteur.is_player]
        if len(cibles) > combien:
            meilleure, combien = direction, len(cibles)
    if meilleure is None:
        return None
    if combien >= 2:
        return slot, meilleure
    cibles = [a for a in game.acteurs_dans_la_zone(
        game.player.pos, meilleure, baton.type.portee, baton.type.largeur)
        if not a.is_player]
    if cibles and _echange_perdant(game, cibles[0]):
        return slot, meilleure
    return None


def _tir_possible(game, portee=6):
    """(slot, direction) pour lancer une flèche sur une cible alignée, sinon None.

    Le bot ne lançait rien : mesurer un talent de projectiles avec lui, c'était
    mesurer sa cécité. Il vise en ligne droite, la portée d'un jet.
    """
    from .geom import ALL_DIRS, add

    slot = _find(game, "pierre")
    if slot is None:
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


# --------------------------------------------------------------------------
# Choisir son arme — et savoir en changer
# --------------------------------------------------------------------------
# Le brief du chantier des matières le disait sans détour : « le bot devra
# apprendre à décider d'un pivot. S'il ne sait pas le faire, **il ne mesure
# rien** ». Comparer les `power` bruts, c'était choisir une arme comme on
# choisit un nombre ; décider d'un pivot, c'est répondre à trois questions que
# le jeu pose vraiment :
#
#   1. qu'est-ce que je vais croiser à cet étage ? (les familles, pondérées)
#   2. qu'est-ce que cette matière leur fait ? (la table des affinités)
#   3. qu'est-ce que je perds en lâchant ce que je tiens ? (ma compétence de
#      matière ne vaut que l'objet en main)
#
# Rien de tout ça n'est une règle de jeu : le moteur n'a pas bougé d'une ligne.
# C'est le bot qui apprend à lire ce qui était déjà écrit.

#: Marge exigée pour changer d'équipement. Sans elle, deux armes à un pour
#: cent l'une de l'autre se relaieraient à chaque étage, et chaque échange
#: coûte un tour : le bot passerait sa vie à se rhabiller.
MARGE_DE_PIVOT = 1.10


def _familles_attendues(game):
    """Ce qu'on risque de croiser à cet étage, famille par famille.

    Le bot juge sur la population de l'étage et non sur le monstre qu'il a sous
    le nez : sans ça il changerait d'arme à chaque rencontre, ce qui n'est pas
    un pivot mais un tic.
    """
    from . import monsters as monsters_mod

    table = monsters_mod.table_for_depth(game.depth, game.config.classes)
    total = sum(poids for _, poids in table)
    if not total:
        return {}
    parts = {}
    for espece, poids in table:
        famille = espece["famille"]
        parts[famille] = parts.get(famille, 0) + poids / total
    return parts


def _mordant_moyen(matiere, parts):
    """Ce que cette matière vaut contre la population attendue."""
    from . import affinites as affinites_mod

    if not matiere or not parts:
        return 1.0
    return sum(part * affinites_mod.multiplicateur(matiere, famille)
               for famille, part in parts.items())


def _familles_si(joueur, objet):
    """Les familles équipées si on prenait cet objet, l'autre main inchangée.

    Le détail qui compte : une compétence de matière se gagne dès qu'on porte
    la matière, arme **ou** bouclier. Lâcher l'épée en bois quand le bouclier
    est en bois ne fait donc rien perdre. Un bot qui l'ignore surestime le prix
    du pivot, et ne pivote jamais.
    """
    from . import items as items_mod

    autre = (joueur.shield if objet.category == items_mod.WEAPON
             else joueur.weapon)
    familles = []
    for porte in (objet, autre):
        if porte is None:
            continue
        familles.append(porte.type.skill)
        if porte.type.matiere:
            familles.append(porte.type.matiere)
    return familles


def _valeur_en_main(game, objet, parts):
    """Ce que vaut cet équipement **dans ces mains-là, à cet étage-là**.

    Une arme se juge aux dégâts qu'elle sortira pour cent d'énergie : la forme
    donne l'attaque et la cadence, la matière donne le mordant, la compétence
    donne le reste. Un bouclier se juge à ce qu'il évite d'encaisser — sa
    défense, et la matière qui repousse ce qui frappe.
    """
    from . import items as items_mod
    from .entities import ACTION_COST

    joueur = game.player
    familles = _familles_si(joueur, objet)
    mordant = _mordant_moyen(objet.type.matiere, parts)
    if objet.category == items_mod.WEAPON:
        attaque = (joueur.base_attack + objet.power
                   + joueur.skills.bonus("attaque", familles))
        cadence = objet.type.cadence or ACTION_COST
        return attaque * mordant * ACTION_COST / cadence
    defense = (joueur.base_defense + objet.power
               + joueur.skills.bonus("defense", familles))
    return defense * mordant


def _a_mieux_en_main(game):
    """Le slot d'un équipement meilleur que celui porté, sinon None.

    Sans ça le bot ramasse l'épée en fer et continue à cogner avec celle en
    bois : toute mesure sur l'armement mesurerait sa cécité, pas le jeu.
    """
    from . import items as items_mod

    player = game.player
    porte = {items_mod.WEAPON: player.weapon, items_mod.SHIELD: player.shield}
    parts = _familles_attendues(game)
    meilleur, ecart = None, MARGE_DE_PIVOT
    for index, objet in enumerate(player.inventory):
        if objet.category not in porte:
            continue
        actuel = porte[objet.category]
        if objet is actuel:
            continue
        tenu = _valeur_en_main(game, actuel, parts) if actuel else 0.0
        candidat = _valeur_en_main(game, objet, parts)
        if tenu <= 0:
            return index          # une main vide se remplit sans discuter
        if candidat / tenu > ecart:
            meilleur, ecart = index, candidat / tenu
    return meilleur


def _find(game, key):
    for index, item in enumerate(game.player.inventory):
        if item.type.key == key:
            return index
    return None


def _objet_proche(game, path, portee=14):
    """L'objet connu le plus proche s'il vaut le détour, sinon None.

    Sans ça le bot ne ramasse que ce qu'il piétine, et toute mesure sur
    l'économie des objets ne dit rien du jeu — seulement de sa trajectoire.

    Le ventre creux, il ne se détourne plus que pour ce qui se mange : il
    mourait de faim en allant chercher une troisième épée.
    """
    from . import items as items_mod

    joueur = game.player
    if len(joueur.inventory) >= joueur.max_items:
        return None
    connus = [pos for pos in game.level.items if pos in game.level.explored]
    if joueur.fullness < joueur.max_fullness * 0.4:
        connus = [pos for pos in connus
                  if game.level.items[pos].category == items_mod.FOOD]
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
