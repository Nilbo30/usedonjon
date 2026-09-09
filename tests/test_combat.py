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


class TestTirADistance(unittest.TestCase):
    """L'archer : la première créature qui peut te toucher sans t'approcher."""

    def setUp(self):
        from tests.helpers import place_monster, sandbox

        self.game = sandbox(seed=4)
        self.joueur = self.game.player
        self.placer = place_monster

    def _archer(self, case):
        monstre = self.placer(self.game, case)
        monstre.behaviour = "archer"
        monstre.base_attack = 10
        return monstre

    def test_il_touche_de_loin_en_ligne_droite(self):
        depart = self.joueur.hp
        case = (self.joueur.pos[0] + 4, self.joueur.pos[1])
        if not self.game.level.walkable(case):
            self.skipTest("pas de couloir dégagé sur cette graine")
        archer = self._archer(case)
        self.assertTrue(self.game.tirer(archer, (-1, 0)))
        self.assertLess(self.joueur.hp, depart)

    def test_un_trait_qui_ne_rencontre_personne_ne_touche_rien(self):
        case = (self.joueur.pos[0] + 2, self.joueur.pos[1])
        if not self.game.level.walkable(case):
            self.skipTest("pas de couloir dégagé sur cette graine")
        archer = self._archer(case)
        vie = self.joueur.hp
        self.assertFalse(self.game.tirer(archer, (1, 0)))   # dos tourné
        self.assertEqual(self.joueur.hp, vie)

    def test_une_creature_qui_passe_devant_prend_le_trait(self):
        """Se mettre derrière un monstre est un abri réel."""
        case_proche = (self.joueur.pos[0] + 1, self.joueur.pos[1])
        case_loin = (self.joueur.pos[0] + 3, self.joueur.pos[1])
        for case in (case_proche, case_loin):
            if not self.game.level.walkable(case):
                self.skipTest("pas de couloir dégagé sur cette graine")
        bouclier_vivant = self.placer(self.game, case_proche)
        archer = self._archer(case_loin)
        vie_joueur, vie_bouclier = self.joueur.hp, bouclier_vivant.hp
        self.game.tirer(archer, (-1, 0))
        self.assertEqual(self.joueur.hp, vie_joueur)
        self.assertLess(bouclier_vivant.hp, vie_bouclier)

    def test_il_tire_de_lui_meme_quand_tu_es_sur_sa_ligne(self):
        from donjon import ai

        case = (self.joueur.pos[0] + 3, self.joueur.pos[1])
        if not all(self.game.level.walkable((self.joueur.pos[0] + n,
                                             self.joueur.pos[1]))
                   for n in (1, 2, 3)):
            self.skipTest("pas de couloir dégagé sur cette graine")
        archer = self._archer(case)
        vie = self.joueur.hp
        ai.take_turn(self.game, archer)
        self.assertLess(self.joueur.hp, vie)
        self.assertEqual(archer.pos, case)      # il n'a pas bougé : il a tiré

    def test_sans_ligne_de_tir_il_se_replace_au_lieu_de_tirer(self):
        from donjon import ai

        case = (self.joueur.pos[0] + 3, self.joueur.pos[1] + 2)
        if not self.game.level.walkable(case):
            self.skipTest("pas de place sur cette graine")
        archer = self._archer(case)
        vie = self.joueur.hp
        ai.take_turn(self.game, archer)
        self.assertEqual(self.joueur.hp, vie)
        self.assertNotEqual(archer.pos, case)

    def test_tirer_coute_moins_que_frapper(self):
        """Frapper de loin est plus sûr : ça doit faire moins mal."""
        from donjon.game import DEGATS_A_DISTANCE

        self.assertLess(DEGATS_A_DISTANCE, 1.0)
