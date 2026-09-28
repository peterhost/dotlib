# lib/palette.sh — la routine de couleurs : une palette, un thème (clair/sombre), une profondeur
#
# bash 3.2+, aucun processus lancé (sauf « defaults » sur macOS en thème auto, une fois : le
# résultat est exporté). Réglage de l'utilisateur : $DOTLIB_DIR/local/theme.conf (dotlib_theme_set),
# lignes CLÉ=valeur ; une variable d'environnement du même nom l'emporte.
#   DOTLIB_PALETTE  catppuccin (défaut) | gruvbox | nord | solarized | tokyonight | everforest | edge |
#                   lucius | papercolor | pencil | xterm
#                   (xterm : palette 256 couleurs historique ; « actuel », son ancien nom, reste accepté)
#   DOTLIB_THEME    auto (défaut) | dark | light
#                   auto : COLORFGBG, sinon le fond réel du terminal (OSC 11, shell interactif seulement),
#                   sinon LC_DOTLIB_THEME (transmis par ssh), sinon apparence macOS, sinon sombre ;
#                   console linux : sombre
#   DOTLIB_MATCH    fond (défaut) | texte   correspondances : fond coloré (Search de vim) ou texte gras
# Fournis par l'appelant (sinon déduits de TERM / COLORTERM / NO_COLOR) :
#   DOTLIB_COLORS   0 | 8 | 256 | 16m       profondeur du terminal
#   DOTLIB_TERM     console pour la console linux (sinon libre, ex. warp : arrondis des pastilles)
# Définit (dotlib_palette_load) :
#   C_RESET C_BOLD C_DIM C_UL C_REV, C_BLACK… C_WHITE C_GREY (couleurs de base : suivent le terminal)
#   C_OK C_WARN C_ERR C_INFO (sens)
#   C_R_NUM C_R_DATE C_R_TEXT C_R_MATCH C_R_KEY C_R_PATH C_R_BAD C_R_NOTE (rôles, selon la palette)
#   DOTLIB_THEME_EFF, DOTLIB_PALETTE_EFF    thème et palette retenus (EXPORTÉS : vim, outils)
# Voir API.md pour ce qui est garanti.

: "${DOTLIB_DIR:=$HOME/.dotlib}"
DOTLIB_PALETTES='catppuccin gruvbox nord solarized tokyonight everforest edge lucius papercolor pencil xterm'

# _dotlib_depth : DOTLIB_COLORS d'après l'environnement, si l'appelant ne l'a pas fixé
_dotlib_depth() {
  [ -n "${DOTLIB_COLORS:-}" ] && return
  DOTLIB_COLORS=8
  case ${TERM:-dumb} in
    dumb|'') DOTLIB_COLORS=0; return ;;
    linux) DOTLIB_TERM=${DOTLIB_TERM:-console}; return ;;
    *256color*|xterm-kitty|xterm-ghostty|alacritty|wezterm) DOTLIB_COLORS=256 ;;
  esac
  case ${COLORTERM:-} in truecolor|24bit) DOTLIB_COLORS=16m ;; esac
}

