"""Les questions du moteur, et ce qui peut y répondre.

Deux choses à prouver, et la seconde est le but du chantier :

* les onze effets de compétence donnent **exactement** ce qu'ils donnaient — ce
  sont les seize empreintes qui le prouvent sur le jeu entier, et les tests
  ci-dessous qui le nomment effet par effet ;
* une interception déclarée **en données** change bien le résultat, sans qu'une
  ligne de moteur ait bougé. Sans ce test, on aurait construit un mécanisme
  sans preuve qu'il sert.
"""

import unittest

from donjon import questions, skills
from donjon.questions import demander
from tests.helpers import sandbox


class TestTables(unittest.TestCase):
    def test_chaque_contribution_vise_une_question_et_un_effet_reels(self):
        """Une faute de frappe ici serait un bonus silencieusement mort."""
        for question, (effet, sens) in questions.CONTRIBUTIONS.items():
            self.assertIn(question, questions.QUESTIONS, question)
            self.assertIn(effet, skills.EFFETS, effet)
            self.assertIn(sens, (questions.AJOUTER, questions.RETIRER))

    def test_chaque_effet_de_competence_alimente_une_question(self):
        """Un effet que plus aucune question ne lit ne servirait plus à rien."""
        alimentes = {effet for effet, _ in questions.CONTRIBUTIONS.values()}
        self.assertEqual(set(skills.EFFETS), alimentes)

    def test_une_interception_sur_une_question_inconnue_est_refusee(self):
        with self.assertRaises(ValueError):
            questions.intercepte("atttaque")(lambda q: None)


class TestLesCinqTemoins(unittest.TestCase):
    """Les cinq effets que le brief désignait : ils sont lus très différemment."""

    def setUp(self):
        self.jeu = sandbox(seed=1)
        self.joueur = self.jeu.player
        self.joueur.weapon = self.joueur.shield = None

    def test_attaque_ajoute_la_competence(self):
        depart = self.joueur.attack
        self.joueur.skills.levels["combat"] = 4      # +0,5 d'attaque par niveau
        self.assertEqual(self.joueur.attack, depart + 2)

    def test_endurance_se_retire_de_la_faim(self):
        """L'effet ne s'ajoute pas à une question « endurance » : il retire de la faim."""
        self.joueur.skills.levels["marche"] = 10     # 0,30 de faim en moins
        creuse = demander(questions.FAIM, 1.0, porteur=self.joueur, mini=0.25)
        self.assertAlmostEqual(creuse, 0.70)

    def test_la_faim_a_un_plancher(self):
        self.joueur.skills.levels["marche"] = 40     # 1,20 : plus que le coût
        creuse = demander(questions.FAIM, 1.0, porteur=self.joueur, mini=0.25)
        self.assertEqual(creuse, 0.25)

    def test_esquive_part_de_zero_et_plafonne(self):
        self.joueur.skills.levels["esquive"] = 3     # 0,27
        self.assertAlmostEqual(
            demander(questions.ESQUIVE, 0, porteur=self.joueur, maxi=0.55), 0.27)
        self.joueur.skills.levels["esquive"] = 20    # 1,80, plafonné
        self.assertAlmostEqual(
            demander(questions.ESQUIVE, 0, porteur=self.joueur, maxi=0.55), 0.55)

    def test_chance_s_ajoute_au_butin_de_base(self):
        self.joueur.skills.levels["chance"] = 5      # +0,15
        self.assertAlmostEqual(
            demander(questions.BUTIN, 0.22, porteur=self.joueur, maxi=0.60), 0.37)

    def test_regeneration_raccourcit_le_repos_sans_passer_sous_un_tour(self):
        self.joueur.skills.levels["recuperation"] = 4    # −1 tour
        self.assertEqual(demander(questions.REPOS, 3, porteur=self.joueur,
                                  mini=1), 2)
        self.joueur.skills.levels["recuperation"] = 40   # −10 tours
        self.assertEqual(demander(questions.REPOS, 3, porteur=self.joueur,
                                  mini=1), 1)

    def test_sans_porteur_la_question_rend_son_depart(self):
        """Un monstre n'a pas de compétences : la question doit rester muette."""
        self.assertEqual(demander(questions.ATTAQUE, 7), 7)


