"""Géométrie : positions et directions sur la grille (8 directions)."""

DIRECTIONS = {
    "n": (0, -1),
    "s": (0, 1),
    "w": (-1, 0),
    "e": (1, 0),
    "nw": (-1, -1),
    "ne": (1, -1),
    "sw": (-1, 1),
    "se": (1, 1),
}

ALL_DIRS = list(DIRECTIONS.values())
CARDINALS = [DIRECTIONS[k] for k in ("n", "s", "w", "e")]


def add(pos, delta):
    return (pos[0] + delta[0], pos[1] + delta[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def sign(n):
    return (n > 0) - (n < 0)


def chebyshev(a, b):
    """Distance en nombre de pas quand les diagonales coûtent 1."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def step_toward(src, dst):
    """Direction (dx, dy) d'un pas de src vers dst."""
    return (sign(dst[0] - src[0]), sign(dst[1] - src[1]))


def neighbours(pos, dirs=None):
    for d in (dirs or ALL_DIRS):
        yield add(pos, d)


def is_diagonal(delta):
    return delta[0] != 0 and delta[1] != 0