# Mémoire de la sonde : $DOTLIB_DIR/local/cache/fond, une ligne « clé|epoch|dark|light » (clé = TERM et
# DOTLIB_TERM), valable DOTLIB_PROBE_TTL minutes (60). brc theme / dotlib_theme_set l'effacent.
_DOTLIB_PROBE_CACHE=${DOTLIB_DIR:-$HOME/.dotlib}/local/cache/fond
_dotlib_probe_key() { printf '%s' "${TERM:-}/${DOTLIB_TERM:-}"; }
_dotlib_probe_cached() {   # pose DOTLIB_THEME_EFF depuis la mémoire si elle est fraîche ; 1 sinon
  local k e t now line
  [ "${BASH_VERSINFO[0]:-0}${BASH_VERSINFO[1]:-0}" -ge 42 ] || return 1      # printf %(%s)T
  [ -r "$_DOTLIB_PROBE_CACHE" ] || return 1
  IFS= read -r line < "$_DOTLIB_PROBE_CACHE" || return 1
  k=${line%%|*}; line=${line#*|}; e=${line%%|*}; t=${line#*|}
  [ "$k" = "$(_dotlib_probe_key)" ] || return 1
  printf -v now '%(%s)T' -1
  case $e in ''|*[!0-9]*) return 1 ;; esac
  [ $(( now - e )) -lt $(( ${DOTLIB_PROBE_TTL:-60} * 60 )) ] || return 1
  case $t in dark|light) DOTLIB_THEME_EFF=$t ;; *) return 1 ;; esac
}
_dotlib_probe_remember() {
  local now
  [ "${BASH_VERSINFO[0]:-0}${BASH_VERSINFO[1]:-0}" -ge 42 ] || return 0
  printf -v now '%(%s)T' -1
  { [ -d "${_DOTLIB_PROBE_CACHE%/*}" ] || mkdir -p "${_DOTLIB_PROBE_CACHE%/*}"; } 2>/dev/null &&
    printf '%s|%s|%s\n' "$(_dotlib_probe_key)" "$now" "$DOTLIB_THEME_EFF" > "$_DOTLIB_PROBE_CACHE" 2>/dev/null
  return 0
}

