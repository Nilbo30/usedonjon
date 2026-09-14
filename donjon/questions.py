"""Les questions que le moteur pose avant de calculer un nombre.

Ce fichier remplace treize expressions arithmétiques écrites à la main. Le
moteur ne lit plus « le bonus d'attaque » : il **demande** combien vaut
l'attaque, et ce qui sait répondre répond.

    degats = questions.demander(ATTAQUE, base + arme, porteur=heros,
                                cible=monstre, arme=arme)

Trois choses changent, et la troisième est la raison du chantier :

1. Les compétences répondent toujours, par la table `CONTRIBUTIONS` — les onze
   effets de `skills.EFFETS` continuent de marcher sans qu'aucun d'eux ne soit
   réécrit.
2. **Une interception** peut modifier la réponse en route, en données :
   `@intercepte(ATTAQUE)` et rien d'autre. Ajouter « +50 % contre le métal » ne
   demande plus une ligne de moteur.
3. La question **porte son contexte** — qui frappe, qui encaisse, avec quoi.
   C'est ce que `porteur.bonus("attaque")` ne pouvait pas dire, et c'est ce
   qu'il faut pour les affinités de matière.

Deux garanties, tenues par le code et non par la discipline :

* **L'ordre est déterministe sans table de priorités.** Deux passes : tout ce
  qui ajoute, puis tout ce qui multiplie, puis le bornage. À l'intérieur d'une
  passe l'ordre n'existe pas, l'addition et la multiplication étant
  commutatives.
* **Une interception ne peut rien déclencher.** Elle ne reçoit pas le `Game` :
  il n'y a donc aucune cascade possible au milieu d'un calcul de dégâts, et
  aucun garde-fou n'a à en protéger.

Ne pas confondre avec `skills.EFFETS`, qui nomme les bonus qu'une compétence
donne. Ici on nomme les **quantités que le moteur calcule** ; la table
`CONTRIBUTIONS` relie les deux.
"""

from . import skills

# --- les questions que le moteur sait poser -------------------------------
ATTAQUE = "attaque"
DEFENSE = "defense"
PV_MAX = "pv_max"
FAIM = "faim"                    # ce qu'un tour creuse le ventre
REPOS = "repos"                  # tours entre deux PV regagnés en soufflant
ESQUIVE = "esquive"              # chance de se dérober entièrement
BUTIN = "butin"                  # chance qu'une créature laisse quelque chose
SOIN = "soin"                    # PV rendus par une herbe
SATIETE = "satiete"              # ventre rendu par un repas
DUREE_EFFET = "duree_effet"      # tours que dure un parchemin
DEGATS_JET = "degats_jet"        # puissance d'un objet lancé
DEGATS_SORT = "degats_sort"      # puissance d'un sort lancé depuis un bâton

#: Chaque question, et ce qu'elle veut dire. Une interception qui vise un nom
#: absent d'ici est refusée : c'est ce qui empêche une faute de frappe de
#: devenir un effet silencieusement mort.
QUESTIONS = {
    ATTAQUE: "points d'attaque du porteur",
    DEFENSE: "points de défense du porteur",
    PV_MAX: "points de vie maximum",
    FAIM: "ventre creusé par un tour de marche",
    REPOS: "tours entre deux PV regagnés en se reposant",
    ESQUIVE: "chance d'éviter un coup entièrement",
    BUTIN: "chance qu'une créature vaincue laisse quelque chose",
    SOIN: "PV rendus par une herbe",
    SATIETE: "ventre rendu par un repas",
    DUREE_EFFET: "tours que dure l'effet d'un parchemin",
    DEGATS_JET: "puissance d'un objet lancé",
    DEGATS_SORT: "puissance d'un sort",
}

AJOUTER, RETIRER = "ajouter", "retirer"

#: Quel effet de compétence alimente quelle question, et dans quel sens.
#: C'est toute la traduction entre l'ancien monde et le nouveau : « Endurance »
#: ne s'ajoute pas à une question « endurance », elle se **retire** de la faim.
#: Nommer la question d'après la quantité calculée, et non d'après le bonus,
#: est ce qui rend l'interception lisible : on intercepte « la faim », pas
#: « l'endurance ».
CONTRIBUTIONS = {
    ATTAQUE: ("attaque", AJOUTER),
    DEFENSE: ("defense", AJOUTER),
    PV_MAX: ("pv_max", AJOUTER),
    FAIM: ("endurance", RETIRER),
    REPOS: ("regeneration", RETIRER),
    ESQUIVE: ("esquive", AJOUTER),
    BUTIN: ("chance", AJOUTER),
    SOIN: ("soin", AJOUTER),
    SATIETE: ("satiete", AJOUTER),
    DUREE_EFFET: ("duree_effet", AJOUTER),
    DEGATS_JET: ("degats_jet", AJOUTER),
    DEGATS_SORT: ("degats_sort", AJOUTER),
}


