"""Outils partagés par les tests : une partie propre et contrôlable.

Contient aussi le **filet du chantier des déclencheurs** : `trace_de_partie`
rejoue une vie de bot à graine fixe et en tire une empreinte. Tant qu'une
refonte du moteur laisse les empreintes intactes, elle n'a rien changé au jeu —
c'est la seule façon de tenir « à comportement identique » autrement qu'en
intention.

L'empreinte porte sur l'**état**, jamais sur les messages : reformuler une
phrase du journal ne doit pas casser le filet, changer un dégât doit le casser.
"""

import hashlib

from donjon.entities import Monster
from donjon.game import Game
from donjon.monsters import SPECIES


def sandbox(seed=1, max_depth=5, config=None):
    """Une partie sans monstres, objets ni pièges : on place ce qu'on teste.

    `config` sert aux scènes qui ont besoin de réglages précis — un héros qui
    encaisse longtemps, un ventre assez grand pour mesurer la faim.
    """
    if config is not None:
        game = Game(seed=seed, config=config)
    else:
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


# --------------------------------------------------------------------------
# Le filet : empreintes de parties rejouées
# --------------------------------------------------------------------------
def instantane(game):
    """L'état complet qui compte, en une ligne stable et lisible.

    Tout ce qu'une refonte du moteur pourrait déplacer sans le vouloir : la
    position, les jauges, les stats dérivées (donc les bonus de compétence),
    le sac, les statuts, les monstres vivants, les niveaux, l'XP versée.
    """
    joueur = game.player
    sac = ",".join(f"{o.type.key}x{o.quantite}+{o.plus}"
                   for o in joueur.inventory)
    statuts = ",".join(f"{n}:{t}" for n, t in sorted(joueur.statuses.items())
                       if t > 0)
    monstres = ";".join(f"{m.name}@{m.pos[0]}.{m.pos[1]}:{m.hp}"
                        for m in sorted(game.monsters(), key=lambda m: m.pos))
    sol = ";".join(f"{pos[0]}.{pos[1]}={o.type.key}x{o.quantite}"
                   for pos, o in sorted(game.level.items.items()))
    niveaux = ",".join(f"{c}:{n}"
                       for c, n in sorted(joueur.skills.levels.items()))
    arme = joueur.weapon.type.key if joueur.weapon else "-"
    bouclier = joueur.shield.type.key if joueur.shield else "-"
    return (f"T{game.turn} E{game.depth} P{joueur.pos[0]}.{joueur.pos[1]} "
            f"PV{joueur.hp}/{joueur.max_hp} V{joueur.fullness} "
            f"A{joueur.attack} D{joueur.defense} [{arme}/{bouclier}] "
            f"S({sac}) St({statuts}) M({monstres}) O({sol}) "
            f"C({niveaux}) X{joueur.skills.total_xp():.3f}")


def trace_de_partie(graine, talents=(), tours=4000):
    """Rejoue une vie de bot et renvoie (empreinte, repères, trace complète).

    Les repères — étage, tours, PV, XP versée — accompagnent l'empreinte pour
    qu'un échec dise **ce qui** a bougé et pas seulement qu'il a bougé. Sans
    eux, une empreinte cassée n'apprend rien.
    """
    from donjon.script import autoplay
    from donjon.session import Session

    session = Session(sauvegarde=False, seed=graine)
    session.meta.xp = 10 ** 9
    restant = list(talents)
    while restant:
        avant = len(restant)
        for cle in list(restant):
            if session.meta.acheter(cle):
                restant.remove(cle)
        if len(restant) == avant:
            raise AssertionError(f"talents inachetables : {restant}")
    session.meta.xp = 0

    jeu = session.descendre()
    lignes = [instantane(jeu)]
    autoplay(jeu, tours, on_step=lambda g, _t, _a: lignes.append(instantane(g)))
    bilan = jeu.summary
    reperes = {
        "etage": bilan.deepest if bilan else jeu.deepest,
        "tours": bilan.turns if bilan else jeu.turn,
        "pv": jeu.player.hp,
        "xp": round(jeu.player.skills.total_xp(), 3),
        "pas": len(lignes),
    }
    trace = "\n".join(lignes)
    return hashlib.md5(trace.encode("utf-8")).hexdigest(), reperes, trace


def trace_de_partition(construire, partition):
    """Rejoue une partition écrite à la main sur une scène contrôlée.

    Le bot ne lance presque jamais, ne pose jamais rien et ne déséquipe pas :
    mesuré sur ses huit vies, `pose` n'apparaît pas une seule fois et `jet` une
    seule. Ces commandes-là ne peuvent être couvertes que délibérément.
    """
    from donjon.script import run_script

    jeu = construire()
    lignes = [instantane(jeu)]
    run_script(jeu, partition,
               on_step=lambda g, _t, _a: lignes.append(instantane(g)))
    reperes = {"tours": jeu.turn, "pv": jeu.player.hp,
               "xp": round(jeu.player.skills.total_xp(), 3),
               "pas": len(lignes)}
    trace = "\n".join(lignes)
    return hashlib.md5(trace.encode("utf-8")).hexdigest(), reperes, trace


def donner(game, cle, quantite=1, plus=0):
    """Met un objet dans le sac du héros, sans passer par le hasard."""
    from donjon import items as items_mod

    objet = items_mod.make(cle, plus, game.player.registre, quantite)
    game.player.add_item(objet)
    return objet


def poser_au_sol(game, pos, cle, quantite=1):
    from donjon import items as items_mod

    game.level.items[pos] = items_mod.make(cle, 0, game.player.registre,
                                           quantite)


def poser_piege(game, pos, cle="explosion"):
    from donjon import traps as traps_mod

    nom = next(t[1] for t in traps_mod.TRAP_TYPES if t[0] == cle)
    game.level.traps[pos] = traps_mod.Trap(cle, nom, cle)
