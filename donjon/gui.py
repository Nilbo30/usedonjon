"""Affichage graphique (tkinter). Dessine le même jeu que l'UI texte.

tkinter est livré avec Python : aucune installation supplémentaire. Comme
l'interface curses, ce fichier ne contient AUCUNE règle de jeu — il lit l'état
et appelle les commandes `game.cmd_*`.

Les formes sont dessinées à la main (rectangles, ovales, polygones) : pas
d'images à charger, mais la structure est prête à accueillir des sprites PNG
plus tard (tkinter sait afficher des PhotoImage).
"""

import tkinter as tk

from . import items as items_mod
from .game import DEAD, PLAYING, WON, Game
from .geom import DIRECTIONS

TILE = 20
HUD_HEIGHT = 46
LOG_LINES = 4
LOG_HEIGHT = 18 * LOG_LINES + 10

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
BARRE_FOND = "#26222f"
BARRE_PV = "#5fd07a"
BARRE_PV_BAS = "#e0574f"
BARRE_VENTRE = "#e0a54f"

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
    "Flèches ou hjkl / yubn : se déplacer, foncer sur un monstre pour l'attaquer",
    "« , » ramasser      « > » descendre l'escalier      « . » attendre",
    "« i » ouvrir le sac       « ? » cette aide       « q » quitter",
    "",
    "Dans le sac : la lettre de l'objet, puis",
    "u utiliser   e équiper   t lancer (puis une direction)   d poser",
    "",
    "Après la partie : R pour rejouer, q pour quitter.",
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


