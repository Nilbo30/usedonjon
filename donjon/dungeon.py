"""Génération d'étage : grille de secteurs, une salle par secteur, couloirs entre voisins.

C'est la structure classique des Mystery Dungeon : des salles rectangulaires
reliées par des couloirs, et une visibilité « salle entière » une fois dedans.
"""

from . import tiles
from .geom import add


class Room:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def center(self):
        return (self.x + self.w // 2, self.y + self.h // 2)

    def contains(self, pos):
        return self.x <= pos[0] < self.x + self.w and self.y <= pos[1] < self.y + self.h

    def cells(self):
        for y in range(self.y, self.y + self.h):
            for x in range(self.x, self.x + self.w):
                yield (x, y)


class Level:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = [[tiles.WALL for _ in range(width)] for _ in range(height)]
        self.rooms = []
        self.items = {}      # pos -> Item
        self.traps = {}      # pos -> Trap
        self.stairs = None
        self.explored = set()

    # --- accès cases ---------------------------------------------------
    def in_bounds(self, pos):
        return 0 <= pos[0] < self.width and 0 <= pos[1] < self.height

    def tile(self, pos):
        if not self.in_bounds(pos):
            return tiles.WALL
        return self.grid[pos[1]][pos[0]]

    def set_tile(self, pos, tile):
        self.grid[pos[1]][pos[0]] = tile

    def walkable(self, pos):
        return self.in_bounds(pos) and tiles.walkable(self.tile(pos))

    def room_at(self, pos):
        for room in self.rooms:
            if room.contains(pos):
                return room
        return None

    def walkable_cells(self):
        for y in range(self.height):
            for x in range(self.width):
                if tiles.walkable(self.grid[y][x]):
                    yield (x, y)

    # --- champ de vision ------------------------------------------------
    def visible_from(self, pos):
        """Règle Shiren : dans une salle on voit toute la salle, sinon les 8 cases autour."""
        room = self.room_at(pos)
        seen = {pos}
        if room:
            for y in range(room.y - 1, room.y + room.h + 1):
                for x in range(room.x - 1, room.x + room.w + 1):
                    if self.in_bounds((x, y)):
                        seen.add((x, y))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p = (pos[0] + dx, pos[1] + dy)
                if self.in_bounds(p):
                    seen.add(p)
        return seen

    def reveal_all(self):
        self.explored.update(self.walkable_cells())
        for pos in list(self.explored):
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    p = add(pos, (dx, dy))
                    if self.in_bounds(p):
                        self.explored.add(p)


def generate(rng, width=60, height=22, cols=3, rows=2):
    """Construit un étage : une salle par secteur, puis relie les secteurs voisins."""
    level = Level(width, height)
    cell_w = width // cols
    cell_h = height // rows
    grid_rooms = {}

    for cy in range(rows):
        for cx in range(cols):
            ox, oy = cx * cell_w, cy * cell_h
            max_w = max(4, cell_w - 4)
            max_h = max(3, cell_h - 3)
            w = rng.randint(4, max_w)
            h = rng.randint(3, max_h)
            x = ox + rng.randint(2, max(2, cell_w - w - 2))
            y = oy + rng.randint(1, max(1, cell_h - h - 2))
            room = Room(x, y, w, h)
            grid_rooms[(cx, cy)] = room
            level.rooms.append(room)
            for pos in room.cells():
                level.set_tile(pos, tiles.FLOOR)

    # Couloirs : chaque salle est reliée à sa voisine de droite et du dessous.
    for (cx, cy), room in grid_rooms.items():
        for dx, dy in ((1, 0), (0, 1)):
            other = grid_rooms.get((cx + dx, cy + dy))
            if other:
                _carve_corridor(level, room.center, other.center, rng)

    # Escalier dans une salle au hasard.
    stair_room = rng.choice(level.rooms)
    level.stairs = _free_spot_in(level, stair_room, rng)
    level.set_tile(level.stairs, tiles.STAIRS)
    return level


def _carve_corridor(level, a, b, rng):
    """Couloir en L (horizontal puis vertical, ou l'inverse)."""
    if rng.chance(0.5):
        waypoint = (b[0], a[1])
    else:
        waypoint = (a[0], b[1])
    for pos in _line(a, waypoint):
        _dig(level, pos)
    for pos in _line(waypoint, b):
        _dig(level, pos)


def _dig(level, pos):
    if level.tile(pos) == tiles.WALL:
        level.set_tile(pos, tiles.CORRIDOR)


def _line(a, b):
    x, y = a
    while (x, y) != b:
        if x != b[0]:
            x += 1 if b[0] > x else -1
        elif y != b[1]:
            y += 1 if b[1] > y else -1
        yield (x, y)
    yield b


def _free_spot_in(level, room, rng):
    cells = [c for c in room.cells() if level.tile(c) == tiles.FLOOR]
    return rng.choice(cells)


def random_floor(level, rng, exclude=()):
    """Une case de salle libre (on évite les couloirs pour les spawns)."""
    candidates = [
        pos
        for room in level.rooms
        for pos in room.cells()
        if level.tile(pos) == tiles.FLOOR and pos not in exclude
    ]
    if not candidates:
        candidates = [p for p in level.walkable_cells() if p not in exclude]
    return rng.choice(candidates)
