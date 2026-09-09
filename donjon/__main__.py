"""Point d'entrée en ligne de commande.

    python -m donjon                          # jouer (fenêtre graphique)
    python -m donjon --tui                    # jouer dans le terminal (curses)
    python -m donjon --seed 42                # partie reproductible
    python -m donjon --script "lllj,>" -f     # rejouer une partition, mode texte
    python -m donjon --auto 500 --reveal      # bot de test, carte dévoilée
"""

import argparse
import sys

from .game import Game
from .script import ScriptError, autoplay, run_script


def build_parser():
    parser = argparse.ArgumentParser(prog="donjon", description="Petit donjon mystère")
    parser.add_argument("--tui", action="store_true",
                        help="jouer dans le terminal au lieu de la fenêtre")
    parser.add_argument("--tile", type=int, default=20,
                        help="taille des cases en pixels (fenêtre graphique)")
    parser.add_argument("--seed", type=int, default=None,
                        help="graine aléatoire (partie reproductible)")
    parser.add_argument("--depth", type=int, default=None,
                        help="nombre d'étages à franchir pour gagner "
                             "(par défaut celui de RunConfig)")
    parser.add_argument("--script", metavar="CMDS",
                        help="joue une suite de commandes sans interface")
    parser.add_argument("--auto", type=int, metavar="N",
                        help="fait jouer le bot pendant N décisions")
    parser.add_argument("-f", "--frames", action="store_true",
                        help="affiche la carte après chaque commande")
    parser.add_argument("--reveal", action="store_true",
                        help="affiche tout l'étage (débogage)")
    parser.add_argument("--no-save", action="store_true",
                        help="ne pas toucher à la progression permanente")
    parser.add_argument("--meta", action="store_true",
                        help="affiche la progression permanente et quitte")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.meta:
        from . import meta as meta_mod
        print("\n".join(meta_mod.load().lines()))
        return 0

    headless = args.script is not None or args.auto is not None

    if not headless:
        if args.tui:
            from . import ui
            ui.run(seed=args.seed, max_depth=args.depth,
                   sauvegarde=not args.no_save)
            return 0
        try:
            from . import gui
        except ImportError:
            print("tkinter est absent de cette installation de Python.\n"
                  "Relance avec --tui pour jouer dans le terminal, ou installe "
                  "tkinter (Linux : « sudo apt install python3-tk »).",
                  file=sys.stderr)
            return 3
        gui.run(seed=args.seed, max_depth=args.depth, tile=args.tile,
                sauvegarde=not args.no_save)
        return 0

    # Les modes script et bot ne touchent jamais à la sauvegarde : ce sont des
    # outils de test, ils n'ont pas à faire progresser un joueur.
    game = Game(seed=args.seed, max_depth=args.depth)
    print(f"graine : {game.seed}")

    def show(game, token, acted):
        if args.frames:
            print(f"\n== {''.join(token)} ({'ok' if acted else 'refusé'}) ==")
            print(game.render_text(reveal=args.reveal))

    try:
        if args.script:
            run_script(game, args.script, on_step=show)
        if args.auto:
            autoplay(game, args.auto, on_step=show)
    except ScriptError as error:
        print(f"erreur de script : {error}", file=sys.stderr)
        return 2

    print(game.render_text(reveal=args.reveal, log_lines=8))
    print(f"état : {game.state}")
    if game.summary:
        print("\n".join("  " + ligne for ligne in game.summary.lines()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