# _dotlib_probe_bg : demande au terminal sa couleur de fond (OSC 11) et pose DOTLIB_THEME_EFF (light si
# luma > 128) ; 1 si rien de lisible. Le terminal répond par le flux lui-même : ça traverse ssh et tmux
# sans rien demander au serveur. Conditions CUMULATIVES, sinon rien n'est écrit du tout : shell
# interactif, entrée ET sortie sur un terminal, TERM utilisable, DOTLIB_PROBE≠0, bash ≥ 4, aucune frappe en
# attente. Jamais dans
# « ssh hôte commande », un script ou une pose : leur flux serait corrompu.
# Délai : DOTLIB_PROBE_TIME dixièmes de seconde (3) ; terminal TOUJOURS restauré (trap EXIT INT TERM).
_dotlib_probe_bg() {
  case $- in *i*) ;; *) return 1 ;; esac
  [ -t 0 ] && [ -t 1 ] || return 1
  [ "${DOTLIB_PROBE:-1}" = 1 ] || return 1
  case ${TERM:-dumb} in dumb|'') return 1 ;; esac
  # Lignes déjà validées (Entrée) ou envoyées d'avance par un programme : on ne sonde pas, sinon la
  # lecture les avalerait. ATTENTION, limite : une ligne en cours de frappe (pas encore validée) dort
  # dans le tampon du pilote, read -t 0 ne la voit pas, et la sonde peut l'avaler. D'où la mémoire du
  # résultat (_dotlib_probe_cache) : la sonde ne part qu'une fois par heure et par terminal, pas à
  # chaque shell. bash 3.2 ne sait pas faire read -t 0 : pas de sonde du tout.
  [ "${BASH_VERSINFO[0]:-0}" -ge 4 ] || return 1
  read -t 0 < /dev/tty 2>/dev/null && return 1
  local old r= rgb R G B rest t_exit t_int t_term
  old=$(stty -g 2>/dev/null) || return 1
  t_exit=$(trap -p EXIT) t_int=$(trap -p INT) t_term=$(trap -p TERM)
  trap 'stty "$old" 2>/dev/null' EXIT INT TERM
  if stty raw -echo min 0 time "${DOTLIB_PROBE_TIME:-3}" 2>/dev/null; then
    printf '\033]11;?\033\\' 2>/dev/null > /dev/tty
    # dd et non « read » : read -d reprogramme le terminal (attente sans fin) ; dd respecte le délai.
    # Une lecture rend d'ordinaire toute la réponse ; au plus deux de plus si elle arrive en morceaux
    local i=0 part
    while [ $i -lt 3 ]; do
      part=$(dd bs=64 count=1 2>/dev/null < /dev/tty); r=$r$part
      case $r in *$'\a'*|*$'\e\\'*|'') break ;; esac
      i=$((i + 1))
    done
  fi
  stty "$old" 2>/dev/null
  if [ -n "$t_exit" ]; then eval "$t_exit"; else trap - EXIT; fi
  if [ -n "$t_int" ]; then eval "$t_int"; else trap - INT; fi
  if [ -n "$t_term" ]; then eval "$t_term"; else trap - TERM; fi
  # rgb:RRRR/GGGG/BBBB (16 bits), rgb:RR/GG/BB (8 bits), #RRGGBB ; on garde l'octet de poids fort
  case $r in
    *rgb:*) rgb=${r#*rgb:}; R=${rgb%%/*}; rest=${rgb#*/}; G=${rest%%/*}; B=${rest#*/} ;;
    *'#'[0-9a-fA-F]*) rgb=${r#*#}; R=${rgb:0:2}; G=${rgb:2:2}; B=${rgb:4:2} ;;
    *) return 1 ;;
  esac
  B=${B%%[!0-9a-fA-F]*}
  [ ${#R} = 1 ] && R=$R$R; [ ${#G} = 1 ] && G=$G$G; [ ${#B} = 1 ] && B=$B$B
  R=${R:0:2} G=${G:0:2} B=${B:0:2}
  case "$R$G$B" in ''|*[!0-9a-fA-F]*) return 1 ;; esac
  [ ${#R} = 2 ] && [ ${#G} = 2 ] && [ ${#B} = 2 ] || return 1
  if [ $(( (299 * 16#$R + 587 * 16#$G + 114 * 16#$B) / 1000 )) -gt 128 ]; then DOTLIB_THEME_EFF=light
  else DOTLIB_THEME_EFF=dark; fi
  _dotlib_probe_remember
}

# _dotlib_theme_resolve : DOTLIB_THEME_EFF d'après DOTLIB_THEME
_dotlib_theme_resolve() {
  local bg
  case ${DOTLIB_THEME:-auto} in
    dark|light) DOTLIB_THEME_EFF=$DOTLIB_THEME; return ;;
  esac
  # Console linux : toujours fond noir
  [ "${DOTLIB_TERM:-}" = console ] && { DOTLIB_THEME_EFF=dark; return; }
  # Déjà déterminé par un shell parent
  case ${DOTLIB_THEME_DETECTED:-} in dark|light) DOTLIB_THEME_EFF=$DOTLIB_THEME_DETECTED; return ;; esac
  # Ordre (décidé avec l'utilisateur) : ce que le TERMINAL dit ou montre prime sur les préférences de
  # fenêtres du système — c'est le fond réel qui décide de la lisibilité du texte.
  DOTLIB_THEME_EFF=dark
  if [ -n "${COLORFGBG:-}" ]; then          # « fg;bg » : le terminal se déclare lui-même
    bg=${COLORFGBG##*;}
    case $bg in 7|9|1[0-5]) DOTLIB_THEME_EFF=light ;; esac
  elif _dotlib_probe_cached || _dotlib_probe_bg; then
    :                                          # fond réel mesuré (OSC 11, mémorisé 1 h), shell interactif
  elif [ -n "${LC_DOTLIB_THEME:-}" ]; then     # verdict de la machine d'où l'on vient (ssh, SendEnv LC_*)
    DOTLIB_THEME_EFF=$LC_DOTLIB_THEME
  elif [ "${DOTLIB_OS:-}" = darwin ] && [ -z "${SSH_CONNECTION:-}" ]; then
    # Apparence macOS (préférence de fenêtres, y compris jour/nuit) : « Dark » ou rien. ≈ 7 ms, une fois :
    # le résultat est exporté aux shells enfants
    command -v defaults >/dev/null 2>&1 && case $(defaults read -g AppleInterfaceStyle 2>/dev/null) in Dark) ;; *) DOTLIB_THEME_EFF=light ;; esac
  fi
  export DOTLIB_THEME_DETECTED=$DOTLIB_THEME_EFF
  # Vers les machines où l'on se connecte (ssh transmet LC_* quand le serveur l'accepte)
  [ -z "${SSH_CONNECTION:-}" ] && export LC_DOTLIB_THEME=$DOTLIB_THEME_EFF
}

# _dotlib_sgr HEX/IDX [fond] : séquence SGR selon la profondeur (16m : vraies couleurs, sinon 256)
_dotlib_sgr() {
  local hex=${1%/*} idx=${1#*/} base=38
  [ -n "${2:-}" ] && base=48
  if [ "${DOTLIB_COLORS:-0}" = 16m ]; then
    _S="$base;2;$((16#${hex:0:2}));$((16#${hex:2:2}));$((16#${hex:4:2}))"
  else
    _S="$base;5;$idx"
  fi
}

# _dotlib_palette_data : _p = couleurs de rôle de la palette et du thème courants (1 si palette inconnue)
_dotlib_palette_data() {
  [ "${DOTLIB_PALETTE:-}" = actuel ] && DOTLIB_PALETTE=xterm      # ancien nom
  case ${DOTLIB_PALETTE:-catppuccin}:$DOTLIB_THEME_EFF in
    xterm:dark) _p='d75fd7/170 005faf/25 a8a8a8/248 ffff00/226 - 00afd7/38 6c6c6c/242 ff5f5f/203 d7af5f/179' ;;
    xterm:light) _p='af00af/127 005faf/25 585858/240 af5f00/130 - 0087af/31 8a8a8a/245 d70000/160 af5f00/130' ;;
    catppuccin:dark) _p='cba6f7/183 89b4fa/111 a6adc8/146 1e1e2e/235 f9e2af/223 94e2d5/116 7f849c/103 f38ba8/211 fab387/216' ;;
    catppuccin:light) _p='8839ef/99 1e66f5/27 5c5f77/60 eff1f5/255 df8e1d/172 179299/30 8c8fa1/246 d20f39/161 fe640b/202' ;;
    gruvbox:dark) _p='d3869b/174 83a598/108 a89984/138 282828/235 fabd2f/214 8ec07c/108 928374/244 fb4934/203 fe8019/208' ;;
    gruvbox:light) _p='8f3f71/95 076678/24 7c6f64/242 fbf1c7/230 b57614/136 427b58/65 928374/244 9d0006/124 af3a03/130' ;;
    nord:dark) _p='b48ead/139 81a1c1/109 d8dee9/254 2e3440/237 88c0d0/110 88c0d0/110 616e88/60 bf616a/131 d08770/173' ;;
    nord:light) _p='9a5f96/96 5e81ac/67 4c566a/240 2e3440/237 ebcb8b/186 4c7f8f/66 7b88a1/103 bf616a/131 c5714f/167' ;;
    solarized:dark) _p='d33682/168 268bd2/32 839496/246 002b36/235 b58900/136 2aa198/36 586e75/242 dc322f/166 cb4b16/166' ;;
    solarized:light) _p='d33682/168 268bd2/32 657b83/66 fdf6e3/230 b58900/136 2aa198/36 93a1a1/247 dc322f/166 cb4b16/166' ;;
    tokyonight:dark) _p='bb9af7/141 7aa2f7/111 a9b1d6/146 c0caf5/153 3d59a1/61 7dcfff/117 565f89/60 f7768e/210 ff9e64/215' ;;
    tokyonight:light) _p='9854f1/99 2e7de9/32 6172b0/61 e1e2e7/254 8c6c3e/95 007197/24 848cb5/103 f52a65/197 b15c00/130' ;;
    everforest:dark) _p='d699b6/175 7fbbb3/109 9da9a0/248 2d353b/237 a7c080/144 83c092/108 859289/245 e67e80/174 e69875/174' ;;
    everforest:light) _p='df69ba/169 3a94c5/68 829181/102 fdf6e3/230 8da101/106 35a77c/72 939f91/246 f85552/203 f57d26/208' ;;
    edge:dark) _p='d38aea/176 6cb6eb/74 a0a8b7/248 2c2e34/236 a0c980/150 5dbbc1/73 7f8490/102 ec7279/204 deb974/180' ;;
    edge:light) _p='b05ccc/134 5079be/67 6c7483/243 fafafa/231 608e32/65 3a8b84/66 8790a0/246 d05858/167 be7e05/136' ;;
    lucius:dark) _p='d7afd7/182 87afd7/110 bcbcbc/250 303030/236 d7d7af/187 87d7d7/116 808080/244 d78787/174 d7af87/180' ;;
    lucius:light) _p='870087/90 005faf/25 585858/240 eeeeee/255 af8700/136 008787/30 808080/244 af0000/124 af5f00/130' ;;
    papercolor:dark) _p='af87d7/140 5fafd7/74 bcbcbc/250 1c1c1c/234 d7af5f/179 00afaf/37 808080/244 df0000/160 ff8700/208' ;;
    papercolor:light) _p='8700af/91 0087af/31 585858/240 eeeeee/255 d75f00/166 005f87/24 878787/102 af0000/124 d75f00/166' ;;
    pencil:dark) _p='6855de/62 20bbfc/39 b2b2b2/249 212121/234 f3e430/221 4fb8cc/74 6c6c6c/242 e32791/162 f3e430/221' ;;
    pencil:light) _p='523c79/60 008ec4/32 626262/241 f1f1f1/255 a89c14/142 20a5ba/37 9e9e9e/247 c30771/125 a89c14/142' ;;
    *) return 1 ;;
  esac
}

