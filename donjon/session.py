"""La session : ce qui relie le refuge, les descentes et la progression.

C'est le seul endroit où le méta et une partie se croisent, et c'est elle qui
possède le héros — ce qui lui permet de traverser le refuge et le donjon avec
son sac et ses compétences.

    session = Session()
    game = session.demarrer()          # le refuge
    ...                                # on joue ; le jeu s'arrête tout seul
    game = session.avancer()           # la session enchaîne : donjon, refuge...

Trois façons de terminer une partie, trois suites différentes :

* **mort** ou **victoire** — le bilan alimente le niveau global, et une vie
  neuve commence (sac vide, compétences perdues) ;
* **retour** (l'orbe) — on remonte au refuge avec tout, mais sans un gramme de
  progression permanente : la profondeur atteinte repartira de zéro ;
* **vers le donjon** — depuis le refuge, on s'engage.
"""

from . import hub
from . import tree
from . import items as items_mod
from . import meta as meta_mod
from .entities import Player, equiper_kit
from .game import DEAD, PLAYING, RETOUR, VERS_DONJON, WON, Game
from .rng import Rng


class Session:
    def __init__(self, chemin=None, sauvegarde=True, seed=None, config=None):
        self.chemin = chemin
        self.sauvegarde = sauvegarde
        self.seed = seed
        self.base_config = config
        self.meta = meta_mod.load(chemin) if sauvegarde else meta_mod.Meta()
        self.rng = Rng(seed)
        self.player = None
        self.game = None
        self.dernier_gain = None      # XP rapportée par la dernière descente
        self.dernier_bilan = None     # bilan de la dernière descente

    # ------------------------------------------------------------------ #
    # La vie du héros
    # ------------------------------------------------------------------ #
    def config_de_run(self):
        return self.meta.run_config(self.base_config)

    def nouvelle_vie(self):
        """Un héros neuf, équipé selon ce que le méta a fait gagner."""
        config = self.config_de_run()
        self.player = Player(config=config)
        self.player.registre = items_mod.Registre(self.rng)
        equiper_kit(self.player, config, self.player.registre)
        return self.player

    def demarrer(self):
        """Ouvre la session au refuge, avec un héros neuf si nécessaire."""
        if self.player is None:
            self.nouvelle_vie()
        self.game = self._partie_au_refuge()
        return self.game

    def descendre(self):
        """Entre directement dans le donjon, sans passer par le refuge.

        Sert au bot, aux scripts et aux tests : le jeu, lui, passe par
        l'escalier du refuge.
        """
        if self.player is None:
            self.nouvelle_vie()
        self.game = self._partie_dans_le_donjon()
        return self.game

    def _partie_au_refuge(self):
        return Game(seed=self.seed, config=hub.config(self.config_de_run()),
                    player=self.player)

    def _partie_dans_le_donjon(self):
        return Game(seed=self.seed, config=self.config_de_run(),
                    player=self.player)

    @property
    def au_refuge(self):
        return bool(self.game and self.game.config.is_hub)

    # ------------------------------------------------------------------ #
    # Enchaînement
    # ------------------------------------------------------------------ #
    def avancer(self):
        """Traite la fin de la partie courante et enchaîne. Renvoie la suivante.

        Sans effet tant que la partie est en cours : l'interface peut appeler
        aussi souvent qu'elle veut.
        """
        if self.game is None:
            return self.demarrer()
        etat = self.game.state
        if etat == PLAYING:
            return self.game
        if etat == VERS_DONJON:
            self.game = self._partie_dans_le_donjon()
        elif etat == RETOUR:
            # L'orbe : on garde tout, mais la descente ne rapporte rien.
            self.dernier_bilan = self.game.summary
            self.dernier_gain = None
            self.game = self._partie_au_refuge()
        else:                                   # mort ou victoire
            self.encaisser(self.game)
            self.nouvelle_vie()
            self.game = self._partie_au_refuge()
        return self.game

    def encaisser(self, game):
        """Convertit une descente terminée en progression permanente.

        Sans effet si la partie n'est pas finie, si elle a déjà été encaissée,
        ou si c'est l'orbe qui l'a close — il ne rapporte rien, c'est son prix.
        """
        bilan = game.summary
        if bilan is None or bilan.absorbed or bilan.state not in (DEAD, WON):
            return None
        bilan.absorbed = True
        self.dernier_bilan = bilan
        self.dernier_gain = self.meta.absorb(bilan)
        if self.sauvegarde:
            meta_mod.save(self.meta, self.chemin)
        return self.dernier_gain

    # ------------------------------------------------------------------ #
    # L'entrepôt du refuge
    # ------------------------------------------------------------------ #
    def entrepot(self):
        """Le contenu du coffre, en objets utilisables."""
        registre = self.player.registre if self.player else None
        return [items_mod.make(ligne["cle"], ligne.get("plus", 0), registre)
                for ligne in self.meta.entrepot]

    def capacite_entrepot(self):
        return self.meta.capacite_entrepot()

    def entrepot_plein(self):
        return len(self.meta.entrepot) >= self.capacite_entrepot()

    def deposer(self, item):
        """Range un objet du sac dans le coffre. Il survivra à la mort."""
        if self.entrepot_plein() or item not in self.player.inventory:
            return False
        self.player.remove_item(item)
        self.meta.entrepot.append({"cle": item.type.key, "plus": item.plus})
        self._sauver()
        return True

    def retirer(self, index):
        """Sort un objet du coffre pour le mettre dans le sac."""
        if not 0 <= index < len(self.meta.entrepot):
            return False
        ligne = self.meta.entrepot[index]
        objet = items_mod.make(ligne["cle"], ligne.get("plus", 0),
                               self.player.registre if self.player else None)
        if not self.player.add_item(objet):
            return False
        del self.meta.entrepot[index]
        self._sauver()
        return True

    # ------------------------------------------------------------------ #
    # L'arbre des talents
    # ------------------------------------------------------------------ #
    def acheter(self, cle):
        """Achète un talent au refuge. Renvoie le nœud acquis, ou None."""
        noeud = self.meta.acheter(cle)
        if noeud is not None:
            self._appliquer_au_heros(noeud)
            self._sauver()
        return noeud

    def _appliquer_au_heros(self, noeud):
        """Le talent profite au héros en place, pas seulement au suivant.

        Le héros est créé une fois par vie : sans ça, acheter « Affûtage » au
        refuge n'ajoutait son point d'attaque qu'après la mort suivante — on
        payait pour la vie d'après.
        """
        heros = self.player
        if heros is None:
            return
        config = self.config_de_run()
        gain_pv = config.start_hp - heros.base_max_hp
        heros.base_max_hp = config.start_hp
        heros.base_attack = config.start_attack
        heros.base_defense = config.start_defense
        heros.max_fullness = config.max_fullness
        heros.max_items = config.inventory_size
        if gain_pv > 0:
            heros.hp += gain_pv
        # Et ce que le nœud ajoute au sac de départ, s'il n'y est pas déjà.
        for cle in noeud.objets:
            if not any(objet.type.key == cle for objet in heros.inventory):
                heros.add_item(items_mod.make(cle, registre=heros.registre))

    def _sauver(self):
        if self.sauvegarde:
            meta_mod.save(self.meta, self.chemin)

    # ------------------------------------------------------------------ #
    # Affichage
    # ------------------------------------------------------------------ #
    def lignes_de_gain(self):
        """Ce qu'a rapporté la dernière descente, prêt à afficher."""
        if not self.dernier_gain:
            return []
        lignes = [f"+{self.dernier_gain:.0f} XP  "
                  f"(tu en as {self.meta.xp:.0f} à dépenser)"]
        abordables = [noeud for noeud in tree.disponibles(self.meta.noeuds)
                      if noeud.cost <= self.meta.xp]
        if abordables:
            lignes.append(f"{len(abordables)} talent(s) à ta portée — "
                          f"touche « t » au refuge.")
        return lignes

    def lignes_d_accueil(self):
        """Ce qu'on affiche en arrivant au refuge."""
        if self.dernier_bilan is None:
            lignes = ["Premier pas au refuge.", "L'escalier mène au donjon."]
            if "coffre" in self.config_de_run().unlocks:
                lignes.append("Le coffre garde ce que tu y laisses.")
            return lignes
        lignes = list(self.dernier_bilan.lines())
        if self.dernier_bilan.state == RETOUR:
            lignes.append("Tu es remonté entier : tes acquis restent, mais la "
                          "descente n'a rien rapporté.")
        lignes += self.lignes_de_gain()
        return lignes
