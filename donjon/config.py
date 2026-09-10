"""Réglages d'un run : tout ce qui peut varier d'une partie à l'autre.

C'est le **seul canal** par lequel la progression permanente (le futur méta)
influencera une partie. Un `Game` reçoit une `RunConfig` et ne la modifie
jamais : elle est calculée au démarrage du run, puis lue.

    Meta ──(au lancement)──> RunConfig ──(injectée)──> Game

Concrètement, un bonus de prestige du type « jauge de faim plus grande » sera
un champ de plus ici et une ligne dans la table des bonus — jamais une
modification du moteur.
"""


from . import monsters

#: Une config construite à la main (tests, bot, CLI) a tout le contenu.
TOUT_DEBLOQUE = frozenset({"butin", "vivres", "projectiles", "herbes",
                           "exploration", "auto_repas",
                           "grimoires",
                           "intuition", "epees", "boucliers", "coffre", "orbe"})

#: De même pour le bestiaire : toutes les classes de créatures.
TOUTES_CLASSES = frozenset(monsters.CLASSES)


class RunConfig:
    """Paramètres immuables d'une partie. `replace()` en produit une variante.

    Deux vitesses de régénération : en marchant, le corps récupère à peine ;
    à l'arrêt, il récupère vraiment. C'est ce qui fait du repos une décision
    (échanger du ventre contre des PV) et pas un simple raccourci clavier.
    """

    def __init__(
        self,
        max_depth=30,
        spawn_interval=30,
        monsters_per_floor=(3, 6),
        items_per_floor=(2, 4),
        traps_per_floor=(1, 3),
        regen_interval=8,
        rest_regen_interval=3,
        miss_chance=0.08,
        xp_depth_bonus=0.15,
        monster_scaling=0.06,
        hunger_scaling=0.05,
        palier=10,
        palier_scaling=1.45,
        max_fullness=100,
        start_hp=20,
        start_attack=6,
        start_defense=2,
        inventory_size=12,
        starting_kit=("epee_bois", "bouclier_bois", "onigiri", "herbe_soin"),
        hunger_enabled=True,
        is_hub=False,
        unlocks=(),
        classes=(),
        recuperation_projectile=0.0,
        reanimations=0,
    ):
        self.max_depth = max_depth
        self.spawn_interval = spawn_interval
        self.monsters_per_floor = monsters_per_floor
        self.items_per_floor = items_per_floor
        self.traps_per_floor = traps_per_floor
        self.regen_interval = regen_interval            # en agissant
        self.rest_regen_interval = rest_regen_interval  # en se reposant
        self.miss_chance = miss_chance
        # L'XP par action et la vigueur des monstres montent avec l'étage :
        # c'est ce qui donne une raison de descendre plutôt que de tourner en
        # rond en sécurité au premier étage.
        self.xp_depth_bonus = xp_depth_bonus
        self.monster_scaling = monster_scaling
        # La faim se creuse avec la profondeur : sans cela, un donjon qu'on
        # n'a rien débloqué pour peupler se traverse à pied jusqu'au bout.
        self.hunger_scaling = hunger_scaling
        # Les étages s'achètent par tranches, et chaque tranche franchie fait
        # marcher les créatures d'un cran — la profondeur n'est pas une pente
        # régulière, c'est un escalier.
        self.palier = palier
        self.palier_scaling = palier_scaling
        self.max_fullness = max_fullness
        self.start_hp = start_hp
        self.start_attack = start_attack
        self.start_defense = start_defense
        self.inventory_size = inventory_size
        self.starting_kit = tuple(starting_kit)
        # Le hub est une partie comme une autre, mais sans faim, sans monstre
        # et sans étages : c'est la config qui le dit, pas un cas particulier.
        self.hunger_enabled = hunger_enabled
        self.is_hub = is_hub
        # Drapeaux de contenu débloqué (voir tree.py). Une RunConfig nue les a
        # tous : c'est la progression qui restreint, pas le moteur.
        self.unlocks = frozenset(unlocks) if unlocks else TOUT_DEBLOQUE
        # Classes de créatures réveillées. Le héros et le donjon apprennent les
        # mêmes choses : c'est un talent qui ouvre chacune (voir tree.py).
        self.classes = frozenset(classes) if classes else TOUTES_CLASSES
        # Chance qu'un projectile qui touche retombe au sol au lieu d'être perdu.
        self.recuperation_projectile = recuperation_projectile
        # Combien de fois le coup fatal ne l'est pas, dans une descente.
        self.reanimations = reanimations

    def replace(self, **changements):
        """Copie modifiée : `config.replace(max_depth=10)`."""
        valeurs = dict(self.__dict__)
        inconnus = set(changements) - set(valeurs)
        if inconnus:
            raise TypeError(f"réglage inconnu : {', '.join(sorted(inconnus))}")
        valeurs.update(changements)
        return RunConfig(**valeurs)

    def __repr__(self):
        return f"RunConfig({self.__dict__})"
