"""Objets : des données + une fonction d'effet enregistrée dans un registre.

Ajouter un objet = ajouter une entrée dans ITEM_TYPES et, si besoin, une
fonction décorée par @effect. Aucun autre fichier à toucher.

Chaque objet porte une `skill` : la compétence que son usage entraîne (voir
skills.py). Elle est déduite de la catégorie par défaut, et ne se déclare que
pour distinguer des familles d'armes (épée, hache, arc...).
"""

from . import questions
from .geom import add

WEAPON = "arme"
SHIELD = "bouclier"
HERB = "herbe"
SCROLL = "parchemin"
FOOD = "nourriture"
AMMO = "projectile"
WAND = "bâton"

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
    WAND: "pyromancie",
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
                 unlock=None, bonus=None, regles=(), on_aim=None,
                 portee=0, largeur=0, charges=0):
        self.key = key
        self.name = name
        self.glyph = glyph
        self.category = category
        self.skill = skill or SKILL_PAR_CATEGORIE.get(category)
        self.power = power          # dégâts d'arme, défense, soin, etc.
        self.weight = weight        # poids de tirage à la génération
        self.regles = tuple(regles)  # règles portées (voir regles.py)
        self.on_use = on_use        # effet quand on consomme/lit l'objet
        self.on_hit = on_hit        # effet quand l'objet est lancé sur une cible
        # Troisième registre, ajouté à l'étape 17.6 : un objet qu'on **vise**.
        # `on_use` ne prend pas de direction et `on_hit` est déclenché par un
        # jet ; il manquait la forme « je m'en sers, vers là-bas ».
        self.on_aim = on_aim        # effet quand on s'en sert dans une direction
        self.portee = portee        # jusqu'où, en cases (0 = sans portée)
        self.largeur = largeur      # 0 = un rayon, plus = un cône qui s'ouvre
        self.charges = charges      # usages avant épuisement (0 = consommable)
        self.note = note
        self.depth_min = depth_min  # étage à partir duquel l'objet apparaît
        self.unlock = unlock        # talent requis pour qu'il apparaisse
        # Effet de compétence qui grossit sa puissance : la fiche doit annoncer
        # ce que l'objet fera vraiment dans *ces* mains, pas dans le vide.
        self.bonus = bonus

    @property
    def equippable(self):
        return self.category in (WEAPON, SHIELD)

    @property
    def empilable(self):
        """Les munitions se rangent en pile : on en porte par poignées."""
        return self.category == AMMO

    @property
    def usable(self):
        return self.on_use is not None or self.on_aim is not None

    @property
    def vise(self):
        """S'utilise-t-il vers une direction plutôt que sur soi ?"""
        return self.on_aim is not None


class Item:
    """Instance concrète : un type + un bonus d'amélioration (+1, +2...).

    `registre` est celui du run : il décide si l'objet se montre sous son vrai
    nom ou sous une apparence. Un objet créé hors partie (tests) n'en a pas et
    reste donc toujours identifié.
    """

    def __init__(self, item_type, plus=0, registre=None, quantite=1):
        self.type = item_type
        self.plus = plus
        self.registre = registre
        self.quantite = quantite
        # Les charges appartiennent à l'exemplaire, la réserve au type : un
        # bâton à moitié vidé n'est pas un demi-bâton, et `quantite` compte
        # des exemplaires, pas des usages.
        self.charges = item_type.charges

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
    def regles(self):
        """Les règles d'un objet vivent sur son **type**, jamais sur l'exemplaire.

        C'est ce qui rend le coffre indolore : il n'y stocke qu'une clé et
        reconstruit l'objet depuis le catalogue. Le jour où un enchantement
        sera propre à un exemplaire, il faudra l'écrire dans l'entrepôt.
        """
        return self.type.regles

    @property
    def etiquette(self):
        """Le nom tel qu'on l'affiche : « une pierre ×4 » pour une pile."""
        return self.name if self.quantite <= 1 else f"{self.name} ×{self.quantite}"

    def copie(self, quantite=1):
        """Un exemplaire détaché de la pile, identique par ailleurs."""
        return Item(self.type, self.plus, self.registre, quantite)

    def puissance_pour(self, joueur=None):
        """La puissance réelle entre ces mains : l'objet plus la compétence.

        Passe par la même question que l'usage réel — sinon la fiche
        annoncerait un chiffre et le jeu en ferait un autre.
        """
        from . import questions

        if joueur is None or not self.type.bonus:
            return int(self.power)
        return int(questions.demander(self.type.bonus, self.power,
                                      porteur=joueur, objet=self))

    def description(self, joueur=None):
        """Une ligne expliquant l'effet, chiffres compris.

        Ils tiennent compte du bonus de l'exemplaire (+1, +2...) et, si un
        porteur est donné, de ses compétences : un onigiri rend 55 de ventre
        et non 50 quand la cuisine est au niveau 2.
        """
        if not self.identifie:
            return "Effet inconnu — il faudra l'essayer pour le savoir."
        if self.category == WEAPON:
            return f"Arme : +{self.power} en attaque."
        if self.category == SHIELD:
            return f"Bouclier : +{self.power} en défense."
        return self.type.note.format(n=self.puissance_pour(joueur))

    def use(self, game, user):
        fn = EFFECTS.get(self.type.on_use)
        return fn(game, user, self) if fn else False

    def aim(self, game, user, direction):
        """S'en servir vers une direction — la troisième forme, à côté de
        `use` et `hit`."""
        fn = EFFECTS.get(self.type.on_aim)
        return fn(game, user, self, direction) if fn else False

    def hit(self, game, thrower, target):
        fn = EFFECTS.get(self.type.on_hit)
        return fn(game, thrower, target, self) if fn else False


