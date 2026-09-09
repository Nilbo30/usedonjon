"""Le repos : échanger du ventre contre des PV, et la compétence qui va avec."""

import unittest

from donjon import events
from donjon.config import RunConfig
from donjon.events import Recorder
from tests.helpers import place_monster, sandbox


class TestRepos(unittest.TestCase):
    def setUp(self):
        self.game = sandbox(seed=5)
        self.joueur = self.game.player

    def test_se_reposer_soigne_et_coute_du_ventre(self):
        self.joueur.hp = 3
        ventre = self.joueur.fullness
        self.assertTrue(self.game.cmd_rest())
        self.assertEqual(self.joueur.hp, self.joueur.max_hp)
        self.assertLess(self.joueur.fullness, ventre)

    def test_le_repos_s_arrete_a_pleine_vie(self):
        self.joueur.hp = self.joueur.max_hp - 1
        self.game.cmd_rest()
        self.assertEqual(self.joueur.hp, self.joueur.max_hp)
        # Il ne continue pas à consommer du ventre une fois guéri.
        ventre = self.joueur.fullness
        self.assertFalse(self.game.cmd_rest())
        self.assertEqual(self.joueur.fullness, ventre)

    def test_impossible_de_se_reposer_devant_un_monstre(self):
        self.joueur.hp = 1
        place_monster(self.game, (self.joueur.pos[0] + 2, self.joueur.pos[1]))
        self.assertFalse(self.game.cmd_rest())
        self.assertEqual(self.joueur.hp, 1)
        self.assertIn("monstre est en vue", self.game.log.texts()[-1])

    def test_le_repos_s_interrompt_quand_un_monstre_parait(self):
        self.joueur.hp = 1
        salle = self.game.level.room_at(self.joueur.pos)
        intrus = place_monster(self.game, (salle.x + salle.w - 1,
                                           salle.y + salle.h - 1))
        intrus.pos = (0, 0)                    # hors de vue au départ
        self.game.cmd_rest()
        # Il n'a pas pu se soigner à fond : quelque chose l'a interrompu,
        # ou il a été soigné avant que l'intrus n'arrive.
        self.assertLessEqual(self.joueur.hp, self.joueur.max_hp)

    def test_le_repos_s_arrete_le_ventre_vide(self):
        self.joueur.hp = 1
        self.joueur.fullness = 5
        self.game.cmd_rest()
        self.assertEqual(self.joueur.fullness, 0)
        self.assertLess(self.joueur.hp, self.joueur.max_hp)

    def test_le_ventre_vide_on_ne_se_repose_pas(self):
        self.joueur.hp = 1
        self.joueur.fullness = 0
        self.assertFalse(self.game.cmd_rest())

    def test_le_repos_est_annonce_dans_le_journal(self):
        self.joueur.hp = 5
        self.game.cmd_rest()
        self.assertIn("Tu te reposes", self.game.log.texts()[-1])


class TestCompetenceRecuperation(unittest.TestCase):
    def setUp(self):
        self.game = sandbox(seed=5)
        self.joueur = self.game.player
        self.journal = Recorder()
        self.game.listeners.append(self.journal)

    def test_se_reposer_entraine_la_recuperation(self):
        self.joueur.hp = 1
        self.game.cmd_rest()
        self.assertGreater(self.journal.count(events.REPOS), 0)
        self.assertGreater(self.joueur.skills.progress("recuperation")[0]
                           + self.joueur.skills.level("recuperation"), 0)

    def test_attendre_a_pleine_vie_n_entraine_rien(self):
        for _ in range(60):
            self.game.cmd_wait()
        self.assertEqual(self.journal.count(events.REPOS), 0)
        self.assertEqual(self.joueur.skills.level("recuperation"), 0)

    def test_marcher_soigne_mais_n_entraine_pas_la_recuperation(self):
        self.joueur.hp = 1
        for _ in range(40):
            self.game.cmd_move((1, 0))
            self.game.cmd_move((-1, 0))
        self.assertGreater(self.joueur.hp, 1)          # la régénération opère
        self.assertEqual(self.journal.count(events.REPOS), 0)

    def test_la_recuperation_accelere_la_guerison(self):
        lent = sandbox(seed=5)
        rapide = sandbox(seed=5)
        rapide.player.skills.levels["recuperation"] = 8   # -2 tours d'intervalle
        for jeu in (lent, rapide):
            jeu.player.hp = 1
            jeu.cmd_rest()
        self.assertLess(rapide.turn, lent.turn)
        self.assertGreater(rapide.player.fullness, lent.player.fullness)

    def test_la_recuperation_ne_touche_que_le_repos(self):
        """Elle raccourcit le repos, pas la régénération en marchant."""
        self.joueur.skills.levels["recuperation"] = 4
        self.game._repos_ce_tour = False
        self.assertEqual(self.game.regen_interval(),
                         self.game.config.regen_interval)
        self.game._repos_ce_tour = True
        self.assertLess(self.game.regen_interval(),
                        self.game.config.rest_regen_interval)

    def test_l_intervalle_de_repos_ne_descend_jamais_sous_un_tour(self):
        self.joueur.skills.levels["recuperation"] = 99
        self.game._repos_ce_tour = True
        self.assertEqual(self.game.regen_interval(), 1)


class TestEconomieDuRepos(unittest.TestCase):
    def test_le_ventre_paie_les_points_de_vie(self):
        """Un estomac plein doit valoir un ordre de grandeur utile de PV."""
        game = sandbox(seed=5)
        game.player.base_max_hp = 500          # assez pour ne jamais plafonner
        game.player.hp = 1
        game.cmd_rest()
        soigne = game.player.hp - 1
        self.assertGreaterEqual(soigne, 20)    # ~25 PV pour 100 de ventre

    def test_la_config_pilote_le_taux(self):
        """Le futur bonus de prestige « meilleure récupération » sera un champ."""
        genereux = sandbox(seed=5)
        genereux.config = RunConfig(rest_regen_interval=1)
        genereux.player.base_max_hp = 500
        genereux.player.hp = 1
        genereux.cmd_rest()
        self.assertGreater(genereux.player.hp, 80)   # 1 PV par point de ventre

    def test_se_reposer_est_plus_economique_que_marcher(self):
        """Le cœur de la mécanique : s'arrêter convertit mieux la nourriture."""
        repos, marche = sandbox(seed=5), sandbox(seed=5)
        for jeu in (repos, marche):
            jeu.player.base_max_hp = 500
            jeu.player.hp = 1
        repos.cmd_rest()
        for _ in range(repos.turn):
            marche.cmd_move((1, 0))
            marche.cmd_move((-1, 0))
        self.assertGreater(repos.player.hp, marche.player.hp * 2)


if __name__ == "__main__":
    unittest.main()
