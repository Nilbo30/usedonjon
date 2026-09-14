"""La décision que le bot devait apprendre : changer de matière, ou pas.

Le brief du chantier le disait sans détour : « le bot devra apprendre à décider
d'un pivot. **S'il ne sait pas le faire, il ne mesure rien.** » Ces tests ne
mesurent rien non plus — ils vérifient l'**instrument** avant qu'on se fie à
ses chiffres. Un nombre de pivots par vie ne vaut que si l'on a d'abord prouvé
que le bot sait pivoter quand il le faut, et qu'il sait ne pas le faire quand
il ne le faut pas.

Les quatre choses à tenir :

* il choisit la matière qui mord **la population de l'étage**, pas la dernière
  créature croisée ;
* il change quand l'étage change de peuple ;
* il compte ce qu'il perd — sa compétence de matière ne vaut que l'objet en
  main ;
* il ne change pas pour trois fois rien, sinon il passe sa vie à se rhabiller.
"""

import unittest

from donjon import items, script
from tests.helpers import donner, sandbox


class TestLaLectureDeLEtage(unittest.TestCase):
    def test_le_haut_du_donjon_est_peuple_d_animaux_et_le_bas_d_homoncules(self):
        """Tout le pivot repose là-dessus : si c'est faux, le reste ne tient pas."""
        jeu = sandbox(seed=1)
        jeu.depth = 2
        haut = script._familles_attendues(jeu)
        jeu.depth = 11
        bas = script._familles_attendues(jeu)
        self.assertGreater(haut.get("animal", 0), 0.5)
        self.assertEqual(bas.get("animal", 0), 0)
        self.assertGreater(bas.get("homoncule", 0), 0.5)

    def test_le_mordant_suit_la_population(self):
        jeu = sandbox(seed=1)
        jeu.depth = 2
        haut = script._familles_attendues(jeu)
        jeu.depth = 11
        bas = script._familles_attendues(jeu)
        self.assertGreater(script._mordant_moyen("argent", haut),
                           script._mordant_moyen("fer", haut))
        self.assertGreater(script._mordant_moyen("fer", bas),
                           script._mordant_moyen("argent", bas))


class TestLeChoix(unittest.TestCase):
    """Deux armes dans le sac, une seule main : laquelle ?"""

    def _bot_choisit(self, profondeur, tenue, candidates):
        jeu = sandbox(seed=1)
        jeu.depth = profondeur
        jeu.player.inventory.clear()
        jeu.player.weapon = items.make(tenue) if tenue else None
        for cle in candidates:
            donner(jeu, cle)
        index = script._a_mieux_en_main(jeu)
        return None if index is None else jeu.player.inventory[index].type.key

    def test_en_haut_il_prend_ce_qui_mord_le_vivant(self):
        self.assertEqual(
            self._bot_choisit(2, "epee_bois", ["epee_fer", "epee_argent"]),
            "epee_argent")

    def test_en_bas_il_prend_ce_qui_mord_le_fabrique(self):
        self.assertEqual(
            self._bot_choisit(11, "epee_bois", ["epee_fer", "epee_argent"]),
            "epee_fer")

    def test_il_pivote_quand_l_etage_change_de_peuple(self):
        """La même arme en main, le même sac : seule la profondeur décide."""
        self.assertIsNone(self._bot_choisit(2, "epee_argent", ["epee_fer"]))
        self.assertEqual(self._bot_choisit(11, "epee_argent", ["epee_fer"]),
                         "epee_fer")

    def test_une_main_vide_se_remplit_sans_discuter(self):
        self.assertEqual(self._bot_choisit(1, None, ["epee_bois"]), "epee_bois")


class TestCeQuIlEnCoute(unittest.TestCase):
    """Pivoter, c'est lâcher une compétence : le bot doit le compter."""

    def _jeu(self, profondeur=11):
        jeu = sandbox(seed=1)
        jeu.depth = profondeur
        jeu.player.inventory.clear()
        jeu.player.weapon = items.make("epee_argent")
        donner(jeu, "epee_fer")
        return jeu

    def test_sans_entrainement_il_pivote(self):
        self.assertIsNotNone(script._a_mieux_en_main(self._jeu()))

    def test_une_matiere_longuement_pratiquee_retient_la_main(self):
        """Le prix du pivot, et personne ne l'a écrit comme une règle."""
        jeu = self._jeu()
        jeu.player.skills.levels["argent"] = 12
        self.assertIsNone(script._a_mieux_en_main(jeu))

    def test_la_matiere_portee_au_bras_ne_se_perd_pas_en_lachant_l_arme(self):
        """Un bouclier en argent garde la compétence d'argent : le pivot est gratuit.

        Un bot qui l'ignorerait surestimerait le prix du changement, et ne
        pivoterait jamais quand les deux mains ne sont pas de la même matière.
        """
        jeu = self._jeu()
        jeu.player.skills.levels["argent"] = 12
        jeu.player.shield = items.make("bouclier_argent")
        self.assertIsNotNone(script._a_mieux_en_main(jeu))


class TestLaMarge(unittest.TestCase):
    def test_il_ne_change_pas_pour_trois_fois_rien(self):
        """Chaque échange coûte un tour : sans marge, le bot se rhabille sans fin."""
        jeu = sandbox(seed=1)
        jeu.depth = 6                      # l'étage où bronze et fer s'égalent
        jeu.player.inventory.clear()
        jeu.player.weapon = items.make("epee_bronze")
        donner(jeu, "epee_fer")
        self.assertIsNone(script._a_mieux_en_main(jeu))

    def test_la_marge_est_une_donnee_et_non_un_chiffre_perdu_dans_le_code(self):
        self.assertGreater(script.MARGE_DE_PIVOT, 1.0)


class TestLeBouclier(unittest.TestCase):
    """L'autre moitié de l'engagement : ce qu'on porte au bras se choisit aussi."""

    def test_le_bouclier_suit_la_meme_lecture_de_l_etage(self):
        jeu = sandbox(seed=1)
        jeu.depth = 2
        jeu.player.inventory.clear()
        jeu.player.shield = items.make("bouclier_bois")
        donner(jeu, "bouclier_argent")
        index = script._a_mieux_en_main(jeu)
        self.assertIsNotNone(index)
        self.assertEqual(jeu.player.inventory[index].type.key,
                         "bouclier_argent")


if __name__ == "__main__":
    unittest.main()
