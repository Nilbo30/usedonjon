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


TALENTS_DE_TEST = ("estomac", "epee", "nourriture", "herbes",
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

    def test_un_talent_verrouille_se_lit_mais_ne_s_achete_pas(self):
        """On peut regarder ce qui attend derrière un rond éteint, pas le prendre."""
        from donjon.gui import Fenetre
        fenetre = Fenetre(seed=7, sauvegarde=False)
        self.addCleanup(fenetre.root.destroy)
        fenetre.session.meta.xp = 10000
        fenetre.mode = "talents"
        fenetre.dessiner()
        zone = next(z for z in fenetre.zones if z[5] == "talent second_souffle")
        fenetre.on_click(Clic((zone[0] + zone[2]) / 2, (zone[1] + zone[3]) / 2))
        self.assertNotIn("second_souffle", fenetre.session.meta.noeuds)
        self.assertEqual(fenetre.session.meta.xp, 10000)

    def test_un_talent_repetable_reste_cliquable_entre_deux_reprises(self):
        """Sinon il aurait l'air fini dès le premier achat."""
        from donjon.gui import Fenetre

        fenetre = Fenetre(seed=7, sauvegarde=False)
        self.addCleanup(fenetre.root.destroy)
        fenetre.session.meta.xp = 10 ** 4
        for cle in ("nourriture", "projectiles"):
            fenetre.session.meta.acheter(cle)
        fenetre.mode = "talents"
        for reprise in range(3):
            fenetre.dessiner()
            etiquettes = [z[5] for z in fenetre.zones]
            self.assertIn("talent rien_ne_se_perd", etiquettes, reprise)
            self._cliquer_zone_de("rien_ne_se_perd", fenetre)
        self.assertEqual(fenetre.session.meta.fois("rien_ne_se_perd"), 3)
        fenetre.dessiner()
        self.assertIsNone(fenetre.session.acheter("rien_ne_se_perd"))

    def _cliquer_zone_de(self, cle, fenetre):
        zone = next(z for z in fenetre.zones if z[5] == f"talent {cle}")
        fenetre.on_click(Clic((zone[0] + zone[2]) / 2, (zone[1] + zone[3]) / 2))

    def test_l_eventail_place_tous_les_noeuds_dans_le_cadre(self):
        """Un nœud d'une branche oubliée dans `BRANCHES` disparaîtrait sans bruit.

        La marge laisse la place au nom, posé à côté du rond : c'est elle qui a
        manqué le jour où l'arbre a gagné un rang de profondeur.
        """
        from donjon import tree
        from donjon.gui import HUD_HEIGHT

        fenetre = self.fenetre
        fenetre.mode = "talents"
        fenetre.dessiner()
        places = fenetre._disposition_talents()
        self.assertEqual(len(places), len(tree.ARBRE))
        bas = HUD_HEIGHT + fenetre.hauteur_carte
        for cle, (x, y, _angle, _place) in places.items():
            self.assertTrue(40 <= x <= fenetre.largeur - 40, f"{cle} en x={x}")
            self.assertTrue(HUD_HEIGHT + 60 <= y <= bas - 40, f"{cle} en y={y}")

    def test_les_ronds_de_l_eventail_ne_se_touchent_pas(self):
        """Deux talents collés seraient impossibles à distinguer et à cliquer."""
        import math

        from donjon.gui import RAYON_TALENT

        fenetre = self.fenetre
        fenetre.mode = "talents"
        fenetre.dessiner()
        places = fenetre._disposition_talents()
        for premier, un in places.items():
            for second, autre in places.items():
                if premier < second:
                    self.assertGreater(math.dist(un[:2], autre[:2]),
                                       2 * RAYON_TALENT + 6,
                                       f"{premier} / {second}")

    def _croisements(self):
        """Les paires de traits qui se croisent, nommées par leur nœud."""
        places = self.fenetre._disposition_talents()
        traits = self.fenetre.traits_de_talents(places)
        ou = {place[:2]: cle for cle, place in places.items()}

        def cote(un, deux, point):
            valeur = ((deux[0] - un[0]) * (point[1] - un[1])
                      - (deux[1] - un[1]) * (point[0] - un[0]))
            return (valeur > 1e-9) - (valeur < -1e-9)

        paires = []
        for index, (un, deux, cle) in enumerate(traits):
            for autre, (trois, quatre, sienne) in enumerate(traits):
                if autre <= index or {un, deux} & {trois, quatre}:
                    continue
                if (cote(un, deux, trois) * cote(un, deux, quatre) < 0
                        and cote(trois, quatre, un)
                        * cote(trois, quatre, deux) < 0):
                    paires.append(f"{ou.get(un, 'cœur')}→{cle} × "
                                  f"{ou.get(trois, 'cœur')}→{sienne}")
        return paires

    def test_aucun_trait_de_talent_n_en_croise_un_autre(self):
        """Deux traits qui se croisent donnent un prérequis faux à l'œil.

        La disposition l'interdit à l'intérieur d'une sous-branche — un enfant
        reste dans la part de son parent. Restent deux leviers, qui ne changent
        rien au jeu : l'ordre de `tree.BRANCHES` entre branches, et le champ
        `ordre` d'un nœud entre voisins. Si ce test tombe après l'ajout d'un
        nœud, le message nomme les deux traits qui se coupent : c'est l'un de
        ces deux leviers qu'il faut bouger.
        """
        self.fenetre.mode = "talents"
        self.fenetre.dessiner()
        paires = self._croisements()
        self.assertEqual(paires, [], " ; ".join(paires))

    def test_l_ordre_des_branches_croise_le_moins_possible(self):
        """Aucun autre ordre de branches ne ferait mieux que celui retenu.

        Le test précédent exige zéro croisement ; celui-ci vérifie que l'ordre
        écrit dans `tree.BRANCHES` reste le bon choix, et nomme le meilleur
        ordre s'il a cessé de l'être.
        """
        import itertools

        from donjon import tree

        self.fenetre.mode = "talents"
        self.fenetre.dessiner()
        origine = tree.BRANCHES
        try:
            actuel = len(self._croisements())
            meilleur, ordre = actuel, origine
            for essai in itertools.permutations(origine):
                tree.BRANCHES = essai
                compte = len(self._croisements())
                if compte < meilleur:
                    meilleur, ordre = compte, essai
        finally:
            tree.BRANCHES = origine
        self.assertEqual(actuel, meilleur,
                         f"{actuel} croisements ; « {' · '.join(ordre)} » "
                         f"n'en laisserait que {meilleur}")

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
        for mode in ("competences", "sac", "action", "direction", "aide",
                     "talents"):
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


@unittest.skipUnless(_ecran_disponible(), "pas d'écran disponible")
class TestExploration(unittest.TestCase):
    """L'exploration automatique : elle avance seule, et s'arrête quand il faut."""

    def setUp(self):
        from donjon.gui import Fenetre

        self.fenetre = Fenetre(seed=5, sauvegarde=False)
        self.addCleanup(self.fenetre.root.destroy)
        _debloquer(self.fenetre, *TALENTS_DE_TEST, "exploration")
        self.fenetre.game = self.fenetre.session.descendre()
        self.fenetre.mode = "jeu"
        self.fenetre.dessiner()

    def _explorer(self, pas=40):
        """Déroule la boucle à la main : pas de minuterie dans un test."""
        self.fenetre.explorer()
        for _ in range(pas):
            if not self.fenetre.exploration:
                break
            self.fenetre.pas_exploration()

    def test_elle_decouvre_du_terrain(self):
        game = self.fenetre.game
        game.actors = [game.player]          # personne en vue : elle peut courir
        connu = len(game.level.explored)
        self._explorer()
        self.assertGreater(len(self.fenetre.game.level.explored), connu)

    def test_un_monstre_en_vue_l_arrete(self):
        from tests.helpers import place_monster

        joueur = self.fenetre.game.player
        place_monster(self.fenetre.game, (joueur.pos[0] + 1, joueur.pos[1]))
        self.fenetre.explorer()
        self.fenetre.pas_exploration()
        self.assertFalse(self.fenetre.exploration)

    def test_voir_l_escalier_lui_fait_rendre_la_main(self):
        """C'est une nouvelle : au joueur de décider s'il descend.

        Une nouvelle, donc : l'escalier déjà en vue au départ n'arrête rien —
        c'est le passage de « pas vu » à « vu » qui compte.
        """
        game = self.fenetre.game
        game.actors = [game.player]
        game.player.pos = game.level.stairs
        game.update_explored()
        self.fenetre.explorer()
        self.assertTrue(self.fenetre.exploration)     # déjà vu : ce n'est pas
        self.fenetre._escalier_vu = False             # une nouvelle. Là, si.
        self.fenetre.pas_exploration()
        self.assertFalse(self.fenetre.exploration)
        self.assertIn("escalier", " ".join(game.log.texts()[-3:]).lower())

    def test_sans_le_talent_elle_ne_demarre_pas(self):
        from donjon.config import RunConfig

        self.fenetre.game.config = RunConfig(unlocks={"vivres"})
        self.fenetre.explorer()
        self.assertFalse(self.fenetre.exploration)

    def test_le_bouton_n_apparait_qu_avec_le_talent(self):
        from donjon.config import RunConfig

        self.fenetre.dessiner()
        self.assertIn("Explorer", [zone[5] for zone in self.fenetre.zones])
        self.fenetre.game.config = RunConfig(unlocks={"vivres"})
        self.fenetre.dessiner()
        self.assertNotIn("Explorer", [zone[5] for zone in self.fenetre.zones])


@unittest.skipUnless(_ecran_disponible(), "pas d'écran disponible")
class TestPanneauxDuRefuge(unittest.TestCase):
    """Coffre et stèle : s'ouvrir en arrivant, et se laisser refermer."""

    def setUp(self):
        from donjon.gui import Fenetre

        self.fenetre = Fenetre(seed=7, sauvegarde=False)
        self.addCleanup(self.fenetre.root.destroy)
        _debloquer(self.fenetre, "nourriture", "coffre")
        self.fenetre.game = self.fenetre.session.demarrer()
        self.fenetre.mode = "jeu"

    def _aller_sur(self, case):
        self.fenetre.game.player.pos = case
        self.fenetre._verifier_fin()

    def test_la_stele_s_ouvre_en_arrivant(self):
        self._aller_sur(self.fenetre.game.level.stele)
        self.assertEqual(self.fenetre.mode, "talents")

    def test_et_se_referme_pour_de_bon(self):
        """Régression : le panneau se rouvrait tant qu'on piétinait la case."""
        self._aller_sur(self.fenetre.game.level.stele)
        self.fenetre.dessiner()
        self._cliquer_zone_de_fenetre("Fermer")
        self.assertEqual(self.fenetre.mode, "jeu")
        self.fenetre._verifier_fin()
        self.assertEqual(self.fenetre.mode, "jeu")

    def test_elle_se_rouvre_si_on_revient(self):
        self._aller_sur(self.fenetre.game.level.stele)
        self.fenetre.mode = "jeu"
        self._aller_sur((self.fenetre.game.level.stele[0] + 2,
                         self.fenetre.game.level.stele[1] + 2))
        self._aller_sur(self.fenetre.game.level.stele)
        self.assertEqual(self.fenetre.mode, "talents")

    def test_le_coffre_suit_la_meme_regle(self):
        self._aller_sur(self.fenetre.game.level.chest)
        self.assertEqual(self.fenetre.mode, "coffre")
        self.fenetre.mode = "jeu"
        self.fenetre._verifier_fin()
        self.assertEqual(self.fenetre.mode, "jeu")

    def _cliquer_zone_de_fenetre(self, etiquette):
        zone = next(z for z in self.fenetre.zones if z[5] == etiquette)
        self.fenetre.on_click(Clic((zone[0] + zone[2]) / 2,
                                   (zone[1] + zone[3]) / 2))


@unittest.skipUnless(_ecran_disponible(), "pas d'écran disponible")
class TestOptions(unittest.TestCase):
    """Le bouton qui efface tout : atteignable, mais jamais d'un seul clic."""

    def setUp(self):
        from donjon.gui import Fenetre

        self.fenetre = Fenetre(seed=7, sauvegarde=False)
        self.addCleanup(self.fenetre.root.destroy)
        _debloquer(self.fenetre, "nourriture", "coffre")
        self.fenetre.game = self.fenetre.session.demarrer()
        self.fenetre.mode = "jeu"
        self.fenetre.dessiner()

    def _cliquer(self, etiquette):
        zone = next(z for z in self.fenetre.zones if z[5] == etiquette)
        self.fenetre.on_click(Clic((zone[0] + zone[2]) / 2,
                                   (zone[1] + zone[3]) / 2))

    def test_un_seul_clic_n_efface_rien(self):
        """Sans confirmation, un clic malheureux coûterait toute la partie."""
        self._cliquer("Options")
        self._cliquer("Repartir de zéro")
        self.assertTrue(self.fenetre.session.meta.noeuds)

    def test_deux_clics_effacent_tout(self):
        self._cliquer("Options")
        self._cliquer("Repartir de zéro")
        self._cliquer("Oui, tout effacer")
        self.assertEqual(self.fenetre.session.meta.noeuds, [])
        self.assertEqual(self.fenetre.session.meta.xp, 0)
        self.assertTrue(self.fenetre.game.config.is_hub)

    def test_annuler_desamorce(self):
        self._cliquer("Options")
        self._cliquer("Repartir de zéro")
        self._cliquer("Annuler")
        self.assertNotIn("Oui, tout effacer",
                         [z[5] for z in self.fenetre.zones])
        self.assertTrue(self.fenetre.session.meta.noeuds)

    def test_rouvrir_les_options_desamorce_aussi(self):
        self._cliquer("Options")
        self._cliquer("Repartir de zéro")
        self.fenetre.mode = "jeu"
        self.fenetre.dessiner()
        self._cliquer("Options")
        self.assertNotIn("Oui, tout effacer",
                         [z[5] for z in self.fenetre.zones])
