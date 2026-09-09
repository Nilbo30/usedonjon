"""Recherche de chemin (BFS) sur la grille.

Utilisée par l'IA pour contourner les murs et par le bot de test. Un BFS sur un
étage (60x22) est instantané ; si un jour la carte grossit, seule cette fonction
sera à remplacer (A*, Dijkstra pondéré...).
"""

from collections import deque

from .geom import ALL_DIRS, add, is_diagonal


def _passable(level, src, delta, blocked, allowed=None):
    dest = add(src, delta)
    if not level.walkable(dest) or dest in blocked:
        return False
    if allowed is not None and dest not in allowed:
        return False
    if is_diagonal(delta):
        if not (level.walkable(add(src, (delta[0], 0)))
                and level.walkable(add(src, (0, delta[1])))):
            return False
    return True


def find_path(level, start, goal, blocked=frozenset(), max_nodes=4000,
              allowed=None):
    """Renvoie la liste des cases de start (exclu) à goal (inclus), ou None.

    `allowed`, s'il est fourni, limite le chemin à ces cases : c'est ainsi que
    le déplacement à la souris ne traverse que ce que le joueur a déjà vu.
    """
    if start == goal:
        return []
    frontier = deque([start])
    came_from = {start: None}
    visited = 0
    while frontier:
        current = frontier.popleft()
        visited += 1
        if visited > max_nodes:
            return None
        for delta in ALL_DIRS:
            nxt = add(current, delta)
            if nxt in came_from:
                continue
            # La case d'arrivée est autorisée même si occupée (c'est la cible).
            if nxt != goal and not _passable(level, current, delta, blocked, allowed):
                continue
            if nxt == goal and not level.walkable(nxt):
                continue
            came_from[nxt] = current
            if nxt == goal:
                return _rebuild(came_from, goal)
            frontier.append(nxt)
    return None


def _rebuild(came_from, goal):
    path = []
    node = goal
    while came_from[node] is not None:
        path.append(node)
        node = came_from[node]
    path.reverse()
    return path


def step_along(level, start, goal, blocked=frozenset(), allowed=None):
    """Direction du premier pas d'un chemin vers goal, ou None."""
    path = find_path(level, start, goal, blocked, allowed=allowed)
    if not path:
        return None
    first = path[0]
    return (first[0] - start[0], first[1] - start[1])
