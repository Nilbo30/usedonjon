"""Le moteur est le seul à toucher aux jauges.

`Actor.heal`, `take_damage` et `add_status` ne connaissent pas le jeu : elles
ne peuvent rien annoncer. Les faire converger vers `Game` est ce qui permettra
à l'étape 17.3 de publier un fait d'effet au seul endroit possible.

Le test de source ci-dessous est la garantie : au point d'appel, un oubli
serait **silencieux** — l'effet marcherait, mais rien ne l'écouterait. C'est
exactement le genre de bug qui survit trois étapes.
"""

import pathlib
import re
import unittest

from donjon import game as game_mod
from tests.helpers import place_monster, sandbox

#: Les mutations qui doivent passer par le moteur.
MUTATIONS = (r"\.heal\(", r"\.take_damage\(", r"\.add_status\(",
             r"\.fullness\s*(?:=[^=]|\+=|-=)",
             r"\.base_max_hp\s*(?:\+=|-=)")

#: `entities.py` les définit ; `game.py` est le seul autorisé à les appeler.
LIBRES = {"entities.py", "game.py"}


class TestConvergence(unittest.TestCase):
    def test_aucun_module_ne_touche_aux_jauges_hors_du_moteur(self):
        dossier = pathlib.Path(game_mod.__file__).parent
        for fichier in sorted(dossier.glob("*.py")):
            if fichier.name in LIBRES:
                continue
            source = fichier.read_text(encoding="utf-8")
            for motif in MUTATIONS:
                trouve = re.findall(motif, source)
                self.assertEqual(
                    trouve, [],
                    f"{fichier.name} touche une jauge directement ({motif}) — "
                    f"passe par game.soigner / blesser / nourrir / poser_statut")

    def test_le_moteur_ne_les_appelle_qu_a_un_seul_endroit_chacune(self):
        """Une seule porte par jauge : sinon l'étape 17.3 en oubliera une."""
        source = pathlib.Path(game_mod.__file__).read_text(encoding="utf-8")
        for motif in MUTATIONS:
            self.assertEqual(
                len(re.findall(motif, source)), 1,
                f"{motif} apparaît plusieurs fois dans game.py")


class TestLesQuatrePortes(unittest.TestCase):
    def setUp(self):
        self.jeu = sandbox(seed=1)
        self.joueur = self.jeu.player

    def test_soigner_rend_ce_qui_manquait_et_pas_plus(self):
        self.joueur.hp = self.joueur.max_hp - 3
        self.assertEqual(self.jeu.soigner(self.joueur, 10), 3)
        self.assertEqual(self.joueur.hp, self.joueur.max_hp)

    def test_blesser_ne_verifie_pas_la_mort(self):
        """Et c'est voulu : replier `check_death` déplacerait `monstre_vaincu`.

        Deux sites glissent un `say` et un `notify` entre le dégât et la mort —
        le coup au contact et le tir ennemi. Replier avancerait la mort du
        monstre avant l'évènement du coup qui l'a tué.
        """
        monstre = place_monster(self.jeu, (self.joueur.pos[0] + 1,
                                           self.joueur.pos[1]), hp=1)
        self.jeu.blesser(monstre, 5, source=self.joueur)
        self.assertFalse(monstre.alive)
        self.assertIn(monstre, self.jeu.actors)     # personne ne l'a ramassé

    def test_nourrir_borne_des_deux_cotes(self):
        self.joueur.fullness = 5
        self.assertEqual(self.jeu.nourrir(self.joueur, -20), -5)
        self.assertEqual(self.joueur.fullness, 0)
        self.assertEqual(self.jeu.nourrir(self.joueur, 10 ** 6),
                         self.joueur.max_fullness)
        self.assertEqual(self.joueur.fullness, self.joueur.max_fullness)

    def test_gagner_pv_max_augmente_le_plafond(self):
        avant = self.joueur.max_hp
        self.jeu.gagner_pv_max(self.joueur, 5)
        self.assertEqual(self.joueur.max_hp, avant + 5)

    def test_poser_statut_garde_la_plus_longue_duree(self):
        self.jeu.poser_statut(self.joueur, "confus", 10)
        self.jeu.poser_statut(self.joueur, "confus", 3)
        self.assertEqual(self.joueur.statuses["confus"], 10)


