# lib/tui.sh — petite bibliothèque d'interface pour des outils en ligne de commande (bash 3.2+)
#
# À sourcer en tête d'un outil (DOTLIB_DIR : racine de dotlib, défaut ~/.dotlib) :
#   . "${DOTLIB_DIR:-$HOME/.dotlib}/lib/tui.sh"
#
# Fournit :
#   tui_title TEXTE · tui_info · tui_ok · tui_warn · tui_err · tui_die TEXTE [code]
#   tui_confirm "Question ?" [o|n]          0 = oui (défaut sur Entrée ; TUI_YES=1 : oui)
#   tui_ask VAR "Question" [défaut]         lit une réponse (défaut sur Entrée)
#   tui_menu VAR "Titre" [défaut] -- choix1 choix2 …   menu aux flèches (↑↓ ou j/k, Entrée, q),
#                                            repli en liste numérotée si le terminal est limité ;
#                                            VAR reçoit le texte choisi, TUI_INDEX son rang (1…)
#   tui_need cmd…                           outil manquant → message + commande d'installation
#   tui_table                               aligne des colonnes séparées par des tabulations (stdin)
#   Couleurs : T_RESET T_BOLD T_DIM T_UL T_REV T_RED T_GREEN T_YELLOW T_BLUE T_MAGENTA T_CYAN T_GREY,
#   et celles de lib/palette.sh (C_*, C_R_*) : vides si la sortie n'est pas un terminal
#   TUI_INTERACTIVE=1 si stdin et stdout sont des terminaux ; TUI_OK TUI_KO TUI_WARN TUI_PTR (glyphes)
#
# Aucun tput : séquences ANSI directes (tput manque sur certains systèmes).

[ -n "${_TUI_LOADED:-}" ] && return 0
_TUI_LOADED=1

: "${DOTLIB_DIR:=$HOME/.dotlib}"
[ -n "${DOTLIB_OS:-}" ] || . "$DOTLIB_DIR/lib/platform.sh"
declare -F dotlib_have >/dev/null || . "$DOTLIB_DIR/lib/hints.sh"
declare -F dotlib_palette_load >/dev/null || . "$DOTLIB_DIR/lib/palette.sh"

TUI_INTERACTIVE=0
[ -t 0 ] && [ -t 1 ] && TUI_INTERACTIVE=1

# Couleurs seulement vers un terminal ; profondeur héritée (DOTLIB_COLORS) ou déduite
if [ ! -t 1 ] || [ -n "${NO_COLOR:-}" ]; then DOTLIB_COLORS=0; fi
dotlib_palette_load
T_RESET=$C_RESET T_BOLD=$C_BOLD T_DIM=$C_DIM T_UL=$C_UL T_REV=$C_REV
T_RED=$C_RED T_GREEN=$C_GREEN T_YELLOW=$C_YELLOW T_BLUE=$C_BLUE
T_MAGENTA=$C_MAGENTA T_CYAN=$C_CYAN T_GREY=$C_GREY
TUI_OK='✓' TUI_KO='✗' TUI_WARN='!' TUI_PTR='›'
case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in *[Uu][Tt][Ff]*8*) ;; *) TUI_OK='+' TUI_KO='x' TUI_PTR='>' ;; esac
[ "${TERM:-}" = linux ] && TUI_OK='+' TUI_KO='x' TUI_PTR='>'

tui_title() { printf '\n%s%s== %s ==%s\n' "$T_BOLD" "$T_CYAN" "$*" "$T_RESET"; }
tui_info()  { printf '  %s\n' "$*"; }
tui_ok()    { printf '  %s%s%s %s\n' "$T_GREEN" "$TUI_OK" "$T_RESET" "$*"; }
tui_warn()  { printf '  %s%s%s %s\n' "$T_YELLOW" "$TUI_WARN" "$T_RESET" "$*" >&2; }
tui_err()   { printf '  %s%s%s %s\n' "$T_RED" "$TUI_KO" "$T_RESET" "$*" >&2; }
tui_die()   { tui_err "$1"; exit "${2:-1}"; }

# tui_confirm "Question ?" [o|n]
tui_confirm() {
  local def=${2:-n} hint ans
  [ "${TUI_YES:-0}" = 1 ] && return 0
  if [ "$TUI_INTERACTIVE" = 0 ]; then [ "$def" = o ]; return; fi
  if [ "$def" = o ]; then hint='[O/n]'; else hint='[o/N]'; fi
  printf '%s%s%s %s ' "$T_BOLD" "$1" "$T_RESET" "$hint"
  read -r ans || ans=
  [ -n "$ans" ] || ans=$def
  case $ans in [oOyY]*) return 0 ;; *) return 1 ;; esac
}

