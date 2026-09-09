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


TALENTS_DE_TEST = ("estomac", "barda", "creatures", "fouille", "herbes",
                   "grimoires", "coffre")


def _debloquer(fenetre, *cles):
    """Offre des talents et refait le héros : le jeu s'ouvre verrouillé."""
    fenetre.session.meta.xp = 10 ** 4
    for cle in (cles or TALENTS_DE_TEST):
        fenetre.session.meta.acheter(cle)
    fenetre.session.player = None


def _entrer_dans_le_donjon(fenetre):
    """La fenêtre s'ouvre au refuge ; ces tests portent sur le donjon."""
    _debloquer(fenetre)
    fenetre.game = fenetre.session.descendre()
    fenetre.mode = "jeu"
    fenetre.dessiner()


@unittest.skipUnless(_ecran_disponible(), "tkinter ou écran indisponible")
class TestFenetre(unittest.TestCase):
    def setUp(self):
        from donjon.gui import Fenetre
        self.fenetre = Fenetre(seed=11, max_depth=5, sauvegarde=False)
        _entrer_dans_le_donjon(self.fenetre)

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
        for mode in ("jeu", "sac", "action", "direction", "aide", "competences"):
            self.fenetre.mode = mode
            self.fenetre.slot = 0
            self.fenetre.dessiner()

    def test_ecran_de_fin(self):
        from donjon.game import DEAD
        self.fenetre.game.state = DEAD
        self.fenetre.dessiner()


@unittest.skipUnless(_ecran_disponible(), "tkinter ou écran indisponible")
class TestRefuge(unittest.TestCase):
    """La fenêtre s'ouvre au refuge et sait enchaîner vers le donjon."""

    def setUp(self):
        from donjon.gui import Fenetre
        self.fenetre = Fenetre(seed=7, sauvegarde=False)
        _debloquer(self.fenetre)
        self.fenetre.game = self.fenetre.session.demarrer()
        self.fenetre.dessiner()

    def tearDown(self):
        self.fenetre.root.destroy()

    def test_on_ouvre_au_refuge_avec_le_mot_d_accueil(self):
        from donjon.gui import Fenetre
        neuve = Fenetre(seed=7, sauvegarde=False)
        self.assertTrue(neuve.session.au_refuge)
        self.assertEqual(neuve.mode, "accueil")
        neuve.root.destroy()

    def test_marcher_sur_le_coffre_l_ouvre(self):
        fenetre = self.fenetre
        fenetre.mode = "jeu"
        coffre = fenetre.game.level.chest
        fenetre.game.player.pos = (coffre[0], coffre[1] - 1)
        fenetre.on_key(Evenement(keysym="Down"))
        self.assertEqual(fenetre.game.player.pos, coffre)
        self.assertEqual(fenetre.mode, "coffre")

    def test_deposer_puis_reprendre_a_la_souris(self):
        fenetre = self.fenetre
        fenetre.mode = "coffre"
        fenetre.dessiner()
        objet = fenetre.game.player.inventory[0]
        zone = next(z for z in fenetre.zones if z[5] == "sac 0")
        fenetre.on_click(Clic((zone[0] + zone[2]) / 2, (zone[1] + zone[3]) / 2))
        self.assertNotIn(objet, fenetre.game.player.inventory)
        self.assertEqual(len(fenetre.session.entrepot()), 1)
        zone = next(z for z in fenetre.zones if z[5] == "coffre 0")
        fenetre.on_click(Clic((zone[0] + zone[2]) / 2, (zone[1] + zone[3]) / 2))
        self.assertEqual(fenetre.session.entrepot(), [])

    def test_l_escalier_du_refuge_lance_la_descente(self):
        fenetre = self.fenetre
        fenetre.mode = "jeu"
        heros = fenetre.game.player
        fenetre.game.player.pos = fenetre.game.level.stairs
        fenetre.on_key(Evenement(char=">"))
        self.assertFalse(fenetre.session.au_refuge)
        self.assertIs(fenetre.game.player, heros)
        self.assertEqual(fenetre.mode, "jeu")

    def test_l_arbre_des_talents_s_ouvre_au_refuge(self):
        fenetre = self.fenetre
        fenetre.mode = "jeu"
        fenetre.on_key(Evenement(char="t"))
        self.assertEqual(fenetre.mode, "talents")

    def test_acheter_un_talent_d_un_clic(self):
        from donjon.gui import Fenetre
        fenetre = Fenetre(seed=7, sauvegarde=False)
        self.addCleanup(fenetre.root.destroy)
        fenetre.session.meta.xp = 50
        fenetre.mode = "talents"
        fenetre.dessiner()
        zone = next(z for z in fenetre.zones if z[5] == "talent estomac")
        fenetre.on_click(Clic((zone[0] + zone[2]) / 2, (zone[1] + zone[3]) / 2))
        self.assertIn("estomac", fenetre.session.meta.noeuds)
        self.assertAlmostEqual(fenetre.session.meta.xp, 47)

    def test_un_talent_trop_cher_ne_s_achete_pas(self):
        from donjon.gui import Fenetre
        fenetre = Fenetre(seed=7, sauvegarde=False)
        self.addCleanup(fenetre.root.destroy)
        fenetre.session.meta.xp = 0
        fenetre.mode = "talents"
        fenetre.dessiner()
        zone = next(z for z in fenetre.zones if z[5] == "talent estomac")
        fenetre.on_click(Clic((zone[0] + zone[2]) / 2, (zone[1] + zone[3]) / 2))
        self.assertEqual(fenetre.session.meta.noeuds, [])

    def test_un_talent_verrouille_n_est_pas_cliquable(self):
        from donjon.gui import Fenetre
        fenetre = Fenetre(seed=7, sauvegarde=False)
        self.addCleanup(fenetre.root.destroy)
        fenetre.session.meta.xp = 10000
        fenetre.mode = "talents"
        fenetre.dessiner()
        etiquettes = [z[5] for z in fenetre.zones]
        self.assertIn("talent estomac", etiquettes)
        self.assertNotIn("talent second_souffle", etiquettes)

    def test_la_carte_du_refuge_est_centree(self):
        fenetre = self.fenetre
        fenetre.dessiner()
        self.assertGreater(fenetre.offset_x, 0)
        case = fenetre.case_sous(*fenetre._cellule(*fenetre.game.player.pos))
        self.assertEqual(case, fenetre.game.player.pos)