class TestLesFaitsPublies(unittest.TestCase):
    """Étape 17.3 : les cinq portes annoncent ce qu'elles viennent de faire."""

    def setUp(self):
        from donjon.events import Recorder

        self.jeu = sandbox(seed=1)
        self.joueur = self.jeu.player
        self.journal = Recorder()
        self.jeu.listeners.append(self.journal)

    def test_chaque_porte_publie_son_fait(self):
        from donjon import events

        self.joueur.hp = 1
        self.jeu.soigner(self.joueur, 5, source="test")
        self.jeu.blesser(self.joueur, 2, source="test")
        self.jeu.nourrir(self.joueur, -7)
        self.jeu.poser_statut(self.joueur, "confus", 4, source="test")
        self.jeu.gagner_pv_max(self.joueur, 3, source="test")
        self.assertEqual(self.journal.faits(),
                         [events.SOIN_RECU, events.DEGATS_SUBIS,
                          events.VENTRE_CHANGE, events.STATUT_POSE,
                          events.PV_MAX_GAGNE])

    def test_le_fait_porte_ce_qui_est_reellement_arrive(self):
        """Et non ce qui était demandé : soigner de 99 quand il en manque 3."""
        from donjon import events

        self.joueur.hp = self.joueur.max_hp - 3
        self.jeu.soigner(self.joueur, 99, source="test")
        (fait,) = self.journal.of(events.SOIN_RECU)
        self.assertEqual(fait["points"], 3)
        self.assertIs(fait["cible"], self.joueur)
        self.assertEqual(fait["source"], "test")

    def test_rien_ne_part_quand_rien_ne_change(self):
        """Comme une commande refusée n'annonce rien."""
        self.jeu.soigner(self.joueur, 10)           # déjà au maximum
        self.jeu.nourrir(self.joueur, 10 ** 6)      # déjà repu
        self.jeu.poser_statut(self.joueur, "confus", 10)
        self.journal.clear()
        self.jeu.poser_statut(self.joueur, "confus", 3)   # plus court : sans effet
        self.assertEqual(self.journal.faits(), [])

    def test_un_fait_precede_toujours_la_mort_qu_il_cause(self):
        """Un auditeur voit les dégâts avant `monstre_vaincu`, jamais l'inverse.

        C'est la raison pour laquelle `blesser` ne replie pas `check_death` :
        au coup au contact, un `notify` s'intercale entre les deux.
        """
        from donjon import events

        cible = place_monster(self.jeu, (self.joueur.pos[0] + 1,
                                         self.joueur.pos[1]), hp=1)
        for _ in range(20):
            if not cible.alive:
                break
            self.jeu.cmd_move((1, 0))
        self.assertFalse(cible.alive)
        noms = self.journal.noms()
        self.assertLess(noms.index(events.DEGATS_SUBIS),
                        noms.index(events.MONSTRE_VAINCU))

    def test_un_piege_publie_lui_aussi(self):
        """Un fait part quel que soit l'acteur — un piège n'a pas d'auteur."""
        from donjon import events
        from tests.helpers import poser_piege

        case = (self.joueur.pos[0] + 1, self.joueur.pos[1])
        poser_piege(self.jeu, case, "explosion")
        self.jeu.cmd_move((1, 0))
        (fait,) = self.journal.of(events.DEGATS_SUBIS)
        self.assertIs(fait["cible"], self.joueur)
        self.assertIsNone(fait["source"])

    def test_aucune_regle_de_competence_n_ecoute_encore(self):
        """L'étape ne change rien au jeu : les nouveaux noms sont inertes.

        C'est ce que les seize empreintes prouvent sur le jeu entier ; ce test
        le dit à l'endroit où ça se décide.
        """
        from donjon import events, skills

        ecoutes = {regle.evenement for regle in skills.REGLES}
        self.assertEqual(ecoutes & set(events.FAITS), set())


if __name__ == "__main__":
    unittest.main()
