"""Tests de l'interface graphique.

Ils sont ignorés automatiquement si tkinter ou un écran ne sont pas disponibles
(serveur sans affichage, Python sans tkinter) : la suite reste verte partout.
"""

import unittest

try:
    import tkinter
except ImportError:                                  # pragma: no cover
    tkinter = None


def _ecran_disponible():
    if tkinter is None:
        return False
    try:
        racine = tkinter.Tk()
    except Exception:                                # pragma: no cover
        return False
    racine.destroy()
    return True


class Evenement:
    """Imite un évènement clavier tkinter."""

    def __init__(self, char="", keysym=""):
        self.char = char
        self.keysym = keysym or char


class Clic:
    """Imite un évènement souris tkinter."""

    def __init__(self, x, y):
        self.x = x
        self.y = y


@unittest.skipUnless(_ecran_disponible(), "tkinter ou écran indisponible")
class TestFenetre(unittest.TestCase):
    def setUp(self):
        from donjon.gui import Fenetre
        self.fenetre = Fenetre(seed=11, max_depth=5)

    def tearDown(self):
        self.fenetre.root.destroy()

    def test_une_touche_de_deplacement_fait_avancer_le_tour(self):
        avant = self.fenetre.game.turn
        self.fenetre.on_key(Evenement(keysym="Right"))
        self.assertGreater(self.fenetre.game.turn, avant)

    def test_le_sac_s_ouvre_et_se_ferme(self):
        self.fenetre.on_key(Evenement(char="i"))
        self.assertEqual(self.fenetre.mode, "sac")
        self.fenetre.on_key(Evenement(keysym="Escape"))
        self.assertEqual(self.fenetre.mode, "jeu")

    def test_utiliser_un_objet_depuis_le_sac(self):
        joueur = self.fenetre.game.player
        joueur.fullness = 10
        slot = next(i for i, o in enumerate(joueur.inventory)
                    if o.type.key == "onigiri")
        self.fenetre.on_key(Evenement(char="i"))
        self.fenetre.on_key(Evenement(char=chr(ord("a") + slot)))
        self.assertEqual(self.fenetre.mode, "action")
        self.fenetre.on_key(Evenement(char="u"))
        self.assertEqual(self.fenetre.mode, "jeu")
        self.assertGreater(joueur.fullness, 10)

    def test_le_dessin_ne_plante_dans_aucun_mode(self):
        for mode in ("jeu", "sac", "action", "direction", "aide"):
            self.fenetre.mode = mode
            self.fenetre.slot = 0
            self.fenetre.dessiner()

    def test_ecran_de_fin(self):
        from donjon.game import DEAD
        self.fenetre.game.state = DEAD
        self.fenetre.dessiner()


@unittest.skipUnless(_ecran_disponible(), "tkinter ou écran indisponible")
class TestSouris(unittest.TestCase):
    def setUp(self):
        from donjon.gui import Fenetre
        self.fenetre = Fenetre(seed=11, max_depth=5)
        self.fenetre.game.actors = [self.fenetre.game.player]   # scène calme

    def tearDown(self):
        self.fenetre.root.destroy()

    def _clic_case(self, case):
        px, py = self.fenetre._cellule(*case)
        moitie = self.fenetre.tile // 2
        self.fenetre.on_click(Clic(px + moitie, py + moitie))

    def _zone(self, etiquette):
        """La zone cliquable portant cette étiquette (bouton ou ligne du sac)."""
        for zone in self.fenetre.zones:
            if zone[5] == etiquette:
                return zone
        self.fail(f"zone « {etiquette} » introuvable")

    def _cliquer_zone(self, etiquette):
        zone = self._zone(etiquette)
        self.fenetre.on_click(Clic((zone[0] + zone[2]) / 2,
                                   (zone[1] + zone[3]) / 2))

    def test_clic_sur_une_case_voisine_deplace(self):
        joueur = self.fenetre.game.player
        voisine = None
        for delta in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            case = (joueur.pos[0] + delta[0], joueur.pos[1] + delta[1])
            if self.fenetre.game.level.walkable(case):
                voisine = case
                break
        self._clic_case(voisine)
        self.assertEqual(joueur.pos, voisine)

    def test_clic_sur_le_heros_ramasse_l_objet_au_sol(self):
        from donjon import items
        game = self.fenetre.game
        game.level.items[game.player.pos] = items.make("fleche")
        self._clic_case(game.player.pos)
        self.assertEqual(len(game.player.inventory), 5)

    def test_clic_lointain_declenche_un_trajet(self):
        fenetre = self.fenetre
        fenetre.game.level.reveal_all()
        cible = fenetre.game.level.stairs
        self._clic_case(cible)
        self.assertEqual(fenetre.destination, cible)
        for _ in range(600):
            if fenetre.destination is None:
                break
            fenetre.pas_trajet()
        self.assertEqual(fenetre.game.player.pos, cible)

    def test_un_clic_droit_annule_le_trajet(self):
        fenetre = self.fenetre
        fenetre.game.level.reveal_all()
        self._clic_case(fenetre.game.level.stairs)
        self.assertIsNotNone(fenetre.destination)
        fenetre.on_click_droit(Clic(0, 0))
        self.assertIsNone(fenetre.destination)

    def test_le_bouton_attendre_consomme_un_tour(self):
        avant = self.fenetre.game.turn
        self._cliquer_zone("Attendre")
        self.assertGreater(self.fenetre.game.turn, avant)

    def test_le_bouton_ramasser_n_apparait_que_sur_un_objet(self):
        from donjon import items
        game = self.fenetre.game
        etiquettes = [z[5] for z in self.fenetre.zones]
        self.assertNotIn("Ramasser", etiquettes)
        game.level.items[game.player.pos] = items.make("fleche")
        self.fenetre.dessiner()
        self._cliquer_zone("Ramasser")
        self.assertEqual(len(game.player.inventory), 5)

    def test_le_sac_se_pilote_a_la_souris(self):
        fenetre = self.fenetre
        joueur = fenetre.game.player
        joueur.fullness = 10
        slot = next(i for i, o in enumerate(joueur.inventory)
                    if o.type.key == "onigiri")
        fenetre.mode = "sac"
        fenetre.dessiner()
        self._cliquer_zone(f"objet {slot}")
        self.assertEqual(fenetre.mode, "action")
        self._cliquer_zone("Utiliser")
        self.assertEqual(fenetre.mode, "jeu")
        self.assertGreater(joueur.fullness, 10)

    def test_le_bouton_fermer_referme_le_sac(self):
        self.fenetre.mode = "sac"
        self.fenetre.dessiner()
        self._cliquer_zone("Fermer")
        self.assertEqual(self.fenetre.mode, "jeu")

    def test_survol_decrit_ce_qui_est_sous_le_curseur(self):
        from tests.helpers import place_monster
        fenetre = self.fenetre
        joueur = fenetre.game.player
        case = (joueur.pos[0] + 1, joueur.pos[1])
        monstre = place_monster(fenetre.game, case)
        px, py = fenetre._cellule(*case)
        fenetre.on_motion(Clic(px + 5, py + 5))
        self.assertEqual(fenetre.case_survolee, case)
        self.assertIn(monstre.name, fenetre.description(case))

    def test_survol_du_heros_annonce_l_action_du_clic(self):
        fenetre = self.fenetre
        texte = fenetre.description(fenetre.game.player.pos)
        self.assertIn("clic", texte.lower())


if __name__ == "__main__":
    unittest.main()
