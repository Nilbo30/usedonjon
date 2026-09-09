import unittest

from donjon import items
from tests.helpers import place_monster, sandbox


class TestFiches(unittest.TestCase):
    """Chaque objet doit pouvoir expliquer ce qu'il fait."""

    def test_tous_les_objets_ont_une_fiche(self):
        for cle in items.ITEM_TYPES:
            self.assertTrue(items.make(cle).description, cle)

    def test_l_equipement_annonce_son_bonus_reel(self):
        self.assertIn("+8", items.make("epee_fer", plus=2).description)
        self.assertIn("+1", items.make("bouclier_bois", plus=-2).description)

    def test_les_chiffres_des_fiches_suivent_les_donnees(self):
        """Garde-fou : une fiche qui ment après un changement de puissance."""
        for cle in ("herbe_soin", "herbe_vie", "onigiri", "fleche"):
            objet = items.make(cle)
            self.assertIn(str(objet.power), objet.description, cle)

    def test_chaque_objet_entraine_une_competence_connue(self):
        from donjon import skills
        for cle, type_objet in items.ITEM_TYPES.items():
            self.assertIn(type_objet.skill, skills.CATALOGUE, cle)


class TestApparitionParProfondeur(unittest.TestCase):
    def test_l_orbe_ne_se_trouve_pas_dans_les_premiers_etages(self):
        from donjon.rng import Rng

        rng = Rng(1)
        haut = [items.random_item(rng, 1).type.key for _ in range(400)]
        self.assertNotIn("orbe_retour", haut)

    def test_il_apparait_en_profondeur(self):
        from donjon.rng import Rng

        rng = Rng(1)
        bas = [items.random_item(rng, 10).type.key for _ in range(400)]
        self.assertIn("orbe_retour", bas)


class TestNourritureAuSol(unittest.TestCase):
    """La faim est le premier tueur : elle ne doit pas dépendre du tirage."""

    def test_chaque_etage_porte_de_quoi_manger(self):
        """Sinon débloquer une famille d'objets revient à s'affamer.

        La part de nourriture dans le tirage tombe de 100 % à 12 % quand tout
        est ouvert : sans garantie, acheter du contenu réduirait les vivres au
        sol d'un facteur trois.
        """
        from donjon.game import Game

        for graine in range(12):
            game = Game(seed=graine)
            au_sol = [objet.category for objet in game.level.items.values()]
            self.assertIn(items.FOOD, au_sol, f"graine {graine}")

    def test_le_tirage_sait_se_limiter_a_une_categorie(self):
        from donjon.rng import Rng

        rng = Rng(3)
        for _ in range(50):
            objet = items.random_item(rng, 8, categorie=items.FOOD)
            self.assertEqual(objet.category, items.FOOD)

    def test_une_categorie_absente_ne_tire_rien(self):
        """Au générateur d'étage de décider quoi faire du refus."""
        from donjon.rng import Rng

        self.assertIsNone(items.random_item(Rng(3), 8, unlocks={"herbes"},
                                            categorie=items.FOOD))


class TestIdentification(unittest.TestCase):
    """Les parchemins ne disent leur nom qu'une fois essayés."""

    def setUp(self):
        self.game = sandbox(seed=5)
        self.parchemin = items.make("parchemin_lumiere",
                                    registre=self.game.identification)

    def test_un_parchemin_neuf_cache_son_nom_et_son_effet(self):
        self.assertFalse(self.parchemin.identifie)
        self.assertNotEqual(self.parchemin.name, "parchemin de lumière")
        self.assertIn("parchemin", self.parchemin.name)
        self.assertIn("inconnu", self.parchemin.description)

    def test_l_utiliser_l_identifie(self):
        self.game.player.inventory = [self.parchemin]
        self.game.cmd_use(0)
        self.assertTrue(self.parchemin.identifie)
        self.assertEqual(self.parchemin.name, "parchemin de lumière")
        self.assertTrue(any("Identifié" in t for t in self.game.log.texts()))

    def test_l_identification_vaut_pour_tous_les_exemplaires(self):
        autre = items.make("parchemin_lumiere", registre=self.game.identification)
        self.game.player.inventory = [self.parchemin]
        self.game.cmd_use(0)
        self.assertTrue(autre.identifie)

    def test_l_apparence_est_stable_dans_un_run(self):
        jumeau = items.make("parchemin_lumiere", registre=self.game.identification)
        self.assertEqual(self.parchemin.name, jumeau.name)

    def test_deux_parchemins_n_ont_pas_la_meme_apparence(self):
        autre = items.make("parchemin_panique", registre=self.game.identification)
        self.assertNotEqual(self.parchemin.name, autre.name)

    def test_les_autres_objets_ne_sont_pas_masques(self):
        for cle in ("herbe_soin", "onigiri", "epee_fer", "fleche"):
            objet = items.make(cle, registre=self.game.identification)
            self.assertTrue(objet.identifie, cle)

    def test_un_objet_sans_registre_reste_identifie(self):
        self.assertTrue(items.make("parchemin_lumiere").identifie)

    def test_chaque_run_rebat_les_apparences(self):
        vus = {sandbox(seed=graine).identification.apparences["parchemin_lumiere"]
               for graine in range(12)}
        self.assertGreater(len(vus), 1)


