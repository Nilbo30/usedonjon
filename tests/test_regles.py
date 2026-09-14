"""Les règles portées : qui réagit, et surtout qui ne réagit pas.

Le test qui compte est celui de l'objet **au sol** : sans lui, chaque pas
balaierait l'inventaire de l'étage et le coût par évènement grandirait avec le
nombre d'objets par terre. C'est la ligne manquante de la table des porteurs,
et elle ne se voit que si on la vérifie.
"""

import unittest

from donjon import events, items, regles, tree
from donjon.config import RunConfig
from donjon.meta import Meta
from donjon.regles import Regle
from tests.helpers import donner, place_monster, poser_au_sol, sandbox


def compteur():
    """Une règle qui ne fait que se compter : (action, liste des porteurs)."""
    vus = []
    return (lambda declenchement: vus.append(declenchement.porteur)), vus


class TestPorteurs(unittest.TestCase):
    def setUp(self):
        self.jeu = sandbox(seed=1)
        self.jeu.player.inventory.clear()
        self.jeu.player.weapon = self.jeu.player.shield = None

    def _type_avec_regle(self, cle, action, evenement=events.PAS, **champs):
        return items.ItemType(cle, cle, "?", items.WEAPON,
                              regles=(Regle(evenement, action),), **champs)

    # --- l'équipement ---------------------------------------------------
    def test_une_regle_d_arme_ne_se_declenche_qu_arme_au_poing(self):
        action, vus = compteur()
        epee = items.Item(self._type_avec_regle("epee_vivante", action))

        self.jeu.player.inventory.append(epee)
        self.jeu.cmd_move((1, 0))
        self.assertEqual(vus, [], "dans le sac, elle ne doit rien faire")

        self.jeu.player.weapon = epee
        self.jeu.cmd_move((1, 0))
        self.assertEqual(vus, [epee])

    # --- le sol ---------------------------------------------------------
    def test_une_regle_d_objet_au_sol_dort_jusqu_a_ce_qu_on_y_touche(self):
        """La ligne qui décide du coût de tout le mécanisme.

        Un objet posé ne porte rien tant qu'aucun évènement ne le nomme : on
        peut marcher dessus sans le réveiller, et le ramasser le réveille.
        """
        action, vus = compteur()
        type_vivant = self._type_avec_regle("caillou_vivant", action,
                                            evenement=events.RAMASSAGE)
        case = (self.jeu.player.pos[0] + 1, self.jeu.player.pos[1])
        self.jeu.level.items[case] = items.Item(type_vivant)

        self.jeu.cmd_move((1, 0))            # on marche dessus
        self.assertEqual(vus, [])
        self.jeu.cmd_pickup()                # là, l'évènement le nomme
        self.assertEqual(len(vus), 1)

    def test_marcher_ne_balaye_pas_l_etage(self):
        """Vingt objets au sol ne doivent concerner personne pendant un pas."""
        for index in range(20):
            poser_au_sol(self.jeu, (20 + index, 4), "pierre")
        evenement = events.Event(events.PAS, {"depart": (1, 1),
                                              "arrivee": (1, 2),
                                              "diagonale": False})
        self.assertEqual(regles.porteurs_concernes(self.jeu, evenement), [])

    # --- le run et l'étage ----------------------------------------------
    def test_une_regle_du_run_se_declenche_toujours(self):
        action, vus = compteur()
        self.jeu.config = self.jeu.config.replace(
            regles=(Regle(events.PAS, action),))
        self.jeu.cmd_move((1, 0))
        self.jeu.cmd_move((1, 0))
        self.assertEqual(vus, [self.jeu.config, self.jeu.config])

    def test_une_regle_d_etage_ne_suit_pas_le_heros_en_bas(self):
        """L'étage est un porteur : il disparaît avec lui."""
        action, vus = compteur()
        self.jeu.level.regles = (Regle(events.PAS, action),)
        self.jeu.cmd_move((1, 0))
        self.assertEqual(len(vus), 1)
        ancien = self.jeu.level
        self.jeu.player.pos = self.jeu.level.stairs
        self.jeu.cmd_descend()
        self.jeu.cmd_move((1, 0))
        self.assertIsNot(self.jeu.level, ancien)
        self.assertEqual(len(vus), 1)

    # --- les créatures ---------------------------------------------------
    def test_une_creature_reagit_a_ce_qui_la_nomme(self):
        action, vus = compteur()
        monstre = place_monster(self.jeu, (self.jeu.player.pos[0] + 1,
                                           self.jeu.player.pos[1]), hp=200)
        monstre.regles = (Regle(events.DEGATS_SUBIS, action),)
        self.jeu.blesser(monstre, 3, source=self.jeu.player)
        self.assertEqual(vus, [monstre])

    def test_une_creature_ignore_ce_qui_ne_la_nomme_pas(self):
        action, vus = compteur()
        monstre = place_monster(self.jeu, (self.jeu.player.pos[0] + 3,
                                           self.jeu.player.pos[1]), hp=200)
        monstre.regles = (Regle(events.PAS, action),)
        self.jeu.cmd_move((0, 1))
        self.assertEqual(vus, [])