class TestInterception(unittest.TestCase):
    """Le mécanisme mord-il ? Sinon on aura construit un décor."""

    def setUp(self):
        self.jeu = sandbox(seed=1)
        self.joueur = self.jeu.player

    def _poser(self, question, fonction):
        """Enregistre une interception et la retire à la fin du test."""
        questions.intercepte(question)(fonction)
        self.addCleanup(questions.INTERCEPTIONS[question].remove, fonction)

    def test_une_interception_declaree_en_donnees_change_le_resultat(self):
        self._poser(questions.ATTAQUE, lambda q: q.ajouter(5))
        self.assertEqual(demander(questions.ATTAQUE, 10), 15)

    def test_elle_voit_le_contexte_de_la_question(self):
        """C'est tout l'intérêt : `bonus("attaque")` ne savait pas qui on frappait."""
        def contre_le_metal(question):
            if getattr(question.get("cible"), "famille", None) == "metal":
                question.multiplier(2)

        self._poser(questions.ATTAQUE, contre_le_metal)

        class Cible:
            famille = "metal"

        self.assertEqual(demander(questions.ATTAQUE, 10), 10)
        self.assertEqual(demander(questions.ATTAQUE, 10, cible=Cible()), 20)

    def test_les_additions_passent_avant_les_multiplications(self):
        """L'ordre de déclaration ne doit rien décider : sinon il faudrait le régler."""
        fois_deux = lambda q: q.multiplier(2)
        plus_cinq = lambda q: q.ajouter(5)
        self._poser(questions.ATTAQUE, fois_deux)      # déclarée en premier
        self._poser(questions.ATTAQUE, plus_cinq)
        self.assertEqual(demander(questions.ATTAQUE, 10), 30)   # (10+5)×2

    def test_les_multiplicateurs_se_cumulent_sans_ordre(self):
        self._poser(questions.ATTAQUE, lambda q: q.multiplier(2))
        self._poser(questions.ATTAQUE, lambda q: q.multiplier(1.5))
        self.assertEqual(demander(questions.ATTAQUE, 10), 30)

    def test_la_borne_s_applique_apres_tout_le_reste(self):
        self._poser(questions.ESQUIVE, lambda q: q.multiplier(10))
        self.assertAlmostEqual(
            demander(questions.ESQUIVE, 0.1, maxi=0.55), 0.55)

    def test_une_interception_agit_dans_le_jeu_sans_toucher_au_moteur(self):
        """Le vrai test : la question est posée par `game.py`, pas par le test."""
        self.joueur.weapon = self.joueur.shield = None
        avant = self.joueur.attack
        self._poser(questions.ATTAQUE, lambda q: q.multiplier(3))
        self.assertEqual(self.joueur.attack, avant * 3)

    def test_une_interception_ne_peut_rien_declencher(self):
        """Pas de `game` dans une question : aucune cascade au milieu d'un calcul.

        C'est une garantie de structure, pas de discipline — et c'est elle qui
        dispense les questions du garde-fou de l'étape 17.4.
        """
        vues = []
        self._poser(questions.ATTAQUE, lambda q: vues.append(q))
        demander(questions.ATTAQUE, 10, porteur=self.joueur)
        question = vues[0]
        self.assertNotIn("game", question.contexte)
        self.assertFalse(hasattr(question, "game"))
        self.assertFalse(hasattr(question, "notify"))


class TestTypes(unittest.TestCase):
    def test_une_question_sans_multiplicateur_garde_son_type(self):
        """`20 * 1.0` vaut 20.0, et « PV 20/20.0 » est déjà une régression.

        Les seize empreintes l'ont attrapée à la première exécution de
        l'étape 17.1 : c'est la seule chose que cette étape avait cassée.
        """
        self.assertIsInstance(demander(questions.PV_MAX, 20), int)
        self.assertEqual(sandbox(seed=1).player.max_hp, 20)


if __name__ == "__main__":
    unittest.main()
