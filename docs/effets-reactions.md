# Chantier 2 — deux formes possibles pour les effets

**Rien n'est codé.** Ce document compare deux façons de remplacer `EFFETS` par
un système de réactions, et confronte chacune aux onze effets existants. La
décision revient au joueur ; la migration se fera ensuite à comportement
identique, empreinte md5 sur huit parties scriptées à l'appui.

## Ce qu'on a aujourd'hui, exactement

Onze effets, **treize points de lecture**, tous de la même forme :
`porteur.bonus("nom")`.

| effet | lu dans | forme du calcul |
|---|---|---|
| `pv_max` | `entities.py:44` | `base + bonus` |
| `attaque` | `entities.py:152` | `int(base + arme + bonus)` |
| `defense` | `entities.py:157` | `int(base + bouclier + bonus)` |
| `endurance` | `game.py:278` | `max(0.25, creuse − bonus)` — **soustraction avec plancher** |
| `regeneration` | `game.py:325` | `config − bonus` |
| `esquive` | `game.py:504` | `min(0.55, bonus)` — **probabilité avec plafond** |
| `chance` | `game.py:570` | `min(plafond, 0.22 + bonus)` |
| `degats_jet` | `game.py:875`, `items.py:299` | `power + bonus` |
| `soin` | `items.py:211` | `power + bonus` |
| `satiete` | `items.py:232` | `power + bonus` |
| `duree_effet` | `items.py:262` | `10 + bonus` |

Deux choses à retenir avant de choisir :

1. **Le nombre de points de lecture ne grandit pas avec le contenu.** Il
   grandit avec le nombre d'endroits où le moteur calcule un nombre. Il y en a
   treize, et une hache n'en ajoutera aucun.
2. **Les bornes vivent au point de lecture**, pas dans l'effet. Le plancher de
   la faim et le plafond d'esquive ne sont pas des sommes : c'est la raison
   pour laquelle « tout additionner ailleurs » ne suffit pas.

Et ce que le système ne sait pas exprimer du tout, aujourd'hui : un effet qui
dépend de **la cible**. « +50 % contre le métal » n'a nulle part où se poser —
`bonus("attaque")` ne sait pas qui on frappe. C'est le besoin du chantier 3.

---

## Forme A — le moteur pose une question, les effets répondent

Les treize points de lecture deviennent treize **questions nommées**. Une
question porte son contexte et sa borne ; les réactions y répondent sans savoir
d'où elle vient.

```python
# au point de lecture, dans le moteur
degats = self.demander(questions.ATTAQUE, self.base_attack + equipement,
                       porteur=self, cible=defenseur, arme=arme)
```

```python
# les effets, en données
@repond(questions.ATTAQUE)
def carrure(q):
    q.ajouter(q.porteur.niveau("combat") * 0.5)

@repond(questions.ATTAQUE)
def tranchant_contre_la_chair(q):
    if q.arme and q.arme.matiere == "argent" and q.cible.famille == "chair":
        q.multiplier(1.5)
```

Une question est un petit objet : une valeur de départ, `ajouter`,
`multiplier`, et un `borner(mini, maxi)` déclaré à la création. Les effets
**déclenchés** restent ce qu'ils sont déjà — des règles sur un évènement de
fait — mais elles peuvent maintenant agir, pas seulement créditer de l'XP.

### Les cinq effets témoins

| effet | en forme A |
|---|---|
| `attaque` | `@repond(ATTAQUE): q.ajouter(niveau)` |
| `endurance` | `demander(FAIM, creuse, borne=(0.25, None))` puis `q.retirer(niveau × 0.03)` |
| `esquive` | `demander(ESQUIVE, 0, borne=(0, 0.55))` puis `q.ajouter(niveau × 0.09)` |
| `chance` | `demander(BUTIN, 0.22, borne=(0, 0.60))` puis `q.ajouter(niveau × 0.03)` |
| `regeneration` | `demander(REPOS, config.rest_regen_interval)` puis `q.retirer(niveau × 0.25)` |

### Ce que ça rend gratuit

- **Tout effet contextuel.** Affinité de matière, « +2 contre ce qui vole »,
  « le bouclier ne sert à rien contre le feu » : la question porte l'attaquant,
  la cible, l'arme. Zéro ligne de moteur. C'est précisément ce que le chantier
  3 demande.
- **Les multiplicateurs.** Aujourd'hui tout est additif parce que le point de
  lecture l'est. Un effet peut multiplier sans qu'on touche au moteur.
- **Les conditions.** `si=lambda` existe déjà pour l'XP ; il devient disponible
  pour les bonus.

### Ce que ça rend plus lourd

- **Treize appels à réécrire**, et chacun doit nommer son contexte. C'est le
  gros de la migration, et c'est fait une fois.
- **Le coût d'exécution.** Une question par calcul d'attaque au lieu d'une
  somme sur un dictionnaire. Mesurable, à surveiller sur les campagnes de bot.
- **Un effet dont le moteur ne pose pas la question reste impossible.** La
  forme A ne supprime pas la frontière, elle la déplace : d'« un point de
  lecture par effet » à « une question par endroit où un nombre se calcule ».

### Passifs et déclenchés

