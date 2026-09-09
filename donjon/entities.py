"""Acteurs : le héros et les monstres.

Tout ce qui agit partage `Actor` : points de vie, statuts, énergie (voir le
scheduler dans game.py). Ajouter une créature = ajouter une entrée de données
dans monsters.py, pas une sous-classe.
"""

from . import items as items_mod
from .config import RunConfig
from .skills import SkillSet

ACTION_COST = 100

# Statuts qui empêchent d'agir pendant leur durée.
BLOCKING_STATUSES = ("endormi", "paralysé")


class Actor:
    def __init__(self, name, glyph, hp, attack, defense, speed=100):
        self.name = name
        self.glyph = glyph
        self.base_max_hp = hp
        self.hp = hp
        self.base_attack = attack
        self.base_defense = defense
        self.speed = speed
        self.pos = (0, 0)
        self.energy = 0
        self.alive = True
        self.statuses = {}       # nom -> tours restants
        self.is_player = False

    # --- statistiques (surchargées par le joueur : équipement + compétences)
    @property
    def attack(self):
        return self.base_attack

    @property
    def defense(self):
        return self.base_defense

    @property
    def max_hp(self):
        return self.base_max_hp + self.bonus("pv_max")

    def bonus(self, effet):
        """Bonus de compétence. Nul pour tout le monde sauf le héros."""
        return 0

    # --- statuts ---------------------------------------------------------
    def add_status(self, name, turns):
        self.statuses[name] = max(self.statuses.get(name, 0), turns)

    def has_status(self, name):
        return self.statuses.get(name, 0) > 0

    def clear_status(self, name):
        self.statuses.pop(name, None)

    def tick_statuses(self):
        """Décrémente les durées, renvoie la liste des statuts terminés."""
        expired = []
        for name in list(self.statuses):
            self.statuses[name] -= 1
            if self.statuses[name] <= 0:
                del self.statuses[name]
                expired.append(name)
        return expired

    def can_act(self):
        return self.alive and not any(self.has_status(s) for s in BLOCKING_STATUSES)

    # --- dégâts ----------------------------------------------------------
    def heal(self, amount):
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - before

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return amount

    def status_line(self):
        return ", ".join(f"{n}({t})" for n, t in self.statuses.items())


class Monster(Actor):
    def __init__(self, species):
        super().__init__(
            species["name"], species["glyph"], species["hp"],
            species["attack"], species["defense"], species.get("speed", 100),
        )
        self.species = species
        self.behaviour = species.get("behaviour", "chasseur")
        self.target_pos = None   # dernière position connue du héros


class Player(Actor):
    """Le héros. Sa progression est entièrement dans `skills` (voir skills.py).

    Toutes ses statistiques passent par un même empilement : valeur de base
    (RunConfig) + équipement + compétences. Une nouvelle source de bonus
    s'ajoutera ici, à un seul endroit.
    """

    def __init__(self, name="Shiren", config=None):
        config = config or RunConfig()
        super().__init__(name, "@", hp=config.start_hp,
                         attack=config.start_attack, defense=config.start_defense)
        self.is_player = True
        self.skills = SkillSet()
        self.max_fullness = config.max_fullness
        self.fullness = self.max_fullness
        self.inventory = []
        self.weapon = None
        self.shield = None
        self.max_items = config.inventory_size

    @property
    def weapon_skill(self):
        """Famille de l'arme portée — « pugilat » à mains nues."""
        return self.weapon.type.skill if self.weapon else "pugilat"

    @property
    def shield_skill(self):
        """Famille de défense active — « esquive » quand le bras est nu.

        Symétrique de `weapon_skill` : sans bouclier on n'apprend pas à parer,
        on apprend à se dérober. C'est ce qui fait exister deux façons de
        traverser un run, selon ce qu'on a trouvé.
        """
        if self.shield and self.shield.type.skill:
            return self.shield.type.skill
        return "esquive"

    def families(self):
        """Familles d'équipement actives, pour les bonus de compétence."""
        return [self.weapon_skill, self.shield_skill]

    def bonus(self, effet):
        return self.skills.bonus(effet, self.families())

    @property
    def attack(self):
        equipement = self.weapon.power if self.weapon else 0
        return int(self.base_attack + equipement + self.bonus("attaque"))

    @property
    def defense(self):
        equipement = self.shield.power if self.shield else 0
        return int(self.base_defense + equipement + self.bonus("defense"))

    def add_item(self, item):
        if len(self.inventory) >= self.max_items:
            return False
        self.inventory.append(item)
        return True

    def remove_item(self, item):
        if item in self.inventory:
            self.inventory.remove(item)
        if self.weapon is item:
            self.weapon = None
        if self.shield is item:
            self.shield = None

    def slot_of(self, item):
        return self.inventory.index(item)


def equiper_kit(player, config, registre=None):
    """Donne au héros son matériel de départ, et le lui met sur le dos."""
    for cle in config.starting_kit:
        objet = items_mod.make(cle, registre=registre)
        if not player.add_item(objet):
            break
        if objet.category == items_mod.WEAPON and player.weapon is None:
            player.weapon = objet
        elif objet.category == items_mod.SHIELD and player.shield is None:
            player.shield = objet
    return player
