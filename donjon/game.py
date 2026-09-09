"""Cœur du jeu : état, ordonnanceur de tours et API d'actions.

Deux idées portent l'extensibilité :

1. **Ordonnanceur à énergie.** Chaque acteur gagne `speed` points par tour de
   monde et agit dès qu'il atteint ACTION_COST. Un monstre rapide joue deux
   fois, un lent une fois sur deux — et une action pourra plus tard coûter
   moins (attaque rapide) ou plus (incantation) sans rien changer d'autre.
2. **API d'actions découplée de l'affichage.** Les commandes `cmd_*` sont le
   seul point d'entrée du joueur : l'UI curses et le lanceur de scripts de test
   appellent exactement les mêmes fonctions.
"""

from . import ai, dungeon, items, monsters, tiles, traps
from .entities import ACTION_COST, Monster, Player, exp_threshold
from .geom import ALL_DIRS, add, chebyshev, is_diagonal
from .log import MessageLog
from .rng import Rng

PLAYING, DEAD, WON = "en cours", "mort", "victoire"

# Réglages faciles à bouger pour équilibrer.
SPAWN_INTERVAL = 30          # un monstre supplémentaire tous les N tours
MONSTERS_PER_FLOOR = (3, 6)
ITEMS_PER_FLOOR = (2, 4)
TRAPS_PER_FLOOR = (1, 3)
REGEN_INTERVAL = 8           # 1 PV régénéré tous les N tours si rassasié
MISS_CHANCE = 0.08