@unittest.skipUnless(_ecran_disponible(), "tkinter ou écran indisponible")
class TestSouris(unittest.TestCase):
    def setUp(self):
        from donjon.gui import Fenetre
        self.fenetre = Fenetre(seed=11, max_depth=5, sauvegarde=False)
        _entrer_dans_le_donjon(self.fenetre)
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
        avant = len(game.player.inventory)
        game.level.items[game.player.pos] = items.make("fleche")
        self._clic_case(game.player.pos)
        self.assertEqual(len(game.player.inventory), avant + 1)

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
        avant = len(game.player.inventory)
        game.level.items[game.player.pos] = items.make("fleche")
        self.fenetre.dessiner()
        self._cliquer_zone("Ramasser")
        self.assertEqual(len(game.player.inventory), avant + 1)

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

    def test_viser_efface_le_sac_pour_voir_la_carte(self):
        from donjon import items
        fenetre = self.fenetre
        fenetre.game.player.inventory = [items.make("fleche")]
        fenetre.mode = "sac"
        fenetre.dessiner()
        self._cliquer_zone("objet 0")
        self._cliquer_zone("Lancer")
        self.assertEqual(fenetre.mode, "direction")
        etiquettes = [zone[5] for zone in fenetre.zones]
        self.assertNotIn("objet 0", etiquettes)   # le sac a disparu
        self.assertIn("Annuler", etiquettes)

    def test_annuler_la_visee_rouvre_le_sac(self):
        self.fenetre.mode = "direction"
        self.fenetre.slot = 0
        self.fenetre.dessiner()
        self._cliquer_zone("Annuler")
        self.assertEqual(self.fenetre.mode, "sac")

    def test_les_panneaux_tiennent_dans_la_fenetre(self):
        """Régression : les chiffres de compétences débordaient du cadre."""
        fenetre = self.fenetre
        fenetre.game.player.skills.levels.update(
            {"marche": 2, "combat": 2, "recuperation": 1})
        fenetre.game.player.skills.xp.update({"marche": 15.2})
        for mode in ("competences", "sac", "action", "direction", "aide"):
            fenetre.mode = mode
            fenetre.slot = 0
            fenetre.dessiner()
            for zone in fenetre.zones:
                self.assertGreaterEqual(zone[0], 0, mode)
                self.assertLessEqual(zone[2], fenetre.largeur, mode)

    def test_la_mesure_de_texte_suit_la_longueur(self):
        court = self.fenetre.largeur_texte("ab")
        long = self.fenetre.largeur_texte("abcdefghijklmnop")
        self.assertGreater(long, court > 0)

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
        self.assertIn(monstre.name, fenetre.description(case)[0])

    def test_survol_du_heros_annonce_l_action_du_clic(self):
        fenetre = self.fenetre
        (ligne,) = fenetre.description(fenetre.game.player.pos)
        self.assertIn("clic", ligne.lower())

    def test_survol_d_un_objet_au_sol_explique_son_effet(self):
        from donjon import items
        fenetre = self.fenetre
        case = (fenetre.game.player.pos[0] + 1, fenetre.game.player.pos[1])
        fenetre.game.level.items[case] = items.make("graine_sommeil")
        lignes = fenetre.description(case)
        self.assertEqual(lignes[0], "graine de sommeil")
        self.assertIn("endort", lignes[1])
        self.assertIn("Herboristerie", lignes[2])

    def test_le_sac_affiche_la_fiche_de_l_objet_choisi(self):
        from donjon import items
        fenetre = self.fenetre
        fenetre.game.player.inventory = [items.make("parchemin_lumiere")]
        fenetre.mode = "action"
        fenetre.slot = 0
        fenetre.dessiner()
        self.assertIs(fenetre._objet_decrit(), fenetre.game.player.inventory[0])


if __name__ == "__main__":
    unittest.main()
