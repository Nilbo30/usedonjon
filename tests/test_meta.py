"""Progression permanente : l'XP gagnée en mourant, et ce qu'elle achète.

Le point qui compte : le méta n'influence une partie que par la `RunConfig`,
et une config construite à la main garde tout son contenu — c'est le chemin du
méta, et lui seul, qui verrouille ce qui n'a pas été gagné.
"""

import json
import os
import tempfile
import unittest

from donjon import meta as meta_mod
from donjon import monsters
from donjon import tree
from donjon.config import RunConfig
from donjon.meta import Meta
from donjon.run import RunSummary
from donjon.session import Session


def bilan(deepest=1, levels=10, state="mort"):
    return RunSummary(state, deepest, deepest, 100,
                      {"marche": levels}, "Test.")


class TestConversion(unittest.TestCase):
    def test_la_profondeur_multiplie_la_recompense(self):
        peu_profond = meta_mod.valeur_du_run(bilan(deepest=1, levels=10))
        profond = meta_mod.valeur_du_run(bilan(deepest=11, levels=10))
        self.assertEqual(peu_profond, 10)
        self.assertAlmostEqual(profond, 20)

    def test_le_pari_de_l_orbe(self):
        """Mourir plus haut qu'avant doit rapporter moins, même mieux entraîné."""
        sans_orbe = meta_mod.valeur_du_run(bilan(deepest=12, levels=20))
        orbe_rate = meta_mod.valeur_du_run(bilan(deepest=8, levels=26))
        orbe_reussi = meta_mod.valeur_du_run(bilan(deepest=16, levels=30))
        self.assertLess(orbe_rate, orbe_reussi)
        self.assertLess(abs(orbe_rate - sans_orbe), sans_orbe * 0.15)

    def test_un_run_sans_competence_ne_rapporte_rien(self):
        self.assertEqual(meta_mod.valeur_du_run(bilan(deepest=20, levels=0)), 0)


class TestProgression(unittest.TestCase):
    def test_absorber_credite_le_solde(self):
        meta = Meta()
        gagnee = meta.absorb(bilan(deepest=5, levels=30))
        self.assertGreater(gagnee, 0)
        self.assertEqual(meta.xp, gagnee)
        self.assertEqual(meta.xp_totale, gagnee)
        self.assertEqual(meta.runs, 1)

    def test_depenser_entame_le_solde_sans_toucher_au_total(self):
        meta = Meta()
        meta.absorb(bilan(levels=100))
        total = meta.xp_totale
        noeud = meta.acheter("estomac")
        self.assertIsNotNone(noeud)
        self.assertEqual(meta.xp, total - noeud.cost)
        self.assertEqual(meta.xp_totale, total)

    def test_les_records_sont_retenus(self):
        meta = Meta()
        meta.absorb(bilan(deepest=9, levels=4))
        meta.absorb(bilan(deepest=3, levels=12))
        self.assertEqual(meta.best_depth, 9)
        self.assertEqual(meta.best_levels, 12)


