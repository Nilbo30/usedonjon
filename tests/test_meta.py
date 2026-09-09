"""Progression permanente : la boucle qui fait de la mort un progrès.

On vérifie surtout deux choses : que le méta n'influence les runs que par la
`RunConfig`, et que le pari de l'orbe tient — mourir moins profond rapporte
moins, à niveaux de compétences égaux.
"""

import json
import os
import tempfile
import unittest

from donjon import meta as meta_mod
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
    def test_absorber_fait_monter_le_niveau(self):
        meta = Meta()
        gagnee, franchis = meta.absorb(bilan(deepest=5, levels=30))
        self.assertGreater(gagnee, 0)
        self.assertTrue(franchis)
        self.assertEqual(meta.level, len(franchis))
        self.assertEqual(meta.runs, 1)

    def test_l_xp_restante_est_conservee(self):
        meta = Meta()
        meta.absorb(bilan(levels=5))
        self.assertEqual(meta.level, 0)
        self.assertEqual(meta.progress(), (5, meta_mod.cout_du_niveau(0)))

    def test_les_records_sont_retenus(self):
        meta = Meta()
        meta.absorb(bilan(deepest=9, levels=4))
        meta.absorb(bilan(deepest=3, levels=12))
        self.assertEqual(meta.best_depth, 9)
        self.assertEqual(meta.best_levels, 12)


class TestInfluenceSurLesRuns(unittest.TestCase):
    def test_sans_niveau_la_config_est_la_config_de_base(self):
        base = RunConfig()
        self.assertEqual(Meta().run_config(base).max_fullness, base.max_fullness)

    def test_les_bonus_s_accumulent(self):
        base = RunConfig()
        meta = Meta(level=3)
        config = meta.run_config(base)
        attendu = (base.max_fullness + meta_mod.BONUS[1]["max_fullness"]
                   + meta_mod.BONUS[3]["max_fullness"])
        self.assertEqual(config.max_fullness, attendu)
        self.assertEqual(config.start_hp,
                         base.start_hp + meta_mod.BONUS[2]["start_hp"])

    def test_la_table_de_bonus_ne_vise_que_des_champs_reels(self):
        base = RunConfig()
        for niveau, apports in meta_mod.BONUS.items():
            for champ in apports:
                self.assertTrue(hasattr(base, champ), f"niveau {niveau}: {champ}")

    def test_le_run_recoit_bien_les_bonus(self):
        session = Session(sauvegarde=False)
        session.meta = Meta(level=3)
        game = session.nouvelle_partie(seed=1)
        self.assertGreater(game.player.max_fullness, RunConfig().max_fullness)
        self.assertGreater(game.player.max_hp, RunConfig().start_hp)


class TestSession(unittest.TestCase):
    def test_encaisser_une_seule_fois(self):
        session = Session(sauvegarde=False)
        game = session.nouvelle_partie(seed=1)
        game.end_run("mort", "Test.")
        self.assertIsNotNone(session.encaisser(game))
        self.assertIsNone(session.encaisser(game))
        self.assertEqual(session.meta.runs, 1)

    def test_chaque_run_est_bien_encaisse(self):
        """Régression : un dédoublonnage par id() ratait des runs entiers.

        Python recycle les identifiants des objets libérés ; un bilan neuf
        tombait sur l'adresse d'un ancien et passait pour déjà encaissé.
        """
        session = Session(sauvegarde=False)
        for numero in range(12):
            game = session.nouvelle_partie(seed=numero)
            game.player.skills.levels["marche"] = 1
            game.end_run("mort", "Test.")
            self.assertIsNotNone(session.encaisser(game), f"run {numero}")
        self.assertEqual(session.meta.runs, 12)

    def test_une_partie_en_cours_ne_s_encaisse_pas(self):
        session = Session(sauvegarde=False)
        game = session.nouvelle_partie(seed=1)
        self.assertIsNone(session.encaisser(game))
        self.assertEqual(session.meta.runs, 0)

    def test_le_moteur_ignore_le_meta(self):
        """La frontière : rien dans Game ne connaît la progression permanente."""
        import donjon.game as game_mod

        source = open(game_mod.__file__, encoding="utf-8").read()
        self.assertNotIn("import meta", source)
        self.assertNotIn("from .meta", source)
        self.assertNotIn("Meta", source)


class TestPersistance(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.chemin = os.path.join(self.dossier, "sous-dossier", "meta.json")

    def test_aller_retour(self):
        meta = Meta(level=4, xp=12.5, runs=9, best_depth=13, best_levels=22)
        self.assertTrue(meta_mod.save(meta, self.chemin))
        relu = meta_mod.load(self.chemin)
        self.assertEqual(relu.to_dict(), meta.to_dict())

    def test_un_fichier_absent_donne_une_progression_neuve(self):
        neuf = meta_mod.load(os.path.join(self.dossier, "rien.json"))
        self.assertEqual(neuf.level, 0)
        self.assertEqual(neuf.runs, 0)

    def test_un_fichier_corrompu_ne_bloque_pas_le_jeu(self):
        with open(self.chemin.replace("sous-dossier/", ""), "w") as f:
            f.write("{ceci n'est pas du json")
        self.assertEqual(meta_mod.load(self.chemin).level, 0)

    def test_un_fichier_partiel_est_tolere(self):
        os.makedirs(os.path.dirname(self.chemin), exist_ok=True)
        with open(self.chemin, "w") as f:
            json.dump({"level": 3, "inconnu": "ignoré"}, f)
        relu = meta_mod.load(self.chemin)
        self.assertEqual(relu.level, 3)
        self.assertEqual(relu.runs, 0)

    def test_la_session_sauvegarde_a_la_fin_d_un_run(self):
        session = Session(chemin=self.chemin)
        game = session.nouvelle_partie(seed=1)
        game.player.skills.levels["marche"] = 30
        game.end_run("mort", "Test.")
        session.encaisser(game)
        self.assertGreater(meta_mod.load(self.chemin).level, 0)

    def test_sans_sauvegarde_rien_n_est_ecrit(self):
        session = Session(chemin=self.chemin, sauvegarde=False)
        game = session.nouvelle_partie(seed=1)
        game.end_run("mort", "Test.")
        session.encaisser(game)
        self.assertFalse(os.path.exists(self.chemin))


if __name__ == "__main__":
    unittest.main()