class Question:
    """Un nombre en route vers le moteur, et ce qui peut encore le changer.

    Volontairement sans `game` : une réponse lit et contribue, elle n'agit pas.
    """

    __slots__ = ("nom", "valeur", "contexte", "mini", "maxi", "_facteur")

    def __init__(self, nom, depart, mini=None, maxi=None, contexte=None):
        self.nom = nom
        self.valeur = depart
        self.mini = mini
        self.maxi = maxi
        self.contexte = contexte or {}
        self._facteur = 1.0

    # --- ce qu'une réponse peut faire ------------------------------------
    def ajouter(self, valeur):
        self.valeur += valeur

    def retirer(self, valeur):
        self.valeur -= valeur

    def multiplier(self, facteur):
        """Appliqué **après** toutes les additions, d'où l'ordre déterministe."""
        self._facteur *= facteur

    # --- ce qu'une réponse peut lire -------------------------------------
    @property
    def porteur(self):
        return self.contexte.get("porteur")

    def get(self, cle, defaut=None):
        return self.contexte.get(cle, defaut)

    def __getitem__(self, cle):
        return self.contexte[cle]

    def resultat(self):
        # Sans multiplicateur déclaré, on ne multiplie pas : `20 * 1.0` vaut
        # 20.0 et pas 20, et un « PV 20/20.0 » sur la fiche est déjà une
        # différence de comportement. Les empreintes l'ont attrapé.
        valeur = self.valeur if self._facteur == 1.0 else self.valeur * self._facteur
        if self.mini is not None:
            valeur = max(self.mini, valeur)
        if self.maxi is not None:
            valeur = min(self.maxi, valeur)
        return valeur

    def __repr__(self):
        return f"<{self.nom} {self.resultat():g}>"


# --------------------------------------------------------------------------
# Les interceptions : du contenu, pas du moteur
# --------------------------------------------------------------------------
INTERCEPTIONS = {}


def intercepte(question):
    """Enregistre une réponse à une question. Le nom doit exister.

        @intercepte(questions.ATTAQUE)
        def argent_contre_la_chair(q):
            if q.get("arme") and q["cible"].famille == "chair":
                q.multiplier(1.5)
    """
    if question not in QUESTIONS:
        raise ValueError(f"question inconnue : {question!r}")

    def enregistrer(fonction):
        INTERCEPTIONS.setdefault(question, []).append(fonction)
        return fonction

    return enregistrer


def _repondre_par_les_competences(question):
    """La réponse toujours présente : ce que les compétences du porteur donnent."""
    contribution = CONTRIBUTIONS.get(question.nom)
    porteur = question.porteur
    if contribution is None or porteur is None:
        return
    effet, sens = contribution
    valeur = porteur.bonus(effet)
    if sens is RETIRER:
        question.retirer(valeur)
    else:
        question.ajouter(valeur)


def demander(nom, depart, porteur=None, mini=None, maxi=None, **contexte):
    """Pose une question et renvoie la réponse, bornée.

    `mini` et `maxi` sont les bornes du moteur — elles restent au point de
    lecture tant que les constantes de `game.py` n'ont pas déménagé (c'est une
    étape à part). Il y en a quatre dans tout le jeu : le plancher de la faim,
    le plancher du repos, le plafond d'esquive et le plafond de butin.
    """
    contexte["porteur"] = porteur
    question = Question(nom, depart, mini=mini, maxi=maxi, contexte=contexte)
    _repondre_par_les_competences(question)
    for interception in INTERCEPTIONS.get(nom, ()):
        interception(question)
    return question.resultat()


def _verifier_les_tables():
    """Les deux tables doivent se répondre, et ne viser que des effets réels."""
    inconnues = set(CONTRIBUTIONS) - set(QUESTIONS)
    if inconnues:
        raise ValueError(f"contributions sans question : {sorted(inconnues)}")
    inconnus = {effet for effet, _ in CONTRIBUTIONS.values()} - set(skills.EFFETS)
    if inconnus:
        raise ValueError(f"effets de compétence inconnus : {sorted(inconnus)}")


_verifier_les_tables()