class TestRamassageAutomatique(unittest.TestCase):
    def setUp(self):
        self.game = sandbox(seed=5)
        self.voisine = (self.game.player.pos[0] + 1, self.game.player.pos[1])

    def test_un_consommable_se_ramasse_en_marchant_dessus(self):
        self.game.level.items[self.voisine] = items.make("herbe_soin")
        avant, tour = len(self.game.player.inventory), self.game.turn
        self.game.cmd_move((1, 0))
        self.assertEqual(len(self.game.player.inventory), avant + 1)
        self.assertNotIn(self.voisine, self.game.level.items)
        self.assertEqual(self.game.turn - tour, 1)   # gratuit : le pas suffit

    def test_une_arme_reste_au_sol(self):
        self.game.level.items[self.voisine] = items.make("epee_fer")
        self.game.cmd_move((1, 0))
        self.assertIn(self.voisine, self.game.level.items)
        self.assertTrue(self.game.cmd_pickup())     # à la main, ça marche

    def test_le_sac_plein_laisse_l_objet_au_sol(self):
        self.game.player.inventory = [items.make("fleche")
                                      for _ in range(self.game.player.max_items)]
        self.game.level.items[self.voisine] = items.make("herbe_soin")
        self.game.cmd_move((1, 0))
        self.assertIn(self.voisine, self.game.level.items)
        self.assertIn("sac est plein", self.game.log.texts()[-1])


class TestObjets(unittest.TestCase):
    def test_herbe_de_soin(self):
        game = sandbox()
        game.player.hp = 5
        game.player.inventory = [items.make("herbe_soin")]
        game.cmd_use(0)
        self.assertGreater(game.player.hp, 5)
        self.assertEqual(game.player.inventory, [])

    def test_manger_remplit_le_ventre(self):
        game = sandbox()
        game.player.fullness = 10
        game.player.inventory = [items.make("onigiri")]
        game.cmd_use(0)
        self.assertGreater(game.player.fullness, 10)

    def test_equiper_augmente_l_attaque(self):
        game = sandbox()
        game.player.weapon = None
        game.player.inventory = [items.make("epee_fer", plus=3)]
        before = game.player.attack
        game.cmd_equip(0)
        self.assertEqual(game.player.attack, before + 9)

    def test_ramasser_et_poser(self):
        game = sandbox()
        game.player.inventory = []
        game.level.items[game.player.pos] = items.make("fleche")
        self.assertTrue(game.cmd_pickup())
        self.assertEqual(len(game.player.inventory), 1)
        self.assertNotIn(game.player.pos, game.level.items)
        self.assertTrue(game.cmd_drop(0))
        self.assertIn(game.player.pos, game.level.items)

    def test_sac_plein(self):
        game = sandbox()
        game.player.inventory = [items.make("fleche")
                                 for _ in range(game.player.max_items)]
        game.level.items[game.player.pos] = items.make("onigiri")
        self.assertFalse(game.cmd_pickup())
        self.assertIn(game.player.pos, game.level.items)

    def test_lancer_une_graine_endort_la_cible(self):
        game = sandbox()
        target = place_monster(game, (game.player.pos[0] + 3, game.player.pos[1]))
        game.player.inventory = [items.make("graine_sommeil")]
        game.cmd_throw(0, (1, 0))
        self.assertTrue(target.has_status("endormi"))
        self.assertEqual(game.player.inventory, [])

    def test_objet_lance_dans_le_vide_tombe_au_sol(self):
        game = sandbox()
        game.player.inventory = [items.make("fleche")]
        game.cmd_throw(0, (1, 0))
        self.assertTrue(any(i.type.key == "fleche" for i in game.level.items.values()))

    def test_parchemin_de_lumiere_revele_l_etage(self):
        game = sandbox()
        game.player.inventory = [items.make("parchemin_lumiere")]
        before = len(game.level.explored)
        game.cmd_use(0)
        self.assertGreater(len(game.level.explored), before)


if __name__ == "__main__":
    unittest.main()
