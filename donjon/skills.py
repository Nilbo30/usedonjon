"""Compétences : on progresse dans ce qu'on pratique, pas en tuant.

Trois tables, et **rien d'autre à toucher pour ajouter du contenu** :

* `COMPETENCES` — le catalogue : une entrée par compétence, sa courbe et ses
  bonus par niveau.
* `REGLES` — quel évènement (voir events.py) crédite quelle compétence, et de
  combien. Plusieurs règles peuvent viser le même évènement : une action peut
  donc nourrir plusieurs compétences à la fois.
* le champ `skill` des objets (items.py), déduit par défaut de leur catégorie.

Ajouter une hache = une entrée `Skill("hache", ...)` + `skill="hache"` sur les
objets concernés. Le moteur ne change pas : quand le héros frappe, la règle
`"@arme"` lit la famille de l'arme portée et crédite la compétence du même nom.

En revanche, un **nouveau type de bonus** (autre que ceux listés dans EFFETS)
demande un point de lecture dans le moteur : c'est la seule extension qui n'est
pas gratuite, et ils sont volontairement peu nombreux.
"""

from . import events

# --- portées ---------------------------------------------------------------
TOUJOURS = "toujours"        # le bonus s'applique en permanence
EQUIPEMENT = "equipement"    # seulement si l'objet de cette famille est porté

# --- effets connus du moteur (chacun lu à un seul endroit) -----------------
EFFETS = {
    "attaque": "points d'attaque",
    "defense": "points de défense",
    "pv_max": "points de vie maximum",
    "endurance": "part de la faim évitée (0.03 = 3 %)",
    "soin": "points de soin en plus par herbe",
    "satiete": "points de ventre en plus par repas",
    "degats_jet": "dégâts en plus des objets lancés",
    "duree_effet": "tours en plus sur les effets de parchemins",
    "regeneration": "tours en moins entre deux points de vie regagnés",
    "esquive": "chance d'éviter un coup entièrement (0.03 = 3 %)",
}


#: Étiquettes courtes des effets, pour dire au joueur ce qu'il gagnera.
LIBELLES = {
    "attaque": "attaque",
    "defense": "défense",
    "pv_max": "PV max",
    "endurance": "de faim en moins",
    "soin": "soin par herbe",
    "satiete": "ventre par repas",
    "degats_jet": "dégâts de jet",
    "duree_effet": "tour d'effet",
    "regeneration": "tour de repos en moins",
    "esquive": "d'esquive",
}


class Skill:
    """Une compétence : une courbe d'XP et des bonus proportionnels au niveau."""

    def __init__(self, key, name, base, growth=1.5, scope=TOUJOURS,
                 effects=None, note=""):
        self.key = key
        self.name = name
        self.base = base            # XP pour passer du niveau 0 au niveau 1
        self.growth = growth        # coût multiplié par ce facteur à chaque niveau
        self.scope = scope
        self.effects = effects or {}
        self.note = note
        inconnus = set(self.effects) - set(EFFETS)
        if inconnus:
            raise ValueError(f"{key} : effet inconnu {sorted(inconnus)}")

    def cost(self, level):
        """XP nécessaire pour passer de `level` à `level + 1`."""
        return max(1, round(self.base * self.growth ** level))

    def bonus(self, effet, level):
        return self.effects.get(effet, 0) * level

    def gain_par_niveau(self):
        """Ce qu'un niveau de plus apportera, en clair."""
        morceaux = []
        for effet, valeur in self.effects.items():
            if effet == "endurance":
                morceaux.append(f"{valeur * 100:g} % {LIBELLES[effet]}")
            elif effet == "esquive":
                morceaux.append(f"+{valeur * 100:g} % {LIBELLES[effet]}")
            else:
                morceaux.append(f"+{valeur:g} {LIBELLES[effet]}")
        return " · ".join(morceaux)


# --------------------------------------------------------------------------
# Le catalogue
# --------------------------------------------------------------------------
CATALOGUE = {}


