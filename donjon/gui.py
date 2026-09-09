"""Affichage graphique (tkinter), jouable à la souris ou au clavier.

tkinter est livré avec Python : aucune installation supplémentaire. Comme
l'interface curses, ce fichier ne contient AUCUNE règle de jeu — il lit l'état
et appelle les commandes `game.cmd_*`.

Les formes sont dessinées à la main (rectangles, ovales, polygones) : pas
d'images à charger, mais la structure est prête à accueillir des sprites PNG
plus tard (tkinter sait afficher des PhotoImage).

Souris : un clic sur une case adjacente s'y déplace ou attaque, un clic plus
loin lance un déplacement automatique (calculé par le BFS de path.py) qui
s'interrompt dès qu'un monstre apparaît. Les boutons du bas et le sac sont
entièrement cliquables ; le survol décrit ce qu'il y a sous le curseur.
"""

import textwrap
import tkinter as tk

from . import items as items_mod
from . import path
from . import skills as skills_mod
from .game import PLAYING, WON, Game
from .geom import DIRECTIONS, chebyshev, step_toward

TILE = 20
HUD_HEIGHT = 46
LOG_LINES = 4
LOG_HEIGHT = 18 * LOG_LINES + 22
PAS_TRAJET_MS = 55          # vitesse du déplacement automatique

# --- palette ---------------------------------------------------------------
FOND = "#0b0b10"
SOL = "#3b3450"
SOL_POINT = "#4c4463"
COULOIR = "#2b2539"
MUR = "#565073"
MUR_HAUT = "#6f6893"
ESCALIER = "#46d17a"
JOUEUR = "#4fd1e0"
PIEGE = "#e0574f"
TEXTE = "#e8e6f0"
TEXTE_PALE = "#8e89a3"
PANNEAU = "#1d1a26"
BORDURE = "#4a4460"
BOUTON = "#2b2739"
BOUTON_SURVOL = "#3c374f"
BARRE_FOND = "#26222f"
BARRE_PV = "#5fd07a"
BARRE_PV_BAS = "#e0574f"
BARRE_VENTRE = "#e0a54f"
SURVOL = "#f0e9a8"

COULEUR_MONSTRE = "#c76b6b"
COULEUR_OBJET = {
    items_mod.HERB: "#7ad07a",
    items_mod.SCROLL: "#ded1a8",
    items_mod.FOOD: "#e0a54f",
    items_mod.WEAPON: "#c8ccd8",
    items_mod.SHIELD: "#9aa6d0",
    items_mod.AMMO: "#b89a76",
}

DIRECTION_TOUCHES = {
    "h": DIRECTIONS["w"], "l": DIRECTIONS["e"],
    "j": DIRECTIONS["s"], "k": DIRECTIONS["n"],
    "y": DIRECTIONS["nw"], "u": DIRECTIONS["ne"],
    "b": DIRECTIONS["sw"], "n": DIRECTIONS["se"],
}
DIRECTION_SYMBOLES = {
    "Left": DIRECTIONS["w"], "Right": DIRECTIONS["e"],
    "Up": DIRECTIONS["n"], "Down": DIRECTIONS["s"],
    "KP_4": DIRECTIONS["w"], "KP_6": DIRECTIONS["e"],
    "KP_8": DIRECTIONS["n"], "KP_2": DIRECTIONS["s"],
    "KP_7": DIRECTIONS["nw"], "KP_9": DIRECTIONS["ne"],
    "KP_1": DIRECTIONS["sw"], "KP_3": DIRECTIONS["se"],
}

AIDE = [
    "SOURIS",
    "  Clic sur une case voisine : s'y déplacer, ou attaquer ce qui s'y trouve.",
    "  Clic plus loin : le héros y va tout seul (il s'arrête s'il voit un monstre).",
    "  Clic sur le héros : ramasser, descendre l'escalier, ou attendre un tour.",
    "  Bouton « Se reposer » : patienter pour se soigner, au prix du ventre.",
    "  Clic droit : annuler le déplacement ou fermer un panneau.",
    "  Les boutons en bas et le sac sont cliquables.",
    "",
    "PROGRESSION",
    "  On progresse dans ce qu'on pratique : marcher entraîne la marche,",
    "  frapper entraîne l'arme en main, se reposer entraîne la récupération.",
    "  Tout est perdu à la mort.",
    "",
    "CLAVIER",
    "  Flèches, pavé numérique ou hjkl / yubn : se déplacer et attaquer.",
    "  « , » ramasser    « > » descendre    « . » attendre    « i » sac",
    "  « s » se reposer jusqu'à guérison (interrompu si un monstre paraît)",
    "  « c » compétences    « ? » cette aide    « q » quitter",
    "  « R » rejouer après la partie",
    "",
    "  Dans le sac : la lettre de l'objet, puis u utiliser, e équiper,",
    "  t lancer (puis une direction), d poser.",
]


