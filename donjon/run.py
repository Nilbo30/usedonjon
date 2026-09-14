"""Bilan d'un run : ce qu'il reste quand la partie s'arrête.

`RunSummary` est le pendant de `RunConfig` : la config entre dans la partie,
le bilan en sort. C'est lui, et lui seul, qui alimentera la progression
permanente — le méta ne lira jamais un `Game`.
"""


class RunSummary:
    def __init__(self, state, depth, deepest, turns, skills, cause="", seed=None,
                 xp_investie=0.0, effort=0.0):
        self.state = state          # "mort" ou "victoire"
        self.depth = depth          # étage où la partie s'est arrêtée
        self.deepest = deepest      # étage le plus profond atteint du run
        self.turns = turns
        self.skills = dict(skills)  # clé -> niveau
        self.cause = cause
        self.seed = seed
        # Deux chiffres, et un seul s'échange. `xp_investie` est l'XP brute
        # versée aux compétences — ce qui s'est passé dans la partie.
        # `effort` la ramène en « premiers crans équivalents » (voir
        # `SkillSet.effort`) : c'est **lui** la monnaie du méta. Les niveaux,
        # eux, ne restent que pour la fiche de fin et les records.
        self.xp_investie = xp_investie
        self.effort = effort
        self.absorbed = False   # marqué par la session, pour n'encaisser qu'une fois

    @property
    def total_levels(self):
        return sum(self.skills.values())

    def lines(self, catalogue=None):
        """Résumé prêt à afficher, une information par ligne."""
        from . import skills as skills_mod

        catalogue = catalogue or skills_mod.CATALOGUE
        lignes = [f"Étage le plus profond : {self.deepest}",
                  f"Tours survécus : {self.turns}",
                  f"Niveaux de compétences : {self.total_levels}",
                  f"Effort : {self.effort:.0f} XP"]
        if self.cause:
            lignes.append(self.cause)
        acquises = sorted(((niveau, catalogue[cle].name)
                           for cle, niveau in self.skills.items()
                           if niveau and cle in catalogue), reverse=True)
        if acquises:
            detail = " · ".join(f"{nom} {niveau}" for niveau, nom in acquises[:4])
            lignes.append(detail)
        return lignes

    def to_dict(self):
        return {"state": self.state, "depth": self.depth, "deepest": self.deepest,
                "turns": self.turns, "skills": self.skills, "cause": self.cause,
                "seed": self.seed, "xp_investie": self.xp_investie,
                "effort": self.effort}

    def __repr__(self):
        return f"<RunSummary {self.state} étage {self.deepest} T{self.turns}>"