def _enregistrer(*competences):
    for competence in competences:
        CATALOGUE[competence.key] = competence


_enregistrer(
    Skill("marche", "Marche", base=25, growth=1.55,
          effects={"endurance": 0.03},
          note="Marcher creuse moins l'estomac."),
    Skill("combat", "Combat", base=8,
          effects={"attaque": 0.5, "pv_max": 2},
          note="Toute arme entretient la carrure."),
    Skill("epee", "Épée", base=5, scope=EQUIPEMENT,
          effects={"attaque": 1},
          note="Ne compte que l'épée à la main."),
    Skill("pugilat", "Pugilat", base=5, scope=EQUIPEMENT,
          effects={"attaque": 1},
          note="Se pratique les mains vides."),
    Skill("bouclier", "Bouclier", base=6, scope=EQUIPEMENT,
          effects={"defense": 1},
          note="S'apprend en encaissant, bouclier au bras."),
    # Elle monte vite et rapporte gros, à dessein : elle ne remplace pas la
    # compétence du bouclier mais le bouclier lui-même — un +6 de défense
    # gagné d'un coup en le ramassant. Sans ça, le bras nu est un handicap et
    # non une autre façon de jouer : 16,1 XP/vie au premier réglage contre
    # 27,3 pour le bouclier, 24,4 une fois calée.
    Skill("esquive", "Esquive", base=3, growth=1.4, scope=EQUIPEMENT,
          effects={"esquive": 0.09},
          note="S'apprend en encaissant sans bouclier : le corps apprend à "
               "se dérober."),
    Skill("herboristerie", "Herboristerie", base=2, growth=1.6,
          effects={"soin": 2},
          note="Les herbes rendent davantage."),
    Skill("nourriture", "Cuisine", base=2, growth=1.6,
          effects={"satiete": 5},
          note="On tire plus de chaque repas."),
    Skill("recuperation", "Récupération", base=10, growth=1.6,
          effects={"regeneration": 0.25},
          note="Se reposer soigne plus vite."),
    Skill("jet", "Jet", base=3,
          effects={"degats_jet": 1},
          note="Viser fait mal."),
    Skill("parchemins", "Parchemins", base=2, growth=1.6,
          effects={"duree_effet": 1},
          note="Les incantations durent plus longtemps."),
)


# --------------------------------------------------------------------------
# Quel évènement nourrit quelle compétence
# --------------------------------------------------------------------------
class Regle:
    """« Cet évènement donne N XP à cette compétence. »

    `competence` est soit une clé du catalogue, soit `"@champ"` : on lit alors
    la famille (`skill`) de l'objet rangé sous ce champ de l'évènement. C'est ce
    qui rend l'ajout d'une arme purement déclaratif.
    """

    def __init__(self, evenement, competence, xp=1, defaut=None, si=None):
        self.evenement = evenement
        self.competence = competence
        self.xp = xp
        self.defaut = defaut
        self.si = si            # prédicat optionnel sur l'évènement

    def resoudre(self, event):
        """Clé de compétence à créditer pour cet évènement, ou None."""
        if self.si and not self.si(event):
            return None
        if not self.competence.startswith("@"):
            return self.competence
        objet = event.get(self.competence[1:])
        if objet is None:
            return self.defaut
        return getattr(objet.type, "skill", None) or self.defaut


