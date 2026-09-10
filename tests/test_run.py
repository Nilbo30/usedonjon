"""Fin de run, bilan, et ce qui pousse à descendre plutôt qu'à farmer en haut."""

import unittest

from donjon.config import RunConfig
from donjon.game import Game
from donjon.run import RunSummary
from tests.helpers import place_monster, sandbox


class TestProfondeurRecompensee(unittest.TestCase):
    def test_le_multiplicateur_monte_avec_l_etage(self):
        game = sandbox(seed=5)
        self.assertEqual(game.xp_multiplier(), 1)
        game.depth = 11
        self.assertAlmostEqual(game.xp_multiplier(),
                               1 + 10 * game.config.xp_depth_bonus)

    def test_une_meme_action_rapporte_plus_en_profondeur(self):
        haut, bas = sandbox(seed=5), sandbox(seed=5)
        bas.depth = 15
        for jeu in (haut, bas):
            jeu.cmd_move((1, 0))
        self.assertGreater(bas.player.skills.progress("marche")[0],
                           haut.player.skills.progress("marche")[0])

    def _gobelin(self, game, etage):
        """Le même gobelin, mis à l'échelle de l'étage demandé."""
        from donjon.entities import Monster
        from tests.helpers import species

        monstre = Monster(species("gobelin"))
        game.depth = etage
        game._scale_to_depth(monstre)
        return monstre

    def test_les_monstres_s_endurcissent_en_profondeur(self):
        game = sandbox(seed=5)
        faible = self._gobelin(game, 1)
        costaud = self._gobelin(game, 20)
        self.assertGreater(costaud.max_hp, faible.max_hp)
        self.assertGreater(costaud.attack, faible.attack)
        self.assertEqual(costaud.hp, costaud.max_hp)

    def test_sans_mise_a_l_echelle_les_monstres_restent_identiques(self):
        game = sandbox(seed=5)
        game.config = game.config.replace(monster_scaling=0, palier_scaling=1)
        self.assertEqual(self._gobelin(game, 20).max_hp,
                         self._gobelin(game, 1).max_hp)

    def test_chaque_tranche_d_etages_fait_une_marche(self):
        """Ouvrir la suite du donjon doit se sentir au premier pas."""
        game = sandbox(seed=5)
        palier = game.config.palier
        dernier_du_haut = self._gobelin(game, palier).max_hp
        premier_du_bas = self._gobelin(game, palier + 1).max_hp
        pente = self._gobelin(game, palier).max_hp - self._gobelin(game, palier - 1).max_hp
        self.assertGreater(premier_du_bas - dernier_du_haut, pente * 3)


class TestFinDeRun(unittest.TestCase):
    def test_pas_de_bilan_tant_que_la_partie_dure(self):
        self.assertIsNone(sandbox(seed=5).summary)

    def test_la_mort_produit_un_bilan(self):
        game = sandbox(seed=5)
        game.player.hp = 1
        tueur = place_monster(game, (game.player.pos[0] + 1, game.player.pos[1]),
                              attack=99)
        game.attack(tueur, game.player)
        bilan = game.summary
        self.assertIsNotNone(bilan)
        self.assertEqual(bilan.state, "mort")
        self.assertIn(tueur.name, bilan.cause)
        self.assertEqual(bilan.turns, game.turn)
        self.assertEqual(bilan.seed, game.seed)

    def test_la_victoire_produit_un_bilan(self):
        game = Game(seed=4, config=RunConfig(max_depth=1))
        game.player.pos = game.level.stairs
        game.cmd_descend()
        self.assertEqual(game.state, "victoire")
        self.assertEqual(game.summary.state, "victoire")

    def test_le_bilan_retient_les_competences(self):
        game = sandbox(seed=5)
        game.player.skills.levels.update({"marche": 4, "combat": 2})
        game.end_run("mort", "Test.")
        self.assertEqual(game.summary.skills, {"marche": 4, "combat": 2})
        self.assertEqual(game.summary.total_levels, 6)

    def test_le_record_de_profondeur_est_suivi(self):
        """L'orbe ramènera au premier étage : c'est le record qui comptera."""
        game = sandbox(seed=5)
        for _ in range(3):
            game.player.pos = game.level.stairs
            game.cmd_descend()
        self.assertEqual(game.deepest, 4)
        game.depth = 1                       # comme après un usage de l'orbe
        game.end_run("mort", "Test.")
        self.assertEqual(game.summary.deepest, 4)
        self.assertEqual(game.summary.depth, 1)


class TestBilan(unittest.TestCase):
    def test_les_lignes_disent_l_essentiel(self):
        bilan = RunSummary("mort", 3, 9, 412, {"marche": 4, "combat": 3},
                           "Tué par un Golem.")
        texte = "\n".join(bilan.lines())
        self.assertIn("9", texte)            # étage le plus profond
        self.assertIn("412", texte)
        self.assertIn("Golem", texte)
        self.assertIn("Marche 4", texte)

    def test_un_bilan_sans_competence_reste_lisible(self):
        bilan = RunSummary("mort", 1, 1, 3, {})
        self.assertEqual(bilan.total_levels, 0)
        self.assertTrue(bilan.lines())

    def test_le_bilan_est_serialisable(self):
        import json

        bilan = RunSummary("mort", 3, 9, 412, {"marche": 4}, "Test.", seed=7)
        self.assertEqual(json.loads(json.dumps(bilan.to_dict()))["deepest"], 9)


if __name__ == "__main__":
    unittest.main()
