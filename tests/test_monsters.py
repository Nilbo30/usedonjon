"""Le bestiaire : deux axes, une table, et un tirage qui les respecte."""

import unittest

from donjon import monsters
from donjon.config import RunConfig


class TestCoherence(unittest.TestCase):
    def test_chaque_creature_a_une_famille_et_une_classe_connues(self):
        for entree in monsters.BESTIAIRE:
            self.assertIn(entree["famille"], monsters.FAMILLES, entree["key"])
            self.assertIn(entree["classe"], monsters.CLASSES, entree["key"])

    def test_les_cles_sont_uniques(self):
        cles = [entree["key"] for entree in monsters.BESTIAIRE]
        self.assertEqual(len(cles), len(set(cles)))

    def test_la_composition_complete_l_allure_et_le_comportement(self):
        """Le reste du jeu lit une espèce sans savoir d'où viennent ses champs."""
        for espece in monsters.SPECIES:
            self.assertTrue(espece["color"] and espece["shape"])
            self.assertEqual(espece["behaviour"],
                             monsters.CLASSES[espece["classe"]]["behaviour"])

    def test_chaque_famille_et_chaque_classe_sert(self):
        for cle in monsters.FAMILLES:
            self.assertIn(cle, {e["famille"] for e in monsters.BESTIAIRE}, cle)
        for cle in monsters.CLASSES:
            self.assertIn(cle, {e["classe"] for e in monsters.BESTIAIRE}, cle)

    def test_chaque_etage_a_de_quoi_peupler(self):
        for profondeur in range(1, 31):
            self.assertTrue(monsters.table_for_depth(profondeur), profondeur)


class TestTirage(unittest.TestCase):
    def test_la_profondeur_borne_le_tirage(self):
        haut = {e["key"] for e, _ in monsters.table_for_depth(1)}
        bas = {e["key"] for e, _ in monsters.table_for_depth(12)}
        self.assertIn("mamel", haut)
        self.assertNotIn("automate", haut)
        self.assertIn("automate", bas)
        self.assertNotIn("mamel", bas)

    def test_seules_les_classes_reveillees_apparaissent(self):
        rodeurs = monsters.table_for_depth(5, {"rodeur"})
        self.assertTrue(rodeurs)
        for espece, _ in rodeurs:
            self.assertEqual(espece["classe"], "rodeur")

    def test_sans_classe_le_donjon_reste_vide(self):
        """Le repli ne doit pas repeupler un donjon que le méta a verrouillé."""
        self.assertEqual(monsters.table_for_depth(5, frozenset()), [])

    def test_un_etage_trop_profond_rappelle_les_plus_proches(self):
        """Ne rien débloquer ne doit pas rendre les profondeurs plus sûres."""
        table = monsters.table_for_depth(25, {"erratique"})
        self.assertTrue(table)
        self.assertEqual({espece["key"] for espece, _ in table},
                         {"chauve_souris"})

    def test_une_config_nue_joue_tout_le_bestiaire(self):
        self.assertEqual(RunConfig().classes, frozenset(monsters.CLASSES))


if __name__ == "__main__":
    unittest.main()