REGLES = (
    Regle(events.PAS, "marche"),
    # Un coup nourrit à la fois la famille d'arme et la carrure générale :
    # c'est le cas type d'une action qui crédite deux compétences.
    Regle(events.COUP, "@arme", defaut="pugilat", si=lambda e: e["touche"]),
    Regle(events.COUP, "combat", si=lambda e: e["touche"]),
    Regle(events.MONSTRE_VAINCU, "combat", xp=3),
    # Deux écoles pour la même leçon, selon ce qu'on a au bras — le pendant
    # exact de « épée / pugilat » du côté de la défense.
    Regle(events.COUP_RECU, "bouclier", si=lambda e: e["bouclier"] is not None),
    Regle(events.COUP_RECU, "esquive", si=lambda e: e["bouclier"] is None),
    # Et surtout : bouger pendant que quelque chose peut te toucher. Encaisser
    # seul ne suffit pas à la faire monter — encaisser est ce qui tue.
    Regle(events.PAS, "esquive",
          si=lambda e: e.get("menace") and e.get("bouclier") is None),
    Regle(events.REPOS, "recuperation"),
    Regle(events.USAGE_OBJET, "@objet"),
    Regle(events.JET, "jet"),
    Regle(events.JET, "@objet", si=lambda e: e["cible"] is not None),
)


def regles_par_evenement(regles=REGLES):
    table = {}
    for regle in regles:
        table.setdefault(regle.evenement, []).append(regle)
    return table


# --------------------------------------------------------------------------
# L'état de compétences d'un run
# --------------------------------------------------------------------------
class SkillSet:
    """Niveaux et XP du héros. Détruit avec le run — rien ici ne survit."""

    def __init__(self, catalogue=None):
        self.catalogue = catalogue if catalogue is not None else CATALOGUE
        self.levels = {}         # clé -> niveau atteint
        self.xp = {}             # clé -> XP accumulée dans le niveau courant

    # --- consultation ---------------------------------------------------
    def level(self, key):
        return self.levels.get(key, 0)

    def progress(self, key):
        """(xp dans le niveau, xp nécessaire) pour la barre de progression."""
        competence = self.catalogue.get(key)
        if competence is None:
            return (0, 0)
        return (self.xp.get(key, 0), competence.cost(self.level(key)))

    def total_levels(self):
        return sum(self.levels.values())

    def known(self):
        """Compétences déjà pratiquées, les plus hautes d'abord."""
        pratiquees = [k for k in self.levels if k in self.catalogue]
        return sorted(pratiquees,
                      key=lambda k: (-self.levels[k], self.catalogue[k].name))

    # --- gain -----------------------------------------------------------
    def gain(self, key, amount=1):
        """Ajoute de l'XP. Renvoie la liste des niveaux franchis."""
        competence = self.catalogue.get(key)
        if competence is None or amount <= 0:
            return []
        niveau = self.levels.get(key, 0)
        acquis = self.xp.get(key, 0) + amount
        franchis = []
        while acquis >= competence.cost(niveau):
            acquis -= competence.cost(niveau)
            niveau += 1
            franchis.append(niveau)
        self.levels[key] = niveau
        self.xp[key] = round(acquis, 3)     # le multiplicateur donne des flottants
        return franchis

    # --- bonus ----------------------------------------------------------
    def bonus(self, effet, familles=()):
        """Somme d'un effet : compétences permanentes + familles équipées."""
        total = 0
        for key, niveau in self.levels.items():
            competence = self.catalogue.get(key)
            if competence is None or not niveau:
                continue
            if competence.scope == EQUIPEMENT and key not in familles:
                continue
            total += competence.bonus(effet, niveau)
        return total


# --------------------------------------------------------------------------
# L'auditeur qui transforme les actions en XP
# --------------------------------------------------------------------------
class Trainer:
    """Branché sur `Game.listeners`, il traduit les évènements en XP."""

    def __init__(self, regles=REGLES, catalogue=None):
        self.table = regles_par_evenement(regles)
        self.catalogue = catalogue if catalogue is not None else CATALOGUE

    def __call__(self, game, event):
        competences = game.player.skills
        multiplicateur = game.xp_multiplier()
        for regle in self.table.get(event.nom, ()):
            cle = regle.resoudre(event)
            if cle is None:
                continue
            for niveau in competences.gain(cle, regle.xp * multiplicateur):
                nom = self.catalogue[cle].name
                game.say(f"{nom} niveau {niveau} !")