def melange(couleur, vers, facteur):
    """Mélange deux couleurs hexadécimales (sert au brouillard de guerre)."""
    a = [int(couleur[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(vers[i:i + 2], 16) for i in (1, 3, 5)]
    c = [round(x + (y - x) * facteur) for x, y in zip(a, b)]
    return "#%02x%02x%02x" % tuple(c)


def sombre(couleur, facteur=0.62):
    """Version « déjà visitée mais hors de vue » d'une couleur."""
    return melange(couleur, FOND, facteur)


def fiche_objet(objet):
    """Effet de l'objet et compétence qu'il entraîne, en une ou deux lignes."""
    lignes = []
    if objet.description:
        lignes.append(objet.description)
    competence = skills_mod.CATALOGUE.get(objet.type.skill)
    if competence:
        lignes.append(f"S'en servir entraîne : {competence.name}")
    return lignes


class Fenetre:
    def __init__(self, seed=None, max_depth=5, tile=TILE):
        self.seed = seed
        self.max_depth = max_depth
        self.tile = tile
        self.game = Game(seed=seed, max_depth=max_depth)
        # jeu | sac | action | direction | aide | competences
        self.mode = "jeu"
        self.slot = None
        self.note = None

        # zones cliquables : (x1, y1, x2, y2, action, étiquette)
        self.zones = []
        self.zone_survolee = None  # géométrie (x1, y1, x2, y2) de la zone survolée
        self.etiquette_survolee = None
        self.ferme = False
        self.case_survolee = None
        self.destination = None    # cible du déplacement automatique
        self._trajet_prevu = None

        self.root = tk.Tk()
        self.root.title("Donjon mystère")
        self.root.configure(bg=FOND)
        self.largeur = self.game.level.width * tile
        self.hauteur = self.game.level.height * tile + HUD_HEIGHT + LOG_HEIGHT
        self.canvas = tk.Canvas(self.root, width=self.largeur, height=self.hauteur,
                                bg=FOND, highlightthickness=0)
        self.canvas.pack()
        self.root.bind("<Key>", self.on_key)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", self.on_click_droit)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", self.on_leave)
        self.root.resizable(False, False)
        self.dessiner()

    def run(self):
        self.root.mainloop()

    def quitter(self):
        self.ferme = True
        self.arreter_trajet()
        self.root.destroy()

    # ------------------------------------------------------------------ #
    # Conversions écran <-> carte
    # ------------------------------------------------------------------ #
    def _cellule(self, x, y):
        """Coin haut-gauche en pixels d'une case de la carte."""
        return x * self.tile, y * self.tile + HUD_HEIGHT

    def case_sous(self, px, py):
        """Case de la carte sous un point de l'écran, ou None."""
        if py < HUD_HEIGHT or py >= HUD_HEIGHT + self.game.level.height * self.tile:
            return None
        case = (int(px // self.tile), int((py - HUD_HEIGHT) // self.tile))
        return case if self.game.level.in_bounds(case) else None

    # ------------------------------------------------------------------ #
    # Clavier
    # ------------------------------------------------------------------ #
    def on_key(self, event):
        self.arreter_trajet()
        touche, char = event.keysym, event.char

        if self.game.state != PLAYING:
            self._fin_de_partie(char, touche)
            return

        if self.mode in ("aide", "competences"):
            self.mode = "jeu"
        elif self.mode == "jeu":
            self._touche_jeu(touche, char)
        elif self.mode == "sac":
            self._touche_sac(touche, char)
        elif self.mode == "action":
            self._touche_action(touche, char)
        elif self.mode == "direction":
            self._touche_direction(touche, char)
        if not self.ferme:
            self.dessiner()

    def _fin_de_partie(self, char, touche):
        if char.lower() == "r":
            self.rejouer()
        elif char.lower() == "q" or touche == "Escape":
            self.quitter()
        else:
            self.dessiner()

    def _touche_jeu(self, touche, char):
        direction = DIRECTION_SYMBOLES.get(touche) or DIRECTION_TOUCHES.get(char)
        if direction:
            self.game.cmd_move(direction)
        elif char == ".":
            self.game.cmd_wait()
        elif char == "s":
            self.game.cmd_rest()
        elif char == ",":
            self.game.cmd_pickup()
        elif char == ">":
            self.game.cmd_descend()
        elif char == "i":
            self.mode = "sac"
        elif char == "c":
            self.mode = "competences"
        elif char == "?":
            self.mode = "aide"
        elif char == "q" or touche == "Escape":
            self.quitter()

    def _touche_sac(self, touche, char):
        if touche == "Escape" or char == "i":
            self.mode = "jeu"
            return
        slot = ord(char.lower()) - ord("a") if char.isalpha() else -1
        if 0 <= slot < len(self.game.player.inventory):
            self.choisir_objet(slot)
        else:
            self.note = "Pas d'objet à cette lettre."

    def _touche_action(self, touche, char):
        if touche == "Escape":
            self.mode = "sac"
            return
        if char == "t":
            self.mode = "direction"
            return
        commandes = {"u": self.game.cmd_use, "e": self.game.cmd_equip,
                     "d": self.game.cmd_drop}
        if char in commandes:
            commandes[char](self.slot)
            self.mode = "jeu"

    def _touche_direction(self, touche, char):
        if touche == "Escape":
            self.mode = "sac"
            return
        direction = DIRECTION_SYMBOLES.get(touche) or DIRECTION_TOUCHES.get(char)
        if direction:
            self.lancer(direction)

    # ------------------------------------------------------------------ #
    # Souris
    # ------------------------------------------------------------------ #
    def on_click(self, event):
        """Un clic gauche : d'abord les boutons et panneaux, puis la carte."""
        for x1, y1, x2, y2, action, _ in reversed(self.zones):
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.arreter_trajet()
                action()
                if not self.ferme:
                    self.dessiner()
                return
        if self.game.state != PLAYING or self.mode in ("sac", "action", "aide",
                                                       "competences"):
            return
        case = self.case_sous(event.x, event.y)
        if case is None:
            return
        self.arreter_trajet()
        if self.mode == "direction":
            self._lancer_vers(case)
        else:
            self.clic_carte(case)
        self.dessiner()

    def on_click_droit(self, event):
        """Clic droit : tout annuler (déplacement en cours, panneau ouvert)."""
        self.arreter_trajet()
        self.mode = "jeu" if self.mode != "action" else "sac"
        self.dessiner()

    def on_motion(self, event):
        """Survol : cadre + étiquette sur la carte, surbrillance sur les boutons.

        On ne redessine tout que si la zone cliquable survolée change ; sur la
        carte, seuls les objets marqués « survol » sont refaits.
        """
        zone = self._zone_sous(event.x, event.y)
        geometrie = zone[:4] if zone else None
        case = None if zone else self.case_sous(event.x, event.y)
        if geometrie != self.zone_survolee:
            self.zone_survolee = geometrie
            self.etiquette_survolee = zone[5] if zone else None
            self.case_survolee = case
            self.dessiner()
        elif case != self.case_survolee:
            self.case_survolee = case
            self._rafraichir_survol(event.x, event.y)

    def on_leave(self, _event):
        self.case_survolee = None
        self.zone_survolee = None
        self.etiquette_survolee = None
        self.dessiner()

    def _zone_sous(self, px, py):
        for zone in reversed(self.zones):
            if zone[0] <= px <= zone[2] and zone[1] <= py <= zone[3]:
                return zone
        return None

    def clic_carte(self, case):
        """Règle simple : voisin = une action, loin = trajet automatique."""
        joueur = self.game.player
        if case == joueur.pos:
            self.action_sur_place()
            return
        if chebyshev(case, joueur.pos) == 1:
            self.game.cmd_move(step_toward(joueur.pos, case))
            return
        if self.monstres_en_vue():
            # Jamais de pilote automatique en présence d'un monstre : un pas.
            self.game.cmd_move(step_toward(joueur.pos, case))
            return
        if not self.game.level.walkable(case):
            self.note = "Impossible d'aller là."
            return
        if case not in self.game.level.explored:
            self.note = "Tu ne connais pas encore cet endroit."
            return
        self.demarrer_trajet(case)

    def action_sur_place(self):
        """Clic sur le héros : ramasser, descendre, ou attendre."""
        game = self.game
        if game.player.pos in game.level.items:
            game.cmd_pickup()
        elif game.player.pos == game.level.stairs:
            game.cmd_descend()
        else:
            game.cmd_wait()

    def monstres_en_vue(self):
        return self.game.monsters_visible()

    # --- déplacement automatique ---------------------------------------
    def demarrer_trajet(self, destination):
        chemin = path.find_path(self.game.level, self.game.player.pos, destination,
                                blocked={m.pos for m in self.game.monsters()},
                                allowed=self.game.level.explored)
        if not chemin:
            self.note = "Aucun chemin connu jusque-là."
            return
        self.destination = destination
        self.pas_trajet()

    def arreter_trajet(self):
        self.destination = None
        if self._trajet_prevu is not None:
            try:
                self.root.after_cancel(self._trajet_prevu)
            except tk.TclError:                       # pragma: no cover
                pass
            self._trajet_prevu = None

    def pas_trajet(self):
        """Un pas du trajet, puis on se replanifie tant que rien n'interrompt."""
        self._trajet_prevu = None
        if self.destination is None or self.game.state != PLAYING:
            self.arreter_trajet()
            return
        if self.monstres_en_vue():
            self.arreter_trajet()
            self.dessiner()
            return
        joueur = self.game.player
        direction = path.step_along(self.game.level, joueur.pos, self.destination,
                                    {m.pos for m in self.game.monsters()},
                                    allowed=self.game.level.explored)
        pv_avant = joueur.hp
        if direction is None or not self.game.cmd_move(direction):
            self.arreter_trajet()
            self.dessiner()
            return
        arrive = joueur.pos == self.destination
        interessant = (joueur.pos in self.game.level.items
                       or joueur.pos == self.game.level.stairs
                       or joueur.hp < pv_avant
                       or not joueur.can_act())
        if arrive or interessant:
            self.arreter_trajet()
        else:
            self._trajet_prevu = self.root.after(PAS_TRAJET_MS, self.pas_trajet)
        self.dessiner()

    # --- sac et objets à la souris --------------------------------------
    def choisir_objet(self, slot):
        self.slot = slot
        self.mode = "action"

    def utiliser(self, commande):
        commande(self.slot)
        self.mode = "jeu"

    def lancer(self, direction):
        self.game.cmd_throw(self.slot, direction)
        self.mode = "jeu"

    def _lancer_vers(self, case):
        if case == self.game.player.pos:
            self.mode = "sac"
            return
        self.lancer(step_toward(self.game.player.pos, case))

    def rejouer(self):
        self.game = Game(seed=None, max_depth=self.max_depth)
        self.mode = "jeu"
        self.slot = None
        self.destination = None
        self.dessiner()

    # ------------------------------------------------------------------ #
    # Dessin
    # ------------------------------------------------------------------ #
    def dessiner(self):
        self.canvas.delete("all")
        self.zones = []
        self._dessiner_hud()
        self._dessiner_carte()
        self._dessiner_journal()
        if self.mode in ("sac", "action", "direction"):
            self._dessiner_sac()
        elif self.mode == "aide":
            self._panneau("Aide", AIDE, bouton_fermer=True)
        elif self.mode == "competences":
            self._dessiner_competences()
        if self.game.state != PLAYING:
            self._dessiner_fin()
        if self.case_survolee:
            px, py = self._cellule(*self.case_survolee)
            self._rafraichir_survol(px + self.tile / 2, py + self.tile / 2)

    def _dessiner_carte(self):
        game, level = self.game, self.game.level
        visibles = game.visible_cells()
        for (x, y) in level.explored:
            pos = (x, y)
            vue = pos in visibles
            px, py = self._cellule(x, y)
            self._case(px, py, level.tile(pos), vue)
            piege = level.traps.get(pos)
            if piege and piege.revealed:
                self._piege(px, py, vue)
            objet = level.items.get(pos)
            if objet:
                self._objet(px, py, objet, vue)
        if self.destination and self.destination in level.explored:
            px, py = self._cellule(*self.destination)
            self.canvas.create_rectangle(px + 1, py + 1, px + self.tile - 1,
                                         py + self.tile - 1,
                                         outline=SURVOL, dash=(2, 2))
        for monstre in game.monsters():
            if monstre.pos in visibles:
                px, py = self._cellule(*monstre.pos)
                self._creature(px, py, monstre)
        px, py = self._cellule(*game.player.pos)
        self._corps(px, py, JOUEUR, "heros")

    def _case(self, px, py, tuile, vue):
        t = self.tile
        if tuile == "wall":
            fond = MUR if vue else sombre(MUR)
            self.canvas.create_rectangle(px, py, px + t, py + t,
                                         fill=fond, outline=fond)
            haut = MUR_HAUT if vue else sombre(MUR_HAUT)
            self.canvas.create_rectangle(px, py, px + t, py + 3,
                                         fill=haut, outline=haut)
            return
        if tuile == "corridor":
            fond = COULOIR if vue else sombre(COULOIR)
        else:
            fond = SOL if vue else sombre(SOL)
        self.canvas.create_rectangle(px, py, px + t, py + t,
                                     fill=fond, outline=fond)
        if tuile == "stairs":
            self._escalier(px, py, vue)
        elif tuile == "floor":
            point = SOL_POINT if vue else sombre(SOL_POINT)
            self.canvas.create_rectangle(px + t // 2, py + t // 2,
                                         px + t // 2 + 1, py + t // 2 + 1,
                                         fill=point, outline=point)

    def _escalier(self, px, py, vue):
        t = self.tile
        couleur = ESCALIER if vue else sombre(ESCALIER)
        for index in range(3):
            haut = py + 3 + index * (t - 6) // 3
            gauche = px + 3 + index * 2
            self.canvas.create_rectangle(gauche, haut, px + t - 3,
                                         haut + max(2, (t - 6) // 3 - 1),
                                         fill=couleur, outline="")

    def _piege(self, px, py, vue):
        t = self.tile
        couleur = PIEGE if vue else sombre(PIEGE)
        self.canvas.create_line(px + 4, py + 4, px + t - 4, py + t - 4,
                                fill=couleur, width=2)
        self.canvas.create_line(px + t - 4, py + 4, px + 4, py + t - 4,
                                fill=couleur, width=2)

    def _objet(self, px, py, objet, vue):
        t = self.tile
        base = COULEUR_OBJET.get(objet.category, "#cccccc")
        couleur = base if vue else sombre(base)
        cx, cy = px + t / 2, py + t / 2
        categorie = objet.category
        if categorie == items_mod.HERB:
            self.canvas.create_oval(cx - 4, cy - 5, cx + 4, cy + 2,
                                    fill=couleur, outline="")
            self.canvas.create_line(cx, cy + 1, cx, cy + 6, fill=couleur, width=2)
        elif categorie == items_mod.SCROLL:
            self.canvas.create_rectangle(cx - 4, cy - 5, cx + 4, cy + 5,
                                         fill=couleur, outline="")
            trait = melange(couleur, FOND, 0.55)
            for dy in (-2, 1):
                self.canvas.create_line(cx - 2, cy + dy, cx + 2, cy + dy, fill=trait)
        elif categorie == items_mod.FOOD:
            self.canvas.create_polygon(cx, cy - 5, cx + 5, cy + 4, cx - 5, cy + 4,
                                       fill=couleur, outline="")
        elif categorie == items_mod.WEAPON:
            self.canvas.create_line(cx - 4, cy + 4, cx + 4, cy - 4,
                                    fill=couleur, width=3)
            self.canvas.create_line(cx - 5, cy + 1, cx - 1, cy + 5,
                                    fill=melange(couleur, FOND, 0.4), width=2)
        elif categorie == items_mod.SHIELD:
            self.canvas.create_polygon(cx - 4, cy - 5, cx + 4, cy - 5,
                                       cx + 4, cy + 1, cx, cy + 5, cx - 4, cy + 1,
                                       fill=couleur, outline="")
        else:                                   # projectiles
            self.canvas.create_line(cx - 4, cy + 4, cx + 4, cy - 4,
                                    fill=couleur, width=2)
            self.canvas.create_polygon(cx + 4, cy - 4, cx + 1, cy - 3, cx + 3, cy - 1,
                                       fill=couleur, outline="")

    def _creature(self, px, py, monstre):
        couleur = monstre.species.get("color", COULEUR_MONSTRE)
        forme = monstre.species.get("shape", "rond")
        self._corps(px, py, couleur, forme)
        if monstre.has_status("endormi"):
            self._bulle(px, py, "z")
        elif monstre.has_status("confus"):
            self._bulle(px, py, "?")

    def _corps(self, px, py, couleur, forme):
        t = self.tile
        cx, cy = px + t / 2, py + t / 2
        r = t / 2 - 2
        if forme == "carre":
            self.canvas.create_rectangle(cx - r, cy - r + 1, cx + r, cy + r,
                                         fill=couleur, outline="")
        elif forme == "pointu":
            self.canvas.create_polygon(cx, cy - r, cx + r, cy + r, cx - r, cy + r,
                                       fill=couleur, outline="")
        elif forme == "heros":
            self.canvas.create_oval(cx - r, cy - r + 1, cx + r, cy + r,
                                    fill=couleur, outline="#ffffff")
        else:
            self.canvas.create_oval(cx - r, cy - r + 1, cx + r, cy + r,
                                    fill=couleur, outline="")
        oeil = 1.6 if t >= 18 else 1.2
        for dx in (-r / 2.4, r / 2.4):
            self.canvas.create_oval(cx + dx - oeil, cy - oeil - 1,
                                    cx + dx + oeil, cy + oeil - 1,
                                    fill="#12111a", outline="")

    def _bulle(self, px, py, texte):
        self.canvas.create_text(px + self.tile - 3, py + 3, text=texte,
                                fill="#ffffff", anchor="ne",
                                font=("TkDefaultFont", 8, "bold"))

    # --- survol ---------------------------------------------------------
    def _rafraichir_survol(self, px, py):
        """Cadre + étiquette sous le curseur, sans redessiner toute la scène."""
        self.canvas.delete("survol")
        case = self.case_survolee
        if case is None or case not in self.game.level.explored:
            return
        cx, cy = self._cellule(*case)
        self.canvas.create_rectangle(cx, cy, cx + self.tile, cy + self.tile,
                                     outline=SURVOL, tags="survol")
        lignes = self.description(case)
        if not lignes:
            return
        largeur = min(self.largeur - 12,
                      max(len(ligne) for ligne in lignes) * 6.4 + 16)
        hauteur = 8 + len(lignes) * 15
        gauche = max(4, min(px + 14, self.largeur - largeur - 4))
        haut = max(4, min(py + 14, self.hauteur - hauteur - 4))
        self.canvas.create_rectangle(gauche, haut, gauche + largeur,
                                     haut + hauteur, fill=PANNEAU,
                                     outline=BORDURE, tags="survol")
        for index, ligne in enumerate(lignes):
            self.canvas.create_text(gauche + 8, haut + 12 + index * 15, text=ligne,
                                    anchor="w", tags="survol",
                                    fill=TEXTE if index == 0 else TEXTE_PALE,
                                    font=("TkDefaultFont", 9,
                                          "bold" if index == 0 else "normal"))

    def description(self, case):
        """Ce qu'il y a sur une case, en une à trois lignes (étiquette de survol)."""
        game, level = self.game, self.game.level
        objet = level.items.get(case)
        if case == game.player.pos:
            if objet:
                return [f"Toi — clic pour ramasser {objet.name}"] + fiche_objet(objet)
            if case == level.stairs:
                return ["Toi — clic pour descendre l'escalier"]
            lignes = ["Toi — clic pour attendre un tour"]
            if game.player.hp < game.player.max_hp:
                lignes.append("« s » ou le bouton pour te reposer jusqu'à "
                              "guérison.")
            return lignes
        if case in game.visible_cells():
            monstre = game.actor_at(case)
            if monstre:
                statuts = monstre.status_line()
                lignes = [f"{monstre.name} — PV {monstre.hp}/{monstre.max_hp}"
                          f" · atq {monstre.attack} · déf {monstre.defense}"]
                if statuts:
                    lignes.append(statuts)
                return lignes
        if objet:
            return [objet.name] + fiche_objet(objet)
        piege = level.traps.get(case)
        if piege and piege.revealed:
            return [piege.name, "Marcher dessus le déclenche."]
        if case == level.stairs:
            return ["Escalier vers l'étage suivant"]
        if not level.walkable(case):
            return ["Mur"]
        return []

    # --- HUD, journal, boutons -------------------------------------------
    def _dessiner_hud(self):
        joueur = self.game.player
        self.canvas.create_rectangle(0, 0, self.largeur, HUD_HEIGHT,
                                     fill="#16141d", outline="")
        self._texte(10, 8, f"Étage {self.game.depth}", gras=True)
        self._texte(10, 26, f"Comp. {joueur.skills.total_levels()}", pale=True)

        self._barre(95, 10, 110, joueur.hp, joueur.max_hp,
                    BARRE_PV if joueur.hp > joueur.max_hp * 0.3 else BARRE_PV_BAS,
                    f"PV {joueur.hp}/{joueur.max_hp}")
        self._barre(95, 27, 110, joueur.fullness, joueur.max_fullness,
                    BARRE_VENTRE, f"Ventre {joueur.fullness}")

        arme = joueur.weapon.name if joueur.weapon else "mains nues"
        bouclier = joueur.shield.name if joueur.shield else "aucun"
        self._texte(320, 8, f"Attaque {joueur.attack}    Défense {joueur.defense}")
        self._texte(320, 26, f"{arme}  |  {bouclier}", pale=True)

        statuts = joueur.status_line()
        if statuts:
            self._texte(self.largeur - 10, 8, statuts, ancre="ne", couleur="#e0a54f")

    def _barre(self, x, y, largeur, valeur, maximum, couleur, legende):
        """Jauge + légende posée à droite (lisible quelle que soit la valeur)."""
        hauteur = 12
        self.canvas.create_rectangle(x, y, x + largeur, y + hauteur,
                                     fill=BARRE_FOND, outline="")
        part = max(0, min(1, valeur / maximum if maximum else 0))
        if part > 0:
            self.canvas.create_rectangle(x, y, x + largeur * part, y + hauteur,
                                         fill=couleur, outline="")
        self.canvas.create_text(x + largeur + 8, y + hauteur / 2, text=legende,
                                anchor="w", fill=TEXTE,
                                font=("TkDefaultFont", 9, "bold"))

    def _dessiner_journal(self):
        haut = HUD_HEIGHT + self.game.level.height * self.tile
        self.canvas.create_rectangle(0, haut, self.largeur, haut + LOG_HEIGHT,
                                     fill="#16141d", outline="")
        lignes = self.game.log.tail(LOG_LINES)
        if self.note:
            lignes = (lignes + [self.note])[-LOG_LINES:]
            self.note = None
        for index, ligne in enumerate(lignes):
            dernier = index == len(lignes) - 1
            self._texte(10, haut + 6 + index * 18, ligne, pale=not dernier)
        if self.game.state == PLAYING:
            self._barre_de_boutons(haut + LOG_HEIGHT - 32)

    def _barre_de_boutons(self, y):
        """Tout ce qui se fait au clavier se fait aussi d'un clic."""
        joueur, level = self.game.player, self.game.level
        boutons = [
            ("Ramasser", self.game.cmd_pickup, joueur.pos in level.items),
            ("Descendre", self.game.cmd_descend, joueur.pos == level.stairs),
            ("Attendre", self.game.cmd_wait, True),
            ("Se reposer", self.game.cmd_rest,
             joueur.hp < joueur.max_hp and not self.game.monsters_visible()),
            ("Sac", lambda: setattr(self, "mode", "sac"), True),
            ("Compétences", lambda: setattr(self, "mode", "competences"), True),
            ("Aide", lambda: setattr(self, "mode", "aide"), True),
        ]
        # Chaque bouton est dimensionné par son texte : ajouter une commande
        # plus tard ne fera pas déborder la barre.
        tailles = [max(78, len(texte) * 7 + 18) for texte, _, _ in boutons]
        x = self.largeur - 10 - sum(tailles) - 6 * (len(boutons) - 1)
        for (texte, action, actif), largeur in zip(boutons, tailles):
            self._bouton(x, y, largeur, 26, texte, action, actif)
            x += largeur + 6

    def _bouton(self, x, y, largeur, hauteur, texte, action, actif=True):
        zone = (x, y, x + largeur, y + hauteur, action, texte)
        survole = self.zone_survolee == zone[:4]
        fond = BOUTON_SURVOL if (survole and actif) else BOUTON
        self.canvas.create_rectangle(x, y, x + largeur, y + hauteur,
                                     fill=fond if actif else "#211e2b",
                                     outline=BORDURE if actif else "#2f2b3a")
        self.canvas.create_text(x + largeur / 2, y + hauteur / 2, text=texte,
                                fill=TEXTE if actif else TEXTE_PALE,
                                font=("TkDefaultFont", 9, "bold" if actif else "normal"))
        if actif:
            self.zones.append(zone)

    def _texte(self, x, y, texte, pale=False, gras=False, ancre="nw", couleur=None):
        self.canvas.create_text(
            x, y, text=texte, anchor=ancre,
            fill=couleur or (TEXTE_PALE if pale else TEXTE),
            font=("TkDefaultFont", 10, "bold" if gras else "normal"))

    # --- panneaux --------------------------------------------------------
    def _objet_decrit(self):
        """L'objet dont on montre la fiche : le survolé, sinon le sélectionné."""
        inventaire = self.game.player.inventory
        index = None
        if self.mode == "sac":
            etiquette = self.etiquette_survolee or ""
            if etiquette.startswith("objet "):
                index = int(etiquette.split()[1])
        else:
            index = self.slot
        if index is not None and 0 <= index < len(inventaire):
            return inventaire[index]
        return None

    def _dessiner_sac(self):
        joueur = self.game.player
        if not joueur.inventory:
            self._panneau("Sac", ["Ton sac est vide."], bouton_fermer=True)
            return
        titres = {
            "sac": "Sac — clique ou survole un objet (ou tape sa lettre)",
            "action": "Que faire de cet objet ?",
            "direction": "Clique la cible du jet (ou une direction au clavier)",
        }
        objet_decrit = self._objet_decrit()
        fiche = []
        for ligne in fiche_objet(objet_decrit) if objet_decrit else []:
            fiche += textwrap.wrap(ligne, 64) or [""]
        if not fiche:
            fiche = ["Survole un objet pour savoir ce qu'il fait."]

        lignes = len(joueur.inventory)
        largeur = 520
        hauteur = 74 + lignes * 24 + 14 + len(fiche) * 16 + 44
        gauche = (self.largeur - largeur) / 2
        haut = (HUD_HEIGHT + self.game.level.height * self.tile - hauteur) / 2
        self.canvas.create_rectangle(gauche, haut, gauche + largeur, haut + hauteur,
                                     fill=PANNEAU, outline=BORDURE, width=2)
        self._texte(gauche + 16, haut + 14, titres[self.mode], gras=True)

        for index, objet in enumerate(joueur.inventory):
            y = haut + 44 + index * 24
            choisi = index == self.slot and self.mode != "sac"
            self._ligne_objet(gauche + 12, y, largeur - 24, index, objet, choisi)

        # Fiche de l'objet : à quoi il sert, et ce que son usage entraîne.
        y_fiche = haut + 50 + lignes * 24
        self.canvas.create_line(gauche + 12, y_fiche, gauche + largeur - 12, y_fiche,
                                fill=BORDURE)
        for index, ligne in enumerate(fiche):
            self._texte(gauche + 16, y_fiche + 8 + index * 16, ligne,
                        pale=objet_decrit is None or index > 0)

        y_actions = y_fiche + 14 + len(fiche) * 16
        if self.mode == "action":
            actions = [("Utiliser", lambda: self.utiliser(self.game.cmd_use)),
                       ("Équiper", lambda: self.utiliser(self.game.cmd_equip)),
                       ("Lancer", lambda: setattr(self, "mode", "direction")),
                       ("Poser", lambda: self.utiliser(self.game.cmd_drop))]
            x = gauche + 12
            for texte, action in actions:
                self._bouton(x, y_actions, 92, 26, texte, action)
                x += 96
        else:
            aide = ("Clique une case pour viser."
                    if self.mode == "direction" else
                    "u utiliser · e équiper · t lancer · d poser")
            self._texte(gauche + 16, y_actions + 6, aide, pale=True)
        self._bouton(gauche + largeur - 92, haut + hauteur - 36, 80, 26,
                     "Fermer", lambda: setattr(self, "mode", "jeu"))

    def _ligne_objet(self, x, y, largeur, index, objet, choisi):
        equipe = objet is self.game.player.weapon or objet is self.game.player.shield
        zone = (x, y, x + largeur, y + 22)
        survole = self.zone_survolee == zone
        if choisi or survole:
            self.canvas.create_rectangle(*zone, fill=BOUTON_SURVOL if survole
                                         else BOUTON, outline="")
        couleur = COULEUR_OBJET.get(objet.category, "#cccccc")
        self.canvas.create_oval(x + 8, y + 7, x + 16, y + 15,
                                fill=couleur, outline="")
        self._texte(x + 26, y + 4, f"{chr(ord('a') + index)})  {objet.name}")
        if equipe:
            self._texte(x + largeur - 10, y + 4, "équipé", ancre="ne", pale=True)
        self.zones.append((*zone, lambda i=index: self.choisir_objet(i),
                           f"objet {index}"))

    def _panneau(self, titre, lignes, bouton_fermer=False):
        hauteur_carte = self.game.level.height * self.tile + HUD_HEIGHT
        largeur = min(self.largeur - 60,
                      max([len(titre)] + [len(l) for l in lignes]) * 7 + 50)
        hauteur = 54 + len(lignes) * 19 + (36 if bouton_fermer else 0)
        gauche = (self.largeur - largeur) / 2
        haut = (hauteur_carte - hauteur) / 2
        self.canvas.create_rectangle(gauche, haut, gauche + largeur, haut + hauteur,
                                     fill=PANNEAU, outline=BORDURE, width=2)
        self._texte(gauche + 16, haut + 14, titre, gras=True)
        for index, ligne in enumerate(lignes):
            self._texte(gauche + 16, haut + 40 + index * 19, ligne)
        if bouton_fermer:
            self._bouton(gauche + largeur - 92, haut + hauteur - 34, 80, 26,
                         "Fermer", lambda: setattr(self, "mode", "jeu"))

    def _dessiner_competences(self):
        """Panneau des compétences : niveau et progression vers le suivant."""
        lignes = self.game.skill_lines()
        if not lignes:
            self._panneau("Compétences",
                          ["Tu n'as encore rien pratiqué.",
                           "Marche, frappe, mange : tout s'apprend à l'usage."],
                          bouton_fermer=True)
            return
        largeur, hauteur = 430, 78 + len(lignes) * 26
        gauche = (self.largeur - largeur) / 2
        haut = (HUD_HEIGHT + self.game.level.height * self.tile - hauteur) / 2
        self.canvas.create_rectangle(gauche, haut, gauche + largeur,
                                     haut + hauteur, fill=PANNEAU,
                                     outline=BORDURE, width=2)
        self._texte(gauche + 16, haut + 14, "Compétences de ce run", gras=True)
        for index, (nom, niveau, acquis, requis) in enumerate(lignes):
            y = haut + 44 + index * 26
            self._texte(gauche + 16, y, f"{nom}")
            self._texte(gauche + 190, y, f"niv. {niveau}", gras=True)
            self._barre(gauche + 250, y + 2, 90, acquis, requis,
                        BARRE_PV, f"{acquis}/{requis}")
        self._bouton(gauche + largeur - 92, haut + hauteur - 36, 80, 26,
                     "Fermer", lambda: setattr(self, "mode", "jeu"))

    def _dessiner_fin(self):
        self.canvas.create_rectangle(0, 0, self.largeur, self.hauteur,
                                     fill="#000000", stipple="gray75", outline="")
        gagne = self.game.state == WON
        titre = "VICTOIRE !" if gagne else "TU ES MORT"
        couleur = ESCALIER if gagne else PIEGE
        cx, cy = self.largeur / 2, self.hauteur / 2
        self.canvas.create_rectangle(cx - 210, cy - 76, cx + 210, cy + 76,
                                     fill=PANNEAU, outline=couleur, width=2)
        self.canvas.create_text(cx, cy - 40, text=titre, fill=couleur,
                                font=("TkDefaultFont", 28, "bold"))
        detail = (f"Étage {self.game.depth} · "
                  f"{self.game.player.skills.total_levels()} niveaux de "
                  f"compétences · {self.game.turn} tours")
        self.canvas.create_text(cx, cy - 2, text=detail, fill=TEXTE,
                                font=("TkDefaultFont", 12))
        self._bouton(cx - 150, cy + 26, 140, 30, "Rejouer (R)", self.rejouer)
        self._bouton(cx + 10, cy + 26, 140, 30, "Quitter (q)", self.quitter)


def run(seed=None, max_depth=5, tile=TILE):
    Fenetre(seed=seed, max_depth=max_depth, tile=tile).run()
