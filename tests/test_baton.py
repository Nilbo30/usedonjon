"""Le bâton de flammes : le test de validation du bus de déclencheurs.

Écrit après coup, il ne prouve pas que le bâton *marche* — ça, n'importe quel
code le ferait. Il prouve **où** la généralisation s'arrête : ce qui a tenu en
données, et ce qui a demandé du moteur. Le compte est dans le journal.

Ce bâton est volontairement **verrouillé** : aucun nœud n'ouvre « batons ».
C'était un test de mécanisme, pas une livraison de contenu.
"""

import unittest

from donjon import items, questions, skills, tree
from donjon.geom import DIRECTIONS
from tests.helpers import donner, place_monster, sandbox


class TestCeQuiTientEnDonnees(unittest.TestCase):
    """Tout ce qui n'a coûté qu'une ligne de table."""

    def setUp(self):
        self.jeu = sandbox(seed=1)
        self.jeu.player.inventory.clear()
        self.baton = donner(self.jeu, "baton_flammes")
        self.est = DIRECTIONS["e"]

    def _bete(self, distance, ecart=0, hp=200):
        return place_monster(self.jeu, (self.jeu.player.pos[0] + distance,
                                        self.jeu.player.pos[1] + ecart), hp=hp)

    def test_il_brule_ce_qui_est_devant(self):
        bete = self._bete(3)
        self.jeu.cmd_use(0, self.est)
        self.assertLess(bete.hp, 200)

    def test_sa_portee_vient_du_type(self):
        loin = self._bete(items.ITEM_TYPES["baton_flammes"].portee + 2)
        self.jeu.cmd_use(0, self.est)
        self.assertEqual(loin.hp, 200, "hors de portée, rien ne doit brûler")

    def test_il_touche_plusieurs_cibles_a_la_fois(self):
        """`ligne_de_tir` s'arrête au premier acteur ; une flamme, non."""
        proche, loin = self._bete(2), self._bete(4)
        self.jeu.cmd_use(0, self.est)
        self.assertLess(proche.hp, 200)
        self.assertLess(loin.hp, 200)

    def test_le_cone_s_ouvre_avec_la_distance(self):
        """Largeur 1 : rien sur le côté au premier pas, une case au-delà."""
        colle = self._bete(1, ecart=1)
        de_biais = self._bete(3, ecart=1)
        self.jeu.cmd_use(0, self.est)
        self.assertEqual(colle.hp, 200)
        self.assertLess(de_biais.hp, 200)

    def test_ses_charges_s_epuisent_sans_le_dupliquer(self):
        """Cinq charges, pas cinq bâtons : `quantite` ne pouvait pas le dire."""
        self.assertEqual(self.baton.charges, 5)
        for restant in (4, 3, 2, 1):
            self.jeu.cmd_use(0, self.est)
            self.assertEqual(self.baton.charges, restant)
            self.assertEqual(self.baton.quantite, 1)
        self.jeu.cmd_use(0, self.est)
        self.assertEqual(self.jeu.player.inventory, [])

    def test_il_entraine_la_pyromancie_sans_regle_nouvelle(self):
        """Le champ `skill` de l'objet et la règle `@objet` suffisent."""
        self._bete(2)
        self.jeu.cmd_use(0, self.est)
        self.assertGreater(self.jeu.player.skills.xp.get("pyromancie", 0)
                           + self.jeu.player.skills.level("pyromancie"), 0)

    def test_ses_degats_passent_par_une_question(self):
        """Donc une interception pourra dire « le feu mord la chair »."""
        vues = []
        questions.intercepte(questions.DEGATS_SORT)(vues.append)
        self.addCleanup(questions.INTERCEPTIONS[questions.DEGATS_SORT].remove,
                        vues.append)
        bete = self._bete(2)
        self.jeu.cmd_use(0, self.est)
        self.assertEqual([q.get("cible") for q in vues], [bete])

    def test_la_pyromancie_augmente_les_degats(self):
        faible, fort = self._bete(2), self._bete(3)
        self.jeu.cmd_use(0, self.est)
        degats_nus = 200 - faible.hp
        self.jeu.player.skills.levels["pyromancie"] = 20
        self.jeu.cmd_use(0, self.est)
        self.assertGreater(200 - fort.hp, degats_nus)


class TestCeQuiADemandeDuMoteur(unittest.TestCase):
    """Les cinq points, nommés — c'est l'information que le test cherchait."""

    def test_un_objet_vise_refuse_de_s_utiliser_sans_direction(self):
        """`cmd_use(slot)` ne suffisait pas : il a fallu lui ajouter la direction."""
        jeu = sandbox(seed=1)
        jeu.player.inventory.clear()
        donner(jeu, "baton_flammes")
        self.assertFalse(jeu.cmd_use(0))
        self.assertIn("direction", " ".join(jeu.log.texts()))

    def test_la_zone_est_une_primitive_du_moteur_pas_du_bus(self):
        """Aucun bus d'évènements ne fabrique une géométrie : elle s'achète.

        C'était la prédiction de l'audit, et c'est le seul point de l'étape que
        les données ne pouvaient pas couvrir.
        """
        jeu = sandbox(seed=1)
        jeu.actors = [jeu.player]
        for distance in (1, 2, 3):
            place_monster(jeu, (jeu.player.pos[0] + distance,
                                jeu.player.pos[1]), hp=50)
        rayon = jeu.acteurs_dans_la_zone(jeu.player.pos, DIRECTIONS["e"], 5)
        self.assertEqual(len(rayon), 3)
        ligne = jeu.ligne_de_tir(jeu.player.pos, DIRECTIONS["e"], 5)
        self.assertIs(ligne[1], rayon[0], "le jet, lui, s'arrête au premier")

    def test_les_trois_champs_de_type_sont_des_donnees(self):
        """Portée, largeur et charges : trois champs, aucune ligne de logique."""
        type_baton = items.ITEM_TYPES["baton_flammes"]
        for champ in ("portee", "largeur", "charges", "on_aim"):
            self.assertTrue(getattr(type_baton, champ), champ)


class TestIlResteHorsDuJeu(unittest.TestCase):
    def test_le_baton_n_est_ouvert_par_aucun_noeud(self):
        """Prouvé, pas livré : l'accrocher à l'arbre est une autre décision."""
        self.assertIn("batons", tree.VERROUS_EN_ATTENTE)
        ouverts = {drapeau for noeud in tree.ARBRE.values()
                   for drapeau in noeud.unlocks}
        self.assertNotIn("batons", ouverts)

    def test_la_pyromancie_existe_quand_meme_dans_le_catalogue(self):
        self.assertIn("pyromancie", skills.CATALOGUE)


if __name__ == "__main__":
    unittest.main()
