import unittest

from donjon import items
from tests.helpers import place_monster, sandbox


class TestFiches(unittest.TestCase):
    """Chaque objet doit pouvoir expliquer ce qu'il fait."""

    def test_tous_les_objets_ont_une_fiche(self):
        for cle in items.ITEM_TYPES:
            self.assertTrue(items.make(cle).description(), cle)

    def test_l_equipement_annonce_son_bonus_reel(self):
        self.assertIn("+8", items.make("epee_fer", plus=2).description())
        self.assertIn("+1", items.make("bouclier_bois", plus=-2).description())

    def test_les_chiffres_des_fiches_suivent_les_donnees(self):
        """Garde-fou : une fiche qui ment après un changement de puissance."""
        for cle in ("herbe_soin", "herbe_vie", "onigiri", "fleche"):
            objet = items.make(cle)
            self.assertIn(str(objet.power), objet.description(), cle)

    def test_chaque_objet_entraine_une_competence_connue(self):
        from donjon import skills
        for cle, type_objet in items.ITEM_TYPES.items():
            self.assertIn(type_objet.skill, skills.CATALOGUE, cle)


class TestApparitionParProfondeur(unittest.TestCase):
    def test_l_orbe_ne_se_trouve_pas_dans_les_premiers_etages(self):
        from donjon.rng import Rng

        rng = Rng(1)
        haut = [items.random_item(rng, 1).type.key for _ in range(400)]
        self.assertNotIn("orbe_retour", haut)

    def test_il_apparait_en_profondeur(self):
        from donjon.rng import Rng

        rng = Rng(1)
        bas = [items.random_item(rng, 10).type.key for _ in range(400)]
        self.assertIn("orbe_retour", bas)


class TestNourritureAuSol(unittest.TestCase):
    """La faim est le premier tueur : elle ne doit pas dépendre du tirage."""

    def test_la_nourriture_garde_sa_part_quoi_qu_on_debloque(self):
        """Sinon chaque famille débloquée noie les vivres.

        La part de nourriture tombait de 100 % à 11,7 % une fois tout ouvert :
        acheter du contenu réduisait les vivres au sol d'un facteur trois.
        """
        from donjon.config import TOUT_DEBLOQUE
        from donjon.rng import Rng

        for unlocks in ({"vivres", "herbes"}, TOUT_DEBLOQUE):
            rng = Rng(5)
            tires = [objet for objet in
                     (items.random_item(rng, 5, unlocks=unlocks)
                      for _ in range(600)) if objet is not None]
            part = sum(1 for objet in tires
                       if objet.category == items.FOOD) / len(tires)
            self.assertGreater(part, items.PART_NOURRITURE - 0.08, unlocks)

    def test_le_plancher_tient_quel_que_soit_le_catalogue(self):
        """La question qui compte : et si le jeu grossit de dix ans ?

        La part n'est pas un poids réglé à la main mais une proportion
        recalculée sur le tirage du moment : cinquante familles de plus ne la
        font pas bouger d'un pouce.
        """
        vivres = [(type_objet, type_objet.weight)
                  for type_objet in items.ITEM_TYPES.values()
                  if type_objet.category == items.FOOD]
        for familles in (1, 5, 50, 200):
            faux = [(items.ItemType(f"x{i}", "x", "x", f"categorie_{i // 4}",
                                    weight=12), 12)
                    for i in range(familles * 4)]
            table = items._part_reservee(vivres + faux)
            total = sum(poids for _, poids in table)
            part = sum(poids for type_objet, poids in table
                       if type_objet.category == items.FOOD) / total
            self.assertAlmostEqual(part, items.PART_NOURRITURE, places=6,
                                   msg=f"{familles} familles")

    def test_un_etage_peut_rester_avare(self):
        """La part est statistique, pas un vivre posé d'office : ça se sentirait."""
        from donjon.game import Game

        sans_vivre = 0
        for graine in range(20):
            game = Game(seed=graine)
            if not any(objet.category == items.FOOD
                       for objet in game.level.items.values()):
                sans_vivre += 1
        self.assertGreater(sans_vivre, 0)