**Un seul mécanisme, deux familles de noms.** Une réaction s'abonne à un nom :
si c'est une question, elle répond ; si c'est un fait, elle agit. Même table,
même `si=`, même déclaration.

### Dix effets sur le même nom

- **Ordre** : `ajouter` avant `multiplier` avant `borner`, en deux passes. À
  l'intérieur d'une passe l'ordre n'existe pas — l'addition et la
  multiplication sont commutatives, donc deux effets ne peuvent pas se disputer
  la priorité.
- **Cascades** : impossibles par construction. **Une réponse à une question n'a
  pas le droit d'émettre un fait.** Elle lit et contribue, elle ne mute rien.
  C'est la propriété qui rend la forme A sûre sans garde-fou.
- **Boucles** : il n'y en a pas côté questions. Côté faits, voir plus bas — le
  problème est le même dans les deux formes.

---

## Forme B — l'effet agit, et les passifs sont un instantané

Deux mécanismes assumés, séparés :

- **`CONTRIBUTIONS`** — les passifs. Un instantané des stats, recalculé quand
  quelque chose change (niveau gagné, équipement changé). `joueur.attaque` est
  un champ, plus un calcul.
- **`REACTIONS`** — les déclenchés. Une réaction écoute un fait et **fait
  quelque chose** : soigner, blesser, poser un statut, ouvrir une porte.

```python
@contribue("attaque")
def carrure(joueur):
    return joueur.niveau("combat") * 0.5

@reagit(events.MONSTRE_VAINCU)
def vampirisme(jeu, e):
    jeu.player.heal(2)
```

### Les cinq effets témoins

| effet | en forme B |
|---|---|
| `attaque` | une contribution — l'instantané l'absorbe sans rien changer |
| `endurance` | une contribution, **mais le plancher de 0,25 reste dans le moteur** |
| `esquive` | une contribution, **mais le plafond de 0,55 reste dans le moteur** |
| `chance` | idem — la borne ne rentre pas dans l'instantané |
| `regeneration` | une contribution |

### Ce que ça rend gratuit

- **Les pouvoirs qui font quelque chose.** « Quand une créature meurt, soigne »,
  « au troisième coup encaissé, repousse » : c'est le cœur de la densité
  combinatoire visée, et la forme B l'exprime directement.
- **La lecture.** `joueur.attaque` devient un champ. Plus aucun calcul dans les
  chemins chauds.

### Ce que ça rend plus lourd

- **L'invalidation de l'instantané.** Il faut le recalculer au bon moment, et
  un oubli donne un bonus fantôme qui ne se voit pas — le genre de bug qui
  survit trois étapes. C'est le vrai coût de cette forme.
- **Les bornes restent dans le moteur.** Les cinq effets témoins le montrent :
  trois des cinq gardent un morceau de logique au point de lecture.
- **Les effets contextuels ne rentrent pas.** Un instantané ne connaît pas la
  cible. « +50 % contre le métal » demanderait une « contribution
  contextuelle » — c'est-à-dire la forme A, réinventée à côté.

### Passifs et déclenchés

**Deux mécanismes distincts**, et c'est explicite : deux tables, deux
décorateurs, deux façons d'écrire. Plus simple à lire séparément, plus lourd à
apprendre — et la frontière est floue dès qu'un pouvoir est « passif mais
conditionnel ».

### Dix effets sur le même fait

- **Ordre** : l'ordre de déclaration dans la table. Déterministe, mais
  fragile — déplacer une ligne change le jeu.
- **Cascades** : réelles, et voulues (un soin peut réveiller autre chose).
  Garde-fou nécessaire : un compteur de profondeur sur le bus, et une réaction
  qui ne peut pas se redéclencher sur l'évènement qu'elle a elle-même émis.
- **Boucles** : le vrai risque. « Tuer soigne » + « être soigné blesse » +
  « être blessé peut tuer » ferme la boucle. Le compteur de profondeur la
  coupe, mais silencieusement : il faudra que ça se voie dans le journal.

---

## Ce que je recommande, et pourquoi

**La forme A**, pour une raison qui n'est pas une préférence de style : les
onze effets existants sont tous des **nombres lus dans un calcul**, et les cinq
témoins montrent que trois d'entre eux portent une borne qui n'est pas une
somme. La forme B les recopie sans les capturer ; la forme A capture les trois.

Et surtout : le chantier 3 demande « affinité contre une famille de créature ».
C'est un effet qui dépend de la cible. La forme A le rend gratuit ; la forme B
oblige à lui inventer un mécanisme de plus.

**Mais la forme B fait mieux ce que la forme A fait mal** — les pouvoirs qui
agissent. D'où la troisième possibilité, si tu la veux :

**A d'abord, B ensuite.** Migrer les onze effets en questions (comportement
identique, empreinte md5), et ne poser les réactions-qui-agissent que le jour
où un pouvoir les demandera vraiment. Le bus existe déjà pour ça ; il ne lui
manque que le droit d'agir, et ce droit n'a pas besoin d'être pris maintenant.

Le risque de tout faire d'un coup est connu et documenté deux fois dans le
plan : un mécanisme ajouté avant le contenu qui le justifie se règle à
l'aveugle.
