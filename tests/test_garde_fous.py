"""Les garde-fous des chaînes : profondeur, et plafond par règle et par tour.

Aucune règle n'agit encore — le jeu ne peut donc pas boucler aujourd'hui, et
c'est mesuré : sur tout le corpus, la profondeur de chaîne maximale vaut
**un**. Ces garde-fous sont préventifs, et c'est précisément pourquoi il faut
les prouver maintenant : un garde-fou qu'on n'a jamais vu mordre est une
intention, pas une protection.

Les deux valeurs sont en données, jamais en dur : la profondeur est un champ de
`RunConfig` (donc un talent pourra l'ouvrir), le plafond est un champ de la
règle.
"""

import unittest

from donjon import events, skills
from donjon.config import RunConfig
from donjon.skills import Regle, Skill, SkillSet, Trainer
from tests.helpers import sandbox


class Boucleur:
    """Un auditeur qui se mord la queue : soigné il blesse, blessé il soigne.

    C'est le scénario que le brief redoutait, écrit en trois lignes. Sans
    garde-fou, il tourne jusqu'à la pile.
    """

    def __call__(self, game, event):
        if event.nom == events.DEGATS_SUBIS:
            game.soigner(event["cible"], 1)
        elif event.nom == events.SOIN_RECU:
            game.blesser(event["cible"], 1)


class TestProfondeurDeChaine(unittest.TestCase):
    def _jeu_qui_boucle(self, profondeur):
        jeu = sandbox(seed=1, config=RunConfig(
            max_depth=5, monsters_per_floor=(0, 0), items_per_floor=(0, 0),
            traps_per_floor=(0, 0), start_hp=200,
            profondeur_max_chaine=profondeur))
        jeu.actors = [jeu.player]
        jeu.player.hp = 100
        self.journal = events.Recorder()
        jeu.listeners = [self.journal, Boucleur()]
        return jeu

    def test_une_boucle_est_coupee_a_la_profondeur_declaree(self):
        jeu = self._jeu_qui_boucle(4)
        jeu.blesser(jeu.player, 1)
        # dégâts, soin, dégâts, soin — puis le cinquième maillon est refusé.
        self.assertEqual(self.journal.faits(),
                         [events.DEGATS_SUBIS, events.SOIN_RECU,
                          events.DEGATS_SUBIS, events.SOIN_RECU])
        self.assertEqual(jeu.chaines_coupees, [events.DEGATS_SUBIS])

    def test_la_profondeur_vient_de_la_config_et_de_nulle_part_ailleurs(self):
        for profondeur in (2, 4, 7):
            with self.subTest(profondeur=profondeur):
                jeu = self._jeu_qui_boucle(profondeur)
                jeu.blesser(jeu.player, 1)
                self.assertEqual(len(self.journal), profondeur)

    def test_une_coupure_se_voit(self):
        """Un garde-fou silencieux est pire que la boucle qu'il coupe.

        Sans trace, on déboguerait un effet qui « marche une fois sur deux ».
        """
        jeu = self._jeu_qui_boucle(3)
        jeu.blesser(jeu.player, 1)
        self.assertTrue(any("chaîne coupée" in ligne
                            for ligne in jeu.log.texts()),
                        jeu.log.texts())

    def test_le_compteur_de_maillons_revient_a_zero(self):
        """Sinon la première boucle condamnerait tout le reste de la partie."""
        jeu = self._jeu_qui_boucle(3)
        jeu.blesser(jeu.player, 1)
        self.assertEqual(jeu.maillons, 0)
        jeu.chaines_coupees.clear()
        jeu.blesser(jeu.player, 1)
        self.assertEqual(len(jeu.chaines_coupees), 1)

    def test_le_compteur_redescend_meme_si_un_auditeur_explose(self):
        """`finally` : un auditeur qui lève ne doit pas bloquer le bus."""
        jeu = sandbox(seed=1)
        jeu.listeners = [lambda g, e: 1 / 0]
        with self.assertRaises(ZeroDivisionError):
            jeu.notify(events.ATTENTE)
        self.assertEqual(jeu.maillons, 0)


class TestPlafondParTour(unittest.TestCase):
    """« Trois fois par tour, pas davantage » — en données, sur la règle."""

    def _formateur(self, max_par_tour):
        catalogue = {"essai": Skill("essai", "Essai", base=10 ** 9)}
        regle = Regle(events.ATTENTE, "essai", max_par_tour=max_par_tour)
        return Trainer((regle,), catalogue), catalogue

    def _jeu(self, formateur):
        jeu = sandbox(seed=1)
        jeu.player.skills = SkillSet(formateur.catalogue)
        jeu.listeners = [formateur]
        return jeu

    def test_sans_plafond_la_regle_se_declenche_autant_que_l_evenement(self):
        formateur, _ = self._formateur(None)
        jeu = self._jeu(formateur)
        for _ in range(5):
            jeu.notify(events.ATTENTE)
        self.assertEqual(jeu.player.skills.total_xp(), 5)

    def test_le_plafond_arrete_les_declenchements_suivants(self):
        formateur, _ = self._formateur(2)
        jeu = self._jeu(formateur)
        for _ in range(5):
            jeu.notify(events.ATTENTE)
        self.assertEqual(jeu.player.skills.total_xp(), 2)

    def test_le_plafond_se_remet_a_zero_au_tour_suivant(self):
        formateur, _ = self._formateur(2)
        jeu = self._jeu(formateur)
        for tour in range(3):
            jeu.turn = tour
            for _ in range(5):
                jeu.notify(events.ATTENTE)
        self.assertEqual(jeu.player.skills.total_xp(), 6)

    def test_aucune_regle_du_jeu_n_est_plafonnee(self):
        """C'est ce qui rend l'ajout du champ invisible pour le joueur.

        Les seize empreintes le prouvent sur le jeu entier ; ce test le dit à
        l'endroit où ça se décide.
        """
        self.assertEqual([r.evenement for r in skills.REGLES
                          if r.max_par_tour is not None], [])


class TestCeQuiSePasseAujourdHui(unittest.TestCase):
    """Rien ne chaîne encore — et c'est ce test qui le fera remarquer."""

    def _jouer(self, graine, talents):
        from donjon.script import autoplay
        from donjon.session import Session

        session = Session(sauvegarde=False, seed=graine)
        session.meta.xp = 10 ** 9
        restant = list(talents)
        while restant:
            for cle in list(restant):
                if session.meta.acheter(cle):
                    restant.remove(cle)
        jeu = session.descendre()
        profondeurs = []
        jeu.listeners.append(lambda g, _e: profondeurs.append(g.maillons))
        autoplay(jeu, 30000)
        return jeu, max(profondeurs, default=0)

    def test_aucune_chaine_n_est_coupee_dans_une_vraie_partie(self):
        from donjon import tree

        for graine, talents in ((7, tuple(tree.ARBRE)), (2, ("nourriture",))):
            with self.subTest(graine=graine):
                jeu, profondeur = self._jouer(graine, talents)
                self.assertEqual(jeu.chaines_coupees, [])
                self.assertEqual(profondeur, 1,
                                 "une chaîne est apparue : le garde-fou "
                                 "commence à servir, il faut le dire au journal")


if __name__ == "__main__":
    unittest.main()