class TestIdentification(unittest.TestCase):
    """Les parchemins ne disent leur nom qu'une fois essayés."""

    def setUp(self):
        self.game = sandbox(seed=5)
        self.parchemin = items.make("parchemin_lumiere",
                                    registre=self.game.identification)

    def test_un_parchemin_neuf_cache_son_nom_et_son_effet(self):
        self.assertFalse(self.parchemin.identifie)
        self.assertNotEqual(self.parchemin.name, "parchemin de lumière")
        self.assertIn("parchemin", self.parchemin.name)
        self.assertIn("inconnu", self.parchemin.description())

    def test_l_utiliser_l_identifie(self):
        self.game.player.inventory = [self.parchemin]
        self.game.cmd_use(0)
        self.assertTrue(self.parchemin.identifie)
        self.assertEqual(self.parchemin.name, "parchemin de lumière")
        self.assertTrue(any("Identifié" in t for t in self.game.log.texts()))

    def test_l_identification_vaut_pour_tous_les_exemplaires(self):
        autre = items.make("parchemin_lumiere", registre=self.game.identification)
        self.game.player.inventory = [self.parchemin]
        self.game.cmd_use(0)
        self.assertTrue(autre.identifie)

    def test_l_apparence_est_stable_dans_un_run(self):
        jumeau = items.make("parchemin_lumiere", registre=self.game.identification)
        self.assertEqual(self.parchemin.name, jumeau.name)

    def test_deux_parchemins_n_ont_pas_la_meme_apparence(self):
        autre = items.make("parchemin_panique", registre=self.game.identification)
        self.assertNotEqual(self.parchemin.name, autre.name)

    def test_les_autres_objets_ne_sont_pas_masques(self):
        for cle in ("herbe_soin", "onigiri", "epee_fer", "fleche"):
            objet = items.make(cle, registre=self.game.identification)
            self.assertTrue(objet.identifie, cle)

    def test_un_objet_sans_registre_reste_identifie(self):
        self.assertTrue(items.make("parchemin_lumiere").identifie)

    def test_chaque_run_rebat_les_apparences(self):
        vus = {sandbox(seed=graine).identification.apparences["parchemin_lumiere"]
               for graine in range(12)}
        self.assertGreater(len(vus), 1)


class TestRamassageAutomatique(unittest.TestCase):
    def setUp(self):
        self.game = sandbox(seed=5)
        self.voisine = (self.game.player.pos[0] + 1, self.game.player.pos[1])

    def test_un_consommable_se_ramasse_en_marchant_dessus(self):
        self.game.level.items[self.voisine] = items.make("herbe_soin")
        avant, tour = len(self.game.player.inventory), self.game.turn
        self.game.cmd_move((1, 0))
        self.assertEqual(len(self.game.player.inventory), avant + 1)
        self.assertNotIn(self.voisine, self.game.level.items)
        self.assertEqual(self.game.turn - tour, 1)   # gratuit : le pas suffit

    def test_une_arme_reste_au_sol(self):
        self.game.level.items[self.voisine] = items.make("epee_fer")
        self.game.cmd_move((1, 0))
        self.assertIn(self.voisine, self.game.level.items)
        self.assertTrue(self.game.cmd_pickup())     # à la main, ça marche

    def test_le_sac_plein_laisse_l_objet_au_sol(self):
        self.game.player.inventory = [items.make("fleche")
                                      for _ in range(self.game.player.max_items)]
        self.game.level.items[self.voisine] = items.make("herbe_soin")
        self.game.cmd_move((1, 0))
        self.assertIn(self.voisine, self.game.level.items)
        self.assertIn("sac est plein", self.game.log.texts()[-1])


