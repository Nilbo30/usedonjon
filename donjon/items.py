"""Objets : des données + une fonction d'effet enregistrée dans un registre.

Ajouter un objet = ajouter une entrée dans ITEM_TYPES et, si besoin, une
fonction décorée par @effect. Aucun autre fichier à toucher.
"""

from .geom import add

WEAPON = "arme"
SHIELD = "bouclier"
HERB = "herbe"
SCROLL = "parchemin"
FOOD = "nourriture"
AMMO = "projectile"

EFFECTS = {}


def effect(name):
    def wrap(fn):
        EFFECTS[name] = fn
        return fn
    return wrap


class ItemType:
    def __init__(self, key, name, glyph, category, power=0, weight=10,
                 on_use=None, on_hit=None, note=""):
        self.key = key
        self.name = name
        self.glyph = glyph
        self.category = category
        self.power = power          # dégâts d'arme, défense, soin, etc.
        self.weight = weight        # poids de tirage à la génération
        self.on_use = on_use        # effet quand on consomme/lit l'objet
        self.on_hit = on_hit        # effet quand l'objet est lancé sur une cible
        self.note = note

    @property
    def equippable(self):
        return self.category in (WEAPON, SHIELD)

    @property
    def usable(self):
        return self.on_use is not None


class Item:
    """Instance concrète : un type + un bonus d'amélioration (+1, +2...)."""

    def __init__(self, item_type, plus=0):
        self.type = item_type
        self.plus = plus

    @property
    def name(self):
        if self.type.equippable:
            sign = "+" if self.plus >= 0 else ""
            return f"{self.type.name} {sign}{self.plus}"
        return self.type.name

    @property
    def glyph(self):
        return self.type.glyph

    @property
    def category(self):
        return self.type.category

    @property
    def power(self):
        return self.type.power + self.plus

    def use(self, game, user):
        fn = EFFECTS.get(self.type.on_use)
        return fn(game, user, self) if fn else False

    def hit(self, game, thrower, target):
        fn = EFFECTS.get(self.type.on_hit)
        return fn(game, thrower, target, self) if fn else False


# ---------------------------------------------------------------------------
# Effets à l'usage (manger / lire)
# ---------------------------------------------------------------------------

@effect("soigner")
def _soigner(game, user, item):
    healed = user.heal(item.power)
    if healed:
        game.say(game.act(user, "récupères", "récupère") + f" {healed} PV.")
    else:
        game.say(game.act(user, "es", "est") + " déjà au maximum : aucun effet.")
    return True


@effect("herbe_de_vie")
def _herbe_de_vie(game, user, item):
    user.max_hp += item.power
    user.heal(item.power)
    game.say(game.act(user, "gagnes", "gagne") + f" {item.power} PV max !")
    return True


@effect("manger")
def _manger(game, user, item):
    if not user.is_player:
        return False
    before = user.fullness
    user.fullness = min(user.MAX_FULLNESS, user.fullness + item.power)
    game.say(f"Tu manges {item.name}. Ventre : {before} -> {user.fullness}.")
    return True


@effect("confusion_soi")
def _confusion_soi(game, user, item):
    user.add_status("confus", 12)
    game.say(game.act(user, "titubes", "titube") + ", la tête qui tourne.")
    return True


@effect("sommeil_soi")
def _sommeil_soi(game, user, item):
    user.add_status("endormi", 8)
    game.say(game.act(user, "t'endors", "s'endort") + " d'un coup.")
    return True


@effect("lire_lumiere")
def _lire_lumiere(game, user, item):
    game.level.reveal_all()
    game.say("La lumière révèle tout l'étage !")
    return True


@effect("lire_panique")
def _lire_panique(game, user, item):
    room = game.level.room_at(user.pos)
    touched = 0
    for monster in game.monsters():
        if room and room.contains(monster.pos):
            monster.add_status("confus", 10)
            touched += 1
    game.say(f"Un cri strident ! {touched} monstre(s) paniquent." if touched
             else "Un cri strident... personne alentour.")
    return True


@effect("lire_teleport")
def _lire_teleport(game, user, item):
    game.teleport_random(user)
    game.say(game.act(user, "disparais", "disparaît") + " dans un tourbillon !")
    return True


# ---------------------------------------------------------------------------
# Effets au jet (objet lancé sur une cible)
# ---------------------------------------------------------------------------

@effect("jet_degats")
def _jet_degats(game, thrower, target, item):
    dmg = max(1, int(game.rng.variance(item.power)))
    target.take_damage(dmg)
    game.say(f"{item.name} touche {target.name} ({dmg} dégâts).")
    game.check_death(target, killer=thrower)
    return True


@effect("jet_sommeil")
def _jet_sommeil(game, thrower, target, item):
    target.add_status("endormi", 10)
    game.say(f"{target.name} s'endort profondément.")
    return True


@effect("jet_confusion")
def _jet_confusion(game, thrower, target, item):
    target.add_status("confus", 12)
    game.say(f"{target.name} est complètement désorienté.")
    return True


@effect("jet_soin")
def _jet_soin(game, thrower, target, item):
    target.heal(item.power)
    game.say(f"{target.name} récupère de la vitalité.")
    return True


# ---------------------------------------------------------------------------
# Table des objets
# ---------------------------------------------------------------------------

ITEM_TYPES = {}


def _register(*types):
    for t in types:
        ITEM_TYPES[t.key] = t


_register(
    ItemType("herbe_soin", "herbe de soin", "*", HERB, power=15, weight=20,
             on_use="soigner", on_hit="jet_soin"),
    ItemType("herbe_vie", "herbe de vie", "*", HERB, power=4, weight=4,
             on_use="herbe_de_vie", on_hit="jet_soin"),
    ItemType("herbe_confusion", "herbe de confusion", "*", HERB, weight=8,
             on_use="confusion_soi", on_hit="jet_confusion"),
    ItemType("graine_sommeil", "graine de sommeil", "*", HERB, weight=8,
             on_use="sommeil_soi", on_hit="jet_sommeil"),
    ItemType("onigiri", "un onigiri", "%", FOOD, power=50, weight=14,
             on_use="manger"),
    ItemType("parchemin_lumiere", "parchemin de lumière", "?", SCROLL, weight=8,
             on_use="lire_lumiere"),
    ItemType("parchemin_panique", "parchemin de panique", "?", SCROLL, weight=7,
             on_use="lire_panique"),
    ItemType("parchemin_teleport", "parchemin de téléportation", "?", SCROLL, weight=7,
             on_use="lire_teleport"),
    ItemType("fleche", "une flèche", "(", AMMO, power=7, weight=12,
             on_hit="jet_degats"),
    ItemType("epee_bois", "épée en bois", ")", WEAPON, power=3, weight=8),
    ItemType("epee_fer", "épée en fer", ")", WEAPON, power=6, weight=5),
    ItemType("bouclier_bois", "bouclier en bois", "[", SHIELD, power=3, weight=8),
    ItemType("bouclier_fer", "bouclier en fer", "[", SHIELD, power=6, weight=5),
)


def make(key, plus=0):
    return Item(ITEM_TYPES[key], plus)


def random_item(rng, depth=1):
    """Tire un objet au hasard; les objets s'améliorent avec la profondeur."""
    item_type = rng.weighted([(t, t.weight) for t in ITEM_TYPES.values()])
    plus = 0
    if item_type.equippable:
        plus = max(0, rng.randint(-1, 1 + depth // 3))
    return Item(item_type, plus)
