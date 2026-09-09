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

from . import ai, dungeon, events, hub, items, monsters, skills, tiles, traps
from .config import RunConfig
from .entities import ACTION_COST, Monster, Player, equiper_kit
from .events import Event
from .geom import ALL_DIRS, add, chebyshev, is_diagonal, sub
from .log import MessageLog
from .rng import Rng
from .run import RunSummary

PLAYING, DEAD, WON = "en cours", "mort", "victoire"
#: L'orbe : la descente s'arrête, on remonte au refuge avec tous ses acquis.
RETOUR = "retour"
#: Depuis le refuge : on s'engage dans le donjon. Ce n'est pas une fin de vie.
VERS_DONJON = "vers le donjon"
#: États où la partie courante est close et où la session doit enchaîner.
TERMINES = (DEAD, WON, RETOUR, VERS_DONJON)

#: Portée d'un tir de créature, et part de son attaque qui porte à distance :
#: tirer est plus sûr que frapper, donc doit faire moins mal.
PORTEE_TIR = 7
DEGATS_A_DISTANCE = 0.75
#: Plafond de l'esquive : au-delà, un run sans bouclier deviendrait
#: invulnérable au lieu d'être une autre façon de jouer. Élevé parce qu'elle
#: remplace à elle seule un bouclier ET la compétence qui va avec.
ESQUIVE_MAX = 0.55
#: Chance qu'une créature vaincue laisse quelque chose, et son plafond une fois
#: la chance du héros ajoutée.
CHANCE_BUTIN = 0.22
CHANCE_BUTIN_MAX = 0.60