class TestObjets(unittest.TestCase):
    def test_herbe_de_soin(self):
        game = sandbox()
        game.player.hp = 5
        game.player.inventory = [items.make("herbe_soin")]
        game.cmd_use(0)
        self.assertGreater(game.player.hp, 5)
        self.assertEqual(game.player.inventory, [])

    def test_manger_remplit_le_ventre(self):
        game = sandbox()
        game.player.fullness = 10
        game.player.inventory = [items.make("onigiri")]
        game.cmd_use(0)
        self.assertGreater(game.player.fullness, 10)

    def test_equiper_augmente_l_attaque(self):
        game = sandbox()
        game.player.weapon = None
        game.player.inventory = [items.make("epee_fer", plus=3)]
        before = game.player.attack
        game.cmd_equip(0)
        self.assertEqual(game.player.attack, before + 9)

    def test_ramasser_et_poser(self):
        game = sandbox()
        game.player.inventory = []
        game.level.items[game.player.pos] = items.make("fleche")
        self.assertTrue(game.cmd_pickup())
        self.assertEqual(len(game.player.inventory), 1)
        self.assertNotIn(game.player.pos, game.level.items)
        self.assertTrue(game.cmd_drop(0))
        self.assertIn(game.player.pos, game.level.items)

    def test_sac_plein(self):
        game = sandbox()
        game.player.inventory = [items.make("fleche")
                                 for _ in range(game.player.max_items)]
        game.level.items[game.player.pos] = items.make("onigiri")
        self.assertFalse(game.cmd_pickup())
        self.assertIn(game.player.pos, game.level.items)

    def test_lancer_une_graine_endort_la_cible(self):
        game = sandbox()
        target = place_monster(game, (game.player.pos[0] + 3, game.player.pos[1]))
        game.player.inventory = [items.make("graine_sommeil")]
        game.cmd_throw(0, (1, 0))
        self.assertTrue(target.has_status("endormi"))
        self.assertEqual(game.player.inventory, [])

    def test_objet_lance_dans_le_vide_tombe_au_sol(self):
        game = sandbox()
        game.player.inventory = [items.make("fleche")]
        game.cmd_throw(0, (1, 0))
        self.assertTrue(any(i.type.key == "fleche" for i in game.level.items.values()))

    def test_parchemin_de_lumiere_revele_l_etage(self):
        game = sandbox()
        game.player.inventory = [items.make("parchemin_lumiere")]
        before = len(game.level.explored)
        game.cmd_use(0)
        self.assertGreater(len(game.level.explored), before)


if __name__ == "__main__":
    unittest.main()


class TestFicheEtCompetences(unittest.TestCase):
    """La fiche doit dire ce que l'objet fera dans *ces* mains."""

    def setUp(self):
        from tests.helpers import sandbox

        self.game = sandbox(seed=2)
        self.joueur = self.game.player

    def test_l_onigiri_annonce_le_ventre_reellement_rendu(self):
        onigiri = items.make("onigiri")
        self.assertIn("50", onigiri.description(self.joueur))
        self.joueur.skills.levels["nourriture"] = 2
        rendu = onigiri.puissance_pour(self.joueur)
        self.assertGreater(rendu, onigiri.power)
        self.assertIn(str(rendu), onigiri.description(self.joueur))

    def test_la_fiche_suit_ce_que_l_effet_fait_vraiment(self):
        """Le contrat : le chiffre annoncé est celui que le moteur applique."""
        self.joueur.skills.levels["nourriture"] = 3
        onigiri = items.make("onigiri")
        self.joueur.fullness = 0
        onigiri.use(self.game, self.joueur)
        self.assertEqual(self.joueur.fullness,
                         onigiri.puissance_pour(self.joueur))

    def test_l_herbe_de_soin_suit_l_herboristerie(self):
        herbe = items.make("herbe_soin")
        self.joueur.skills.levels["herboristerie"] = 3
        self.assertIn(str(herbe.puissance_pour(self.joueur)),
                      herbe.description(self.joueur))

    def test_sans_porteur_la_fiche_reste_celle_de_l_objet_nu(self):
        self.joueur.skills.levels["nourriture"] = 5
        self.assertIn("50", items.make("onigiri").description())


