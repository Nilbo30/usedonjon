import unittest

from donjon import dungeon, path, tiles
from donjon.rng import Rng
from tests.helpers import sandbox


class TestGeneration(unittest.TestCase):
    def test_deterministe(self):
        a = dungeon.generate(Rng(123))
        b = dungeon.generate(Rng(123))
        self.assertEqual(a.grid, b.grid)
        self.assertEqual(a.stairs, b.stairs)

    def test_escalier_accessible_depuis_chaque_salle(self):
        for seed in range(25):
            level = dungeon.generate(Rng(seed))
            self.assertTrue(tiles.walkable(level.tile(level.stairs)))
            for room in level.rooms:
                start = room.center
                if not level.walkable(start):
                    continue
                route = path.find_path(level, start, level.stairs)
                self.assertIsNotNone(
                    route, f"salle isolée (graine {seed}, départ {start})")

    def test_bordures_sont_des_murs(self):
        level = dungeon.generate(Rng(5))
        for x in range(level.width):
            self.assertFalse(level.walkable((x, 0)))
            self.assertFalse(level.walkable((x, level.height - 1)))

    def test_visibilite_salle_entiere(self):
        level = dungeon.generate(Rng(9))
        room = level.rooms[0]
        visible = level.visible_from(room.center)
        for cell in room.cells():
            self.assertIn(cell, visible)


if __name__ == "__main__":
    unittest.main()


class TestCheminEtAngles(unittest.TestCase):
    """Le chemin calculé doit être un chemin que le moteur accepte de suivre."""

    def test_aucun_pas_diagonal_ne_coupe_un_angle(self):
        """Régression : le trajet à la souris s'arrêtait devant les portes.

        La case d'arrivée était exemptée de toute vérification, y compris de la
        géométrie : le dernier pas coupait donc l'angle, le moteur le refusait,
        et le héros restait planté sans explication.
        """
        from donjon import path
        from donjon.geom import ALL_DIRS, add, is_diagonal
        from donjon.rng import Rng

        for graine in range(30):
            niveau = dungeon.generate(Rng(graine))
            for depart in list(niveau.walkable_cells())[::7]:
                for delta in ALL_DIRS:
                    cible = add(depart, delta)
                    if not is_diagonal(delta) or not niveau.walkable(cible):
                        continue
                    coin = not (niveau.walkable(add(depart, (delta[0], 0)))
                                and niveau.walkable(add(depart, (0, delta[1]))))
                    if coin:
                        self.assertNotEqual(
                            path.find_path(niveau, depart, cible), [cible],
                            f"graine {graine} : {depart} → {cible}")

    def test_le_chemin_reste_praticable_de_bout_en_bout(self):
        """Chaque pas d'un chemin doit être un pas que `can_step` autorise."""
        from donjon.game import Game
        from donjon.geom import sub
        from donjon import path

        game = Game(seed=11)
        niveau = game.level
        cases = list(niveau.walkable_cells())
        for cible in cases[::23]:
            chemin = path.find_path(niveau, game.player.pos, cible)
            if not chemin:
                continue
            precedent = game.player.pos
            for case in chemin:
                self.assertFalse(game.corner_blocked(precedent, sub(case, precedent)),
                                 f"{precedent} → {case}")
                precedent = case


class TestCouloirsPropres(unittest.TestCase):
    def test_aucun_pate_de_couloir_2x2(self):
        """Deux tracés qui se croisent laissaient une flaque large de deux cases."""
        from donjon import tiles
        from donjon.geom import add
        from donjon.rng import Rng

        for graine in range(40):
            niveau = dungeon.generate(Rng(graine))
            for case in niveau.walkable_cells():
                if niveau.tile(case) != tiles.CORRIDOR:
                    continue
                bloc = [case, add(case, (1, 0)), add(case, (0, 1)),
                        add(case, (1, 1))]
                self.assertFalse(
                    all(niveau.in_bounds(c)
                        and niveau.tile(c) == tiles.CORRIDOR for c in bloc),
                    f"graine {graine} : pâté en {case}")

    def test_l_etage_reste_d_un_seul_tenant(self):
        """Le dégraissage ne doit jamais couper l'étage en deux."""
        from donjon.rng import Rng

        for graine in range(40):
            self.assertTrue(dungeon._connexe(dungeon.generate(Rng(graine))),
                            f"graine {graine}")


class TestExplorationAutomatique(unittest.TestCase):
    """Ce que l'exploration va chercher — et ce qu'elle laisse par terre."""

    def _jeu(self):
        from donjon.config import RunConfig, TOUT_DEBLOQUE

        jeu = sandbox(seed=1, config=RunConfig(max_depth=5,
                                               monsters_per_floor=(0, 0),
                                               items_per_floor=(0, 0),
                                               traps_per_floor=(0, 0),
                                               unlocks=TOUT_DEBLOQUE))
        jeu.level.explored |= set(jeu.level.walkable_cells())
        return jeu

    def _cases_libres(self, jeu, combien):
        return [pos for pos in sorted(jeu.level.walkable_cells())
                if pos != jeu.player.pos][:combien]

    def test_elle_va_chercher_ce_qui_se_consomme(self):
        from tests.helpers import poser_au_sol

        jeu = self._jeu()
        case = self._cases_libres(jeu, 1)[0]
        poser_au_sol(jeu, case, "onigiri")
        self.assertEqual(jeu.prochaine_exploration(), case)

    def test_elle_ne_va_jamais_chercher_une_arme(self):
        """Marcher sur une arme ne la ramasse pas : aller la chercher non plus.

        Le moteur a déjà tranché ailleurs (`_gerer_objet_au_sol`) qu'emporter
        une arme est une décision. L'exploration automatique contredisait cette
        règle, et le sac finissait plein d'épées qu'on n'avait pas choisies.
        """
        from tests.helpers import poser_au_sol

        jeu = self._jeu()
        case = self._cases_libres(jeu, 1)[0]
        poser_au_sol(jeu, case, "epee_fer")
        self.assertNotEqual(jeu.prochaine_exploration(), case)

    def test_une_arme_ne_masque_pas_un_vivre(self):
        from tests.helpers import poser_au_sol

        jeu = self._jeu()
        arme, vivre = self._cases_libres(jeu, 2)
        poser_au_sol(jeu, arme, "epee_fer")
        poser_au_sol(jeu, vivre, "onigiri")
        self.assertEqual(jeu.prochaine_exploration(), vivre)
