"""L'axe des matières : ce que la matière donne, et surtout ce qu'elle ne donne pas.

Un seul interdit tient tout le chantier : **la matière ne donne jamais
d'attaque brute**. S'il tombe, une épée en bois entraînée bat une épée en
argent trouvée le jour même, et la boucle du butin meurt — on ne ramasse plus
rien, on monte une compétence. Le premier test de ce fichier est donc moins un
test qu'un verrou de design.

Le reste vérifie que la rencontre a bien lieu des deux côtés : l'arme mord la
famille d'en face, le bouclier repousse la famille de celui qui frappe, et le
coup crédite les **deux** compétences — la forme et la matière.
"""

import unittest

from donjon import affinites, events, items, monsters, skills
from tests.helpers import place_monster, sandbox


class TestLeVerrou(unittest.TestCase):
    """La matière ne porte aucun chiffre d'attaque. Jamais."""

    def test_toutes_les_matieres_d_une_forme_frappent_pareil(self):
        for cle_forme, forme in items.FORMES.items():
            puissances = {
                matiere: items.ITEM_TYPES[f"{cle_forme}_{matiere}"].power
                for matiere in items.MATIERES
            }
            self.assertEqual(set(puissances.values()), {forme["attaque"]},
                             f"{cle_forme} : la matière a dérapé sur le chiffre")

    #: Ce qu'une matière a le droit de porter. Pas d'`attaque`, jamais : le
    #: jour où ce champ apparaît, le verrou du chantier a sauté.
    CHAMPS_DE_MATIERE = {"nom", "poids", "profondeur"}

    def test_la_forme_est_le_seul_endroit_ou_l_attaque_est_ecrite(self):
        """Un `attaque` dans `MATIERES` serait le verrou en train de sauter."""
        for matiere, donnees in items.MATIERES.items():
            self.assertNotIn("attaque", donnees, matiere)
            self.assertEqual(set(donnees), self.CHAMPS_DE_MATIERE, matiere)


class TestLesTables(unittest.TestCase):
    """Les trois tables doivent se répondre, sinon une matière est muette."""

    def test_chaque_matiere_a_sa_ligne_d_affinites(self):
        self.assertEqual(set(items.MATIERES), set(affinites.AFFINITES))

    def test_chaque_ligne_couvre_toutes_les_familles(self):
        for matiere, ligne in affinites.AFFINITES.items():
            self.assertEqual(set(ligne), set(monsters.FAMILLES), matiere)

    def test_chaque_matiere_a_sa_competence(self):
        """Sans compétence, la matière n'aurait pas de courbe — donc pas de pivot."""
        for matiere in items.MATIERES:
            competence = skills.CATALOGUE.get(matiere)
            self.assertIsNotNone(competence, matiere)
            self.assertEqual(competence.scope, skills.EQUIPEMENT, matiere)

    def test_aucune_matiere_n_est_bonne_partout(self):
        """Une matière sans faiblesse rendrait les quatre autres décoratives."""
        for matiere, ligne in affinites.AFFINITES.items():
            self.assertLessEqual(min(ligne.values()), 1.0, matiere)


class TestLaMorsure(unittest.TestCase):
    """L'arme rencontre la famille d'en face, et seulement en combat."""

    def setUp(self):
        self.jeu = sandbox(seed=1)
        self.jeu.player.inventory.clear()
        self.jeu.player.shield = None

    def _frappe(self, cle_arme, cle_monstre):
        self.jeu.player.weapon = items.make(cle_arme)
        cible = place_monster(self.jeu, (0, 0), cle_monstre)
        return self.jeu.player.attaque_contre(cible)

    def test_l_argent_mord_la_chair_et_glisse_sur_le_fabrique(self):
        self.assertGreater(self._frappe("epee_argent", "mamel"),
                           self._frappe("epee_argent", "golem"))

    def test_le_fer_fait_l_inverse(self):
        self.assertLess(self._frappe("epee_fer", "mamel"),
                        self._frappe("epee_fer", "golem"))

    def test_la_meme_arme_contre_la_meme_famille_vaut_le_multiplicateur(self):
        nu = self.jeu.player.base_attack + items.ITEM_TYPES["epee_argent"].power
        self.assertEqual(self._frappe("epee_argent", "mamel"),
                         int(nu * affinites.AFFINITES["argent"]["animal"]))

    def test_la_fiche_du_heros_ignore_les_affinites(self):
        """Hors combat il n'y a pas de famille en face : afficher ×1,3 mentirait."""
        self.jeu.player.weapon = items.make("epee_argent")
        self.assertEqual(
            self.jeu.player.attack,
            self.jeu.player.base_attack + items.ITEM_TYPES["epee_argent"].power)

    def test_les_mains_nues_ne_connaissent_aucune_matiere(self):
        self.jeu.player.weapon = None
        cible = place_monster(self.jeu, (0, 0), "mamel")
        self.assertEqual(self.jeu.player.attaque_contre(cible),
                         self.jeu.player.base_attack)


