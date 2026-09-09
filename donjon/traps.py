"""Pièges : cachés jusqu'au déclenchement, effet piloté par une fonction."""

TRAP_EFFECTS = {}


def trap(name):
    def wrap(fn):
        TRAP_EFFECTS[name] = fn
        return fn
    return wrap


class Trap:
    def __init__(self, key, name, effect):
        self.key = key
        self.name = name
        self.effect = effect
        self.revealed = False

    def trigger(self, game, actor):
        self.revealed = True
        TRAP_EFFECTS[self.effect](game, actor)


@trap("sommeil")
def _piege_sommeil(game, actor):
    actor.add_status("endormi", 6)
    game.say(game.act(actor, "respires", "respire")
             + " un gaz soporifique et " + ("t'endors !" if actor.is_player else "s'endort !"))


@trap("teleport")
def _piege_teleport(game, actor):
    game.teleport_random(actor)
    game.say(game.act(actor, "es téléporté", "est téléporté") + " ailleurs !")


@trap("explosion")
def _piege_explosion(game, actor):
    dmg = max(1, actor.max_hp // 5)
    actor.take_damage(dmg)
    game.say("BOUM ! " + game.act(actor, "subis", "subit") + f" {dmg} dégâts.")
    game.check_death(actor)


TRAP_TYPES = [
    ("sommeil", "piège à sommeil", "sommeil", 10),
    ("teleport", "piège de téléportation", "teleport", 8),
    ("explosion", "piège explosif", "explosion", 8),
]


def random_trap(rng):
    key, name, effect, _ = rng.weighted([(t, t[3]) for t in TRAP_TYPES])
    return Trap(key, name, effect)
