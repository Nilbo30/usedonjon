"""Ce que chaque matière mord, et ce sur quoi elle glisse.

La matière d'une arme ne porte **aucun chiffre** — c'est la forme qui donne
l'attaque (voir `items.FORMES`). Ce qu'elle porte, c'est une rencontre : la
matière face à la **famille** de la créature.

    épée en argent  ×  animal      →  ×1,3
    épée en bois    ×  homoncule   →  ×0,7

Le même tableau sert deux fois, et c'est ce qui fait de la matière un
**engagement de run** plutôt qu'un choix par emplacement : l'arme s'en sert
pour mordre, le bouclier pour encaisser. Assortir les deux, c'est décider de
ce qu'on sait affronter.

## Le pivot est offert par la profondeur, pas par une règle

Les animaux peuplent le haut du donjon, les homoncules le bas (voir
`monsters.FAMILLES`). Une matière forte contre le vivant est donc forte tôt et
**faible en profondeur** : l'argent règne jusqu'à l'étage dix et glisse sur tout
ce qui vient après, le fer fait l'inverse.

Personne n'a écrit « le pivot doit coûter ». Il coûte parce qu'au moment où
l'argent cesse de mordre, la compétence d'argent est haute et celle de fer est
à zéro — et parce que traverser quelques étages affaibli se paie en ventre,
donc en profondeur. C'est exactement ce que demandait le brief : le levier est
le danger, jamais une pénalité de changement.

## Ce que ça ne fait pas

Aucune ligne de moteur. Les deux interceptions ci-dessous répondent à des
questions que le moteur pose déjà depuis l'étape 17.1, et elles lisent le
contexte que la question porte — l'arme, le bouclier, la cible. C'était le
besoin annoncé du chantier, et il est servi tel quel.
"""

from . import questions

#: matière → famille de créature → multiplicateur.
#: Une ligne se lit comme un caractère : le bois ne mord rien de particulier et
#: glisse sur le métal ; l'argent aime la chair et déteste le fabriqué ; le fer
#: est son exact contraire ; le bronze est le compromis du début ;
#: l'obsidienne tranche tout ce qui vit sans rien pouvoir contre l'assemblé.
AFFINITES = {
    "bois":       {"animal": 1.0, "humanoide": 1.0, "homoncule": 0.7},
    "bronze":     {"animal": 1.1, "humanoide": 1.0, "homoncule": 0.9},
    "fer":        {"animal": 1.0, "humanoide": 1.1, "homoncule": 1.3},
    "argent":     {"animal": 1.3, "humanoide": 1.2, "homoncule": 0.8},
    "obsidienne": {"animal": 1.2, "humanoide": 1.3, "homoncule": 1.0},
}


def multiplicateur(matiere, famille):
    """Ce que cette matière vaut contre cette famille. 1 quand l'une manque."""
    return AFFINITES.get(matiere, {}).get(famille, 1.0)


def _famille(acteur):
    espece = getattr(acteur, "species", None)
    return espece.get("famille") if espece else None


@questions.intercepte(questions.ATTAQUE)
def la_matiere_mord_ou_glisse(question):
    """Les deux côtés du coup, sur la seule question qui connaît les deux partis.

    L'arme de celui qui frappe mord la famille d'en face ; le bouclier de
    celui qui encaisse la repousse. Le second aurait dû vivre sur la question
    `DEFENSE` — mais `Actor.defense` est une **propriété**, lue sans savoir qui
    attaque, et lui apprendre l'attaquant coûterait une ligne de moteur pour un
    effet qu'on obtient ici sans rien. Mesuré avant d'être décidé ; à revoir si
    le jour vient où la défense doit connaître la scène.

    Rien ne s'applique hors combat : l'attaque se lit aussi pour la fiche du
    héros, et un multiplicateur y serait un mensonge d'affichage.
    """
    cible = question.get("cible")
    if cible is None:
        return
    arme = question.get("arme")
    if arme is not None:
        question.multiplier(multiplicateur(arme.type.matiere, _famille(cible)))
    bouclier = getattr(cible, "shield", None)
    famille_attaquant = _famille(question.porteur)
    if bouclier is not None and famille_attaquant is not None:
        question.multiplier(1 / multiplicateur(bouclier.type.matiere,
                                               famille_attaquant))
