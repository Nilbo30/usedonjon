"""Objets : des données + une fonction d'effet enregistrée dans un registre.

Ajouter un objet = ajouter une entrée dans ITEM_TYPES et, si besoin, une
fonction décorée par @effect. Aucun autre fichier à toucher.

Chaque objet porte une `skill` : la compétence que son usage entraîne (voir
skills.py). Elle est déduite de la catégorie par défaut, et ne se déclare que
pour distinguer des familles d'armes (épée, hache, arc...).
"""

from .geom import add

WEAPON = "arme"
SHIELD = "bouclier"
HERB = "herbe"
SCROLL = "parchemin"
FOOD = "nourriture"
AMMO = "projectile"

#: Apparences des objets non identifiés, par catégorie. Ajouter une catégorie
#: ici suffit à la rendre mystérieuse — les potions, le jour venu.
APPARENCES = {
    SCROLL: ["parchemin ocre", "parchemin taché", "parchemin froissé",
             "parchemin scellé", "parchemin runique", "parchemin poussiéreux"],
}

#: Catégories dont on ignore l'effet tant qu'on ne les a pas essayées.
CATEGORIES_A_IDENTIFIER = set(APPARENCES)


class Registre:
    """Ce que le héros a identifié, et sous quel nom il voit le reste.

    C'est de l'état de run : chaque partie rebat les apparences, et tout est
    perdu à la mort.
    """

    def __init__(self, rng=None):
        self.connus = set()
        self.apparences = {}
        self.intuition_disponible = True   # « Intuition » : une fois par vie
        if rng is not None:
            self.melanger(rng)

    def melanger(self, rng):
        for categorie, pool in APPARENCES.items():
            cles = sorted(cle for cle, type_objet in ITEM_TYPES.items()
                          if type_objet.category == categorie)
            noms = rng.shuffle(list(pool))
            for cle, nom in zip(cles, noms):
                self.apparences[cle] = nom

    def a_identifier(self, type_objet):
        return type_objet.category in CATEGORIES_A_IDENTIFIER

    def connu(self, cle):
        return cle in self.connus

    def identifier(self, cle):
        """Marque l'objet comme identifié. Vrai si c'est une découverte."""
        if cle in self.connus:
            return False
        self.connus.add(cle)
        return True

    def apparence(self, cle):
        return self.apparences.get(cle, "objet inconnu")


#: Compétence entraînée par défaut, selon la catégorie de l'objet.
SKILL_PAR_CATEGORIE = {
    WEAPON: "epee",
    SHIELD: "bouclier",
    HERB: "herboristerie",
    SCROLL: "parchemins",
    FOOD: "nourriture",
    AMMO: "jet",
}

EFFECTS = {}


def effect(name):
    def wrap(fn):
        EFFECTS[name] = fn
        return fn
    return wrap


class ItemType:
    def __init__(self, key, name, glyph, category, power=0, weight=10,
                 on_use=None, on_hit=None, note="", skill=None, depth_min=1,
                 unlock=None):
        self.key = key
        self.name = name
        self.glyph = glyph
        self.category = category
        self.skill = skill or SKILL_PAR_CATEGORIE.get(category)
        self.power = power          # dégâts d'arme, défense, soin, etc.
        self.weight = weight        # poids de tirage à la génération
        self.on_use = on_use        # effet quand on consomme/lit l'objet
        self.on_hit = on_hit        # effet quand l'objet est lancé sur une cible
        self.note = note
        self.depth_min = depth_min  # étage à partir duquel l'objet apparaît
        self.unlock = unlock        # talent requis pour qu'il apparaisse

    @property
    def equippable(self):
        return self.category in (WEAPON, SHIELD)

    @property
    def usable(self):
        return self.on_use is not None


class Item:
    """Instance concrète : un type + un bonus d'amélioration (+1, +2...).

    `registre` est celui du run : il décide si l'objet se montre sous son vrai
    nom ou sous une apparence. Un objet créé hors partie (tests) n'en a pas et
    reste donc toujours identifié.
    """

    def __init__(self, item_type, plus=0, registre=None):
        self.type = item_type
        self.plus = plus
        self.registre = registre

    @property
    def identifie(self):
        if self.registre is None or not self.registre.a_identifier(self.type):
            return True
        return self.registre.connu(self.type.key)

    @property
    def name(self):
        if not self.identifie:
            return self.registre.apparence(self.type.key)
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

    @property
    def description(self):
        """Une ligne expliquant l'effet. Les chiffres d'équipement sont calculés
        pour tenir compte du bonus (+1, +2...) de l'exemplaire."""
        if not self.identifie:
            return "Effet inconnu — il faudra l'essayer pour le savoir."
        if self.category == WEAPON:
            return f"Arme : +{self.power} en attaque."
        if self.category == SHIELD:
            return f"Bouclier : +{self.power} en défense."
        return self.type.note

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
    healed = user.heal(item.power + user.bonus("soin"))
    if healed:
        game.say(game.act(user, "récupères", "récupère") + f" {healed} PV.")
    else:
        game.say(game.act(user, "es", "est") + " déjà au maximum : aucun effet.")
    return True


@effect("herbe_de_vie")
def _herbe_de_vie(game, user, item):
    user.base_max_hp += item.power
    user.heal(item.power)
    game.say(game.act(user, "gagnes", "gagne") + f" {item.power} PV max !")
    return True