dotlib_palette_load() {
  _dotlib_depth
  # Réglages enregistrés (dotlib_theme_set) ; les variables d'environnement l'emportent
  if [ -r "${DOTLIB_DIR:-$HOME/.dotlib}/local/theme.conf" ]; then
    local _k _v
    while IFS='=' read -r _k _v; do
      case $_v in *[!a-z]*|'') continue ;; esac
      case $_k in
        DOTLIB_PALETTE|DOTLIB_THEME|DOTLIB_MATCH) eval "[ -n \"\${$_k:-}\" ] || $_k=\$_v" ;;
      esac
    done < "${DOTLIB_DIR:-$HOME/.dotlib}/local/theme.conf"
  fi
  local _p _S n d t mf mb k p b o
  if [ "${DOTLIB_COLORS:-0}" = 0 ] || [ -n "${NO_COLOR:-}" ]; then
    C_RESET= C_BOLD= C_DIM= C_UL= C_REV=
    C_BLACK= C_RED= C_GREEN= C_YELLOW= C_BLUE= C_MAGENTA= C_CYAN= C_WHITE= C_GREY=
    C_R_NUM= C_R_DATE= C_R_TEXT= C_R_MATCH= C_R_KEY= C_R_PATH= C_R_BAD= C_R_NOTE=
    C_OK= C_WARN= C_ERR= C_INFO=
    _dotlib_theme_resolve             # sans couleur, le thème retenu sert quand même (vim, outils)
    export DOTLIB_THEME_EFF DOTLIB_PALETTE_EFF=${DOTLIB_PALETTE:-catppuccin}
    return 0
  fi
  _dotlib_theme_resolve
  export DOTLIB_THEME_EFF DOTLIB_PALETTE_EFF=${DOTLIB_PALETTE:-catppuccin}
  C_RESET=$'\e[0m' C_BOLD=$'\e[1m' C_DIM=$'\e[2m' C_UL=$'\e[4m' C_REV=$'\e[7m'
  C_BLACK=$'\e[30m' C_RED=$'\e[31m' C_GREEN=$'\e[32m' C_YELLOW=$'\e[33m'
  C_BLUE=$'\e[34m' C_MAGENTA=$'\e[35m' C_CYAN=$'\e[36m' C_WHITE=$'\e[37m' C_GREY=$'\e[90m'
  C_OK=$C_GREEN C_WARN=$C_YELLOW C_ERR=$C_RED C_INFO=$C_CYAN

  if [ "$DOTLIB_COLORS" = 8 ]; then
    # Couleurs de base : c'est le thème du terminal qui les rend lisibles
    C_GREY=$'\e[1;30m'
    C_R_NUM=$'\e[35m' C_R_DATE=$'\e[34m' C_R_TEXT=$C_GREY C_R_MATCH=$'\e[1;33m' C_R_KEY=$'\e[1;36m'
    C_R_PATH=$C_GREY C_R_BAD=$'\e[31m' C_R_NOTE=$'\e[33m'
    [ "$DOTLIB_THEME_EFF" = light ] && C_R_MATCH=$'\e[1;7;33m'
    if [ "${DOTLIB_TERM:-}" = console ]; then
      # Console linux : pas de « dim », bleu foncé illisible sur fond noir
      C_DIM= C_BLUE=$'\e[1;34m' C_R_DATE=$'\e[1;34m' C_R_TEXT=
    fi
    return 0
  fi

  _dotlib_palette_data || { DOTLIB_PALETTE=catppuccin; dotlib_palette_load; return; }
  export DOTLIB_PALETTE_EFF=${DOTLIB_PALETTE:-catppuccin}
  set -- $_p
  _dotlib_sgr "$1"; C_R_NUM=$'\e['"${_S}m"
  _dotlib_sgr "$2"; C_R_DATE=$'\e['"${_S}m"
  _dotlib_sgr "$3"; C_R_TEXT=$'\e['"${_S}m"
  _dotlib_sgr "$6"; C_R_KEY=$'\e[1;'"${_S}m"
  _dotlib_sgr "$7"; C_R_PATH=$'\e['"${_S}m"
  _dotlib_sgr "$8"; C_R_BAD=$'\e['"${_S}m"
  _dotlib_sgr "$9"; C_R_NOTE=$'\e['"${_S}m"
  if [ "$5" != - ] && [ "${DOTLIB_MATCH:-fond}" = fond ]; then
    _dotlib_sgr "$4"; mf=$_S; _dotlib_sgr "$5" fond
    C_R_MATCH=$'\e[1;'"$mf;${_S}m"
  elif [ "$5" != - ]; then
    _dotlib_sgr "$5"; C_R_MATCH=$'\e[1;'"${_S}m"      # la couleur du fond, en texte
  else
    _dotlib_sgr "$4"; C_R_MATCH=$'\e[1;'"${_S}m"
  fi
}

