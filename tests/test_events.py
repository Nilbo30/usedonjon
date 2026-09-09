"""Le bus d'évènements : socle de l'XP par action.

Ces tests fixent le contrat que la table des compétences consommera : quel
évènement part, avec quelles données, et surtout quand il ne part PAS.
"""

import unittest

from donjon import events, items
from donjon.events import Recorder
from tests.helpers import place_monster, sandbox


class BaseEvents(unittest.TestCase):
    def setUp(self):
        self.game = sandbox(seed=5)
        self.journal = Recorder()
        self.game.listeners.append(self.journal)

    def voisine(self, delta=(1, 0)):
        return (self.game.player.pos[0] + delta[0],
                self.game.player.pos[1] + delta[1])


class TestActionsSimples(BaseEvents):
    def test_un_pas_est_annonce(self):
        depart = self.game.player.pos
        self.game.cmd_move((1, 0))
        (event,) = self.journal.of(events.PAS)
        self.assertEqual(event["depart"], depart)
        self.assertEqual(event["arrivee"], self.game.player.pos)
        self.assertFalse(event["diagonale"])

    def test_un_pas_en_diagonale_est_marque(self):
        self.game.cmd_move((1, 1))
        (event,) = self.journal.of(events.PAS)
        self.assertTrue(event["diagonale"])

    def test_attendre_est_annonce(self):
        self.game.cmd_wait()
        self.assertEqual(self.journal.noms(), [events.ATTENTE])

    def test_une_action_refusee_n_annonce_rien(self):
        pos = self.game.player.pos
        self.game.level.set_tile((pos[0] + 1, pos[1]), "wall")
        self.assertFalse(self.game.cmd_move((1, 0)))
        self.assertEqual(len(self.journal), 0)

    def test_ramasser_dans_le_vide_n_annonce_rien(self):
        self.assertFalse(self.game.cmd_pickup())
        self.assertEqual(len(self.journal), 0)

    def test_descendre_sans_escalier_n_annonce_rien(self):
        self.assertFalse(self.game.cmd_descend())
        self.assertEqual(len(self.journal), 0)


class TestCombat(BaseEvents):
    def test_un_coup_porte_son_arme_et_ses_degats(self):
        cible = place_monster(self.game, self.voisine(), hp=500)
        self.game.player.weapon = items.make("epee_fer")
        self.game.cmd_move((1, 0))
        (coup,) = self.journal.of(events.COUP)
        self.assertIs(coup["cible"], cible)
        self.assertEqual(coup["arme"].type.key, "epee_fer")
        if coup["touche"]:
            self.assertGreater(coup["degats"], 0)
        else:
            self.assertEqual(coup["degats"], 0)

    def test_un_coup_a_mains_nues_annonce_une_arme_vide(self):
        place_monster(self.game, self.voisine(), hp=500)
        self.game.player.weapon = None
        self.game.cmd_move((1, 0))
        (coup,) = self.journal.of(events.COUP)
        self.assertIsNone(coup["arme"])

    def test_la_mise_a_mort_suit_le_coup(self):
        cible = place_monster(self.game, self.voisine(), hp=1)
        for _ in range(20):                      # on ignore les ratés
            if not cible.alive:
                break
            self.game.cmd_move((1, 0))
        self.assertFalse(cible.alive)
        self.assertEqual(self.journal.noms()[-2:],
                         [events.COUP, events.MONSTRE_VAINCU])
        (mise_a_mort,) = self.journal.of(events.MONSTRE_VAINCU)
        self.assertIs(mise_a_mort["monstre"], cible)
        self.assertEqual(mise_a_mort["distance"], 1)

    def test_encaisser_un_coup_annonce_le_bouclier_porte(self):
        """Le seul évènement que le héros ne déclenche pas : on pare en encaissant."""
        monstre = place_monster(self.game, self.voisine(), attack=1)
        self.game.attack(monstre, self.game.player)
        (recu,) = self.journal.of(events.COUP_RECU)
        self.assertIs(recu["source"], monstre)
        self.assertIs(recu["bouclier"], self.game.player.shield)

    def test_un_coup_de_monstre_sur_un_monstre_n_annonce_rien(self):
        a = place_monster(self.game, self.voisine())
        b = place_monster(self.game, self.voisine((0, 1)))
        self.game.attack(a, b)
        self.assertEqual(len(self.journal), 0)