# tui_ask VAR "Question" [défaut]
tui_ask() {
  local __var=$1 __q=$2 __def=${3:-} __ans
  if [ "$TUI_INTERACTIVE" = 0 ] || [ "${TUI_YES:-0}" = 1 ]; then eval "$__var=\$__def"; return; fi
  printf '%s%s%s%s ' "$T_BOLD" "$__q" "$T_RESET" "${__def:+ ${T_DIM}[$__def]${T_RESET}}"
  read -r __ans || __ans=
  [ -n "$__ans" ] || __ans=$__def
  eval "$__var=\$__ans"
}

# tui_menu VAR "Titre" [défaut] -- choix…
tui_menu() {
  local __var=$1 __title=$2 __def=1 __n __i __key __rest __sel
  shift 2
  if [ "${1:-}" != -- ]; then __def=$1; shift; fi
  [ "${1:-}" = -- ] && shift
  __n=$#
  [ "$__n" -gt 0 ] || return 1
  if [ "$TUI_INTERACTIVE" = 0 ] || [ "${TUI_YES:-0}" = 1 ]; then
    TUI_INDEX=$__def; eval "$__var=\${$__def}"; return 0
  fi
  local -a __opts=("$@")
  __sel=$(( __def - 1 ))
  printf '%s%s%s\n' "$T_BOLD" "$__title" "$T_RESET"
  if [ "${TERM:-dumb}" = dumb ] || [ "${TUI_SIMPLE:-0}" = 1 ]; then
    for (( __i = 0; __i < __n; __i++ )); do printf '  %2d) %s\n' $((__i + 1)) "${__opts[__i]}"; done
    printf 'Choix [%d] : ' "$__def"; read -r __key || __key=
    case $__key in ''|*[!0-9]*) __key=$__def ;; esac
    [ "$__key" -ge 1 ] && [ "$__key" -le "$__n" ] || __key=$__def
    TUI_INDEX=$__key; eval "$__var=\${__opts[__key-1]}"; return 0
  fi
  printf '\e[?25l'                                   # curseur masqué pendant le menu
  while :; do
    for (( __i = 0; __i < __n; __i++ )); do
      if [ $__i -eq $__sel ]; then printf '\r\e[K  %s%s %s%s\n' "$T_CYAN$T_BOLD" "$TUI_PTR" "${__opts[__i]}" "$T_RESET"
      else printf '\r\e[K    %s\n' "${__opts[__i]}"; fi
    done
    IFS= read -rsn1 __key
    case $__key in
      $'\e') read -rsn2 __rest; case $__rest in '[A'|'OA') __key=up ;; '[B'|'OB') __key=down ;; *) __key= ;; esac ;;
      k) __key=up ;; j) __key=down ;; '') __key=enter ;; q) __key=quit ;;
      [1-9]) [ "$__key" -le "$__n" ] && { __sel=$(( __key - 1 )); __key=enter; } ;;
    esac
    case $__key in
      up)    __sel=$(( (__sel + __n - 1) % __n )) ;;
      down)  __sel=$(( (__sel + 1) % __n )) ;;
      enter) break ;;
      quit)  printf '\e[?25h'; return 1 ;;
    esac
    printf '\e[%dA' "$__n"                           # remonter pour redessiner
  done
  printf '\e[?25h'
  TUI_INDEX=$(( __sel + 1 )); eval "$__var=\${__opts[__sel]}"
  return 0
}

# tui_need cmd… : 0 si tout est là, sinon explique et renvoie 1
tui_need() {
  local c miss=0
  for c in "$@"; do
    dotlib_have "$c" && continue
    tui_err "outil manquant : $c — $(dotlib_install_hint "$c")"
    miss=1
  done
  return $miss
}

# tui_table : colonnes séparées par des tabulations → alignées (les codes couleur ne comptent pas)
tui_table() {
  # awk en octets (LC_ALL=C) ; on retire les octets de continuation UTF-8 pour compter les caractères
  LC_ALL=C awk -F '\t' '
    function vis(s) { gsub(/\033\[[0-9;]*m/, "", s); gsub(/[\200-\277]/, "", s); return length(s) }
    { for (i = 1; i <= NF; i++) { cell[NR, i] = $i; w = vis($i); if (w > max[i]) max[i] = w }
      if (NF > nf) nf = NF; rows = NR }
    END { for (r = 1; r <= rows; r++) { line = ""
            for (i = 1; i <= nf; i++) { c = cell[r, i]; pad = max[i] - vis(c)
              line = line c (i < nf ? sprintf("%" (pad + 2) "s", "") : "") }
            print line } }'
}

# Trap commun : rétablir le curseur si l'outil est interrompu dans un menu
trap '[ -t 1 ] && printf "\e[?25h"' EXIT
