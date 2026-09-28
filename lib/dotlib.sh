# lib/dotlib.sh — point d'entrée de dotlib pour un shell bash (3.2+)
#
#   . "${DOTLIB_DIR:-$HOME/.dotlib}/lib/dotlib.sh"
#
# Charge la plateforme, les conseils d'installation et la palette ; ne charge PAS l'interface
# (lib/tui.sh, pour les outils). Ne lance aucun processus (voir lib/palette.sh pour l'exception macOS)
# et n'écrit rien. DOTLIB_API : version du contrat (API.md) — un appelant vérifie
#   [ "${DOTLIB_API:-0}" -ge 1 ]
# et utilise son propre repli sinon.

DOTLIB_API=1
: "${DOTLIB_DIR:=$HOME/.dotlib}"
. "$DOTLIB_DIR/lib/platform.sh"
. "$DOTLIB_DIR/lib/hints.sh"
. "$DOTLIB_DIR/lib/palette.sh"
