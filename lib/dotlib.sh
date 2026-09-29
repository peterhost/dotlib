# lib/dotlib.sh — point d'entrée de dotlib pour un shell bash (3.2+)
#
#   . "${DOTLIB_DIR:-$HOME/.dotlib}/lib/dotlib.sh"
#
# Charge la plateforme, les conseils d'installation et la palette ; ne charge PAS l'interface
# (lib/tui.sh, pour les outils). Ne lance aucun processus (voir lib/palette.sh pour l'exception macOS)
# et n'écrit rien. DOTLIB_API : version du contrat (API.md) — un appelant vérifie
#   [ "${DOTLIB_API:-0}" -ge 1 ]
# et utilise son propre repli sinon.
#
# DOTLIB_REVISION : incrémenté à chaque AJOUT au contrat, l'API ne bougeant pas pour autant. Il existe
# parce qu'un appelant ne pouvait pas savoir si le dotlib qu'il a en face porte l'ajout dont il a
# besoin : « API 1 » ne distingue pas celui d'hier de celui d'aujourd'hui. Côté shell, l'absence se
# paie plus cher que côté Python : « dotlib_pill -p BAD x T » sur un dotlib ancien prend « -p » pour un
# nom de couleur et rend une pastille fausse, SANS ERREUR. Un appelant teste donc
#   [ "${DOTLIB_REVISION:-1}" -ge 2 ]
# avant d'employer une nouveauté, et construit sans elle sinon.
#   1 : API 1 d'origine
#   2 : dotlib_utf8, dotlib_pill -p et -c, arrondis par défaut, share/palettes-sources.tsv

DOTLIB_API=1
DOTLIB_REVISION=2
: "${DOTLIB_DIR:=$HOME/.dotlib}"
. "$DOTLIB_DIR/lib/platform.sh"
. "$DOTLIB_DIR/lib/hints.sh"
. "$DOTLIB_DIR/lib/palette.sh"
