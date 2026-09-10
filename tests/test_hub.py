"""Le refuge, le coffre et l'orbe : les deux boucles imbriquées.

* mourir — on perd tout, le niveau global monte ;
* l'orbe — on remonte au refuge avec tout, mais sans un gramme de méta.
"""

import os
import tempfile
import unittest

from donjon import hub, items
from donjon.game import DEAD, PLAYING, RETOUR, VERS_DONJON
from donjon.session import Session


class TestRefuge(unittest.TestCase):
    def setUp(self):
        self.session = Session(sauvegarde=False, seed=7)
        self.session.meta.xp = 1000
        for cle in ("nourriture", "coffre", "epee"):
            self.session.meta.acheter(cle)
        self.game = self.session.demarrer()

    def test_on_commence_au_refuge(self):
        self.assertTrue(self.session.au_refuge)
        self.assertTrue(self.game.config.is_hub)

    def test_le_refuge_n_a_ni_faim_ni_monstre(self):
        ventre = self.game.player.fullness
        for _ in range(60):
            self.game.cmd_wait()
        self.assertEqual(self.game.player.fullness, ventre)
        self.assertEqual(self.game.monsters(), [])

    def test_le_refuge_a_un_coffre_et_un_escalier(self):
        self.assertIsNotNone(self.game.level.chest)
        self.assertIsNotNone(self.game.level.stairs)
        self.assertNotEqual(self.game.level.chest, self.game.level.stairs)

    def test_sans_le_talent_il_n_y_a_pas_de_coffre(self):
        """Le coffre lui-même se gagne : la première vie n'en a pas."""
        nue = Session(sauvegarde=False, seed=7)
        self.assertIsNone(nue.demarrer().level.chest)

    def test_l_escalier_mene_au_donjon(self):
        heros = self.game.player
        self.game.player.pos = self.game.level.stairs
        self.assertTrue(self.game.cmd_descend())
        self.assertEqual(self.game.state, VERS_DONJON)
        suivant = self.session.avancer()
        self.assertFalse(self.session.au_refuge)
        self.assertIs(suivant.player, heros)      # même héros, même sac
        self.assertEqual(suivant.depth, 1)


class TestOrbe(unittest.TestCase):
    """L'orbe : tout garder, mais renoncer à la progression permanente."""

    def setUp(self):
        self.session = Session(sauvegarde=False, seed=7)
        self.session.meta.xp = 1000
        for cle in ("nourriture", "grimoires", "coffre", "voie_du_retour"):
            self.session.meta.acheter(cle)
        self.session.demarrer()
        self.game = self.session.descendre()
        self.heros = self.game.player
        self.heros.skills.levels["marche"] = 6
        for _ in range(4):                        # on descend un peu
            self.game.player.pos = self.game.level.stairs
            self.game.cmd_descend()

    def _briser_l_orbe(self):
        orbe = items.make("orbe_retour", registre=self.game.identification)
        self.heros.inventory.append(orbe)
        self.game.cmd_use(len(self.heros.inventory) - 1)

    def test_l_orbe_renvoie_au_refuge_avec_tout(self):
        self._briser_l_orbe()
        self.assertEqual(self.game.state, RETOUR)
        suivant = self.session.avancer()
        self.assertTrue(self.session.au_refuge)
        self.assertIs(suivant.player, self.heros)
        self.assertEqual(suivant.player.skills.level("marche"), 6)

    def test_l_orbe_ne_rapporte_aucun_meta(self):
        avant = self.session.meta.xp
        self._briser_l_orbe()
        self.session.avancer()
        self.assertEqual(self.session.meta.xp, avant)
        self.assertEqual(self.session.meta.runs, 0)

    def test_apres_l_orbe_la_profondeur_repart_de_zero(self):
        self.assertEqual(self.game.deepest, 5)
        self._briser_l_orbe()
        refuge = self.session.avancer()
        refuge.player.pos = refuge.level.stairs
        refuge.cmd_descend()
        descente = self.session.avancer()
        self.assertEqual(descente.deepest, 1)
        descente.end_run(DEAD, "Test.")
        self.session.avancer()
        # Le méta ne compte que la nouvelle descente, pas le record d'avant.
        self.assertEqual(self.session.dernier_bilan.deepest, 1)

    def test_mourir_efface_tout_mais_fait_progresser(self):
        self.game.end_run(DEAD, "Test.")
        suivant = self.session.avancer()
        self.assertIsNot(suivant.player, self.heros)
        self.assertEqual(suivant.player.skills.total_levels(), 0)
        self.assertGreater(self.session.meta.xp, 0)