class TestButin(unittest.TestCase):
    """Ce qu'une créature laisse en tombant, et la chance qui s'y entretient."""

    def setUp(self):
        from tests.helpers import place_monster, sandbox

        self.game = sandbox(seed=9)
        self.joueur = self.game.player
        self.placer = place_monster

    def _tuer(self, cle="rat", fois=1):
        laisses = []
        for _ in range(fois):
            case = (self.joueur.pos[0] + 1, self.joueur.pos[1])
            self.game.level.items.pop(case, None)
            monstre = self.placer(self.game, case, cle)
            monstre.take_damage(monstre.hp)
            self.game.check_death(monstre, killer=self.joueur)
            objet = self.game.level.items.get(case)
            if objet is not None:
                laisses.append(objet)
        return laisses

    def test_sans_le_talent_rien_ne_tombe(self):
        from donjon.config import RunConfig

        self.game.config = RunConfig(unlocks={"vivres"})
        self.assertEqual(self._tuer(fois=60), [])

    def test_avec_le_talent_il_tombe_quelque_chose(self):
        laisses = self._tuer(fois=60)
        self.assertTrue(laisses)
        self.assertLess(len(laisses), 60)          # jamais garanti

    def test_une_creature_ne_lache_pas_ce_qui_est_verrouille(self):
        """L'archer laisse ses flèches parce que son talent les a ouvertes."""
        from donjon.config import RunConfig

        self.game.config = RunConfig(unlocks={"butin", "vivres"})
        for objet in self._tuer("limace", fois=80):
            self.assertEqual(objet.type.key, "onigiri")

    def test_ramasser_du_butin_entraine_la_chance(self):
        self._tuer(fois=60)
        self.assertGreater(self.joueur.skills.level("chance"), 0)

    def test_la_chance_est_plafonnee(self):
        """Elle s'entretient de ce qu'elle produit : sans plafond, elle s'emballe."""
        from donjon.game import CHANCE_BUTIN, CHANCE_BUTIN_MAX

        self.joueur.skills.levels["chance"] = 500
        self.assertGreater(self.joueur.bonus("chance"), 1)
        self.assertLess(CHANCE_BUTIN_MAX, 1.0)
        self.assertGreater(CHANCE_BUTIN_MAX, CHANCE_BUTIN)
        laisses = self._tuer(fois=100)
        self.assertLess(len(laisses), 90)


class TestPiles(unittest.TestCase):
    """Les munitions s'empilent : dix pierres ne remplissent pas un sac."""

    def setUp(self):
        from tests.helpers import sandbox

        self.game = sandbox(seed=2)
        self.joueur = self.game.player
        self.joueur.inventory = []

    def test_les_pierres_se_rangent_ensemble(self):
        for _ in range(6):
            self.joueur.add_item(items.make("pierre"))
        self.assertEqual(len(self.joueur.inventory), 1)
        self.assertEqual(self.joueur.inventory[0].quantite, 6)
        self.assertIn("×6", self.joueur.inventory[0].etiquette)

    def test_ce_qui_n_est_pas_munition_ne_s_empile_pas(self):
        for _ in range(3):
            self.joueur.add_item(items.make("onigiri"))
        self.assertEqual(len(self.joueur.inventory), 3)

    def test_lancer_n_en_consomme_qu_une(self):
        self.joueur.add_item(items.make("pierre", quantite=4))
        self.game.cmd_throw(0, (1, 0))
        self.assertEqual(self.joueur.inventory[0].quantite, 3)

    def test_la_derniere_pierre_vide_la_ligne(self):
        self.joueur.add_item(items.make("pierre"))
        self.game.cmd_throw(0, (1, 0))
        self.assertEqual(self.joueur.inventory, [])

    def test_une_pile_ne_depasse_pas_le_plafond(self):
        """Sinon le sac deviendrait infini pour tout ce qui s'empile."""
        self.joueur.add_item(items.make("pierre", quantite=items.MAX_PILE))
        self.joueur.add_item(items.make("pierre", quantite=3))
        self.assertEqual(len(self.joueur.inventory), 2)

    def test_une_pile_ramassee_rejoint_la_pile_du_sac(self):
        self.joueur.add_item(items.make("pierre", quantite=2))
        self.game.level.items[self.joueur.pos] = items.make("pierre", quantite=3)
        self.game.cmd_pickup()
        self.assertEqual(len(self.joueur.inventory), 1)
        self.assertEqual(self.joueur.inventory[0].quantite, 5)


