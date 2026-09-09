#!/bin/sh
# Lanceur Mac / Linux : ./jouer.sh
# Se place dans le dossier du script, ce qui evite l'erreur
# "No module named donjon" quand le terminal n'est pas au bon endroit.
cd "$(dirname "$0")" || exit 1
exec python3 -m donjon "$@"