class TestOrdreEtPlafond(unittest.TestCase):
    def setUp(self):
        self.jeu = sandbox(seed=1)
        self.jeu.player.inventory.clear()
        self.jeu.player.weapon = self.jeu.player.shield = None

    def test_l_ordre_des_porteurs_est_celui_du_parcours(self):
        """Héros, puis ce que l'évènement nomme, puis l'étage, puis le run.

        Stable d'une partie à l'autre : deux règles ne peuvent pas se disputer
        la priorité par hasard.
        """
        action, vus = compteur()
        epee = items.Item(items.ItemType("epee_vivante", "épée", "?",
                                         items.WEAPON,
                                         regles=(Regle(events.PAS, action),)))
        self.jeu.player.weapon = epee
        self.jeu.level.regles = (Regle(events.PAS, action),)
        self.jeu.config = self.jeu.config.replace(
            regles=(Regle(events.PAS, action),))
        self.jeu.cmd_move((1, 0))
        self.assertEqual(vus, [epee, self.jeu.level, self.jeu.config])

    def test_une_regle_portee_se_plafonne_aussi(self):
        """Le garde-fou de l'étape 17.4 vaut pour les deux familles de règles.

        On émet à la main : un `cmd_move` avance le tour, donc « une fois par
        tour » ne se verrait jamais en marchant.
        """
        vus = []
        regle = Regle(events.ATTENTE, lambda d: vus.append(d), max_par_tour=2)
        self.jeu.config = self.jeu.config.replace(regles=(regle,))
        for tour in range(3):
            self.jeu.turn = tour
            for _ in range(5):
                self.jeu.notify(events.ATTENTE)
        self.assertEqual(len(vus), 6)

    def test_un_evenement_inconnu_est_refuse_a_la_declaration(self):
        with self.assertRaises(ValueError):
            Regle("paas", lambda d: None)


class TestLaFrontiere(unittest.TestCase):
    """Une règle de talent passe par la `RunConfig`, jamais par le méta."""

    def test_un_noeud_peut_porter_une_regle_jusqu_au_run(self):
        action, _ = compteur()
        regle = Regle(events.PAS, action)
        noeud = tree.Noeud("essai", "Essai", 150, "Pour le test.",
                           branche="Survie", regles=(regle,))
        tree.ARBRE["essai"] = noeud
        self.addCleanup(tree.ARBRE.pop, "essai")

        meta = Meta(xp=10 ** 6)
        self.assertEqual(meta.run_config().regles, ())
        meta.acheter("essai")
        self.assertEqual(meta.run_config().regles, (regle,))

    def test_une_config_a_la_main_ne_porte_aucune_regle(self):
        self.assertEqual(RunConfig().regles, ())


class TestRienNeBouge(unittest.TestCase):
    def test_aucun_porteur_du_jeu_ne_declare_encore_de_regle(self):
        """C'est ce qui rend l'étape invisible — et les empreintes le prouvent."""
        porteurs = [(cle, t.regles) for cle, t in items.ITEM_TYPES.items()
                    if t.regles]
        porteurs += [(n.key, n.regles) for n in tree.ARBRE.values() if n.regles]
        self.assertEqual(porteurs, [])


if __name__ == "__main__":
    unittest.main()