# --- Pastilles (style de la ligne de statut Claude : icône sur fond coloré, texte sur fond neutre) -----
# dotlib_pill COULEUR ICÔNE TEXTE → DOTLIB_PILL (séquences prêtes à imprimer, sans \[ \] : pas pour PS1)
#   COULEUR : un rôle (BAD NOTE KEY NUM DATE) de la palette courante, ou RRGGBB/idx256
#   Arrondis powerline (U+E0B6/U+E0B4) seulement si DOTLIB_PILL_ROUND=1 (défaut : sous Warp, dont la
#   police les a ; ailleurs, des espaces). 8 couleurs : [ texte ] inversé ; sans couleur : [texte].
_dotlib_pill_base() {   # fond neutre / texte / « creux » (texte sur la couleur) de la palette courante
  case ${DOTLIB_PALETTE:-catppuccin}:${DOTLIB_THEME_EFF:-dark} in
    catppuccin:dark)  _pb='313244/236 cdd6f4/189 11111b/233' ;;
    catppuccin:light) _pb='ccd0da/252 4c4f69/60 dce0e8/254' ;;
    gruvbox:dark)     _pb='3c3836/237 ebdbb2/223 1d2021/234' ;;
    gruvbox:light)    _pb='ebdbb2/223 3c3836/237 f9f5d7/230' ;;
    nord:dark)        _pb='3b4252/238 eceff4/255 2e3440/236' ;;
    nord:light)       _pb='e5e9f0/254 2e3440/236 eceff4/255' ;;
    solarized:dark)   _pb='073642/236 93a1a1/247 002b36/234' ;;
    solarized:light)  _pb='eee8d5/254 586e75/242 fdf6e3/230' ;;
    tokyonight:dark)  _pb='292e42/236 c0caf5/153 16161e/233' ;;
    tokyonight:light) _pb='c4c8da/252 3760bf/25 e9e9ec/255' ;;
    everforest:dark) _pb='3d484d/238 d3c6aa/187 232a2e/235' ;;
    everforest:light) _pb='e6e2cc/253 5c6a72/242 f4f0d9/230' ;;
    edge:dark) _pb='3b3e48/238 c5cdd9/252 222327/235' ;;
    edge:light) _pb='dde2e7/254 4b505b/239 eef1f4/255' ;;
    lucius:dark) _pb='444444/238 d7d7d7/188 262626/235' ;;
    lucius:light) _pb='dadada/253 444444/238 e4e4e4/254' ;;
    papercolor:dark) _pb='3a3a3a/237 d0d0d0/252 121212/233' ;;
    papercolor:light) _pb='d0d0d0/252 444444/238 e4e4e4/254' ;;
    pencil:dark) _pb='303030/236 f1f1f1/255 1c1c1c/234' ;;
    pencil:light) _pb='d9d9d9/253 424242/238 e5e5e5/254' ;;
    xterm:light)      _pb='d0d0d0/252 303030/236 eeeeee/255' ;;
    *)                _pb='3a3a3a/237 d0d0d0/252 121212/233' ;;
  esac
}
dotlib_pill() {
  local c=$1 icon=$2 text=$3 _S _p _pb cs sf tx cr l= r= R=$'\e[0m'
  if [ "${DOTLIB_COLORS:-0}" = 0 ] || [ -n "${NO_COLOR:-}" ]; then DOTLIB_PILL="[$text]"; return; fi
  if [ "$DOTLIB_COLORS" = 8 ]; then DOTLIB_PILL=$'\e[1;7;31m'" $icon $text "$R; return; fi
  _dotlib_palette_data                                     # _p : couleurs de rôle de la palette courante
  set -- $_p
  case $c in NUM) c=$1 ;; DATE) c=$2 ;; KEY) c=$6 ;; BAD) c=$8 ;; NOTE) c=$9 ;; esac
  _dotlib_pill_base; set -- $_pb
  _dotlib_sgr "$c"; cs=$_S; _dotlib_sgr "$c" fond; local cb=$_S
  _dotlib_sgr "$1" fond; sf=$_S; _dotlib_sgr "$1"; local sff=$_S
  _dotlib_sgr "$2"; tx=$_S; _dotlib_sgr "$3"; cr=$_S
  local round=${DOTLIB_PILL_ROUND:-}
  [ -z "$round" ] && { round=0; [ "${DOTLIB_TERM:-}" = warp ] && round=1; }
  if [ "$round" = 1 ]; then        # U+E0B6 et U+E0B4 en UTF-8 (bash 3.2 ne connaît pas \u)
    l=$'\e['"${cs}m"$'\xee\x82\xb6'; r=$R$'\e['"${sff}m"$'\xee\x82\xb4'
  else l=$'\e['"${cb}m"' '; r=$'\e['"${sf}m"' '; fi
  DOTLIB_PILL="$l"$'\e['"${cb};${cr}m$icon "$'\e['"${sf};${tx}m $text$r$R"
}