class Fenetre:
    def __init__(self, seed=None, max_depth=5, tile=TILE):
        self.seed = seed
        self.max_depth = max_depth
        self.tile = tile
        self.game = Game(seed=seed, max_depth=max_depth)
        self.mode = "jeu"          # jeu | sac | action | direction | aide
        self.slot = None
        self.note = None

        self.root = tk.Tk()
        self.root.title("Donjon mystère")
        self.root.configure(bg=FOND)
        width = self.game.level.width * tile
        height = self.game.level.height * tile + HUD_HEIGHT + LOG_HEIGHT
        self.canvas = tk.Canvas(self.root, width=width, height=height,
                                bg=FOND, highlightthickness=0)
        self.canvas.pack()
        self.root.bind("<Key>", self.on_key)
        self.root.resizable(False, False)
        self.dessiner()

    # ------------------------------------------------------------------ #
    # Boucle
    # ------------------------------------------------------------------ #
    def run(self):
        self.root.mainloop()

    def on_key(self, event):
        touche = event.keysym
        char = event.char

        if self.game.state != PLAYING:
            if char.lower() == "r":
                self.game = Game(seed=None, max_depth=self.max_depth)
                self.mode = "jeu"
            elif char.lower() == "q" or touche == "Escape":
                self.root.destroy()
                return
            self.dessiner()
            return

        if self.mode == "aide":
            self.mode = "jeu"
        elif self.mode == "jeu":
            self._touche_jeu(touche, char)
        elif self.mode == "sac":
            self._touche_sac(touche, char)
        elif self.mode == "action":
            self._touche_action(touche, char)
        elif self.mode == "direction":
            self._touche_direction(touche, char)
        self.dessiner()

    def _touche_jeu(self, touche, char):
        direction = DIRECTION_SYMBOLES.get(touche) or DIRECTION_TOUCHES.get(char)
        if direction:
            self.game.cmd_move(direction)
        elif char == ".":
            self.game.cmd_wait()
        elif char == ",":
            self.game.cmd_pickup()
        elif char == ">":
            self.game.cmd_descend()
        elif char == "i":
            self.mode = "sac"
        elif char == "?":
            self.mode = "aide"
        elif char == "q" or touche == "Escape":
            self.root.destroy()

    def _touche_sac(self, touche, char):
        if touche == "Escape" or char == "i":
            self.mode = "jeu"
            return
        slot = ord(char.lower()) - ord("a") if char.isalpha() else -1
        if 0 <= slot < len(self.game.player.inventory):
            self.slot = slot
            self.mode = "action"
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
            self.game.cmd_throw(self.slot, direction)
            self.mode = "jeu"

    # ------------------------------------------------------------------ #
    # Dessin
    # ------------------------------------------------------------------ #
    def dessiner(self):
        self.canvas.delete("all")
        self._dessiner_hud()
        self._dessiner_carte()
        self._dessiner_journal()
        if self.mode in ("sac", "action", "direction"):
            self._dessiner_sac()
        elif self.mode == "aide":
            self._panneau("Aide", AIDE)
        if self.game.state != PLAYING:
            self._dessiner_fin()

    def _cellule(self, x, y):
        """Coin haut-gauche en pixels d'une case de la carte."""
        return x * self.tile, y * self.tile + HUD_HEIGHT

    def _dessiner_carte(self):
        game, level, tile = self.game, self.game.level, self.tile
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
        for monstre in game.monsters():
            if monstre.pos in visibles:
                px, py = self._cellule(*monstre.pos)
                self._creature(px, py, monstre)
        px, py = self._cellule(*game.player.pos)
        self._heros(px, py)

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

    def _heros(self, px, py):
        self._corps(px, py, JOUEUR, "heros")

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

    # --- HUD ------------------------------------------------------------
    def _dessiner_hud(self):
        joueur = self.game.player
        largeur = self.game.level.width * self.tile
        self.canvas.create_rectangle(0, 0, largeur, HUD_HEIGHT,
                                     fill="#16141d", outline="")
        self._texte(10, 8, f"Étage {self.game.depth}", gras=True)
        self._texte(10, 26, f"Niveau {joueur.level}", pale=True)

        self._barre(95, 10, 110, joueur.hp, joueur.max_hp,
                    BARRE_PV if joueur.hp > joueur.max_hp * 0.3 else BARRE_PV_BAS,
                    f"PV {joueur.hp}/{joueur.max_hp}")
        self._barre(95, 27, 110, joueur.fullness, joueur.MAX_FULLNESS,
                    BARRE_VENTRE, f"Ventre {joueur.fullness}")

        arme = joueur.weapon.name if joueur.weapon else "mains nues"
        bouclier = joueur.shield.name if joueur.shield else "aucun"
        self._texte(320, 8, f"Attaque {joueur.attack}    Défense {joueur.defense}")
        self._texte(320, 26, f"{arme}  |  {bouclier}", pale=True)

        statuts = joueur.status_line()
        if statuts:
            self._texte(largeur - 10, 8, statuts, ancre="ne", couleur="#e0a54f")
        self._texte(largeur - 10, 26, "« ? » pour l'aide", ancre="ne", pale=True)

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
        largeur = self.game.level.width * self.tile
        self.canvas.create_rectangle(0, haut, largeur, haut + LOG_HEIGHT,
                                     fill="#16141d", outline="")
        lignes = self.game.log.tail(LOG_LINES)
        if self.note:
            lignes = (lignes + [self.note])[-LOG_LINES:]
            self.note = None
        for index, ligne in enumerate(lignes):
            dernier = index == len(lignes) - 1
            self._texte(10, haut + 6 + index * 18, ligne, pale=not dernier)

    def _texte(self, x, y, texte, pale=False, gras=False, ancre="nw", couleur=None):
        self.canvas.create_text(
            x, y, text=texte, anchor=ancre,
            fill=couleur or (TEXTE_PALE if pale else TEXTE),
            font=("TkDefaultFont", 10, "bold" if gras else "normal"))

    # --- panneaux -------------------------------------------------------
    def _dessiner_sac(self):
        joueur = self.game.player
        if not joueur.inventory:
            self._panneau("Sac", ["(vide)", "", "Échap pour fermer"])
            return
        lignes = []
        for index, objet in enumerate(joueur.inventory):
            marque = ""
            if objet is joueur.weapon or objet is joueur.shield:
                marque = "   [équipé]"
            fleche = "> " if index == self.slot and self.mode != "sac" else "  "
            lignes.append(f"{fleche}{chr(ord('a') + index)})  {objet.name}{marque}")
        if self.mode == "sac":
            titre = "Sac — choisis une lettre (Échap ferme)"
        elif self.mode == "action":
            titre = "u utiliser · e équiper · t lancer · d poser"
            lignes += ["", "Échap pour revenir au sac."]
        else:
            titre = "Dans quelle direction ? (flèches ou hjkl/yubn)"
            lignes += ["", "Échap pour annuler."]
        self._panneau(titre, lignes)

    def _panneau(self, titre, lignes):
        largeur_ecran = self.game.level.width * self.tile
        hauteur_ecran = self.game.level.height * self.tile + HUD_HEIGHT
        largeur = min(largeur_ecran - 60, max(
            [len(titre)] + [len(l) for l in lignes]) * 8 + 50)
        hauteur = 54 + len(lignes) * 19
        gauche = (largeur_ecran - largeur) / 2
        haut = (hauteur_ecran - hauteur) / 2
        self.canvas.create_rectangle(gauche, haut, gauche + largeur, haut + hauteur,
                                     fill="#1d1a26", outline="#4a4460", width=2)
        self._texte(gauche + 16, haut + 14, titre, gras=True)
        for index, ligne in enumerate(lignes):
            self._texte(gauche + 16, haut + 40 + index * 19, ligne)

    def _dessiner_fin(self):
        largeur = self.game.level.width * self.tile
        hauteur = self.game.level.height * self.tile + HUD_HEIGHT + LOG_HEIGHT
        self.canvas.create_rectangle(0, 0, largeur, hauteur,
                                     fill="#000000", stipple="gray75", outline="")
        gagne = self.game.state == WON
        titre = "VICTOIRE !" if gagne else "TU ES MORT"
        couleur = ESCALIER if gagne else PIEGE
        self.canvas.create_rectangle(largeur / 2 - 210, hauteur / 2 - 66,
                                     largeur / 2 + 210, hauteur / 2 + 62,
                                     fill="#1d1a26", outline=couleur, width=2)
        self.canvas.create_text(largeur / 2, hauteur / 2 - 30, text=titre,
                                fill=couleur, font=("TkDefaultFont", 28, "bold"))
        detail = (f"Étage {self.game.depth} · niveau {self.game.player.level} · "
                  f"{self.game.turn} tours")
        self.canvas.create_text(largeur / 2, hauteur / 2 + 8, text=detail,
                                fill=TEXTE, font=("TkDefaultFont", 12))
        self.canvas.create_text(largeur / 2, hauteur / 2 + 40,
                                text="R pour rejouer   ·   q pour quitter",
                                fill=TEXTE_PALE, font=("TkDefaultFont", 11))


def run(seed=None, max_depth=5, tile=TILE):
    Fenetre(seed=seed, max_depth=max_depth, tile=tile).run()