class Game:
    """État d'une partie. Tout ce qui est ici meurt avec le run.

    Les réglages ne sont plus des constantes de module mais une `RunConfig`
    injectée : c'est par là que la progression permanente influencera les
    parties suivantes (voir config.py).
    """

    def __init__(self, seed=None, max_depth=None, config=None,
                 player_name="Shiren", player=None):
        self.config = config or RunConfig()
        if max_depth is not None:      # raccourci pratique (CLI, interfaces)
            self.config = self.config.replace(max_depth=max_depth)
        self.rng = Rng(seed)
        self.seed = self.rng.seed
        self.log = MessageLog()
        self.turn = 0
        self.depth = 0
        self.deepest = 0           # l'orbe ramènera au 1er étage : on garde le record
        self.state = PLAYING
        self.summary = None        # bilan du run, une fois terminé
        # Le héros peut venir de l'extérieur : c'est ainsi qu'il traverse le
        # refuge et le donjon avec son sac et ses compétences.
        self.player = player if player is not None else Player(player_name,
                                                               self.config)
        self.actors = [self.player]
        self.level = None
        # Auditeurs d'évènements. Le formateur de compétences en est un comme
        # un autre : le moteur ne sait pas ce qu'il fait de ce qu'on lui dit.
        self.listeners = [skills.Trainer()]
        self._spawn_countdown = self.config.spawn_interval
        self._regen_acc = 0.0
        self._hunger_acc = 0.0
        self._repos_ce_tour = False
        # Les apparences suivent le héros : ce qu'il a identifié le reste tant
        # qu'il vit, refuge compris. Elles sont rebattues à chaque nouvelle vie.
        if getattr(self.player, "registre", None) is None:
            self.player.registre = items.Registre(self.rng)
        self.identification = self.player.registre
        if player is None:
            self._starting_kit()
        self.next_floor(first=True)

    @property
    def max_depth(self):
        return self.config.max_depth

    # ------------------------------------------------------------------ #
    # Mise en place
    # ------------------------------------------------------------------ #
    def _starting_kit(self):
        equiper_kit(self.player, self.config, self.identification)

    def next_floor(self, first=False):
        if self.config.is_hub:
            self.level = hub.generer("coffre" in self.config.unlocks)
            self.actors = [self.player]
            self.player.pos = hub.depart(self.level)
            self.player.energy = ACTION_COST
            self.say("Te voilà au refuge.")
            return
        if self.depth >= self.config.max_depth:
            self.end_run(WON,
                         f"Tu atteins le fond du donjon (étage {self.depth}). "
                         f"Victoire !")
            return
        self.depth += 1
        self.deepest = max(self.deepest, self.depth)
        self.level = dungeon.generate(self.rng)
        self.actors = [self.player]
        self.player.pos = dungeon.random_floor(self.level, self.rng,
                                               exclude={self.level.stairs})
        self.player.energy = ACTION_COST
        self._spawn_countdown = self.config.spawn_interval

        occupied = {self.player.pos, self.level.stairs}
        for _ in range(self.rng.randint(*self.config.monsters_per_floor)):
            self.spawn_monster(occupied)
        for _ in range(self.rng.randint(*self.config.items_per_floor)):
            pos = dungeon.random_floor(self.level, self.rng, exclude=occupied)
            occupied.add(pos)
            objet = items.random_item(self.rng, self.depth,
                                      self.identification, self.config.unlocks)
            if objet is not None:
                self.level.items[pos] = objet
        for _ in range(self.rng.randint(*self.config.traps_per_floor)):
            pos = dungeon.random_floor(self.level, self.rng, exclude=occupied)
            occupied.add(pos)
            self.level.traps[pos] = traps.random_trap(self.rng)

        self.update_explored()
        self.say(f"--- Étage {self.depth} ---" if not first
                 else f"Tu entres dans le donjon. Étage {self.depth}.")

    def spawn_monster(self, occupied=(), away_from_player=False):
        table = monsters.table_for_depth(self.depth, self.config.classes)
        if not table:                 # aucune classe réveillée : donjon désert
            return None
        species = self.rng.weighted(table)
        exclude = set(occupied) | {a.pos for a in self.actors}
        for _ in range(20):
            pos = dungeon.random_floor(self.level, self.rng, exclude=exclude)
            if away_from_player and chebyshev(pos, self.player.pos) < 6:
                continue
            break
        monster = Monster(species)
        self._scale_to_depth(monster)
        monster.pos = pos
        self.actors.append(monster)
        return monster

    def _scale_to_depth(self, monster):
        """Les créatures s'endurcissent avec l'étage.

        Sans ça, un donjon de 30 étages n'aurait plus rien à offrir passé le
        huitième : le bestiaire s'arrête là.
        """
        facteur = 1 + self.config.monster_scaling * (self.depth - 1)
        monster.base_max_hp = max(1, int(round(monster.base_max_hp * facteur)))
        monster.base_attack = max(1, int(round(monster.base_attack * facteur)))
        monster.base_defense = int(round(monster.base_defense * facteur))
        monster.hp = monster.max_hp

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

    def notify(self, nom, **donnees):
        """Annonce une action accomplie du héros (contrat : voir events.py).

        Le moteur ne sait pas ce qu'en feront les auditeurs — c'est ce qui
        permettra de brancher les compétences sans le modifier.
        """
        event = Event(nom, donnees)
        for listener in list(self.listeners):
            listener(self, event)
        return event

    def monsters(self):
        return [a for a in self.actors if a is not self.player and a.alive]

    def monsters_visible(self):
        """Un monstre est-il dans le champ de vision du héros ?"""
        vues = self.visible_cells()
        return any(m.pos in vues for m in self.monsters())

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
        self._repos_ce_tour = False

    def _hunger_tick(self):
        player = self.player
        if not player.alive or not self.config.hunger_enabled:
            return
        if player.fullness > 0:
            # « Marche » réduit le coût d'un tour ; on accumule la fraction
            # restante pour que le rythme reste régulier.
            self._hunger_acc += max(0.25, 1.0 - player.bonus("endurance"))
            while self._hunger_acc >= 1.0 and player.fullness > 0:
                self._hunger_acc -= 1.0
                player.fullness -= 1
            if player.fullness == 20:
                self.say("Ton ventre gargouille. Tu as faim.")
            if player.fullness == 0:
                self.say("Tu meurs de faim !")
            # Régénération : lente en agissant, rapide à l'arrêt. On accumule
            # une fraction de PV par tour pour que les deux rythmes cohabitent.
            self._regen_acc += 1.0 / self.regen_interval()
            while self._regen_acc >= 1.0:
                self._regen_acc -= 1.0
                soigne = player.heal(1)
                # Seul le repos entraîne « Récupération » : marcher soigne
                # aussi, mais ce n'est pas là qu'on apprend à se remettre.
                if soigne and self._repos_ce_tour:
                    self.notify(events.REPOS, pv=soigne)
        else:
            player.take_damage(1)
            self.check_death(player)

    def xp_multiplier(self):
        """Une même action rapporte davantage en profondeur.

        C'est ce qui empêche de farmer tranquillement le premier étage : la
        progression est là où c'est dangereux.
        """
        return 1 + self.config.xp_depth_bonus * (self.depth - 1)

    def regen_interval(self):
        """Tours entre deux PV regagnés, selon qu'on agit ou qu'on souffle.

        « Récupération » ne raccourcit que le repos : c'est en se reposant
        qu'on apprend à se remettre, et c'est là que ça se voit.
        """
        if not self._repos_ce_tour:
            return self.config.regen_interval
        brut = self.config.rest_regen_interval - self.player.bonus("regeneration")
        return max(1, brut)

    def _spawn_tick(self):
        self._spawn_countdown -= 1
        if self._spawn_countdown <= 0:
            self._spawn_countdown = self.config.spawn_interval
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
    def corner_blocked(self, pos, delta):
        """Angle coupé : une diagonale dont les deux cases orthogonales sont murées.

        La règle vaut pour les déplacements ET pour les coups : personne ne
        frappe à travers le coin d'un mur, ni le héros ni les monstres.
        """
        if not is_diagonal(delta):
            return False
        cote_a = add(pos, (delta[0], 0))
        cote_b = add(pos, (0, delta[1]))
        return not (self.level.walkable(cote_a) and self.level.walkable(cote_b))

    def can_step(self, actor, delta):
        dest = add(actor.pos, delta)
        if not self.level.walkable(dest) or self.actor_at(dest):
            return False
        return not self.corner_blocked(actor.pos, delta)

    def can_attack(self, attacker, target):
        """Cible à portée de corps à corps, angles de murs respectés."""
        if chebyshev(attacker.pos, target.pos) != 1:
            return False
        return not self.corner_blocked(attacker.pos, sub(target.pos, attacker.pos))

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
            if item and not self._gerer_objet_au_sol(item):
                self.say(f"Il y a {item.name} ici. "
                         f"(« , » ou le bouton pour ramasser)")
        trap = self.level.traps.get(actor.pos)
        if trap and self.rng.chance(0.85):
            trap.trigger(self, actor)

    def _gerer_objet_au_sol(self, item):
        """Ramasse les consommables au passage. Vrai si le cas est traité.

        Les consommables se ramassent en marchant dessus, sans coûter un tour.
        L'équipement reste un choix délibéré : on ne veut pas encombrer le sac
        d'armes qu'on n'a pas décidé d'emporter — d'où le message d'invite.
        """
        if item.type.equippable:
            return False
        if not self.player.add_item(item):
            self.say(f"Tu marches sur {item.name}, mais ton sac est plein.")
            return True
        del self.level.items[self.player.pos]
        self.say(f"Tu ramasses {item.name}.")
        self._intuition(item)
        self.notify(events.RAMASSAGE, objet=item)
        return True

    def _intuition(self, item):
        """Talent « Intuition » : le premier objet mystérieux de la vie se révèle."""
        registre = self.identification
        if ("intuition" not in self.config.unlocks
                or not registre.intuition_disponible or item.identifie):
            return
        registre.intuition_disponible = False
        registre.identifier(item.type.key)
        self.say(f"Tu reconnais {item.type.name} au premier coup d'œil.")

    def sous_la_menace(self):
        """Quelque chose peut-il frapper le héros là où il est ?

        Adjacent, ou un archer qui le tient dans sa ligne. Sert à savoir si un
        pas se fait sous le feu — c'est ainsi qu'on apprend à se dérober :
        en bougeant quand ça compte, pas en encaissant tranquillement.
        """
        for monstre in self.monsters():
            if chebyshev(monstre.pos, self.player.pos) <= 2:
                return True
            if monstre.behaviour == "archer" and ai.direction_de_tir(
                    self, monstre.pos, self.player):
                return True
        return False

    def esquive(self, defenseur, attaquant):
        """Le héros se dérobe-t-il entièrement ? Coup porté ou trait décoché.

        Seul endroit du moteur qui lit la compétence d'esquive. Le coup esquivé
        n'entraîne rien : on apprend à se dérober en encaissant, pas en
        réussissant — ce qui freine tout seul la montée d'un run qui esquive
        déjà bien.
        """
        if not defenseur.is_player:
            return False
        chance = min(ESQUIVE_MAX, defenseur.bonus("esquive"))
        if chance <= 0 or not self.rng.chance(chance):
            return False
        self.say(f"Tu te dérobes au coup de {attaquant.name}.")
        return True

    def attack(self, attacker, defender):
        self.spend(attacker)
        arme = attacker.weapon if attacker.is_player else None
        if self.esquive(defender, attacker):
            return
        if self.rng.chance(self.config.miss_chance):
            self.say(f"{self.who(attacker)} rate {defender.name}.")
            if attacker.is_player:
                self.notify(events.COUP, arme=arme, cible=defender,
                            touche=False, degats=0)
            return
        raw = max(1.0, attacker.attack - defender.defense * 0.7)
        dmg = max(1, int(round(self.rng.variance(raw))))
        defender.take_damage(dmg)
        if attacker.is_player:
            self.say(f"Tu frappes {defender.name} ({dmg} dégâts).")
            self.notify(events.COUP, arme=arme, cible=defender,
                        touche=True, degats=dmg)
        else:
            self.say(f"{attacker.name} te frappe ({dmg} dégâts).")
            if defender.is_player:
                self.notify(events.COUP_RECU, bouclier=defender.shield,
                            source=attacker, degats=dmg)
        self.check_death(defender, killer=attacker)

    def check_death(self, actor, killer=None):
        if actor.alive:
            return False
        if actor.is_player:
            tueur = f" Tué par {killer.name}." if killer and not killer.is_player else ""
            self.end_run(DEAD, f"Tu t'effondres... Game over.{tueur}")
            return True
        self.say(f"{actor.name} est vaincu !")
        if killer is self.player:
            self.notify(events.MONSTRE_VAINCU, monstre=actor,
                        arme=self.player.weapon,
                        distance=chebyshev(self.player.pos, actor.pos))
            self._laisser_butin(actor)
        return True

    def _laisser_butin(self, monstre):
        """Ce qu'une créature laisse en tombant : sa classe, ou sa famille.

        Elle ne peut jamais lâcher ce que le donjon n'a pas encore ouvert : un
        archer laisse ses flèches parce que le talent qui l'a réveillé est
        celui-là même qui met des flèches au sol.
        """
        if "butin" not in self.config.unlocks:
            return
        possibles = [cle for cle in monsters.butin_possible(monstre.species)
                     if items.ITEM_TYPES[cle].unlock in (None, *self.config.unlocks)]
        if not possibles or monstre.pos in self.level.items:
            return
        chance = min(CHANCE_BUTIN_MAX,
                     CHANCE_BUTIN + self.player.bonus("chance"))
        if not self.rng.chance(chance):
            return
        objet = items.make(self.rng.choice(possibles),
                           registre=self.identification)
        self.level.items[monstre.pos] = objet
        self.say(f"{monstre.name} laisse {objet.name}.")
        self.notify(events.BUTIN, objet=objet, monstre=monstre)

    def end_run(self, state, message):
        """Clôt la partie et fige son bilan — le seul objet que lira le méta."""
        self.state = state
        self.say(message)
        self.summary = RunSummary(
            state=state, depth=self.depth, deepest=self.deepest,
            turns=self.turn, skills=dict(self.player.skills.levels),
            cause=message, seed=self.seed)
        return self.summary

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
            if not self.can_attack(player, target):
                self.say("Le coin du mur t'empêche de frapper là.")
                return False
            self.attack(player, target)
            return self._finish(True)
        depart = player.pos
        if self.try_move(player, delta):
            self.notify(events.PAS, depart=depart, arrivee=player.pos,
                        diagonale=is_diagonal(delta),
                        menace=self.sous_la_menace(),
                        bouclier=player.shield)
            return self._finish(True)
        self.say("Impossible d'aller par là.")
        return False

    def cmd_wait(self):
        self.pass_turn(self.player)
        self.notify(events.ATTENTE)
        self._repos_ce_tour = True
        return self._finish(True)

    def cmd_rest(self, max_turns=300):
        """Se reposer jusqu'à guérison — la technique classique du genre.

        On échange du ventre contre des PV. L'attente s'interrompt d'elle-même
        dès que la situation change : guéri, blessé, affamé, ou un monstre en
        vue. Elle refuse même de commencer si un monstre est déjà visible.
        """
        player = self.player
        if player.hp >= player.max_hp:
            self.say("Tu es déjà au meilleur de ta forme.")
            return False
        if self.monsters_visible():
            self.say("Impossible de souffler : un monstre est en vue.")
            return False
        if player.fullness <= 0:
            self.say("Le ventre vide, ton corps ne récupère plus.")
            return False

        tours, raison = 0, "Tu te remets en route."
        while tours < max_turns and self.state == PLAYING:
            pv_avant = player.hp
            self.cmd_wait()
            tours += 1
            if player.hp >= player.max_hp:
                raison = "Te voilà d'aplomb."
                break
            if player.hp < pv_avant:
                raison = "Quelque chose te frappe !"
                break
            if self.monsters_visible():
                raison = "Un monstre approche !"
                break
            if player.fullness <= 0:
                raison = "La faim te tire de ton repos."
                break
        self.say(f"Tu te reposes {tours} tours. {raison}")
        return True

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
        self._intuition(item)
        self.pass_turn(self.player)
        self.notify(events.RAMASSAGE, objet=item)
        return self._finish(True)

    def cmd_descend(self):
        if self.player.pos != self.level.stairs:
            self.say("Il n'y a pas d'escalier ici.")
            return False
        if self.config.is_hub:
            self.state = VERS_DONJON      # la session prend le relais
            self.say("Tu t'engages dans le donjon.")
            return True
        avant = self.depth
        self.next_floor()
        if self.depth > avant:
            self.notify(events.DESCENTE, etage=self.depth)
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
        mystere = not item.identifie
        item.use(self, self.player)
        if mystere and self.identification.identifier(item.type.key):
            self.say(f"Identifié : {item.type.name}.")
        self.player.remove_item(item)
        self.pass_turn(self.player)
        self.notify(events.USAGE_OBJET, objet=item, categorie=item.category)
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
        self.notify(events.EQUIPEMENT, objet=item, categorie=item.category,
                    equipe=item in (player.weapon, player.shield))
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
        self.notify(events.POSE, objet=item)
        return self._finish(True)

    def ligne_de_tir(self, depuis, direction, portee):
        """Où s'arrête un projectile : (dernière case, premier acteur touché).

        Une seule traversée pour le jet du héros et le tir des créatures — et
        comme elle s'arrête au premier acteur, une créature qui passe devant
        prend le trait à ta place.
        """
        pos = depuis
        for _ in range(portee):
            suivant = add(pos, direction)
            if not self.level.walkable(suivant):
                break
            pos = suivant
            cible = self.actor_at(pos)
            if cible is not None:
                return pos, cible
        return pos, None

    def tirer(self, tireur, direction, portee=PORTEE_TIR):
        """Une créature décoche en ligne droite. Moins fort qu'un coup, mais de loin."""
        self.spend(tireur)
        _pos, cible = self.ligne_de_tir(tireur.pos, direction, portee)
        if cible is None:
            self.say(f"{tireur.name} tire et manque.")
            return False
        if self.esquive(cible, tireur):
            return False
        brut = max(1.0, tireur.attack * DEGATS_A_DISTANCE - cible.defense * 0.7)
        degats = max(1, int(round(self.rng.variance(brut))))
        cible.take_damage(degats)
        self.say(f"{tireur.name} te touche à distance ({degats} dégâts)."
                 if cible.is_player
                 else f"{tireur.name} touche {cible.name} ({degats} dégâts).")
        if cible.is_player:
            self.notify(events.COUP_RECU, bouclier=cible.shield, source=tireur,
                        degats=degats)
        self.check_death(cible, killer=tireur)
        return True

    def cmd_throw(self, slot, delta, max_range=8):
        item = self._item_at_slot(slot)
        if not item:
            return False
        self.player.remove_item(item)
        pos, target = self.ligne_de_tir(self.player.pos, delta, max_range)
        if target:
            self.say(f"Tu lances {item.name} sur {target.name}.")
            if not item.hit(self, self.player, target):
                puissance = max(1, item.power or 2) + self.player.bonus("degats_jet")
                dmg = max(1, int(self.rng.variance(puissance)))
                target.take_damage(dmg)
                self.say(f"{item.name} inflige {dmg} dégâts.")
                self.check_death(target, killer=self.player)
            self.pass_turn(self.player)
            self.notify(events.JET, objet=item, cible=target, direction=delta)
            return self._finish(True)
        if pos not in self.level.items:
            self.level.items[pos] = item
        self.say(f"Tu lances {item.name} dans le vide.")
        self.pass_turn(self.player)
        self.notify(events.JET, objet=item, cible=None, direction=delta)
        return self._finish(True)

    # ------------------------------------------------------------------ #
    # Résumé texte (UI, tests, débogage)
    # ------------------------------------------------------------------ #
    def status_line(self):
        p = self.player
        weapon = p.weapon.name if p.weapon else "mains nues"
        shield = p.shield.name if p.shield else "aucun"
        return (f"Ét.{self.depth}  Comp.{p.skills.total_levels()}  "
                f"PV {p.hp}/{p.max_hp}  "
                f"Ventre {p.fullness}  Atq {p.attack}  Déf {p.defense}  "
                f"[{weapon} / {shield}]  T{self.turn}")

    def skill_lines(self):
        """Compétences pratiquées : nom, niveau, progression, prochain gain."""
        lignes = []
        for cle in self.player.skills.known():
            competence = skills.CATALOGUE[cle]
            acquis, requis = self.player.skills.progress(cle)
            lignes.append((competence.name, self.player.skills.level(cle),
                           acquis, requis, competence.gain_par_niveau()))
        return lignes

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