# ---------------------------------------------------------------------------
# Effets à l'usage (manger / lire)
# ---------------------------------------------------------------------------

@effect("soigner")
def _soigner(game, user, item):
    healed = game.soigner(user, questions.demander(
        questions.SOIN, item.power, porteur=user, objet=item), source=item)
    if healed:
        game.say(game.act(user, "récupères", "récupère") + f" {healed} PV.")
    else:
        game.say(game.act(user, "es", "est") + " déjà au maximum : aucun effet.")
    return True


@effect("herbe_de_vie")
def _herbe_de_vie(game, user, item):
    game.gagner_pv_max(user, item.power, source=item)
    game.soigner(user, item.power, source=item)
    game.say(game.act(user, "gagnes", "gagne") + f" {item.power} PV max !")
    return True


@effect("manger")
def _manger(game, user, item):
    if not user.is_player:
        return False
    before = user.fullness
    gagne = questions.demander(questions.SATIETE, item.power,
                               porteur=user, objet=item)
    game.nourrir(user, gagne)
    game.say(f"Tu manges {item.name}. Ventre : {before} -> {user.fullness}.")
    return True


@effect("confusion_soi")
def _confusion_soi(game, user, item):
    game.poser_statut(user, "confus", 12, source=item)
    game.say(game.act(user, "titubes", "titube") + ", la tête qui tourne.")
    return True


@effect("sommeil_soi")
def _sommeil_soi(game, user, item):
    game.poser_statut(user, "endormi", 8, source=item)
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
    duree = questions.demander(questions.DUREE_EFFET, 10,
                               porteur=user, objet=item)
    touched = 0
    for monster in game.monsters():
        if room and room.contains(monster.pos):
            game.poser_statut(monster, "confus", duree, source=item)
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
    puissance = questions.demander(questions.DEGATS_JET, item.power,
                                   porteur=thrower, objet=item, cible=target)
    dmg = max(1, int(game.rng.variance(puissance)))
    game.blesser(target, dmg, source=thrower)
    game.say(f"{item.name} touche {target.name} ({dmg} dégâts).")
    game.check_death(target, killer=thrower)
    return True


@effect("jet_sommeil")
def _jet_sommeil(game, thrower, target, item):
    game.poser_statut(target, "endormi", 10, source=thrower)
    game.say(f"{target.name} s'endort profondément.")
    return True


@effect("jet_confusion")
def _jet_confusion(game, thrower, target, item):
    game.poser_statut(target, "confus", 12, source=thrower)
    game.say(f"{target.name} est complètement désorienté.")
    return True


@effect("pyromancie")
def _pyromancie(game, user, item, direction):
    """Un souffle de flammes : tout ce qui est sur son passage brûle.

    Écrit **entièrement dans le registre**, comme les treize effets qui le
    précèdent : la portée, la largeur et les charges viennent du type, les
    cibles de `acteurs_dans_la_zone`, et les dégâts d'une question — donc une
    interception pourra un jour dire « le feu mord la chair ».
    """
    from . import questions

    cibles = [acteur for acteur
              in game.acteurs_dans_la_zone(user.pos, direction,
                                           item.type.portee, item.type.largeur)
              if acteur is not user]
    if not cibles:
        game.say("Les flammes se perdent dans le vide.")
        return True
    for cible in cibles:
        puissance = questions.demander(questions.DEGATS_SORT, item.power,
                                       porteur=user, objet=item, cible=cible)
        degats = max(1, int(game.rng.variance(puissance)))
        game.blesser(cible, degats, source=user)
        game.say(f"Les flammes lèchent {cible.name} ({degats} dégâts).")
        game.check_death(cible, killer=user)
    return True