class TestObjets(BaseEvents):
    def test_utiliser_un_objet(self):
        self.game.player.inventory = [items.make("herbe_soin")]
        self.game.player.hp = 1
        self.game.cmd_use(0)
        (event,) = self.journal.of(events.USAGE_OBJET)
        self.assertEqual(event["objet"].type.key, "herbe_soin")
        self.assertEqual(event["categorie"], items.HERB)

    def test_equiper_puis_ranger(self):
        self.game.player.weapon = None
        self.game.player.inventory = [items.make("epee_fer")]
        self.game.cmd_equip(0)
        self.game.cmd_equip(0)
        porte, range_ = self.journal.of(events.EQUIPEMENT)
        self.assertTrue(porte["equipe"])
        self.assertFalse(range_["equipe"])

    def test_ramasser_et_poser(self):
        self.game.player.inventory = []
        self.game.level.items[self.game.player.pos] = items.make("fleche")
        self.game.cmd_pickup()
        self.game.cmd_drop(0)
        self.assertEqual(self.journal.noms(), [events.RAMASSAGE, events.POSE])
        self.assertEqual(self.journal.of(events.POSE)[0]["objet"].type.key, "fleche")

    def test_un_jet_qui_touche(self):
        cible = place_monster(self.game, self.voisine((3, 0)))
        self.game.player.inventory = [items.make("fleche")]
        self.game.cmd_throw(0, (1, 0))
        (jet,) = self.journal.of(events.JET)
        self.assertIs(jet["cible"], cible)
        self.assertEqual(jet["direction"], (1, 0))

    def test_un_jet_dans_le_vide_annonce_une_cible_vide(self):
        self.game.player.inventory = [items.make("fleche")]
        self.game.cmd_throw(0, (1, 0))
        (jet,) = self.journal.of(events.JET)
        self.assertIsNone(jet["cible"])


class TestDescente(BaseEvents):
    def test_descendre_annonce_le_nouvel_etage(self):
        self.game.player.pos = self.game.level.stairs
        self.game.cmd_descend()
        (event,) = self.journal.of(events.DESCENTE)
        self.assertEqual(event["etage"], 2)
        self.assertEqual(event["etage"], self.game.depth)

    def test_atteindre_le_fond_n_est_pas_une_descente(self):
        self.game.config = self.game.config.replace(max_depth=1)
        self.game.player.pos = self.game.level.stairs
        self.game.cmd_descend()
        self.assertEqual(self.game.state, "victoire")
        self.assertEqual(self.journal.of(events.DESCENTE), [])


class TestBus(unittest.TestCase):
    def test_plusieurs_auditeurs_recoivent_le_meme_evenement(self):
        game = sandbox(seed=5)
        a, b = Recorder(), Recorder()
        game.listeners += [a, b]
        game.cmd_wait()
        self.assertEqual(len(a), 1)
        self.assertEqual(len(b), 1)
        self.assertIs(a.events[0], b.events[0])

    def test_l_auditeur_recoit_la_partie_et_l_evenement(self):
        game = sandbox(seed=5)
        recus = []
        game.listeners.append(lambda g, e: recus.append((g, e.nom)))
        game.cmd_wait()
        self.assertEqual(recus, [(game, events.ATTENTE)])

    def test_le_formateur_de_competences_est_branche_par_defaut(self):
        from donjon.skills import Trainer
        game = sandbox(seed=5)
        self.assertTrue(any(isinstance(l, Trainer) for l in game.listeners))

    def test_sans_aucun_auditeur_le_jeu_tourne_normalement(self):
        game = sandbox(seed=5)
        game.listeners.clear()
        game.cmd_wait()
        self.assertGreater(game.turn, 0)

    def test_tous_les_noms_declares_sont_uniques(self):
        self.assertEqual(len(set(events.NOMS)), len(events.NOMS))


if __name__ == "__main__":
    unittest.main()
