"""L'axe des formes : ce que la forme donne, et que la matière n'a pas.

La forme dit **comment on frappe**. C'est elle, et elle seule, qui porte les
chiffres : ce qu'un coup fait mal, ce qu'il coûte d'énergie, jusqu'où il va.
Quatre formes de mêlée et un bouclier, croisés avec cinq matières, font
vingt-cinq équipements qu'aucune ligne ne décrit un par un.

Les tests ci-dessous tiennent trois choses :

* les deux axes restent **indépendants** — changer de matière ne change aucun
  chiffre, changer de forme ne change aucune affinité ;
* la cadence est réellement payée, sinon « une dague frappe vite » serait une
  note dans une docstring ;
* la lance traverse, mais ne touche **pas** à travers un mur, et ne change rien
  à la façon de se déplacer.
"""

import unittest

from donjon import affinites, events, items, skills
from donjon.entities import ACTION_COST
from tests.helpers import place_monster, sandbox


ARMES = [cle for cle, forme in items.FORMES.items()
         if forme["categorie"] == items.WEAPON]


class TestLeCroisement(unittest.TestCase):
    def test_cinq_formes_et_cinq_matieres_font_vingt_cinq_equipements(self):
        equipements = [t for t in items.ITEM_TYPES.values() if t.matiere]
        self.assertEqual(len(equipements),
                         len(items.FORMES) * len(items.MATIERES))
        self.assertEqual(len(ARMES), 4)

    def test_la_forme_porte_les_chiffres_et_la_matiere_aucun(self):
        """Le croisement ne vaut que si les deux axes ne se marchent pas dessus."""
        for cle_forme, forme in items.FORMES.items():
            for champ in ("power", "cadence", "portee"):
                valeurs = {getattr(items.ITEM_TYPES[f"{cle_forme}_{m}"], champ)
                           for m in items.MATIERES}
                self.assertEqual(len(valeurs), 1,
                                 f"{cle_forme}.{champ} varie avec la matière")
            self.assertEqual(
                items.ITEM_TYPES[f"{cle_forme}_bois"].power, forme["attaque"])

    def test_chaque_forme_de_melee_a_sa_competence(self):
        for cle in ARMES:
            competence = skills.CATALOGUE.get(cle)
            self.assertIsNotNone(competence, cle)
            self.assertEqual(competence.scope, skills.EQUIPEMENT, cle)

    def test_les_formes_se_partagent_le_poids_d_une_seule(self):
        """Quatre formes ne doivent pas quadrupler la part des armes au sol.

        Sans la part de `FORMES`, passer d'une forme à quatre couvrait le
        donjon d'épées au détriment des herbes et des vivres — une refonte de
        l'équipement qui aurait discrètement refait l'économie des objets.
        """
        self.assertAlmostEqual(sum(items.FORMES[c]["poids"] for c in ARMES), 1.0)
        arme = sum(items.ITEM_TYPES[f"{c}_{m}"].weight
                   for c in ARMES for m in items.MATIERES)
        matieres = sum(m["poids"] for m in items.MATIERES.values())
        self.assertAlmostEqual(arme, matieres)


class TestLaCadence(unittest.TestCase):
    """Une dague frappe vite : encore faut-il que ça se paie en énergie."""

    def _energie_depensee(self, cle_arme):
        jeu = sandbox(seed=1)
        joueur = jeu.player
        joueur.weapon = items.make(cle_arme) if cle_arme else None
        x, y = joueur.pos
        cible = place_monster(jeu, (x + 1, y), "mamel", hp=999)
        joueur.energy = ACTION_COST
        jeu.attack(joueur, cible)
        return ACTION_COST - joueur.energy

    def test_la_dague_coute_moins_cher_que_l_epee_et_la_hache_plus(self):
        self.assertLess(self._energie_depensee("dague_bois"),
                        self._energie_depensee("epee_bois"))
        self.assertGreater(self._energie_depensee("hache_bois"),
                           self._energie_depensee("epee_bois"))

    def test_chaque_arme_coute_exactement_sa_cadence(self):
        for cle in ARMES:
            self.assertEqual(self._energie_depensee(f"{cle}_bois"),
                             items.FORMES[cle]["cadence"], cle)

    def test_les_mains_nues_coutent_un_tour_plein(self):
        self.assertEqual(self._energie_depensee(None), ACTION_COST)

    def test_le_cout_est_paye_une_fois_meme_quand_la_lance_traverse(self):
        """Sinon une lance devant deux créatures coûterait deux tours."""
        jeu = sandbox(seed=1)
        joueur = jeu.player
        joueur.weapon = items.make("lance_bois")
        x, y = joueur.pos
        premier = place_monster(jeu, (x + 1, y), "mamel", hp=999)
        place_monster(jeu, (x + 2, y), "mamel", hp=999)
        joueur.energy = ACTION_COST
        jeu.attack(joueur, premier)
        self.assertEqual(ACTION_COST - joueur.energy,
                         items.FORMES["lance"]["cadence"])


