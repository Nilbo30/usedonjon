"""Tours, énergie, statuts et faim : les briques qui porteront les mécaniques futures."""

import unittest

from donjon.entities import ACTION_COST
from tests.helpers import place_monster, sandbox


class TestTours(unittest.TestCase):
    def test_une_action_consomme_un_tour_de_monde(self):
        game = sandbox()
        before = game.turn
        game.cmd_wait()
        self.assertEqual(game.turn, before + 1)

    def test_un_monstre_rapide_agit_deux_fois_plus(self):
        game = sandbox()
        fast = place_monster(game, _far_spot(game), speed=200, hp=999)
        self.assertGreaterEqual(_count_actions(game, fast, turns=10), 18)

    def test_un_monstre_lent_agit_moins_souvent(self):
        game = sandbox()
        slow = place_monster(game, _far_spot(game), speed=50, hp=999)
        self.assertLessEqual(_count_actions(game, slow, turns=10), 6)

    def test_statut_bloquant_fait_perdre_le_tour(self):
        game = sandbox()
        game.player.add_status("endormi", 3)
        start = game.player.pos
        game.cmd_wait()
        self.assertGreaterEqual(game.turn, 3)   # les tours passent sans nous
        self.assertEqual(game.player.pos, start)
        self.assertFalse(game.player.has_status("endormi"))

    def test_la_faim_diminue_puis_blesse(self):
        game = sandbox()
        game.player.fullness = 1
        game.cmd_wait()
        self.assertEqual(game.player.fullness, 0)
        hp = game.player.hp
        game.cmd_wait()
        self.assertLess(game.player.hp, hp)

    def test_energie_du_joueur_disponible_a_son_tour(self):
        game = sandbox()
        game.cmd_wait()
        self.assertGreaterEqual(game.player.energy, ACTION_COST)


def _far_spot(game):
    room = game.level.room_at(game.player.pos)
    return (room.x + room.w - 1, room.y + room.h - 1)


def _count_actions(game, monster, turns):
    """Compte les actions du monstre (énergie dépensée) sur `turns` tours."""
    counter = {"n": 0}
    original = game.spend

    def spy(actor, cost=ACTION_COST):
        if actor is monster:
            counter["n"] += 1
        original(actor, cost)

    game.spend = spy
    start_turn = game.turn
    while game.turn - start_turn < turns and game.state == "en cours":
        game.cmd_wait()
    game.spend = original
    return counter["n"]


if __name__ == "__main__":
    unittest.main()