class TestInfluenceSurLesRuns(unittest.TestCase):
    def test_sans_talent_le_donjon_est_nu(self):
        config = Meta().run_config()
        self.assertEqual(config.monsters_per_floor, (0, 0))
        self.assertEqual(config.items_per_floor, (0, 0))
        self.assertEqual(config.starting_kit, ())

    def test_une_config_faite_a_la_main_garde_tout(self):
        """Le moteur n'est pas verrouillé : c'est le méta qui restreint."""
        config = RunConfig()
        self.assertNotEqual(config.monsters_per_floor, (0, 0))
        self.assertIn("herbes", config.unlocks)

    def test_les_effets_s_additionnent(self):
        base = RunConfig()
        meta = Meta(xp=1000)
        meta.acheter("estomac")
        meta.acheter("besace")
        attendu = (base.max_fullness
                   + tree.ARBRE["estomac"].effets["max_fullness"])
        self.assertEqual(meta.run_config(base).max_fullness, attendu)
        self.assertEqual(meta.run_config(base).inventory_size,
                         base.inventory_size
                         + tree.ARBRE["besace"].effets["inventory_size"])

    def test_les_objets_de_depart_s_accumulent(self):
        """Deux nœuds d'équipement remplissent le même sac, sans s'écraser."""
        meta = Meta(xp=1000)
        for cle in ("nourriture",):
            meta.acheter(cle)
        self.assertEqual(meta.run_config().starting_kit,
                         tree.ARBRE["nourriture"].objets)

    def test_les_classes_reveillees_arrivent_dans_la_config(self):
        """Ce que le héros apprend, le donjon l'apprend : pas plus, pas moins."""
        meta = Meta(xp=1000)
        self.assertNotIn("rodeur", meta.run_config().classes)
        meta.acheter("nourriture")           # l'odeur attire les bêtes
        self.assertIn("rodeur", meta.run_config().classes)
        self.assertNotIn("guerrier", meta.run_config().classes)
        meta.acheter("epee")
        self.assertIn("guerrier", meta.run_config().classes)
        self.assertNotIn("blinde", meta.run_config().classes)
        meta.acheter("bouclier")
        self.assertIn("blinde", meta.run_config().classes)

    def test_sans_talent_aucune_classe_n_est_reveillee(self):
        self.assertEqual(Meta().run_config().classes & set(monsters.CLASSES),
                         set())

    def test_les_drapeaux_arrivent_dans_la_config(self):
        meta = Meta(xp=1000)
        meta.acheter("nourriture")
        meta.acheter("herbes")
        self.assertIn("herbes", meta.run_config().unlocks)
        self.assertNotIn("grimoires", meta.run_config().unlocks)

    def test_le_run_recoit_bien_les_talents(self):
        session = Session(sauvegarde=False)
        session.meta = Meta(xp=1000)
        session.meta.acheter("estomac")
        session.meta.acheter("nourriture")
        game = session.descendre()
        self.assertGreater(game.player.max_fullness, RunConfig().max_fullness)
        self.assertEqual([objet.type.key for objet in game.player.inventory],
                         ["onigiri"])

    def test_un_talent_inconnu_dans_la_sauvegarde_est_ignore(self):
        """Une sauvegarde d'une version future ne doit pas planter le jeu."""
        meta = Meta(noeuds=["estomac", "talent_du_futur"])
        self.assertGreater(meta.run_config().max_fullness,
                           RunConfig().max_fullness)


class TestAchats(unittest.TestCase):
    def test_on_ne_peut_pas_payer_ce_qu_on_n_a_pas(self):
        meta = Meta(xp=1)
        self.assertIsNone(meta.acheter("estomac"))
        self.assertEqual(meta.noeuds, [])

    def test_les_prerequis_sont_respectes(self):
        meta = Meta(xp=1000)
        self.assertIsNone(meta.acheter("besace"))        # exige « estomac »
        meta.acheter("estomac")
        self.assertIsNotNone(meta.acheter("besace"))

    def test_on_n_achete_pas_deux_fois(self):
        meta = Meta(xp=1000)
        meta.acheter("besace")                           # exige « estomac »
        meta.acheter("estomac")
        meta.acheter("besace")
        self.assertIsNone(meta.acheter("besace"))
        self.assertEqual(meta.noeuds.count("besace"), 1)

    def test_un_noeud_repetable_coute_de_plus_en_plus_cher(self):
        meta = Meta(xp=1000)
        prix = []
        for _ in range(tree.ARBRE["estomac"].repetitions):
            prix.append(tree.ARBRE["estomac"].prix(meta.noeuds))
            avant = meta.xp
            meta.acheter("estomac")
            self.assertEqual(avant - meta.xp, prix[-1])
        self.assertEqual(prix, sorted(prix))
        self.assertGreater(prix[-1], prix[0])

    def test_la_capacite_du_coffre_suit_l_arbre(self):
        meta = Meta(xp=1000)
        avant = meta.capacite_entrepot()
        for cle in ("nourriture", "coffre", "grand_coffre"):
            meta.acheter(cle)
        self.assertEqual(meta.capacite_entrepot(), avant + 4)


