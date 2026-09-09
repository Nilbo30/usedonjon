"""La session : ce qui relie les runs entre eux.

C'est le seul endroit où le méta et une partie se croisent. `Game` ignore
l'existence de `Meta` ; les interfaces ignorent la mécanique de conversion.
Elles parlent toutes à une `Session` :

    session = Session()
    game = session.nouvelle_partie()
    ...                       # le run se joue
    bilan = session.encaisser(game)   # à la mort : méta mis à jour et sauvegardé
"""

from . import meta as meta_mod
from .game import Game


class Session:
    def __init__(self, chemin=None, sauvegarde=True, seed=None, config=None):
        self.chemin = chemin
        self.sauvegarde = sauvegarde
        self.seed = seed
        self.base_config = config
        self.meta = meta_mod.load(chemin) if sauvegarde else meta_mod.Meta()
        self.dernier_gain = None      # (xp gagnée, niveaux franchis)

    def nouvelle_partie(self, seed=None):
        """Un run neuf, configuré par tout ce qui a été acquis jusque-là."""
        return Game(seed=seed if seed is not None else self.seed,
                    config=self.meta.run_config(self.base_config))

    def encaisser(self, game):
        """Convertit un run terminé en progression permanente, puis sauvegarde.

        Sans effet si le run n'est pas fini, ou s'il a déjà été encaissé.
        """
        bilan = game.summary
        if bilan is None or bilan.absorbed:
            return None
        bilan.absorbed = True
        self.dernier_gain = self.meta.absorb(bilan)
        if self.sauvegarde:
            meta_mod.save(self.meta, self.chemin)
        return self.dernier_gain

    def lignes_de_gain(self):
        """Ce qu'a rapporté le dernier run, prêt à afficher."""
        if not self.dernier_gain:
            return []
        gagnee, franchis = self.dernier_gain
        lignes = [f"+{gagnee:.0f} XP de progression permanente"]
        if franchis:
            lignes.append("Niveau global " + " puis ".join(map(str, franchis))
                          + " !")
        return lignes
