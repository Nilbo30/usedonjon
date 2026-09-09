"""Compétences : progression à l'usage, bonus, et surtout extensibilité.

Le test qui compte vraiment est `TestExtensibilite` : ajouter une arme d'une
nouvelle famille ne doit demander que des données, jamais une ligne de moteur.
"""

import unittest

from donjon import events, items, skills
from donjon.skills import Regle, Skill, SkillSet, Trainer
from tests.helpers import place_monster, sandbox


class TestCourbes(unittest.TestCase):
    def test_le_cout_augmente_avec_le_niveau(self):
        competence = Skill("essai", "Essai", base=10, growth=2.0)
        self.assertEqual(competence.cost(0), 10)
        self.assertEqual(competence.cost(1), 20)
        self.assertEqual(competence.cost(2), 40)

    def test_un_gain_peut_franchir_plusieurs_niveaux(self):
        jeu = SkillSet({"essai": Skill("essai", "Essai", base=1, growth=1.0)})
        self.assertEqual(jeu.gain("essai", 3), [1, 2, 3])
        self.assertEqual(jeu.level("essai"), 3)

    def test_l_xp_restante_est_conservee(self):
        jeu = SkillSet({"essai": Skill("essai", "Essai", base=10, growth=1.0)})
        jeu.gain("essai", 14)
        self.assertEqual(jeu.level("essai"), 1)
        self.assertEqual(jeu.progress("essai"), (4, 10))

    def test_une_competence_inconnue_est_ignoree(self):
        jeu = SkillSet({})
        self.assertEqual(jeu.gain("fantome", 100), [])
        self.assertEqual(jeu.level("fantome"), 0)

    def test_le_catalogue_ne_declare_que_des_effets_connus(self):
        for competence in skills.CATALOGUE.values():
            for effet in competence.effects:
                self.assertIn(effet, skills.EFFETS, f"{competence.key}: {effet}")

    def test_les_regles_visent_des_evenements_et_des_competences_reels(self):
        for regle in skills.REGLES:
            self.assertIn(regle.evenement, events.NOMS)
            if not regle.competence.startswith("@"):
                self.assertIn(regle.competence, skills.CATALOGUE)
            if regle.defaut:
                self.assertIn(regle.defaut, skills.CATALOGUE)


class TestProgressionEnJeu(unittest.TestCase):
    def setUp(self):
        self.game = sandbox(seed=5)
        self.competences = self.game.player.skills

    def test_marcher_entraine_la_marche(self):
        for _ in range(40):
            self.game.cmd_move((1, 0))
            self.game.cmd_move((-1, 0))
        self.assertGreater(self.competences.level("marche"), 0)

    def test_attendre_n_entraine_rien(self):
        for _ in range(50):
            self.game.cmd_wait()
        self.assertEqual(self.competences.total_levels(), 0)

    def test_frapper_entraine_l_arme_et_le_combat(self):
        """Le cas type d'une action qui crédite deux compétences."""
        place_monster(self.game, (self.game.player.pos[0] + 1,
                                  self.game.player.pos[1]), hp=9999)
        for _ in range(30):
            self.game.cmd_move((1, 0))
        self.assertGreater(self.competences.level("epee"), 0)
        self.assertGreater(self.competences.level("combat"), 0)

    def test_frapper_a_mains_nues_entraine_le_pugilat(self):
        self.game.player.weapon = None
        place_monster(self.game, (self.game.player.pos[0] + 1,
                                  self.game.player.pos[1]), hp=9999)
        for _ in range(30):
            self.game.cmd_move((1, 0))
        self.assertGreater(self.competences.level("pugilat"), 0)
        self.assertEqual(self.competences.level("epee"), 0)

    def test_un_coup_rate_n_entraine_pas(self):
        journal = []
        self.competences.gain = lambda *a, **k: journal.append(a) or []
        cible = place_monster(self.game, (self.game.player.pos[0] + 1,
                                          self.game.player.pos[1]), hp=9999)
        self.game.rng.chance = lambda p: True        # tout rate
        self.game.attack(self.game.player, cible)
        self.assertEqual(journal, [])

    def test_encaisser_entraine_le_bouclier(self):
        monstre = place_monster(self.game, (self.game.player.pos[0] + 1,
                                            self.game.player.pos[1]), attack=1)
        for _ in range(30):
            self.game.attack(monstre, self.game.player)
            self.game.player.hp = self.game.player.max_hp
        self.assertGreater(self.competences.level("bouclier"), 0)

    def test_sans_bouclier_encaisser_n_entraine_rien(self):
        self.game.player.shield = None
        monstre = place_monster(self.game, (self.game.player.pos[0] + 1,
                                            self.game.player.pos[1]), attack=1)
        for _ in range(30):
            self.game.attack(monstre, self.game.player)
            self.game.player.hp = self.game.player.max_hp
        self.assertEqual(self.competences.level("bouclier"), 0)

    def test_une_montee_de_niveau_est_annoncee(self):
        for _ in range(60):
            self.game.cmd_move((1, 0))
            self.game.cmd_move((-1, 0))
        self.assertTrue(any("Marche niveau" in t for t in self.game.log.texts()))


