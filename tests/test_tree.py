"""L'arbre des talents : sa cohérence, et le rythme qu'il donne au jeu.

Le test le plus utile est le dernier : il vérifie qu'une première mort suffit
à s'offrir un premier talent. Sans ça, le jeu s'ouvrirait sur deux vies vides.
"""

import unittest

from donjon import items, tree
from donjon.config import RunConfig
from donjon.meta import Meta
from donjon.script import autoplay
from donjon.session import Session


class TestCoherence(unittest.TestCase):
    def test_les_prerequis_existent(self):
        for noeud in tree.ARBRE.values():
            for parent in noeud.parents:
                self.assertIn(parent, tree.ARBRE, f"{noeud.key} → {parent}")

    def test_aucun_noeud_n_est_son_propre_ancetre(self):
        for cle in tree.ARBRE:
            vus, a_voir = set(), list(tree.ARBRE[cle].parents)
            while a_voir:
                courant = a_voir.pop()
                self.assertNotEqual(courant, cle, f"cycle sur {cle}")
                if courant not in vus:
                    vus.add(courant)
                    a_voir += list(tree.ARBRE[courant].parents)

    def test_les_effets_visent_des_champs_reels(self):
        base = RunConfig()
        for noeud in tree.ARBRE.values():
            for champ in noeud.effets:
                self.assertTrue(hasattr(base, champ) or champ in tree.EFFETS_META,
                                f"{noeud.key}: {champ}")
            for champ in noeud.reglages:
                self.assertTrue(hasattr(base, champ), f"{noeud.key}: {champ}")

    def test_la_base_verrouillee_vise_des_champs_reels(self):
        base = RunConfig()
        for champ in tree.BASE_VERROUILLEE:
            self.assertTrue(hasattr(base, champ), champ)

    def test_tout_l_arbre_est_atteignable(self):
        """Aucun nœud ne doit être verrouillé pour toujours."""
        meta = Meta(xp=10 ** 6)
        for _ in range(len(tree.ARBRE)):
            for noeud in tree.disponibles(meta.noeuds):
                meta.acheter(noeud.key)
        self.assertEqual(len(meta.noeuds), len(tree.ARBRE))

    def test_les_prix_suivent_l_echelle(self):
        echelle = {3, 12, 35, 90, 220}
        for noeud in tree.ARBRE.values():
            self.assertIn(noeud.cost, echelle, noeud.key)

    def test_chaque_noeud_s_explique(self):
        for noeud in tree.ARBRE.values():
            self.assertTrue(noeud.description.strip(), noeud.key)
            self.assertTrue(noeud.branche, noeud.key)


class TestVerrouillageDuContenu(unittest.TestCase):
    def test_chaque_verrou_d_objet_est_donne_par_un_noeud(self):
        donnes = {drapeau for noeud in tree.ARBRE.values()
                  for drapeau in noeud.unlocks}
        for type_objet in items.ITEM_TYPES.values():
            if type_objet.unlock:
                self.assertIn(type_objet.unlock, donnes, type_objet.key)

    def test_une_config_nue_a_tous_les_verrous(self):
        """Le moteur, le bot et les tests jouent au jeu complet."""
        config = RunConfig()
        for noeud in tree.ARBRE.values():
            for drapeau in noeud.unlocks:
                self.assertIn(drapeau, config.unlocks, drapeau)

    def test_sans_talent_on_ne_trouve_ni_herbe_ni_parchemin(self):
        from donjon.rng import Rng

        rng = Rng(2)
        config = Meta(xp=100).run_config()
        cles = set()
        for _ in range(200):
            objet = items.random_item(rng, 5, unlocks=config.unlocks)
            if objet:
                cles.add(objet.type.key)
        for interdit in ("herbe_soin", "parchemin_lumiere", "epee_fer",
                         "orbe_retour"):
            self.assertNotIn(interdit, cles)

    def test_le_talent_ouvre_la_famille(self):
        from donjon.rng import Rng

        meta = Meta(xp=1000)
        meta.acheter("fouille")
        meta.acheter("herbes")
        rng = Rng(2)
        cles = {items.random_item(rng, 5, unlocks=meta.run_config().unlocks).type.key
                for _ in range(200)}
        self.assertIn("herbe_soin", cles)
        self.assertNotIn("parchemin_lumiere", cles)


class TestRythme(unittest.TestCase):
    def test_la_premiere_mort_paie_le_premier_talent(self):
        """Sinon le jeu s'ouvrirait sur deux vies vides avant le moindre choix."""
        moins_cher = min(noeud.cost for noeud in tree.disponibles([]))
        gains = []
        for graine in range(12):
            session = Session(sauvegarde=False, seed=graine)
            autoplay(session.descendre(), 30000)
            session.avancer()
            gains.append(session.meta.xp)
        reussites = sum(1 for gain in gains if gain >= moins_cher)
        self.assertGreaterEqual(reussites, 10, f"gains : {gains}")

    def test_le_jeu_s_ouvre_dans_l_ordre_attendu(self):
        """Équipement avant créatures : on ne lâche pas le héros nu devant eux."""
        session = Session(sauvegarde=False, seed=3)
        ordre = []
        for _ in range(12):
            autoplay(session.descendre(), 30000)
            session.avancer()
            while True:
                candidats = [n for n in tree.disponibles(session.meta.noeuds)
                             if n.cost <= session.meta.xp]
                if not candidats:
                    break
                ordre.append(session.acheter(
                    min(candidats, key=lambda n: n.cost).key).key)
        self.assertIn("barda", ordre)
        self.assertIn("creatures", ordre)
        self.assertLess(ordre.index("barda"), ordre.index("creatures"))


if __name__ == "__main__":
    unittest.main()
