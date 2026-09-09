"""Acteurs : le héros et les monstres.

Tout ce qui agit partage `Actor` : points de vie, statuts, énergie (voir le
scheduler dans game.py). Ajouter une créature = ajouter une entrée de données
dans monsters.py, pas une sous-classe.
"""

ACTION_COST = 100

# Statuts qui empêchent d'agir pendant leur durée.
BLOCKING_STATUSES = ("endormi", "paralysé")


class Actor:
    def __init__(self, name, glyph, hp, attack, defense, speed=100):
        self.name = name
        self.glyph = glyph
        self.max_hp = hp
        self.hp = hp
        self.base_attack = attack
        self.base_defense = defense
        self.speed = speed
        self.pos = (0, 0)
        self.energy = 0
        self.alive = True
        self.statuses = {}       # nom -> tours restants
        self.is_player = False

    # --- statistiques (surchargées par le joueur pour l'équipement) ------
    @property
    def attack(self):
        return self.base_attack

    @property
    def defense(self):
        return self.base_defense

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
        self.exp = species.get("exp", 1)
        self.behaviour = species.get("behaviour", "chasseur")
        self.target_pos = None   # dernière position connue du héros


class Player(Actor):
    MAX_FULLNESS = 100

    def __init__(self, name="Shiren"):
        super().__init__(name, "@", hp=20, attack=6, defense=2)
        self.is_player = True
        self.level = 1
        self.exp = 0
        self.fullness = self.MAX_FULLNESS
        self.inventory = []
        self.weapon = None
        self.shield = None
        self.max_items = 12

    @property
    def attack(self):
        bonus = self.weapon.power if self.weapon else 0
        return self.base_attack + bonus

    @property
    def defense(self):
        bonus = self.shield.power if self.shield else 0
        return self.base_defense + bonus

    @property
    def exp_to_next(self):
        return exp_threshold(self.level + 1) - self.exp

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


def exp_threshold(level):
    """XP cumulée nécessaire pour atteindre `level`."""
    if level <= 1:
        return 0
    return int(8 * (level - 1) ** 2 + 4 * (level - 1))
