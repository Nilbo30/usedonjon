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

    def test_les_monstres_restent_sur_des_cases_valides(self):
        game = Game(seed=5)
        autoplay(game, 300)
        for monster in game.monsters():
            self.assertTrue(game.level.walkable(monster.pos))


if __name__ == "__main__":
    unittest.main()