class TestCoffre(unittest.TestCase):
    def setUp(self):
        self.session = Session(sauvegarde=False, seed=7)
        self.session.meta.xp = 1000
        for cle in ("nourriture", "coffre", "epee"):
            self.session.meta.acheter(cle)
        self.game = self.session.demarrer()
        self.heros = self.game.player

    def test_deposer_puis_reprendre(self):
        objet = self.heros.inventory[0]
        sac = len(self.heros.inventory)
        self.assertTrue(self.session.deposer(objet))
        self.assertEqual(len(self.heros.inventory), sac - 1)
        self.assertEqual(len(self.session.entrepot()), 1)
        self.assertTrue(self.session.retirer(0))
        self.assertEqual(len(self.heros.inventory), sac)
        self.assertEqual(self.session.entrepot(), [])

    def test_le_depot_conserve_le_bonus_de_l_objet(self):
        epee = items.make("epee_fer", plus=3)
        self.heros.add_item(epee)
        self.session.deposer(epee)
        self.assertEqual(self.session.entrepot()[0].plus, 3)

    def test_le_coffre_survit_a_la_mort(self):
        self.session.deposer(self.heros.inventory[0])
        donjon = self.session.descendre()
        donjon.end_run(DEAD, "Test.")
        self.session.avancer()
        self.assertEqual(len(self.session.entrepot()), 1)

    def test_le_coffre_a_une_capacite(self):
        for _ in range(self.session.capacite_entrepot() + 3):
            objet = items.make("onigiri")
            self.heros.add_item(objet)
            self.session.deposer(objet)
        self.assertEqual(len(self.session.meta.entrepot),
                         self.session.capacite_entrepot())
        self.assertTrue(self.session.entrepot_plein())

    def test_on_ne_depose_pas_ce_qu_on_n_a_pas(self):
        self.assertFalse(self.session.deposer(items.make("onigiri")))

    def test_reprendre_dans_un_sac_plein_echoue(self):
        self.session.deposer(self.heros.inventory[0])
        while self.heros.add_item(items.make("onigiri")):
            pass
        self.assertFalse(self.session.retirer(0))
        self.assertEqual(len(self.session.entrepot()), 1)


class TestPersistanceDuCoffre(unittest.TestCase):
    def test_le_coffre_est_sauvegarde(self):
        chemin = os.path.join(tempfile.mkdtemp(), "meta.json")
        session = Session(chemin=chemin)
        session.meta.xp = 1000
        for cle in ("nourriture", "coffre", "epee"):
            session.meta.acheter(cle)
        session.demarrer()
        session.deposer(session.player.inventory[0])
        relue = Session(chemin=chemin)
        relue.demarrer()
        self.assertEqual(len(relue.entrepot()), 1)


class TestConfigDuRefuge(unittest.TestCase):
    def test_le_refuge_neutralise_ce_qui_menace(self):
        config = hub.config()
        self.assertTrue(config.is_hub)
        self.assertFalse(config.hunger_enabled)
        self.assertEqual(config.monsters_per_floor, (0, 0))

    def test_il_garde_les_bonus_du_meta(self):
        from donjon.config import RunConfig

        config = hub.config(RunConfig(max_fullness=250))
        self.assertEqual(config.max_fullness, 250)


if __name__ == "__main__":
    unittest.main()


class TestTalentImmediat(unittest.TestCase):
    """Un talent acheté au refuge doit servir tout de suite, pas à la vie d'après."""

    def setUp(self):
        self.session = Session(sauvegarde=False, seed=3)
        self.session.meta.xp = 1000
        for cle in ("epee",):
            self.session.meta.acheter(cle)
        self.session.demarrer()

    def test_un_bonus_de_stat_s_applique_au_heros_en_place(self):
        heros = self.session.player
        avant = heros.attack
        self.session.acheter("affutage")
        self.assertGreater(heros.attack, avant)

    def test_les_points_de_vie_gagnes_sont_rendus(self):
        heros = self.session.player
        maximum, courant = heros.max_hp, heros.hp
        self.session.acheter("constitution")
        self.assertGreater(heros.max_hp, maximum)
        self.assertGreater(heros.hp, courant)

    def test_l_objet_du_talent_arrive_dans_le_sac(self):
        heros = self.session.player
        self.session.acheter("nourriture")
        self.assertTrue(any(objet.type.key == "onigiri"
                            for objet in heros.inventory))

    def test_le_meme_objet_n_est_pas_donne_deux_fois(self):
        """Le kit de « L'épée » est déjà là : ne pas le redonner à chaque achat."""
        heros = self.session.player
        self.session.acheter("nourriture")
        vivres = sum(1 for objet in heros.inventory
                     if objet.type.key == "onigiri")
        self.session.acheter("constitution")
        self.assertEqual(sum(1 for objet in heros.inventory
                             if objet.type.key == "onigiri"), vivres)


class TestAccueil(unittest.TestCase):
    def test_il_ne_parle_pas_d_un_coffre_qu_on_n_a_pas(self):
        session = Session(sauvegarde=False, seed=3)
        self.assertNotIn("coffre", " ".join(session.lignes_d_accueil()).lower())

    def test_il_en_parle_une_fois_gagne(self):
        session = Session(sauvegarde=False, seed=3)
        session.meta.xp = 1000
        for cle in ("nourriture", "coffre"):
            session.meta.acheter(cle)
        self.assertIn("coffre", " ".join(session.lignes_d_accueil()).lower())


class TestCoffreEtPiles(unittest.TestCase):
    def test_une_pile_deposee_revient_entiere(self):
        session = Session(sauvegarde=False, seed=7)
        session.meta.xp = 1000
        for cle in ("nourriture", "coffre"):
            session.meta.acheter(cle)
        session.demarrer()
        pile = items.make("pierre", quantite=7)
        session.player.add_item(pile)
        self.assertTrue(session.deposer(pile))
        self.assertEqual(session.entrepot()[0].quantite, 7)
        self.assertTrue(session.retirer(0))
        self.assertEqual(session.player.inventory[-1].quantite, 7)
