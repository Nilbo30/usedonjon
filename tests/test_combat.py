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


if __name__ == "__main__":
    unittest.main()
