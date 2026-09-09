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


if __name__ == "__main__":
    unittest.main()
