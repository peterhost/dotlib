# lib/palette.sh — la routine de couleurs : une palette, un thème (clair/sombre), une profondeur
#
# bash 3.2+, aucun processus lancé (sauf « defaults » sur macOS en thème auto, une fois : le
# résultat est exporté). Réglage de l'utilisateur : $DOTLIB_DIR/local/theme.conf (dotlib_theme_set),
# lignes CLÉ=valeur ; une variable d'environnement du même nom l'emporte.
#   DOTLIB_PALETTE  catppuccin (défaut) | gruvbox | nord | solarized | tokyonight | xterm
#                   (xterm : palette 256 couleurs historique ; « actuel », son ancien nom, reste accepté)
#   DOTLIB_THEME    auto (défaut) | dark | light
#                   auto : COLORFGBG, sinon LC_DOTLIB_THEME (transmis par ssh), sinon apparence macOS,
#                   sinon sombre ; console linux : sombre
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
DOTLIB_PALETTES='catppuccin gruvbox nord solarized tokyonight xterm'

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
  DOTLIB_THEME_EFF=dark
  if [ -n "${COLORFGBG:-}" ]; then          # « fg;bg » (rxvt, Konsole, iTerm2 si activé…)
    bg=${COLORFGBG##*;}
    case $bg in 7|9|1[0-5]) DOTLIB_THEME_EFF=light ;; esac
  elif [ -n "${LC_DOTLIB_THEME:-}" ]; then     # transmis par ssh depuis le Mac (SendEnv LC_*)
    DOTLIB_THEME_EFF=$LC_DOTLIB_THEME
  elif [ "${DOTLIB_OS:-}" = darwin ] && [ -z "${SSH_CONNECTION:-}" ]; then
    # Apparence macOS (y compris le mode automatique jour/nuit) : « Dark » ou rien. ≈ 7 ms, une fois :
    # le résultat est exporté aux shells enfants
    case $(defaults read -g AppleInterfaceStyle 2>/dev/null) in Dark) ;; *) DOTLIB_THEME_EFF=light ;; esac
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
  dotlib_palette_load
}
