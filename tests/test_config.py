"""La RunConfig est le canal unique entre progression permanente et partie."""

import unittest

from donjon.config import RunConfig
from donjon.game import Game


class TestRunConfig(unittest.TestCase):
    def test_replace_ne_touche_pas_l_original(self):
        base = RunConfig()
        variante = base.replace(max_depth=12, max_fullness=250)
        self.assertEqual(base.max_depth, RunConfig().max_depth)
        self.assertEqual(variante.max_depth, 12)
        self.assertEqual(variante.max_fullness, 250)
        self.assertEqual(variante.miss_chance, base.miss_chance)

    def test_replace_refuse_un_reglage_inconnu(self):
        with self.assertRaises(TypeError):
            RunConfig().replace(vitesse_de_la_lumiere=3)


class TestConfigAppliquee(unittest.TestCase):
    def test_le_heros_naît_avec_les_valeurs_de_la_config(self):
        config = RunConfig(start_hp=77, start_attack=13, start_defense=4,
                           max_fullness=250, inventory_size=3)
        joueur = Game(seed=1, config=config).player
        self.assertEqual(joueur.max_hp, 77)
        self.assertEqual(joueur.hp, 77)
        self.assertEqual(joueur.base_attack, 13)
        self.assertEqual(joueur.base_defense, 4)
        self.assertEqual(joueur.fullness, 250)
        self.assertEqual(joueur.max_fullness, 250)
        self.assertEqual(joueur.max_items, 3)

    def test_le_kit_de_depart_vient_de_la_config(self):
        config = RunConfig(starting_kit=("onigiri", "onigiri"))
        joueur = Game(seed=1, config=config).player
        self.assertEqual([o.type.key for o in joueur.inventory],
                         ["onigiri", "onigiri"])
        self.assertIsNone(joueur.weapon)
        self.assertIsNone(joueur.shield)

    def test_la_profondeur_maximale_pilote_la_victoire(self):
        game = Game(seed=4, config=RunConfig(max_depth=1))
        game.player.pos = game.level.stairs
        game.cmd_descend()
        self.assertEqual(game.state, "victoire")

    def test_max_depth_reste_un_raccourci(self):
        game = Game(seed=1, max_depth=9)
        self.assertEqual(game.config.max_depth, 9)
        self.assertEqual(game.max_depth, 9)

    def test_une_jauge_plus_grande_allonge_le_run(self):
        """Le futur bonus de prestige « ventre plus grand » n'est qu'un champ."""
        court = Game(seed=2, config=RunConfig(max_fullness=10))
        long = Game(seed=2, config=RunConfig(max_fullness=400))
        for _ in range(30):
            court.cmd_wait()
            long.cmd_wait()
        self.assertLess(court.player.fullness, long.player.fullness)


if __name__ == "__main__":
    unittest.main()
