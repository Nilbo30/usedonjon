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

#: XP méta = XP de compétences versée pendant la vie
#:           × (1 + FACTEUR_PROFONDEUR × (étage − 1)).
#: L'étage retenu est le plus profond du passage en cours : l'orbe le remet à
#: zéro, ce qui fait de son usage un pari et non un gain gratuit.
#:
#: La monnaie a été la **somme des niveaux** jusqu'à l'étape 16. C'était un
#: défaut de fond : les courbes étant géométriques, cette somme croît
#: logarithmiquement avec ce qu'on pratique vraiment, quand le danger, lui,
#: croît par marches (×2,32 puis ×4,63). Un run profond coûtait beaucoup plus
#: cher et rapportait à peine plus — d'où le plateau à ~35 XP par vie, noté
#: deux fois dans le plan. Compter l'XP versée rend le gain linéaire en
#: pratique, rend le papillonnage neutre (1 XP vaut 1 XP où qu'elle aille) et
#: pondère chaque cran par son coût réel, sans aucune table à régler.
FACTEUR_PROFONDEUR = 0.1

#: Places dans le coffre avant tout agrandissement.
CAPACITE_ENTREPOT_BASE = 4


def valeur_du_run(summary):
    """XP méta rapportée par un bilan de run."""
    facteur = 1 + FACTEUR_PROFONDEUR * (max(1, summary.deepest) - 1)
    return summary.xp_investie * facteur


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

    def fois(self, cle):
        """Combien de fois ce talent a été pris (les nœuds répétables)."""
        return self.noeuds.count(cle)

    def achetable(self, cle):
        """Le nœud existe, n'est pas acquis, ses parents le sont, et on peut payer."""
        noeud = tree.ARBRE.get(cle)
        return bool(noeud and noeud.reste_a_prendre(self.noeuds) > 0
                    and noeud.accessible(self.noeuds)
                    and self.xp >= noeud.prix(self.noeuds))

    def acheter(self, cle):
        """Achète un talent. Renvoie le nœud, ou None si ce n'est pas possible."""
        if not self.achetable(cle):
            return None
        noeud = tree.ARBRE[cle]
        self.xp -= noeud.prix(self.noeuds)
        self.noeuds.append(cle)
        return noeud

    @staticmethod
    def _somme(actuel, valeur):
        """Additionne deux effets — terme à terme quand ce sont des couples.

        « +1 trouvaille par étage » s'écrit `(1, 1)` : sans ce traitement,
        Python collerait les tuples bout à bout au lieu de les additionner.
        """
        if isinstance(valeur, tuple):
            return tuple(a + b for a, b in zip(actuel, valeur))
        return actuel + valeur

    def _cumul(self):
        """Ce que les talents acquis apportent, chaque genre à sa façon.

        Les effets s'additionnent, les réglages remplacent, les drapeaux, les
        objets de départ et les classes de créatures s'accumulent.
        """
        effets, reglages, unlocks = {}, {}, set()
        objets, classes = [], set()
        for cle in self.noeuds:
            noeud = tree.ARBRE.get(cle)
            if noeud is None:
                continue                      # talent d'une version antérieure
            for champ, valeur in noeud.effets.items():
                courant = effets.get(champ)
                effets[champ] = (valeur if courant is None
                                 else self._somme(courant, valeur))
            reglages.update(noeud.reglages)
            unlocks.update(noeud.unlocks)
            objets += list(noeud.objets)
            classes.update(noeud.classes)
        return effets, reglages, unlocks, objets, classes

    def capacite_entrepot(self):
        effets, *_ = self._cumul()
        return CAPACITE_ENTREPOT_BASE + effets.get("coffre_places", 0)

    # --- influence sur les runs ------------------------------------------
    def run_config(self, base=None):
        """La config de la prochaine vie : un donjon nu, plus les talents acquis.

        Une `RunConfig` construite à la main garde tout son contenu ; c'est ce
        chemin-ci, et lui seul, qui verrouille ce qui n'a pas été gagné.
        """
        base = base or RunConfig()
        effets, reglages, unlocks, objets, classes = self._cumul()
        valeurs = dict(tree.BASE_VERROUILLEE)
        valeurs.update(reglages)
        valeurs["starting_kit"] = tuple(objets)
        for champ, valeur in effets.items():
            if champ in tree.EFFETS_META:
                continue
            # Sur la valeur déjà réglée s'il y en a une : un effet « +1
            # trouvaille » doit s'ajouter à ce que « Fouille » a posé, pas le
            # court-circuiter.
            depart = valeurs.get(champ, getattr(base, champ))
            valeurs[champ] = self._somme(depart, valeur)
        # Un ensemble vide veut dire « tout » côté RunConfig : il faut donc un
        # sentinelle pour dire « rien » sans rouvrir le contenu.
        valeurs["unlocks"] = frozenset(unlocks) or frozenset({"__rien__"})
        valeurs["classes"] = frozenset(classes) or frozenset({"__aucune__"})
        return base.replace(**valeurs)

    def lines(self):
        """Résumé affichable de la progression permanente."""
        lignes = [f"{self.xp:.0f} XP à dépenser  ·  {len(self.noeuds)} talents",
                  f"Vies jouées : {self.runs}"]
        if self.best_depth:
            lignes.append(f"Record : étage {self.best_depth} · "
                          f"{self.best_levels} niveaux de compétences")
        abordables = [n for n in tree.disponibles(self.noeuds)
                      if n.prix(self.noeuds) <= self.xp]
        if abordables:
            lignes.append("À portée : " + " · ".join(
                f"{n.name} ({n.prix(self.noeuds)})"
                for n in sorted(abordables,
                                key=lambda n: n.prix(self.noeuds))[:3]))
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


def effacer(chemin=None):
    """Supprime la sauvegarde. Vrai si le fichier n'existe plus après coup."""
    chemin = chemin or CHEMIN_DEFAUT
    try:
        os.remove(chemin)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


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
