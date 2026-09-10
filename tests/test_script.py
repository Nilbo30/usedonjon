"""Le mode script est le harnais de test : il doit rester fiable et déterministe."""

import unittest

from donjon.game import Game
from donjon.script import ScriptError, autoplay, run_script, tokenize


class TestScript(unittest.TestCase):
    def test_decoupage(self):
        self.assertEqual(
            tokenize("ll ,> Ua Dc Tbk  # commentaire"),
            [("l",), ("l",), (",",), (">",), ("U", "a"), ("D", "c"),
             ("T", "b", "k")],
        )

    def test_commande_inconnue(self):
        with self.assertRaises(ScriptError):
            tokenize("lllZ")

    def test_argument_manquant(self):
        with self.assertRaises(ScriptError):
            tokenize("U")

    def test_partition_jouee(self):
        game = Game(seed=11)
        run_script(game, "lll..,")
        self.assertGreater(game.turn, 0)

    def test_meme_graine_meme_partie(self):
        a, b = Game(seed=99), Game(seed=99)
        run_script(a, "lljjkk..,")
        run_script(b, "lljjkk..,")
        self.assertEqual(a.log.texts(), b.log.texts())
        self.assertEqual(a.player.pos, b.player.pos)
        self.assertEqual(a.render(), b.render())

    def test_graines_differentes_donnent_des_etages_differents(self):
        self.assertNotEqual(Game(seed=1).render(True), Game(seed=2).render(True))


class TestRobustesse(unittest.TestCase):
    def test_le_bot_survit_a_de_longues_parties(self):
        """Test de fumée : aucune exception, aucun blocage sur 40 parties."""
        finished = 0
        for seed in range(40):
            game = Game(seed=seed, max_depth=5)
            autoplay(game, 1200)
            self.assertLessEqual(game.player.hp, game.player.max_hp)
            self.assertTrue(game.level.walkable(game.player.pos))
            if game.state != "en cours":
                finished += 1
        self.assertGreater(finished, 20, "le bot devrait conclure la plupart des parties")

    def test_le_bot_ne_tourne_jamais_a_vide(self):
        """Régression : une cible inatteignable en diagonale bloquait le bot.

        Chaque décision doit consommer un tour, sinon la partie n'avance plus.
        """
        from tests.helpers import place_monster, sandbox

        game = sandbox(seed=5)
        game.player.base_max_hp = 9999       # on mesure les tours, pas la survie
        game.player.hp = 9999
        pos = game.player.pos
        game.level.set_tile((pos[0] + 1, pos[1]), "wall")
        game.level.set_tile((pos[0], pos[1] + 1), "wall")
        place_monster(game, (pos[0] + 1, pos[1] + 1), hp=9999)
        refusees = []
        autoplay(game, 50, on_step=lambda _g, _cmd, agi: refusees.append(agi))
        # C'est l'action refusée qu'on traque, pas l'horloge : le compteur de
        # tours dépend de l'énergie des acteurs et retarde d'un cran.
        self.assertEqual(refusees.count(False), 0)

    def test_les_monstres_restent_sur_des_cases_valides(self):
        game = Game(seed=5)
        autoplay(game, 300)
        for monster in game.monsters():
            self.assertTrue(game.level.walkable(monster.pos))


if __name__ == "__main__":
    unittest.main()


class TestJugementDuBot(unittest.TestCase):
    """Le bot est l'instrument de mesure : ce qu'il ne sait pas faire, on ne
    peut pas le mesurer. Ces quatre réflexes sont ceux qui lui manquaient."""

    def setUp(self):
        from tests.helpers import sandbox

        self.game = sandbox(seed=6)
        self.game.update_explored()     # `sandbox` déplace le héros après coup
        self.joueur = self.game.player
        self.joueur.inventory = []
        self.case = (self.joueur.pos[0] + 1, self.joueur.pos[1])

    def _monstre(self, **stats):
        from tests.helpers import place_monster

        return place_monster(self.game, self.case, **stats)

    def test_il_frappe_ce_qu_il_peut_battre(self):
        faible = self._monstre(hp=2, attack=1, defense=0)
        autoplay(self.game, 1)
        self.assertLess(faible.hp, 2)

    def test_il_fuit_un_echange_perdant(self):
        colosse = self._monstre(hp=999, attack=99, defense=99)
        depart = self.joueur.pos
        autoplay(self.game, 1)
        self.assertEqual(colosse.hp, 999)          # il n'a pas frappé
        self.assertNotEqual(self.joueur.pos, depart)

    def test_accule_il_se_bat_quand_meme(self):
        """Fuir sans issue ferait tourner le bot dans le vide."""
        from donjon.geom import ALL_DIRS, add

        colosse = self._monstre(hp=999, attack=99, defense=0)
        for direction in ALL_DIRS:
            case = add(self.joueur.pos, direction)
            if case != self.case:
                self.game.level.set_tile(case, "wall")
        autoplay(self.game, 1)
        self.assertLess(colosse.hp, 999)

    def test_il_lit_un_parchemin_plutot_que_de_mourir(self):
        from donjon import items

        self._monstre(hp=999, attack=99, defense=99)
        parchemin = items.make("parchemin_teleport")
        self.game.identification.identifier("parchemin_teleport")
        self.joueur.add_item(parchemin)
        self.joueur.hp = 2
        autoplay(self.game, 1)
        self.assertEqual(self.joueur.inventory, [])

    def test_il_mange_l_herbe_de_vie_au_lieu_de_la_garder(self):
        from donjon import items

        maximum = self.joueur.max_hp
        self.joueur.add_item(items.make("herbe_vie"))
        autoplay(self.game, 1)
        self.assertGreater(self.joueur.max_hp, maximum)

    def test_le_ventre_creux_il_ne_se_detourne_que_pour_manger(self):
        from donjon import items, path
        from donjon.script import _objet_proche

        from donjon.geom import chebyshev

        self.joueur.fullness = 5
        proches = sorted((pos for pos in self.game.level.explored
                          if self.game.level.walkable(pos)
                          and pos != self.joueur.pos),
                         key=lambda pos: chebyshev(pos, self.joueur.pos))
        self.game.level.items[proches[0]] = items.make("epee_fer")
        self.assertIsNone(_objet_proche(self.game, path))
        self.game.level.items[proches[1]] = items.make("onigiri")
        self.assertEqual(_objet_proche(self.game, path), proches[1])