@effect("manger")
def _manger(game, user, item):
    if not user.is_player:
        return False
    before = user.fullness
    gagne = item.power + user.bonus("satiete")
    user.fullness = min(user.max_fullness, user.fullness + gagne)
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
    duree = 10 + user.bonus("duree_effet")
    touched = 0
    for monster in game.monsters():
        if room and room.contains(monster.pos):
            monster.add_status("confus", duree)
            touched += 1
    game.say(f"Un cri strident ! {touched} monstre(s) paniquent." if touched
             else "Un cri strident... personne alentour.")
    return True


@effect("orbe_retour")
def _orbe_retour(game, user, item):
    """Interrompt la descente et renvoie au refuge, acquis compris.

    Le prix est ailleurs : la profondeur atteinte repart de zéro, donc la
    prochaine mort rapportera moins de progression permanente.
    """
    from .game import RETOUR

    game.end_run(RETOUR, f"Tu brises {item.type.name} et tout devient blanc...")
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
    dmg = max(1, int(game.rng.variance(item.power + thrower.bonus("degats_jet"))))
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
             on_use="soigner", on_hit="jet_soin",
             note="Rend 15 PV. Lancée, elle soigne la cible.", unlock="herbes"),
    ItemType("herbe_vie", "herbe de vie", "*", HERB, power=4, weight=4,
             on_use="herbe_de_vie", on_hit="jet_soin",
             note="Augmente définitivement les PV maximum de 4.", unlock="herbes"),
    ItemType("herbe_confusion", "herbe de confusion", "*", HERB, weight=8,
             on_use="confusion_soi", on_hit="jet_confusion",
             note="À lancer : désoriente la cible 12 tours. Mangée, "
                  "elle te désoriente toi.", unlock="herbes"),
    ItemType("graine_sommeil", "graine de sommeil", "*", HERB, weight=8,
             on_use="sommeil_soi", on_hit="jet_sommeil",
             note="À lancer : endort la cible 10 tours, sans défense. "
                  "Mangée, elle t'endort 8 tours.", unlock="herbes"),
    ItemType("onigiri", "un onigiri", "%", FOOD, power=50, weight=14,
             on_use="manger", note="Rend 50 points de ventre.", unlock="vivres"),
    ItemType("parchemin_lumiere", "parchemin de lumière", "?", SCROLL, weight=8,
             on_use="lire_lumiere", note="Révèle tout l'étage, escalier compris.", unlock="grimoires"),
    ItemType("parchemin_panique", "parchemin de panique", "?", SCROLL, weight=7,
             on_use="lire_panique",
             note="Désoriente 10 tours tous les monstres de la salle.", unlock="grimoires"),
    ItemType("parchemin_teleport", "parchemin de téléportation", "?", SCROLL,
             weight=7, on_use="lire_teleport",
             note="Te téléporte au hasard sur l'étage. Utile pour fuir.", unlock="grimoires"),
    ItemType("orbe_retour", "orbe de retour", "o", SCROLL, weight=6, depth_min=4,
             on_use="orbe_retour", skill="parchemins",
             note="Te ramène au refuge avec tes objets et tes compétences. "
                  "En échange, la profondeur atteinte est remise à zéro.", unlock="orbe"),
    ItemType("fleche", "une flèche", "(", AMMO, power=7, weight=12,
             on_hit="jet_degats", note="À lancer : 7 dégâts à distance.", unlock="projectiles"),
    ItemType("epee_bois", "épée en bois", ")", WEAPON, power=3, weight=8, unlock="armurerie"),
    ItemType("epee_fer", "épée en fer", ")", WEAPON, power=6, weight=5, unlock="armurerie"),
    ItemType("bouclier_bois", "bouclier en bois", "[", SHIELD, power=3, weight=8, unlock="armurerie"),
    ItemType("bouclier_fer", "bouclier en fer", "[", SHIELD, power=6, weight=5, unlock="armurerie"),
)


def make(key, plus=0, registre=None):
    return Item(ITEM_TYPES[key], plus, registre)


#: Part minimale du tirage revenant à la nourriture, quel que soit le nombre de
#: familles d'objets débloquées par ailleurs. C'est un plancher : quand peu de
#: choses sont ouvertes, les vivres gardent la part plus large qui leur revient.
PART_NOURRITURE = 0.30


def _part_reservee(candidats):
    """Rend à la nourriture sa part du tirage, sans rien garantir par étage.

    Sans ce rééquilibrage, chaque famille débloquée noie les vivres : leur part
    tombe de 100 % à 11,7 % une fois tout ouvert, et acheter du contenu revient
    à s'affamer. Le corriger en posant un vivre d'office à chaque étage serait
    plus simple, mais on le sentirait — un étage doit pouvoir être avare.
    """
    vivres = [(t, w) for t, w in candidats if t.category == FOOD]
    autres = [(t, w) for t, w in candidats if t.category != FOOD]
    if not vivres or not autres:
        return candidats
    facteur = (PART_NOURRITURE / (1 - PART_NOURRITURE)
               * sum(w for _, w in autres) / sum(w for _, w in vivres))
    if facteur <= 1:
        return candidats                  # les vivres sont déjà bien servis
    return [(t, w * facteur) for t, w in vivres] + autres


def random_item(rng, depth=1, registre=None, unlocks=None):
    """Tire un objet au hasard; les objets s'améliorent avec la profondeur."""
    candidats = [(t, t.weight) for t in ITEM_TYPES.values()
                 if depth >= t.depth_min
                 and (t.unlock is None or unlocks is None or t.unlock in unlocks)]
    if not candidats:
        return None
    candidats = _part_reservee(candidats)
    item_type = rng.weighted(candidats)
    plus = 0
    if item_type.equippable:
        plus = max(0, rng.randint(-1, 1 + depth // 3))
    return Item(item_type, plus, registre)