class TestPlafondDeNourriture(unittest.TestCase):
    """Trop de vivres tue la faim, et la faim est ce qui pousse à descendre."""

    def test_seule_debloquee_la_nourriture_ne_prend_pas_tout(self):
        """Bloquant : la partie devenait infinie, on ne pouvait plus mourir."""
        from donjon.rng import Rng

        rng = Rng(5)
        tires = [items.random_item(rng, 3, unlocks={"vivres"})
                 for _ in range(600)]
        part = sum(1 for objet in tires if objet is not None) / len(tires)
        self.assertLess(part, items.PART_MAX_NOURRITURE + 0.06)
        self.assertGreater(part, items.PART_MAX_NOURRITURE - 0.06)

    def test_les_places_en_trop_restent_vides_au_sol(self):
        from donjon.config import RunConfig
        from donjon.game import Game

        game = Game(seed=3, config=RunConfig(unlocks={"vivres"}))
        attendus = game.config.items_per_floor
        self.assertLessEqual(len(game.level.items), attendus[1])

    def test_le_plancher_joue_toujours_quand_tout_est_ouvert(self):
        from donjon.config import TOUT_DEBLOQUE
        from donjon.rng import Rng

        rng = Rng(5)
        tires = [items.random_item(rng, 5, unlocks=TOUT_DEBLOQUE)
                 for _ in range(600)]
        vivres = sum(1 for objet in tires
                     if objet is not None and objet.category == items.FOOD)
        self.assertGreater(vivres / len(tires), items.PART_NOURRITURE - 0.08)


class TestRepasAutomatique(unittest.TestCase):
    """Ne plus avoir à y penser — mais seulement une fois le talent pris."""

    def _partie(self, unlocks):
        from donjon.config import RunConfig
        from donjon.game import Game

        game = Game(seed=4, config=RunConfig(unlocks=unlocks))
        game.player.inventory = [items.make("onigiri")]
        game.player.fullness = 5
        return game

    def test_le_ventre_vide_il_mange_seul(self):
        game = self._partie({"vivres", "auto_repas"})
        game.cmd_wait()
        self.assertGreater(game.player.fullness, 5)
        self.assertEqual(game.player.inventory, [])

    def test_sans_le_talent_il_se_laisse_mourir(self):
        game = self._partie({"vivres"})
        game.cmd_wait()
        self.assertLess(game.player.fullness, 6)
        self.assertEqual(len(game.player.inventory), 1)

    def test_le_ventre_plein_il_ne_touche_a_rien(self):
        game = self._partie({"vivres", "auto_repas"})
        game.player.fullness = game.player.max_fullness
        game.cmd_wait()
        self.assertEqual(len(game.player.inventory), 1)

    def test_le_repas_automatique_entraine_la_cuisine(self):
        """L'automatisation ne doit pas coûter de progression."""
        game = self._partie({"vivres", "auto_repas"})
        game.cmd_wait()
        self.assertGreater(game.player.skills.xp.get("nourriture", 0), 0)

    def test_sans_reserve_rien_ne_se_passe(self):
        game = self._partie({"vivres", "auto_repas"})
        game.player.inventory = []
        game.cmd_wait()
        self.assertLess(game.player.fullness, 6)
