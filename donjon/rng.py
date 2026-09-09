"""Générateur aléatoire encapsulé : tout le hasard du jeu passe par ici.

Un seul point d'entrée => les parties sont reproductibles à partir d'une graine,
ce qui rend les tests automatisés déterministes.
"""

import random


class Rng:
    def __init__(self, seed=None):
        self.seed = random.randrange(1 << 30) if seed is None else int(seed)
        self._r = random.Random(self.seed)

    def randint(self, a, b):
        return self._r.randint(a, b)

    def random(self):
        return self._r.random()

    def choice(self, seq):
        return self._r.choice(list(seq))

    def shuffle(self, seq):
        self._r.shuffle(seq)
        return seq

    def chance(self, p):
        """Vrai avec une probabilité p (0..1)."""
        return self._r.random() < p

    def weighted(self, pairs):
        """pairs = [(valeur, poids), ...] -> une valeur tirée au poids."""
        pairs = [(v, w) for v, w in pairs if w > 0]
        total = sum(w for _, w in pairs)
        roll = self._r.random() * total
        for value, weight in pairs:
            roll -= weight
            if roll <= 0:
                return value
        return pairs[-1][0]

    def variance(self, value, spread=0.125):
        """Applique une variation +/- spread à une valeur (dégâts, etc.)."""
        factor = 1.0 + (self._r.random() * 2 - 1) * spread
        return value * factor