class TestPersistance(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.chemin = os.path.join(self.dossier, "sous-dossier", "meta.json")

    def test_aller_retour(self):
        meta = Meta(xp=12.5, xp_totale=99, runs=9, best_depth=13,
                    best_levels=22, noeuds=["estomac", "epee"])
        self.assertTrue(meta_mod.save(meta, self.chemin))
        relu = meta_mod.load(self.chemin)
        self.assertEqual(relu.to_dict(), meta.to_dict())

    def test_un_fichier_absent_donne_une_progression_neuve(self):
        neuf = meta_mod.load(os.path.join(self.dossier, "rien.json"))
        self.assertEqual(neuf.xp, 0)
        self.assertEqual(neuf.noeuds, [])

    def test_un_fichier_corrompu_ne_bloque_pas_le_jeu(self):
        os.makedirs(os.path.dirname(self.chemin), exist_ok=True)
        with open(self.chemin, "w") as fichier:
            fichier.write("{ceci n'est pas du json")
        self.assertEqual(meta_mod.load(self.chemin).xp, 0)

    def test_un_fichier_partiel_est_tolere(self):
        os.makedirs(os.path.dirname(self.chemin), exist_ok=True)
        with open(self.chemin, "w") as fichier:
            json.dump({"xp": 30, "inconnu": "ignoré"}, fichier)
        relu = meta_mod.load(self.chemin)
        self.assertEqual(relu.xp, 30)
        self.assertEqual(relu.runs, 0)

    def test_la_session_sauvegarde_a_la_fin_d_une_vie(self):
        session = Session(chemin=self.chemin)
        game = session.descendre()
        game.player.skills.levels["marche"] = 30
        game.end_run("mort", "Test.")
        session.encaisser(game)
        self.assertGreater(meta_mod.load(self.chemin).xp, 0)

    def test_un_achat_est_sauvegarde(self):
        session = Session(chemin=self.chemin)
        session.meta.xp = 100
        session.acheter("estomac")
        self.assertIn("estomac", meta_mod.load(self.chemin).noeuds)

    def test_sans_sauvegarde_rien_n_est_ecrit(self):
        session = Session(chemin=self.chemin, sauvegarde=False)
        game = session.descendre()
        game.end_run("mort", "Test.")
        session.encaisser(game)
        self.assertFalse(os.path.exists(self.chemin))


class TestFrontiere(unittest.TestCase):
    def test_le_moteur_ignore_le_meta(self):
        """Rien dans Game ne connaît la progression permanente."""
        import donjon.game as game_mod

        source = open(game_mod.__file__, encoding="utf-8").read()
        self.assertNotIn("import meta", source)
        self.assertNotIn("from .meta", source)
        self.assertNotIn("Meta", source)


if __name__ == "__main__":
    unittest.main()


class TestReinitialisation(unittest.TestCase):
    """Le seul geste destructeur du jeu : il doit être complet et sûr."""

    def setUp(self):
        self.chemin = os.path.join(tempfile.mkdtemp(), "meta.json")
        self.session = Session(chemin=self.chemin)
        self.session.meta.xp = 500
        for cle in ("nourriture", "coffre"):
            self.session.acheter(cle)
        self.session.demarrer()
        self.session.deposer(self.session.player.inventory[0]
                             if self.session.player.inventory
                             else self._offrir())

    def _offrir(self):
        from donjon import items

        objet = items.make("onigiri")
        self.session.player.add_item(objet)
        return objet

    def test_tout_disparait(self):
        self.session.reinitialiser()
        self.assertEqual(self.session.meta.xp, 0)
        self.assertEqual(self.session.meta.noeuds, [])
        self.assertEqual(self.session.meta.entrepot, [])
        self.assertEqual(self.session.meta.runs, 0)

    def test_le_fichier_de_sauvegarde_est_supprime(self):
        self.assertTrue(os.path.exists(self.chemin))
        self.session.reinitialiser()
        self.assertFalse(os.path.exists(self.chemin))

    def test_on_repart_au_refuge_avec_un_heros_neuf(self):
        ancien = self.session.player
        game = self.session.reinitialiser()
        self.assertTrue(game.config.is_hub)
        self.assertIsNot(self.session.player, ancien)
        self.assertEqual(self.session.player.skills.total_levels(), 0)

    def test_le_donjon_redevient_le_couloir_vide_du_debut(self):
        self.session.reinitialiser()
        config = self.session.config_de_run()
        self.assertEqual(config.monsters_per_floor, (0, 0))
        self.assertEqual(config.items_per_floor, (0, 0))
        self.assertEqual(config.starting_kit, ())

    def test_effacer_un_fichier_absent_ne_leve_pas(self):
        self.assertTrue(meta_mod.effacer(self.chemin + ".rien"))
