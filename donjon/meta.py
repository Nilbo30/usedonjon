"""Progression permanente : ce qui survit à la mort.

C'est la seule chose qui traverse les runs. `Meta` ne connaît pas `Game` : il ne
lit qu'un `RunSummary` et ne produit qu'une `RunConfig`.

    Meta ──(run_config)──> RunConfig ──> Game ──(RunSummary)──> Meta.absorb

Deux tables de données, et rien d'autre à toucher pour équilibrer :

* `BONUS` — ce que chaque niveau global ajoute à la config des runs suivants.
* la conversion d'un bilan en XP méta, ci-dessous.
"""

import json
import os

from .config import RunConfig

#: Emplacement de la sauvegarde. Modifiable pour les tests.
CHEMIN_DEFAUT = os.path.join(os.path.expanduser("~"), ".usedonjon", "meta.json")

#: XP méta = niveaux de compétences × (1 + FACTEUR_PROFONDEUR × (étage − 1)).
#: L'étage retenu est le plus profond du passage en cours : l'orbe le remet à
#: zéro, ce qui fait de son usage un pari et non un gain gratuit.
FACTEUR_PROFONDEUR = 0.1

#: Coût du premier niveau global, puis multiplié à chaque palier.
COUT_BASE = 20
CROISSANCE = 1.4

#: Ce que chaque niveau global ajoute, cumulativement, aux runs suivants.
#: Une ligne de plus = un palier de plus. Les clés sont des champs de RunConfig.
BONUS = {
    1: {"max_fullness": 20},
    2: {"start_hp": 5},
    3: {"max_fullness": 20},
    4: {"inventory_size": 2},
    5: {"start_hp": 5},
    6: {"max_fullness": 30},
    7: {"start_attack": 1, "start_defense": 1},
    8: {"start_hp": 10},
    9: {"max_fullness": 30},
    10: {"start_attack": 2, "start_defense": 2},
}


def cout_du_niveau(niveau):
    """XP nécessaire pour passer de `niveau` à `niveau + 1`."""
    return max(1, round(COUT_BASE * CROISSANCE ** niveau))


def valeur_du_run(summary):
    """XP méta rapportée par un bilan de run."""
    facteur = 1 + FACTEUR_PROFONDEUR * (max(1, summary.deepest) - 1)
    return summary.total_levels * facteur


class Meta:
    """L'état permanent d'un joueur. Sérialisable tel quel."""

    #: Places dans l'entrepôt du refuge.
    CAPACITE_ENTREPOT = 8

    def __init__(self, level=0, xp=0.0, runs=0, best_depth=0, best_levels=0,
                 entrepot=None):
        self.level = level
        self.xp = xp                 # XP accumulée dans le niveau courant
        self.runs = runs
        self.best_depth = best_depth
        self.best_levels = best_levels
        # Les objets déposés au refuge : la seule matière qui traverse la mort.
        self.entrepot = list(entrepot or [])

    # --- progression -----------------------------------------------------
    def absorb(self, summary):
        """Encaisse un run terminé. Renvoie (xp gagnée, niveaux franchis)."""
        gagnee = valeur_du_run(summary)
        self.runs += 1
        self.best_depth = max(self.best_depth, summary.deepest)
        self.best_levels = max(self.best_levels, summary.total_levels)
        self.xp += gagnee
        franchis = []
        while self.xp >= cout_du_niveau(self.level):
            self.xp -= cout_du_niveau(self.level)
            self.level += 1
            franchis.append(self.level)
        return gagnee, franchis

    def progress(self):
        """(xp dans le niveau, xp nécessaire) pour une barre de progression."""
        return (self.xp, cout_du_niveau(self.level))

    # --- influence sur les runs ------------------------------------------
    def bonuses(self):
        """Somme des bonus acquis, par champ de RunConfig."""
        acquis = {}
        for niveau, apports in BONUS.items():
            if niveau <= self.level:
                for champ, valeur in apports.items():
                    acquis[champ] = acquis.get(champ, 0) + valeur
        return acquis

    def run_config(self, base=None):
        """La config du prochain run : la base, plus tout ce qui a été gagné."""
        base = base or RunConfig()
        acquis = self.bonuses()
        if not acquis:
            return base
        return base.replace(**{champ: getattr(base, champ) + valeur
                               for champ, valeur in acquis.items()})

    def prochain_avantage(self):
        """Ce que le prochain niveau global débloquera, en clair."""
        apports = BONUS.get(self.level + 1)
        if not apports:
            return None
        libelles = {"max_fullness": "de ventre", "start_hp": "PV de départ",
                    "start_attack": "d'attaque", "start_defense": "de défense",
                    "inventory_size": "places dans le sac"}
        return " · ".join(f"+{valeur} {libelles.get(champ, champ)}"
                          for champ, valeur in sorted(apports.items()))

    def lines(self):
        """Résumé affichable de la progression permanente."""
        xp, requis = self.progress()
        lignes = [f"Niveau global {self.level}  ({xp:.0f}/{requis} vers le suivant)",
                  f"Runs joués : {self.runs}"]
        if self.best_depth:
            lignes.append(f"Record : étage {self.best_depth} · "
                          f"{self.best_levels} niveaux de compétences")
        prochain = self.prochain_avantage()
        if prochain:
            lignes.append(f"Niveau {self.level + 1} débloquera : {prochain}")
        acquis = self.bonuses()
        if acquis:
            lignes.append("Acquis : " + " · ".join(
                f"{champ} +{valeur}" for champ, valeur in sorted(acquis.items())))
        return lignes

    # --- persistance -----------------------------------------------------
    def to_dict(self):
        return {"level": self.level, "xp": self.xp, "runs": self.runs,
                "best_depth": self.best_depth, "best_levels": self.best_levels,
                "entrepot": self.entrepot}

    @classmethod
    def from_dict(cls, donnees):
        connus = {"level", "xp", "runs", "best_depth", "best_levels", "entrepot"}
        return cls(**{k: v for k, v in donnees.items() if k in connus})


def load(chemin=None):
    """Charge la progression, ou en crée une neuve si le fichier manque."""
    chemin = chemin or CHEMIN_DEFAUT
    try:
        with open(chemin, encoding="utf-8") as fichier:
            return Meta.from_dict(json.load(fichier))
    except (OSError, ValueError, TypeError):
        # Fichier absent, illisible ou corrompu : on repart proprement plutôt
        # que d'empêcher le joueur de jouer.
        return Meta()


def save(meta, chemin=None):
    """Écrit la progression. Renvoie False si l'écriture a échoué."""
    chemin = chemin or CHEMIN_DEFAUT
    try:
        dossier = os.path.dirname(chemin)
        if dossier:
            os.makedirs(dossier, exist_ok=True)
        with open(chemin, "w", encoding="utf-8") as fichier:
            json.dump(meta.to_dict(), fichier, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False