class TestLaPortee(unittest.TestCase):
    """La lance traverse — et seulement ça."""

    def _scene(self, cle_arme):
        jeu = sandbox(seed=1)
        jeu.player.weapon = items.make(cle_arme)
        x, y = jeu.player.pos
        devant = place_monster(jeu, (x + 1, y), "mamel", hp=999)
        derriere = place_monster(jeu, (x + 2, y), "mamel", hp=999)
        return jeu, devant, derriere

    def test_la_lance_touche_ce_qui_est_derriere(self):
        jeu, devant, derriere = self._scene("lance_bois")
        jeu.attack(jeu.player, devant)
        self.assertLess(devant.hp, 999)
        self.assertLess(derriere.hp, 999)

    def test_l_epee_ne_touche_que_le_voisin(self):
        jeu, devant, derriere = self._scene("epee_bois")
        jeu.attack(jeu.player, devant)
        self.assertLess(devant.hp, 999)
        self.assertEqual(derriere.hp, 999)

    def test_la_lance_ne_traverse_pas_un_mur(self):
        jeu = sandbox(seed=1)
        jeu.player.weapon = items.make("lance_bois")
        x, y = jeu.player.pos
        devant = place_monster(jeu, (x + 1, y), "mamel", hp=999)
        cache = place_monster(jeu, (x + 2, y), "mamel", hp=999)
        from donjon import tiles
        jeu.level.set_tile((x + 2, y), tiles.WALL)
        jeu.attack(jeu.player, devant)
        self.assertEqual(cache.hp, 999)

    def test_la_lance_ne_change_rien_au_deplacement(self):
        """Frapper reste « avancer sur la case d'à côté ».

        Une lance qui attaquerait à deux cases empêcherait de marcher vers une
        créature : ce serait un piège, pas une portée.
        """
        jeu = sandbox(seed=1)
        jeu.player.weapon = items.make("lance_bois")
        x, y = jeu.player.pos
        loin = place_monster(jeu, (x + 2, y), "mamel", hp=999)
        jeu.cmd_move((1, 0))
        self.assertEqual(jeu.player.pos, (x + 1, y))
        self.assertEqual(loin.hp, 999)

    def test_la_lance_n_atteint_pas_le_porteur(self):
        """Deux héros n'existent pas, mais la règle doit valoir sans ça."""
        jeu = sandbox(seed=1)
        jeu.player.weapon = items.make("lance_bois")
        x, y = jeu.player.pos
        devant = place_monster(jeu, (x + 1, y), "mamel", hp=999)
        avant = jeu.player.hp
        jeu.attack(jeu.player, devant)
        self.assertEqual(jeu.player.hp, avant)


class TestLesDeuxAxesEnsemble(unittest.TestCase):
    """Forme et matière se croisent sans se confondre."""

    def test_la_matiere_mord_quelle_que_soit_la_forme(self):
        jeu = sandbox(seed=1)
        joueur = jeu.player
        joueur.shield = None
        animal = place_monster(jeu, (0, 0), "mamel")
        homoncule = place_monster(jeu, (1, 1), "golem")
        for cle in ARMES:
            joueur.weapon = items.make(f"{cle}_argent")
            self.assertGreater(joueur.attaque_contre(animal),
                               joueur.attaque_contre(homoncule), cle)

    def test_un_coup_credite_la_forme_reelle_et_sa_matiere(self):
        jeu = sandbox(seed=1)
        jeu.player.weapon = items.make("hache_obsidienne")
        cible = place_monster(jeu, (0, 0), "mamel")
        jeu.notify(events.COUP, arme=jeu.player.weapon, cible=cible,
                   touche=True, degats=5)
        investie = jeu.player.skills.investie
        self.assertGreater(investie.get("hache", 0), 0)
        self.assertGreater(investie.get("obsidienne", 0), 0)
        self.assertEqual(investie.get("epee", 0), 0)

    def test_l_affinite_ne_depend_pas_de_la_forme(self):
        """Le tableau des affinités ne connaît que la matière, et doit le rester."""
        for ligne in affinites.AFFINITES.values():
            self.assertNotIn("epee", ligne)
            self.assertNotIn("hache", ligne)


if __name__ == "__main__":
    unittest.main()