class Game:
    def __init__(self, seed=None, max_depth=5, player_name="Shiren"):
        self.rng = Rng(seed)
        self.seed = self.rng.seed
        self.max_depth = max_depth
        self.log = MessageLog()
        self.turn = 0
        self.depth = 0
        self.state = PLAYING
        self.player = Player(player_name)
        self.actors = [self.player]
        self.level = None
        self._spawn_countdown = SPAWN_INTERVAL
        self._regen_countdown = REGEN_INTERVAL
        self._starting_kit()
        self.next_floor(first=True)

    # ------------------------------------------------------------------ #
    # Mise en place
    # ------------------------------------------------------------------ #
    def _starting_kit(self):
        self.player.add_item(items.make("epee_bois"))
        self.player.add_item(items.make("bouclier_bois"))
        self.player.add_item(items.make("onigiri"))
        self.player.add_item(items.make("herbe_soin"))
        self.player.weapon = self.player.inventory[0]
        self.player.shield = self.player.inventory[1]

    def next_floor(self, first=False):
        if self.depth >= self.max_depth:
            self.state = WON
            self.say(f"Tu atteins le fond du donjon (étage {self.depth}). Victoire !")
            return
        self.depth += 1
        self.level = dungeon.generate(self.rng)
        self.actors = [self.player]
        self.player.pos = dungeon.random_floor(self.level, self.rng,
                                               exclude={self.level.stairs})
        self.player.energy = ACTION_COST
        self._spawn_countdown = SPAWN_INTERVAL

        occupied = {self.player.pos, self.level.stairs}
        for _ in range(self.rng.randint(*MONSTERS_PER_FLOOR)):
            self.spawn_monster(occupied)
        for _ in range(self.rng.randint(*ITEMS_PER_FLOOR)):
            pos = dungeon.random_floor(self.level, self.rng, exclude=occupied)
            occupied.add(pos)
            self.level.items[pos] = items.random_item(self.rng, self.depth)
        for _ in range(self.rng.randint(*TRAPS_PER_FLOOR)):
            pos = dungeon.random_floor(self.level, self.rng, exclude=occupied)
            occupied.add(pos)
            self.level.traps[pos] = traps.random_trap(self.rng)

        self.update_explored()
        self.say(f"--- Étage {self.depth} ---" if not first
                 else f"Tu entres dans le donjon. Étage {self.depth}.")

    def spawn_monster(self, occupied=(), away_from_player=False):
        species = self.rng.weighted(monsters.table_for_depth(self.depth))
        exclude = set(occupied) | {a.pos for a in self.actors}
        for _ in range(20):
            pos = dungeon.random_floor(self.level, self.rng, exclude=exclude)
            if away_from_player and chebyshev(pos, self.player.pos) < 6:
                continue
            break
        monster = Monster(species)
        monster.pos = pos
        self.actors.append(monster)
        return monster

    # ------------------------------------------------------------------ #
    # Utilitaires
    # ------------------------------------------------------------------ #
    def say(self, text):
        self.log.add(text, self.turn)

    def who(self, actor):
        return "Tu" if actor.is_player else actor.name

    def act(self, actor, second_person, third_person):
        """Conjugue un message selon que l'acteur est le héros ou un monstre."""
        if actor.is_player:
            return f"Tu {second_person}"
        return f"{actor.name} {third_person}"

    def monsters(self):
        return [a for a in self.actors if a is not self.player and a.alive]

    def actor_at(self, pos):
        for actor in self.actors:
            if actor.alive and actor.pos == pos:
                return actor
        return None

    def update_explored(self):
        self.level.explored |= self.level.visible_from(self.player.pos)

    def visible_cells(self):
        return self.level.visible_from(self.player.pos)

    def teleport_random(self, actor):
        exclude = {a.pos for a in self.actors if a.alive}
        actor.pos = dungeon.random_floor(self.level, self.rng, exclude=exclude)
        if actor.is_player:
            self.update_explored()

    # ------------------------------------------------------------------ #
    # Ordonnanceur
    # ------------------------------------------------------------------ #
    def spend(self, actor, cost=ACTION_COST):
        actor.energy -= cost

    def pass_turn(self, actor):
        self.spend(actor)

    def world_tick(self):
        """Un tour de monde : statuts, faim, régénération, apparitions, énergie."""
        self.turn += 1
        for actor in list(self.actors):
            if not actor.alive:
                continue
            for expired in actor.tick_statuses():
                if actor.is_player or self.is_visible(actor.pos):
                    self.say(self.act(actor, "n'es plus", "n'est plus") + f" {expired}.")
        self._hunger_tick()
        self._spawn_tick()
        for actor in self.actors:
            if actor.alive:
                actor.energy += actor.speed
        self.actors = [a for a in self.actors if a.alive or a.is_player]

    def _hunger_tick(self):
        player = self.player
        if not player.alive:
            return
        if player.fullness > 0:
            player.fullness -= 1
            if player.fullness == 20:
                self.say("Ton ventre gargouille. Tu as faim.")
            if player.fullness == 0:
                self.say("Tu meurs de faim !")
            self._regen_countdown -= 1
            if self._regen_countdown <= 0:
                self._regen_countdown = REGEN_INTERVAL
                player.heal(1)
        else:
            player.take_damage(1)
            self.check_death(player)

    def _spawn_tick(self):
        self._spawn_countdown -= 1
        if self._spawn_countdown <= 0:
            self._spawn_countdown = SPAWN_INTERVAL
            self.spawn_monster(away_from_player=True)

    def process(self):
        """Fait jouer tout le monde jusqu'à ce que le joueur ait la main."""
        guard = 0
        while self.state == PLAYING:
            guard += 1
            if guard > 5000:      # garde-fou anti-boucle infinie
                break
            ready = [a for a in self.actors if a.alive and a.energy >= ACTION_COST]
            if not ready:
                self.world_tick()
                continue
            for actor in ready:
                if not actor.alive or actor.energy < ACTION_COST:
                    continue
                if actor.is_player:
                    if not self.player.can_act():
                        self.pass_turn(self.player)
                        continue
                    return
                self._monster_turn(actor)
                if self.state != PLAYING:
                    return

    def _monster_turn(self, monster):
        if not monster.can_act():
            self.pass_turn(monster)
            return
        before = monster.energy
        ai.take_turn(self, monster)
        if monster.energy == before:   # une IA qui n'a rien fait passe son tour
            self.pass_turn(monster)

    # ------------------------------------------------------------------ #
    # Mouvements et combat (utilisés par le joueur ET les monstres)
    # ------------------------------------------------------------------ #
    def can_step(self, actor, delta):
        dest = add(actor.pos, delta)
        if not self.level.walkable(dest):
            return False
        if self.actor_at(dest):
            return False
        if is_diagonal(delta):
            # Pas de coupe d'angle : les deux cases orthogonales doivent être libres.
            side_a = add(actor.pos, (delta[0], 0))
            side_b = add(actor.pos, (0, delta[1]))
            if not (self.level.walkable(side_a) and self.level.walkable(side_b)):
                return False
        return True

    def try_move(self, actor, delta):
        if not self.can_step(actor, delta):
            return False
        actor.pos = add(actor.pos, delta)
        self.spend(actor)
        self._on_enter(actor)
        return True

    def _on_enter(self, actor):
        if actor.is_player:
            self.update_explored()
            item = self.level.items.get(actor.pos)
            if item:
                self.say(f"Il y a {item.name} ici. (touche « , » pour ramasser)")
        trap = self.level.traps.get(actor.pos)
        if trap and self.rng.chance(0.85):
            trap.trigger(self, actor)

    def attack(self, attacker, defender):
        self.spend(attacker)
        if self.rng.chance(MISS_CHANCE):
            self.say(f"{self.who(attacker)} rate {defender.name}.")
            return
        raw = max(1.0, attacker.attack - defender.defense * 0.7)
        dmg = max(1, int(round(self.rng.variance(raw))))
        defender.take_damage(dmg)
        if attacker.is_player:
            self.say(f"Tu frappes {defender.name} ({dmg} dégâts).")
        else:
            self.say(f"{attacker.name} te frappe ({dmg} dégâts).")
        self.check_death(defender, killer=attacker)

    def check_death(self, actor, killer=None):
        if actor.alive:
            return False
        if actor.is_player:
            self.state = DEAD
            self.say("Tu t'effondres... Game over.")
            return True
        self.say(f"{actor.name} est vaincu !")
        if killer is self.player:
            self.grant_exp(actor.exp)
        return True

    def grant_exp(self, amount):
        player = self.player
        player.exp += amount
        while player.exp >= exp_threshold(player.level + 1):
            player.level += 1
            player.max_hp += 5
            player.base_attack += 2
            player.base_defense += 1
            player.heal(5)
            self.say(f"Niveau {player.level} ! Tu te sens plus fort.")

    def is_visible(self, pos):
        return pos in self.visible_cells()

    # ------------------------------------------------------------------ #
    # Commandes du joueur — chacune renvoie True si un tour a été consommé
    # ------------------------------------------------------------------ #
    def _finish(self, acted):
        if acted:
            self.process()
        return acted

    def cmd_move(self, delta):
        player = self.player
        if player.has_status("confus") and self.rng.chance(0.5):
            delta = self.rng.choice(ALL_DIRS)
        dest = add(player.pos, delta)
        target = self.actor_at(dest)
        if target and target is not player:
            self.attack(player, target)
            return self._finish(True)
        if self.try_move(player, delta):
            return self._finish(True)
        self.say("Impossible d'aller par là.")
        return False

    def cmd_wait(self):
        self.pass_turn(self.player)
        return self._finish(True)

    def cmd_pickup(self):
        item = self.level.items.get(self.player.pos)
        if not item:
            self.say("Il n'y a rien à ramasser.")
            return False
        if not self.player.add_item(item):
            self.say("Ton sac est plein.")
            return False
        del self.level.items[self.player.pos]
        self.say(f"Tu ramasses {item.name}.")
        self.pass_turn(self.player)
        return self._finish(True)

    def cmd_descend(self):
        if self.player.pos != self.level.stairs:
            self.say("Il n'y a pas d'escalier ici.")
            return False
        self.next_floor()
        if self.state == PLAYING:
            self.process()
        return True

    def _item_at_slot(self, slot):
        if 0 <= slot < len(self.player.inventory):
            return self.player.inventory[slot]
        self.say("Aucun objet à cet emplacement.")
        return None

    def cmd_use(self, slot):
        item = self._item_at_slot(slot)
        if not item:
            return False
        if item.type.equippable:
            return self.cmd_equip(slot)
        if not item.type.usable:
            self.say(f"{item.name} ne s'utilise pas comme ça (essaie de le lancer).")
            return False
        item.use(self, self.player)
        self.player.remove_item(item)
        self.pass_turn(self.player)
        return self._finish(True)

    def cmd_equip(self, slot):
        item = self._item_at_slot(slot)
        if not item:
            return False
        player = self.player
        if item.category == items.WEAPON:
            player.weapon = None if player.weapon is item else item
            self.say(f"Tu ranges {item.name}." if player.weapon is None
                     else f"Tu équipes {item.name}.")
        elif item.category == items.SHIELD:
            player.shield = None if player.shield is item else item
            self.say(f"Tu ranges {item.name}." if player.shield is None
                     else f"Tu équipes {item.name}.")
        else:
            self.say(f"{item.name} ne s'équipe pas.")
            return False
        self.pass_turn(player)
        return self._finish(True)

    def cmd_drop(self, slot):
        item = self._item_at_slot(slot)
        if not item:
            return False
        if self.player.pos in self.level.items:
            self.say("Il y a déjà quelque chose par terre ici.")
            return False
        self.player.remove_item(item)
        self.level.items[self.player.pos] = item
        self.say(f"Tu poses {item.name}.")
        self.pass_turn(self.player)
        return self._finish(True)

    def cmd_throw(self, slot, delta, max_range=8):
        item = self._item_at_slot(slot)
        if not item:
            return False
        self.player.remove_item(item)
        pos = self.player.pos
        for _ in range(max_range):
            nxt = add(pos, delta)
            if not self.level.walkable(nxt):
                break
            pos = nxt
            target = self.actor_at(pos)
            if target:
                self.say(f"Tu lances {item.name} sur {target.name}.")
                if not item.hit(self, self.player, target):
                    dmg = max(1, int(self.rng.variance(max(1, item.power or 2))))
                    target.take_damage(dmg)
                    self.say(f"{item.name} inflige {dmg} dégâts.")
                    self.check_death(target, killer=self.player)
                self.pass_turn(self.player)
                return self._finish(True)
        if pos not in self.level.items:
            self.level.items[pos] = item
        self.say(f"Tu lances {item.name} dans le vide.")
        self.pass_turn(self.player)
        return self._finish(True)

    # ------------------------------------------------------------------ #
    # Résumé texte (UI, tests, débogage)
    # ------------------------------------------------------------------ #
    def status_line(self):
        p = self.player
        weapon = p.weapon.name if p.weapon else "mains nues"
        shield = p.shield.name if p.shield else "aucun"
        return (f"Ét.{self.depth}  Niv.{p.level}  PV {p.hp}/{p.max_hp}  "
                f"Ventre {p.fullness}  Atq {p.attack}  Déf {p.defense}  "
                f"[{weapon} / {shield}]  T{self.turn}")

    def render(self, reveal=False):
        """Rend l'étage en lignes de texte (mémoire + champ de vision)."""
        visible = self.visible_cells()
        rows = []
        for y in range(self.level.height):
            row = []
            for x in range(self.level.width):
                pos = (x, y)
                seen = reveal or pos in visible
                known = reveal or pos in self.level.explored
                if not known:
                    row.append(" ")
                    continue
                actor = self.actor_at(pos) if seen else None
                trap = self.level.traps.get(pos)
                if actor:
                    row.append(actor.glyph)
                elif pos in self.level.items:
                    row.append(self.level.items[pos].glyph)
                elif trap and trap.revealed:
                    row.append("^")
                else:
                    row.append(tiles.glyph(self.level.tile(pos)))
            rows.append("".join(row))
        return rows

    def render_text(self, reveal=False, log_lines=5):
        out = [self.status_line()]
        out += self.render(reveal)
        out += self.log.tail(log_lines)
        return "\n".join(out)
