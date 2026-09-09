import unittest

from donjon import dungeon, path, tiles
from donjon.rng import Rng


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
