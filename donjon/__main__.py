"""Point d'entrée en ligne de commande.

    python -m donjon                          # jouer (interface terminal)
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
    parser.add_argument("--seed", type=int, default=None,
                        help="graine aléatoire (partie reproductible)")
    parser.add_argument("--depth", type=int, default=5,
                        help="nombre d'étages à franchir pour gagner")
    parser.add_argument("--script", metavar="CMDS",
                        help="joue une suite de commandes sans interface")
    parser.add_argument("--auto", type=int, metavar="N",
                        help="fait jouer le bot pendant N décisions")
    parser.add_argument("-f", "--frames", action="store_true",
                        help="affiche la carte après chaque commande")
    parser.add_argument("--reveal", action="store_true",
                        help="affiche tout l'étage (débogage)")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    headless = args.script is not None or args.auto is not None

    if not headless:
        from . import ui
        ui.run(seed=args.seed, max_depth=args.depth)
        return 0

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