# dotlib_theme_set CLÉ VALEUR : enregistre un réglage (DOTLIB_PALETTE, DOTLIB_THEME, DOTLIB_MATCH) dans
# $DOTLIB_DIR/local/theme.conf, le pose dans le shell courant et recharge. 2 = clé ou valeur inconnue.
dotlib_theme_set() {
  local k=$1 v=$2 f="$DOTLIB_DIR/local/theme.conf" line out=
  case $k:$v in
    DOTLIB_THEME:auto|DOTLIB_THEME:dark|DOTLIB_THEME:light|DOTLIB_MATCH:fond|DOTLIB_MATCH:texte) ;;
    DOTLIB_PALETTE:*) case " $DOTLIB_PALETTES " in *" $v "*) ;; *) return 2 ;; esac ;;
    *) return 2 ;;
  esac
  [ -d "$DOTLIB_DIR/local" ] || mkdir -p "$DOTLIB_DIR/local" || return 1
  if [ -r "$f" ]; then
    while IFS= read -r line; do case $line in "$k="*) ;; *) out="$out$line"$'\n' ;; esac; done < "$f"
  fi
  printf '%s%s=%s\n' "$out" "$k" "$v" > "$f" || return 1
  eval "$k=\$v"
  unset DOTLIB_THEME_DETECTED
  rm -f "$_DOTLIB_PROBE_CACHE" 2>/dev/null           # thème changé : le fond sera mesuré à nouveau
  dotlib_palette_load
}
