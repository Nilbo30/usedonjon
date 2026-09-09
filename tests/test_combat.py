import unittest

from tests.helpers import place_monster, sandbox


class TestCombat(unittest.TestCase):
    def test_attaquer_inflige_des_degats(self):
        game = sandbox()
        target = place_monster(game, (game.player.pos[0] + 1, game.player.pos[1]),
                               hp=100, defense=0)
        game.attack(game.player, target)
        self.assertLess(target.hp, 100)

    def test_degats_minimum_de_un(self):
        game = sandbox()
        target = place_monster(game, (game.player.pos[0] + 1, game.player.pos[1]),
                               hp=50, defense=999)
        for _ in range(20):
            before = target.hp
            game.attack(game.player, target)
            self.assertLessEqual(target.hp, before)

    def test_deplacement_vers_un_monstre_attaque(self):
        game = sandbox()
        target = place_monster(game, (game.player.pos[0] + 1, game.player.pos[1]),
                               hp=100)
        start = game.player.pos
        game.cmd_move((1, 0))
        self.assertEqual(game.player.pos, start)
        self.assertLess(target.hp, 100)

    def test_vaincre_un_monstre_entraine_le_combat(self):
        """Plus de niveau global : une mise à mort nourrit une compétence."""
        game = sandbox()
        target = place_monster(game, (game.player.pos[0] + 1, game.player.pos[1]),
                               hp=1)
        avant = game.player.skills.progress("combat")[0]
        for _ in range(20):
            if not target.alive:
                break
            game.attack(game.player, target)
        self.assertFalse(target.alive)
        self.assertGreater(game.player.skills.progress("combat")[0], avant)

    def test_mort_du_joueur_termine_la_partie(self):
        game = sandbox()
        game.player.hp = 1
        killer = place_monster(game, (game.player.pos[0] + 1, game.player.pos[1]),
                               attack=99)
        game.attack(killer, game.player)
        self.assertEqual(game.state, "mort")

    def test_pas_de_coupe_d_angle_en_diagonale(self):
        game = sandbox()
        level = game.level
        pos = game.player.pos
        level.set_tile((pos[0] + 1, pos[1]), "wall")
        level.set_tile((pos[0], pos[1] + 1), "wall")
        self.assertFalse(game.can_step(game.player, (1, 1)))


class TestAngles(unittest.TestCase):
    """On ne frappe pas à travers le coin d'un mur — dans les deux sens."""

    def setUp(self):
        self.game = sandbox()
        pos = self.game.player.pos
        self.diagonale = (pos[0] + 1, pos[1] + 1)
        self.monstre = place_monster(self.game, self.diagonale, hp=999, attack=50)

    def murer_l_angle(self):
        pos = self.game.player.pos
        self.game.level.set_tile((pos[0] + 1, pos[1]), "wall")
        self.game.level.set_tile((pos[0], pos[1] + 1), "wall")

    def test_en_terrain_degage_la_diagonale_est_permise(self):
        self.assertTrue(self.game.can_attack(self.monstre, self.game.player))
        self.assertTrue(self.game.can_attack(self.game.player, self.monstre))

    def test_le_monstre_ne_frappe_pas_a_travers_l_angle(self):
        self.murer_l_angle()
        self.assertFalse(self.game.can_attack(self.monstre, self.game.player))
        pv = self.game.player.hp
        for _ in range(10):
            self.game.cmd_wait()
        self.assertEqual(self.game.player.hp, pv)

    def test_le_heros_non_plus(self):
        self.murer_l_angle()
        pv = self.monstre.hp
        self.assertFalse(self.game.cmd_move((1, 1)))
        self.assertEqual(self.monstre.hp, pv)
        self.assertIn("coin du mur", self.game.log.texts()[-1])

    def test_un_seul_mur_suffit_a_bloquer(self):
        """Même règle stricte que pour le déplacement : les deux côtés doivent
        être libres, sinon la diagonale est murée."""
        pos = self.game.player.pos
        self.game.level.set_tile((pos[0] + 1, pos[1]), "wall")
        self.assertFalse(self.game.can_attack(self.monstre, self.game.player))
        self.assertFalse(self.game.can_step(self.game.player, (1, 1)))


if __name__ == "__main__":
    unittest.main()
