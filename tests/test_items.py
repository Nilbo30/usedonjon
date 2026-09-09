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