@effect("jet_soin")
def _jet_soin(game, thrower, target, item):
    game.soigner(target, item.power, source=thrower)
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
             note="Rend {n} PV. Lancée, elle soigne la cible.", unlock="herbes",
             bonus="soin"),
    ItemType("herbe_vie", "herbe de vie", "*", HERB, power=4, weight=4,
             on_use="herbe_de_vie", on_hit="jet_soin",
             note="Augmente définitivement les PV maximum de {n}.", unlock="herbes"),
    ItemType("herbe_confusion", "herbe de confusion", "*", HERB, weight=8,
             on_use="confusion_soi", on_hit="jet_confusion",
             note="À lancer : désoriente la cible 12 tours. Mangée, "
                  "elle te désoriente toi.", unlock="herbes"),
    ItemType("graine_sommeil", "graine de sommeil", "*", HERB, weight=8,
             on_use="sommeil_soi", on_hit="jet_sommeil",
             note="À lancer : endort la cible 10 tours, sans défense. "
                  "Mangée, elle t'endort 8 tours.", unlock="herbes"),
    ItemType("onigiri", "un onigiri", "%", FOOD, power=50, weight=14,
             on_use="manger", note="Rend {n} points de ventre.", unlock="vivres",
             bonus="satiete"),
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
    # Le bâton de flammes, posé à l'étape 17.6 comme test du bus de
    # déclencheurs. Il est **verrouillé** : aucun nœud de l'arbre n'ouvre
    # « batons », donc il n'apparaît nulle part. C'était un test de mécanisme,
    # pas une livraison de contenu — l'équilibrage est un autre chantier.
    ItemType("baton_flammes", "bâton de flammes", "/", WAND, power=7, weight=4,
             on_aim="pyromancie", portee=5, largeur=1, charges=5, depth_min=3,
             unlock="batons",
             note="Un souffle de flammes sur {n} cases. Cinq charges."),

    # La pierre est le projectile de la main nue ; la flèche, taillée pour un
    # arc, ne se ramasse que sur un archer — d'où son poids nul, qui l'exclut
    # du tirage au sol sans l'exclure du butin.
    ItemType("pierre", "une pierre", "*", AMMO, power=5, weight=12,
             on_hit="jet_degats", note="À lancer : {n} dégâts à distance.",
             unlock="projectiles", bonus="degats_jet"),
    ItemType("fleche", "une flèche", "(", AMMO, power=8, weight=0,
             on_hit="jet_degats",
             note="À lancer : {n} dégâts. Faite pour un arc, faute de mieux.",
             unlock="projectiles", bonus="degats_jet"),
    ItemType("epee_bois", "épée en bois", ")", WEAPON, power=3, weight=8, unlock="epees"),
    ItemType("epee_fer", "épée en fer", ")", WEAPON, power=6, weight=5, unlock="epees"),
    ItemType("bouclier_bois", "bouclier en bois", "[", SHIELD, power=3, weight=8, unlock="boucliers"),
    ItemType("bouclier_fer", "bouclier en fer", "[", SHIELD, power=6, weight=5, unlock="boucliers"),
)


def make(key, plus=0, registre=None, quantite=1):
    return Item(ITEM_TYPES[key], plus, registre, quantite)


#: Une pile ne monte pas indéfiniment : au-delà, le sac deviendrait infini.
MAX_PILE = 99

#: Part du tirage revenant à la nourriture : un plancher **et** un plafond.
#:
#: Le plancher empêche les familles débloquées de noyer les vivres. Le plafond
#: règle l'excès inverse : quand la nourriture est seule ouverte, elle occupait
#: 100 % du tirage, soit trois onigiri par étage pour trente tours de ventre
#: dépensés — la faim ne tuait plus personne. Au-delà du plafond, les places
#: excédentaires ne donnent **rien** : un donjon où l'on n'a rien débloqué est
#: un donjon pauvre, pas un garde-manger.
PART_NOURRITURE = 0.30
PART_MAX_NOURRITURE = 0.35


def _part_reservee(candidats):
    """Ramène la nourriture dans sa fourchette, en pesant le tirage.

    Sans plancher, chaque famille débloquée noie les vivres : leur part tombe
    de 100 % à 11,7 % une fois tout ouvert, et acheter du contenu revient à
    s'affamer. Sans plafond, l'inverse : seule ouverte, la nourriture prend
    tout, et l'on ne meurt plus jamais de faim.

    Le trop-plein devient une entrée vide — une place au sol qui ne donne rien.
    """
    vivres = [(t, w) for t, w in candidats if t.category == FOOD]
    autres = [(t, w) for t, w in candidats if t.category != FOOD]
    if not vivres:
        return candidats
    poids_vivres = sum(w for _, w in vivres)
    poids_autres = sum(w for _, w in autres)
    part = poids_vivres / (poids_vivres + poids_autres)
    if part < PART_NOURRITURE and autres:
        facteur = (PART_NOURRITURE / (1 - PART_NOURRITURE)
                   * poids_autres / poids_vivres)
        return [(t, w * facteur) for t, w in vivres] + autres
    if part > PART_MAX_NOURRITURE:
        vide = poids_vivres / PART_MAX_NOURRITURE - poids_vivres - poids_autres
        return candidats + [(None, vide)]
    return candidats


def random_item(rng, depth=1, registre=None, unlocks=None):
    """Tire un objet au hasard; les objets s'améliorent avec la profondeur."""
    candidats = [(t, t.weight) for t in ITEM_TYPES.values()
                 if depth >= t.depth_min
                 and (t.unlock is None or unlocks is None or t.unlock in unlocks)]
    if not candidats:
        return None
    candidats = _part_reservee(candidats)
    item_type = rng.weighted(candidats)
    if item_type is None:
        return None            # une place au sol qui reste vide
    plus = 0
    if item_type.equippable:
        plus = max(0, rng.randint(-1, 1 + depth // 3))
    return Item(item_type, plus, registre)