class TestLaMaitriseResteSoumiseALAffinite(unittest.TestCase):
    """Ce qui garde la boucle du butin en vie, et ce n'est pas un plafond.

    La compétence de matière donne de l'attaque — c'est sa courbe. Le danger
    nommé par le brief est qu'une épée en bois entraînée finisse par battre une
    épée en argent trouvée le jour même : le jour où c'est vrai, on ne ramasse
    plus rien.

    Ce n'est pas vrai, et pas par prudence sur un chiffre : la compétence
    s'**ajoute** avant que l'affinité ne **multiplie**. Maîtriser une matière
    qui glisse, c'est donc voir sa maîtrise glisser avec elle. Le bois à 26 de
    compétence rattrape le fer neuf contre un homoncule ; le bot, lui, plafonne
    à 4. Le test ci-dessous tient la structure, pas la marge.
    """

    def test_la_maitrise_est_multipliee_par_l_affinite(self):
        jeu = sandbox(seed=1)
        joueur = jeu.player
        joueur.shield = None
        cible = place_monster(jeu, (0, 0), "golem")   # homoncule

        joueur.weapon = items.make("epee_bois")       # bois × homoncule = 0,7
        joueur.skills.levels["bois"] = 0
        nu = joueur.attaque_contre(cible)
        joueur.skills.levels["bois"] = 10
        entraine = joueur.attaque_contre(cible)

        gagne = entraine - nu
        self.assertGreater(gagne, 0, "la compétence doit servir à quelque chose")
        self.assertLess(gagne, 10,
                        "une matière qui glisse doit faire glisser sa maîtrise")


class TestLeBouclier(unittest.TestCase):
    """Le même tableau, lu à l'envers : ce que le bouclier repousse."""

    def setUp(self):
        self.jeu = sandbox(seed=1)
        self.jeu.player.inventory.clear()
        self.jeu.player.weapon = None
        self.animal = place_monster(self.jeu, (0, 0), "mamel")

    def _encaisse(self, cle_bouclier):
        self.jeu.player.shield = (items.make(cle_bouclier) if cle_bouclier
                                  else None)
        return self.animal.attaque_contre(self.jeu.player)

    def test_un_bouclier_fort_contre_la_famille_qui_frappe_amortit(self):
        """L'argent mord l'animal : porté en bouclier, il le repousse."""
        self.assertLess(self._encaisse("bouclier_argent"),
                        self._encaisse("bouclier_fer"))

    def test_sans_bouclier_le_coup_est_celui_du_monstre(self):
        nu = self._encaisse(None)
        self.assertEqual(nu, self.animal.base_attack)

    def test_le_bouclier_n_ajoute_pas_d_attaque_au_monstre(self):
        """Le multiplicateur défensif ne doit jamais dépasser 1 vers le haut."""
        self.assertLessEqual(self._encaisse("bouclier_bois"),
                             self._encaisse(None))


class TestLesDeuxCompetences(unittest.TestCase):
    """Un coup entraîne la forme **et** la matière : c'est ce qui crée le pivot."""

    def test_un_coup_porte_credite_la_forme_et_la_matiere(self):
        jeu = sandbox(seed=1)
        jeu.player.weapon = items.make("epee_argent")
        cible = place_monster(jeu, (0, 0), "mamel")
        avant = dict(jeu.player.skills.investie)

        jeu.notify(events.COUP, arme=jeu.player.weapon, cible=cible,
                   touche=True, degats=5)

        apres = jeu.player.skills.investie
        for cle in ("epee", "argent"):
            self.assertGreater(apres.get(cle, 0), avant.get(cle, 0), cle)

    def test_un_coup_manque_n_entraine_rien(self):
        jeu = sandbox(seed=1)
        jeu.player.weapon = items.make("epee_argent")
        cible = place_monster(jeu, (0, 0), "mamel")
        avant = dict(jeu.player.skills.investie)

        jeu.notify(events.COUP, arme=jeu.player.weapon, cible=cible,
                   touche=False, degats=0)

        self.assertEqual(dict(jeu.player.skills.investie), avant)

    def test_un_coup_recu_credite_la_matiere_du_bouclier(self):
        jeu = sandbox(seed=1)
        jeu.player.shield = items.make("bouclier_bronze")
        source = place_monster(jeu, (0, 0), "mamel")
        avant = dict(jeu.player.skills.investie)

        jeu.notify(events.COUP_RECU, bouclier=jeu.player.shield,
                   source=source, degats=3)

        self.assertGreater(jeu.player.skills.investie.get("bronze", 0),
                           avant.get("bronze", 0))


class TestLaProfondeur(unittest.TestCase):
    """Le pivot est offert par la profondeur : encore faut-il qu'elle trie."""

    def test_les_matieres_rares_n_apparaissent_pas_au_premier_etage(self):
        surface = {cle for cle, type_ in items.ITEM_TYPES.items()
                   if type_.matiere and type_.depth_min <= 1}
        self.assertIn("epee_bois", surface)
        self.assertNotIn("epee_obsidienne", surface)

    def test_chaque_matiere_finit_par_apparaitre(self):
        profond = {items.ITEM_TYPES[f"epee_{m}"].depth_min
                   for m in items.MATIERES}
        self.assertTrue(all(p < 20 for p in profond), profond)

    def test_les_familles_ne_se_croisent_pas_partout(self):
        """Le fondement du pivot : l'animal en haut, l'homoncule en bas.

        Si les trois familles se mélangeaient à tous les étages, aucune matière
        ne cesserait jamais de mordre, et changer d'arme n'aurait aucun sens.
        """
        par_famille = {}
        for espece in monsters.SPECIES:
            bas, haut = espece["depth"]
            connu = par_famille.setdefault(espece["famille"], [99, 0])
            par_famille[espece["famille"]] = [min(connu[0], bas),
                                              max(connu[1], haut)]
        self.assertLess(par_famille["animal"][1], par_famille["homoncule"][1])
        self.assertLess(par_famille["animal"][0], par_famille["homoncule"][0])


if __name__ == "__main__":
    unittest.main()
