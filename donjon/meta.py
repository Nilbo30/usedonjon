"""Progression permanente : ce qui survit à la mort.

C'est la seule chose qui traverse les runs. `Meta` ne connaît pas `Game` : il ne
lit qu'un `RunSummary` et ne produit qu'une `RunConfig`.

    Meta ──(run_config)──> RunConfig ──> Game ──(RunSummary)──> Meta.absorb

L'XP gagnée en mourant est une monnaie : on l'échange contre des nœuds de
l'arbre (voir tree.py), qui déverrouillent le jeu morceau par morceau. Rien
n'est linéaire — chaque vie pose une question, pas un palier.
"""

import json
import os

from . import tree
from .config import RunConfig

#: Emplacement de la sauvegarde. Modifiable pour les tests.
CHEMIN_DEFAUT = os.path.join(os.path.expanduser("~"), ".usedonjon", "meta.json")

#: XP méta = niveaux de compétences × (1 + FACTEUR_PROFONDEUR × (étage − 1)).
#: L'étage retenu est le plus profond du passage en cours : l'orbe le remet à
#: zéro, ce qui fait de son usage un pari et non un gain gratuit.
FACTEUR_PROFONDEUR = 0.1

#: Places dans le coffre avant tout agrandissement.
CAPACITE_ENTREPOT_BASE = 4


def valeur_du_run(summary):
    """XP méta rapportée par un bilan de run."""
    facteur = 1 + FACTEUR_PROFONDEUR * (max(1, summary.deepest) - 1)
    return summary.total_levels * facteur


class Meta:
    """L'état permanent d'un joueur. Sérialisable tel quel."""

    def __init__(self, xp=0.0, xp_totale=0.0, runs=0, best_depth=0,
                 best_levels=0, entrepot=None, noeuds=None):
        self.xp = xp                 # solde dépensable
        self.xp_totale = xp_totale   # tout ce qui a été gagné, pour la mémoire
        self.runs = runs
        self.best_depth = best_depth
        self.best_levels = best_levels
        # Les objets déposés au refuge : la seule matière qui traverse la mort.
        self.entrepot = list(entrepot or [])
        # Les talents acquis. Définitifs : on ne réattribue pas.
        self.noeuds = list(noeuds or [])

    # --- progression -----------------------------------------------------
    def absorb(self, summary):
        """Encaisse une descente terminée. Renvoie l'XP gagnée."""
        gagnee = valeur_du_run(summary)
        self.runs += 1
        self.best_depth = max(self.best_depth, summary.deepest)
        self.best_levels = max(self.best_levels, summary.total_levels)
        self.xp += gagnee
        self.xp_totale += gagnee
        return gagnee

    # --- l'arbre ---------------------------------------------------------
    def acquis(self, cle):
        return cle in self.noeuds

    def achetable(self, cle):
        """Le nœud existe, n'est pas acquis, ses parents le sont, et on peut payer."""
        noeud = tree.ARBRE.get(cle)
        return bool(noeud and cle not in self.noeuds
                    and noeud.accessible(self.noeuds) and self.xp >= noeud.cost)

    def acheter(self, cle):
        """Achète un talent. Renvoie le nœud, ou None si ce n'est pas possible."""
        if not self.achetable(cle):
            return None
        noeud = tree.ARBRE[cle]
        self.xp -= noeud.cost
        self.noeuds.append(cle)
        return noeud

    def _cumul(self):
        """Somme des effets, valeurs de réglage et drapeaux des talents acquis."""
        effets, reglages, unlocks = {}, {}, set()
        for cle in self.noeuds:
            noeud = tree.ARBRE.get(cle)
            if noeud is None:
                continue                      # talent d'une version antérieure
            for champ, valeur in noeud.effets.items():
                effets[champ] = effets.get(champ, 0) + valeur
            reglages.update(noeud.reglages)
            unlocks.update(noeud.unlocks)
        return effets, reglages, unlocks

    def capacite_entrepot(self):
        effets, _, _ = self._cumul()
        return CAPACITE_ENTREPOT_BASE + effets.get("coffre_places", 0)

    # --- influence sur les runs ------------------------------------------
    def run_config(self, base=None):
        """La config de la prochaine vie : un donjon nu, plus les talents acquis.

        Une `RunConfig` construite à la main garde tout son contenu ; c'est ce
        chemin-ci, et lui seul, qui verrouille ce qui n'a pas été gagné.
        """
        base = base or RunConfig()
        effets, reglages, unlocks = self._cumul()
        valeurs = dict(tree.BASE_VERROUILLEE)
        valeurs.update(reglages)
        for champ, valeur in effets.items():
            if champ in tree.EFFETS_META:
                continue
            valeurs[champ] = getattr(base, champ) + valeur
        valeurs["unlocks"] = frozenset(unlocks) or frozenset({"__rien__"})
        return base.replace(**valeurs)

    def lines(self):
        """Résumé affichable de la progression permanente."""
        lignes = [f"{self.xp:.0f} XP à dépenser  ·  {len(self.noeuds)} talents",
                  f"Vies jouées : {self.runs}"]
        if self.best_depth:
            lignes.append(f"Record : étage {self.best_depth} · "
                          f"{self.best_levels} niveaux de compétences")
        abordables = [n for n in tree.disponibles(self.noeuds)
                      if n.cost <= self.xp]
        if abordables:
            lignes.append("À portée : " + " · ".join(
                f"{n.name} ({n.cost})" for n in sorted(abordables,
                                                       key=lambda n: n.cost)[:3]))
        return lignes

    # --- persistance -----------------------------------------------------
    def to_dict(self):
        return {"xp": self.xp, "xp_totale": self.xp_totale, "runs": self.runs,
                "best_depth": self.best_depth, "best_levels": self.best_levels,
                "entrepot": self.entrepot, "noeuds": self.noeuds}

    @classmethod
    def from_dict(cls, donnees):
        connus = {"xp", "xp_totale", "runs", "best_depth", "best_levels",
                  "entrepot", "noeuds"}
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