class TestBonus(unittest.TestCase):
    def setUp(self):
        self.game = sandbox(seed=5)
        self.joueur = self.game.player

    def test_l_epee_ne_profite_qu_a_l_epee(self):
        avant = self.joueur.attack
        self.joueur.skills.levels["epee"] = 4
        self.assertEqual(self.joueur.attack, avant + 4)
        self.joueur.weapon = None                  # mains nues : bonus perdu
        self.assertEqual(self.joueur.attack, self.joueur.base_attack + 4 * 0)

    def test_le_combat_profite_toujours(self):
        avant = self.joueur.attack
        self.joueur.skills.levels["combat"] = 4
        self.assertEqual(self.joueur.attack, avant + 2)      # 0.5 par niveau
        self.joueur.weapon = None
        self.assertGreater(self.joueur.attack, self.joueur.base_attack)

    def test_le_combat_donne_des_points_de_vie(self):
        avant = self.joueur.max_hp
        self.joueur.skills.levels["combat"] = 3
        self.assertEqual(self.joueur.max_hp, avant + 6)

    def test_le_bouclier_ne_compte_qu_equipe(self):
        self.joueur.skills.levels["bouclier"] = 3
        avec = self.joueur.defense
        self.joueur.shield = None
        self.assertEqual(self.joueur.defense, avec - 3 - 3)  # bonus + l'objet

    def test_l_herboristerie_augmente_les_soins(self):
        self.joueur.base_max_hp = 100          # pour ne pas buter sur le plafond
        self.joueur.hp = 1
        self.joueur.skills.levels["herboristerie"] = 3
        self.joueur.inventory = [items.make("herbe_soin")]
        self.game.cmd_use(0)
        self.assertEqual(self.joueur.hp, 1 + 15 + 6)   # 15 de base, +2 par niveau

    def test_la_cuisine_augmente_les_repas(self):
        self.joueur.fullness = 0
        self.joueur.skills.levels["nourriture"] = 2
        self.joueur.inventory = [items.make("onigiri")]
        self.game.cmd_use(0)
        self.assertEqual(self.joueur.fullness, 50 + 10 - 1)   # -1 : le tour passé

    def test_la_marche_ralentit_la_faim(self):
        rapide = sandbox(seed=5)
        lent = sandbox(seed=5)
        lent.player.skills.levels["marche"] = 10        # -30 % de faim
        for _ in range(50):
            rapide.cmd_wait()
            lent.cmd_wait()
        self.assertGreater(lent.player.fullness, rapide.player.fullness)


class TestExtensibilite(unittest.TestCase):
    """Ajouter du contenu ne doit demander que des données.

    On simule ici l'ajout d'une hache : une entrée de compétence, un objet qui
    la déclare. Aucune fonction du moteur n'est touchée.
    """

    def setUp(self):
        self.game = sandbox(seed=5)
        self.catalogue = dict(skills.CATALOGUE)
        self.catalogue["hache"] = Skill("hache", "Hache", base=2,
                                        scope=skills.EQUIPEMENT,
                                        effects={"attaque": 2})
        self.game.player.skills.catalogue = self.catalogue
        self.game.listeners = [Trainer(catalogue=self.catalogue)]
        self.hache = items.ItemType("hache_pierre", "hache de pierre", ")",
                                    items.WEAPON, power=4, skill="hache")

    def test_une_nouvelle_famille_d_arme_s_entraine_toute_seule(self):
        self.game.player.weapon = items.Item(self.hache)
        place_monster(self.game, (self.game.player.pos[0] + 1,
                                  self.game.player.pos[1]), hp=9999)
        for _ in range(20):
            self.game.cmd_move((1, 0))
        self.assertGreater(self.game.player.skills.level("hache"), 0)
        self.assertEqual(self.game.player.skills.level("epee"), 0)

    def test_ses_bonus_s_appliquent_sans_toucher_au_moteur(self):
        self.game.player.weapon = items.Item(self.hache)
        avant = self.game.player.attack
        self.game.player.skills.levels["hache"] = 3
        self.assertEqual(self.game.player.attack, avant + 6)

    def test_un_objet_herite_de_la_competence_de_sa_categorie(self):
        for cle, attendu in [("herbe_soin", "herboristerie"),
                             ("onigiri", "nourriture"),
                             ("parchemin_lumiere", "parchemins"),
                             ("fleche", "jet"),
                             ("epee_fer", "epee"),
                             ("bouclier_fer", "bouclier")]:
            self.assertEqual(items.ITEM_TYPES[cle].skill, attendu, cle)

    def test_une_regle_peut_etre_ajoutee_sans_toucher_au_moteur(self):
        """Ici : « descendre entraîne la marche », en une ligne de table."""
        regles = skills.REGLES + (Regle(events.DESCENTE, "marche", xp=50),)
        self.game.listeners = [Trainer(regles=regles)]
        self.game.player.pos = self.game.level.stairs
        self.game.cmd_descend()
        self.assertGreater(self.game.player.skills.level("marche"), 0)


class TestRunSeulement(unittest.TestCase):
    def test_les_competences_appartiennent_au_run(self):
        """Rien ne survit : une nouvelle partie repart de zéro."""
        game = sandbox(seed=5)
        game.player.skills.gain("marche", 500)
        self.assertGreater(game.player.skills.total_levels(), 0)
        neuf = sandbox(seed=5)
        self.assertEqual(neuf.player.skills.total_levels(), 0)


if __name__ == "__main__":
    unittest.main()
