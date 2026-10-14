#!/bin/sh
# test/contract.sh — ce que dotlib garantit (API.md) et le contrat de pose (bin/deploy-local)
#
# Sous chaque bash présent (3.2 → 5.x). La pose est testée dans des HOME temporaires, avec un dépôt
# nu local à la place du réseau : ni le vrai HOME ni le réseau ne sont touchés.
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
if [ -t 1 ]; then G=$(printf '\033[32m'); R=$(printf '\033[31m'); N=$(printf '\033[0m'); else G=''; R=''; N=''; fi
FAIL=0; PASS=0
ok() { PASS=$((PASS + 1)); printf '  %s✓%s %s\n' "$G" "$N" "$1"; }
ko() { FAIL=$((FAIL + 1)); printf '  %s✗%s %s\n' "$R" "$N" "$1"; [ -n "${2:-}" ] && printf '%s\n' "$2" | head -6 | sed 's/^/      /'; }
TMP=$(mktemp -d "${TMPDIR:-/tmp}/dotlib-test.XXXXXX"); trap 'rm -rf "$TMP"' EXIT INT TERM
E=$(printf '\033')

# --- API, sous chaque bash --------------------------------------------------------------------------
FUNCS='dotlib_palette_load dotlib_pill dotlib_theme_set dotlib_have dotlib_need dotlib_install_hint dotlib_pkg_of'
TUIF='tui_title tui_info tui_ok tui_warn tui_err tui_die tui_confirm tui_ask tui_menu tui_need tui_table'
ROLES='C_R_NUM C_R_DATE C_R_TEXT C_R_MATCH C_R_KEY C_R_PATH C_R_BAD C_R_NOTE'
BASE='C_RESET C_BOLD C_DIM C_UL C_REV C_RED C_GREEN C_YELLOW C_BLUE C_MAGENTA C_CYAN C_GREY C_OK C_WARN C_ERR C_INFO'
TVARS='T_RESET T_BOLD T_DIM T_UL T_REV T_RED T_GREEN T_YELLOW T_BLUE T_MAGENTA T_CYAN T_GREY'
# Copie de dotlib SANS local/ : les réglages de l'utilisateur de cette machine ne doivent pas influer
CLEAN="$TMP/propre"; mkdir -p "$CLEAN"; cp -R "$ROOT/lib" "$CLEAN/"
b_() {   # b_ BASH TERM COMMANDE : shell propre, HOME vide, dotlib (copie propre) chargé
  env -i HOME="$TMP/h" PATH=/usr/bin:/bin TERM="$2" DOTLIB_DIR="$CLEAN" DOTLIB_THEME=dark "$1" -c ". \"\$DOTLIB_DIR/lib/dotlib.sh\"; $3" 2>&1
}
mkdir -p "$TMP/h"
for b in /bin/bash /opt/homebrew/bin/bash /usr/bin/bash /usr/local/bin/bash /opt/bin/bash; do
  [ -x "$b" ] || continue
  v=$("$b" -c 'echo ${BASH_VERSION%%(*}')
  out=$(b_ "$b" xterm-256color 'echo "api=$DOTLIB_API"')
  [ "$out" = "api=1" ] && ok "bash $v · chargement silencieux, DOTLIB_API=1" || ko "bash $v · chargement" "$out"
  out=$(b_ "$b" xterm-256color "for f in $FUNCS; do declare -F \$f >/dev/null || echo \"manque \$f\"; done")
  [ -z "$out" ] && ok "bash $v · fonctions garanties présentes" || ko "bash $v · fonctions" "$out"
  out=$(b_ "$b" xterm-256color "dotlib_palette_load; for v in $ROLES $BASE; do eval \"[ -n \\\"\\\${\$v:-}\\\" ]\" || echo \"vide \$v\"; done; echo \"\$DOTLIB_THEME_EFF \$DOTLIB_PALETTE_EFF\"")
  [ "$out" = "dark catppuccin" ] && ok "bash $v · 256 couleurs : rôles et couleurs de base définis, catppuccin sombre par défaut" || ko "bash $v · 256" "$out"
  out=$(b_ "$b" dumb "dotlib_palette_load; for v in $ROLES $BASE; do eval \"[ -z \\\"\\\${\$v:-}\\\" ]\" || echo \"non vide \$v\"; done")
  [ -z "$out" ] && ok "bash $v · TERM=dumb : aucune couleur" || ko "bash $v · dumb" "$out"
  out=$(b_ "$b" xterm-256color 'NO_COLOR=1; dotlib_palette_load; printf "%s" "$C_R_NUM$C_RED"')
  [ -z "$out" ] && ok "bash $v · NO_COLOR respecté" || ko "bash $v · NO_COLOR" "$out"
  out=$(b_ "$b" xterm-256color 'COLORTERM=truecolor; dotlib_palette_load; printf "%s" "$C_R_NUM"' | od -c | tr -d ' \n')
  case $out in *38\;2\;*) ok "bash $v · COLORTERM=truecolor : vraies couleurs" ;; *) ko "bash $v · truecolor" "$out" ;; esac
  out=$(b_ "$b" linux 'dotlib_palette_load; echo "$DOTLIB_COLORS $DOTLIB_THEME_EFF"')
  [ "$out" = "8 dark" ] && ok "bash $v · console linux : 8 couleurs" || ko "bash $v · console" "$out"
  out=$(b_ "$b" xterm-256color 'dotlib_palette_load; for p in $DOTLIB_PALETTES; do for t in dark light; do DOTLIB_PALETTE=$p DOTLIB_THEME=$t; dotlib_palette_load; [ "$DOTLIB_PALETTE_EFF" = $p ] && [ -n "$C_R_NUM" ] && [ -n "$C_R_MATCH" ] || echo "KO $p $t"; dotlib_pill BAD x t; [ -n "$DOTLIB_PILL" ] || echo "pastille $p $t"; done; done; set -- $DOTLIB_PALETTES; echo "n=$#"')
  [ "$out" = "n=11" ] && ok "bash $v · les 11 palettes se chargent, en sombre et en clair (rôles et pastille)" || ko "bash $v · palettes" "$out"
  out=$(b_ "$b" xterm-256color 'DOTLIB_PALETTE=actuel; dotlib_palette_load; echo $DOTLIB_PALETTE_EFF')
  [ "$out" = xterm ] && ok "bash $v · « actuel » accepté comme ancien nom de xterm" || ko "bash $v · actuel" "$out"
  out=$(b_ "$b" xterm-256color 'dotlib_palette_load; dotlib_pill BAD "!" "texte"; printf "%s" "$DOTLIB_PILL"')
  case $out in *"$E["*"texte"*"$E[0m") ok "bash $v · pastille en 256 couleurs" ;; *) ko "bash $v · pastille" "$out" ;; esac
  out=$(b_ "$b" dumb 'dotlib_palette_load; dotlib_pill BAD "!" "texte"; printf "%s" "$DOTLIB_PILL"')
  [ "$out" = "[texte]" ] && ok "bash $v · pastille sans couleur : [texte]" || ko "bash $v · pastille dumb" "$out"
  # Les ARRONDIS powerline de la pastille. Par défaut dès que le terminal peut les afficher, et non
  # plus « seulement sous Warp » : en ssh, l'hôte ne sait pas à quel terminal il parle (aucune variable
  # ne traverse ssh vers les NAS), alors que c'est le terminal qui AFFICHE qui dessine ces glyphes.
  # Les six combinaisons, parce que c'est un DÉFAUT et qu'un défaut se vérifie dans les deux sens.
  # b_() passe par « env -i » : une variable posée AVANT l'appel n'arrive pas dans le shell testé.
  # Mes deux premiers essais passaient pour cette mauvaise raison — le défaut mesuré était celui d'un
  # environnement vide, pas celui qu'on croyait régler. On donne donc les variables à env, nommément.
  PWL=$(printf '\356\202\266')        # U+E0B6 en UTF-8 (bash 3.2 ne connaît pas \u)
  ronds() {   # ronds "VAR=VAL …" : vrai si la pastille porte les arrondis powerline
    env -i HOME="$TMP/h" PATH=/usr/bin:/bin TERM=xterm-256color DOTLIB_DIR="$CLEAN" \
      DOTLIB_THEME=dark $1 "$b" -c '. "$DOTLIB_DIR/lib/dotlib.sh"; dotlib_palette_load
        dotlib_pill BAD "x" "t"; printf "%s" "$DOTLIB_PILL"' > "$TMP/pill" 2>&1
    LC_ALL=C grep -q "$PWL" "$TMP/pill"; }
  ronds "LANG=en_US.UTF-8" && ok "bash $v · pastille : arrondis par défaut en UTF-8" \
    || ko "bash $v · pas d'arrondis alors que le terminal peut" "$(cat -v "$TMP/pill")"
  ronds "LANG=en_US.UTF-8 DOTLIB_PILL_ROUND=0" && ko "bash $v · ROUND=0 n'a pas coupé les arrondis" \
    || ok "bash $v · pastille : DOTLIB_PILL_ROUND=0 les coupe (police sans ces glyphes)"
  ronds "LANG=C" && ko "bash $v · arrondis sous une locale non UTF-8" \
    || ok "bash $v · pastille : pas d'arrondis sans UTF-8"
  ronds "LANG=C DOTLIB_PILL_ROUND=1" && ok "bash $v · pastille : ROUND=1 force, même sans UTF-8" \
    || ko "bash $v · ROUND=1 n'a pas forcé" "$(cat -v "$TMP/pill")"
  ronds "LANG=en_US.UTF-8 DOTLIB_TERM=console" && ko "bash $v · arrondis sur la console" \
    || ok "bash $v · pastille : pas d'arrondis sur la console"
  # La forme PS1 : mêmes octets, chaque suite de séquences entourée de \001 \002. L'invariant est le
  # bon test — RETIRER les marqueurs doit rendre EXACTEMENT la pastille ordinaire —, parce qu'il
  # attrape à la fois un marqueur oublié et un marqueur posé autour d'un caractère qui s'affiche.
  # Ce second cas est le pire : readline compterait une colonne de moins et l'invite se corromprait
  # dès qu'on remonte dans l'historique, sans que rien ne paraisse à l'affichage initial.
  out=$(env -i HOME="$TMP/h" PATH=/usr/bin:/bin TERM=xterm-256color DOTLIB_DIR="$CLEAN" \
    DOTLIB_THEME=dark LANG=en_US.UTF-8 "$b" -c '. "$DOTLIB_DIR/lib/dotlib.sh"; dotlib_palette_load
      dotlib_pill BAD "x" "T"; a=$DOTLIB_PILL
      dotlib_pill -p BAD "x" "T"; b=$DOTLIB_PILL
      case $b in *$'"'"'\001'"'"'*) ;; *) echo "pas de marqueur"; exit ;; esac
      [ "$(printf %s "$b" | tr -d "\001\002")" = "$a" ] && echo identique || echo "diffère"')
  [ "$out" = identique ] && ok "bash $v · pastille -p : marqueurs \001/\002 autour des séquences, et d'elles seules" \
    || ko "bash $v · pastille -p" "$out"
  # LE TEXTE VISIBLE d'une pastille ne contient que l'icône et le texte. Assertion générale, et non
  # un rendu attendu au caractère près : ce qui casse, c'est un morceau de séquence d'échappement qui
  # fuit dans le visible. Avec une icône « x » et un texte « T », aucun chiffre ni point-virgule ne
  # doit subsister une fois les séquences retirées. Défaut trouvé ainsi : le « ;5 » de -c était collé
  # APRÈS le « m » en 8 couleurs, donc affiché — et, avec -p, compté comme invisible par readline,
  # ce qui décalait l'invite de deux colonnes sans que rien ne paraisse à l'affichage initial.
  bon=1
  for prof in 0 8 256; do
    for opt in "" "-c" "-p" "-p -c"; do
      vis=$(env -i HOME="$TMP/h" PATH=/usr/bin:/bin TERM=xterm-256color DOTLIB_DIR="$CLEAN" \
        DOTLIB_THEME=dark LANG=en_US.UTF-8 DOTLIB_COLORS=$prof "$b" -c \
        ". \"\$DOTLIB_DIR/lib/dotlib.sh\"; dotlib_palette_load; dotlib_pill $opt BAD x T
         printf %s \"\$DOTLIB_PILL\"" | LC_ALL=C tr -d '\001\002' | LC_ALL=C sed 's/'"$E"'\[[0-9;]*m//g')
      case $vis in *[0-9';']*)
        ko "bash $v · pastille $prof couleurs « $opt » : un morceau de séquence reste visible" \
           "$(printf %s "$vis" | cat -v)"; bon=0; break 2 ;;
      esac
      # sans couleur, le contrat dit « [TEXTE] » : pas d'icône, rien à colorer pour la porter
      if [ "$prof" = 0 ]; then attendu="[T]"; else attendu=x; fi
      case $vis in *"$attendu"*) ;; *)
        ko "bash $v · pastille $prof couleurs « $opt » : attendu « $attendu »" "$(printf %s "$vis" | cat -v)"
        bon=0; break 2 ;;
      esac
    done
  done
  [ "$bon" = 1 ] && ok "bash $v · pastille : rien que l'icône et le texte de visible (3 profondeurs × 4 formes)"
  out=$(b_ "$b" xterm-256color 'echo "$DOTLIB_API/$DOTLIB_REVISION"')
  [ "$out" = "1/3" ] && ok "bash $v · DOTLIB_API et DOTLIB_REVISION annoncés" || ko "bash $v · version" "$out"
  out=$(b_ "$b" xterm-256color 'dotlib_palette_load; dotlib_pill -p -c BAD "x" "T"
      case $DOTLIB_PILL in *";5m"*) echo clignote ;; *) echo non ;; esac')
  [ "$out" = clignote ] && ok "bash $v · pastille -c : cœur clignotant (SGR 5)" || ko "bash $v · pastille -c" "$out"
  # … et la règle UTF-8 n'existe QU'À UN endroit : tui.sh doit prendre ses glyphes de la même.
  out=$(b_ "$b" xterm-256color 'LC_ALL=C; . "$DOTLIB_DIR/lib/tui.sh" 2>/dev/null; printf "%s%s" "$TUI_OK" "$TUI_KO"')
  [ "$out" = "+x" ] && ok "bash $v · tui.sh prend ses glyphes de dotlib_utf8, sans copie de la règle" \
    || ko "bash $v · glyphes tui sous LC_ALL=C" "$out"
  rm -rf "$TMP/cfg"; mkdir -p "$TMP/cfg/lib"; cp "$ROOT"/lib/*.sh "$TMP/cfg/lib/"
  out=$(env -i HOME="$TMP/h" PATH=/usr/bin:/bin TERM=xterm-256color DOTLIB_DIR="$TMP/cfg" DOTLIB_THEME=dark "$b" -c '. "$DOTLIB_DIR/lib/dotlib.sh"
    dotlib_theme_set DOTLIB_PALETTE nord; echo "a=$? $DOTLIB_PALETTE_EFF"
    dotlib_theme_set DOTLIB_PALETTE inconnue; echo "b=$?"
    dotlib_theme_set DOTLIB_FOO x; echo "c=$?"' 2>&1)
  conf=$(cat "$TMP/cfg/local/theme.conf" 2>/dev/null)
  [ "$out" = "a=0 nord
b=2
c=2" ] && [ "$conf" = "DOTLIB_PALETTE=nord" ] && ok "bash $v · dotlib_theme_set : enregistre, refuse l'inconnu (2)" || ko "bash $v · theme_set" "$out / $conf"
  out=$(env -i HOME="$TMP/h" PATH=/usr/bin:/bin TERM=xterm-256color DOTLIB_DIR="$TMP/cfg" DOTLIB_THEME=dark "$b" -c '. "$DOTLIB_DIR/lib/dotlib.sh"; dotlib_palette_load; bash -c "echo \$DOTLIB_PALETTE_EFF \$DOTLIB_THEME_EFF"' 2>&1)
  [ "$out" = "nord dark" ] && ok "bash $v · réglage relu d'un autre shell ; palette et thème retenus exportés" || ko "bash $v · export" "$out"
  out=$(env -i HOME="$TMP/h" PATH=/usr/bin:/bin TERM=xterm-256color DOTLIB_DIR="$ROOT" "$b" -c ". \"\$DOTLIB_DIR/lib/tui.sh\"; for f in $TUIF; do declare -F \$f >/dev/null || echo \"manque \$f\"; done; for v in $TVARS; do eval \"[ -z \\\"\\\${\$v}\\\" ]\" || echo \"non vide \$v\"; done" 2>&1 </dev/null)
  [ -z "$out" ] && ok "bash $v · tui.sh : fonctions garanties, T_* vides hors terminal" || ko "bash $v · tui" "$out"
done

# --- Sonde du fond (OSC 11) : jamais hors d'un shell interactif sur terminal ; toujours restaurée ------
E=$(printf '\033')
for b in /bin/bash /opt/homebrew/bin/bash /usr/bin/bash; do
  [ -x "$b" ] || continue
  v=$("$b" -c 'echo ${BASH_VERSION%%(*}')
  L='. "$DOTLIB_DIR/lib/dotlib.sh"; DOTLIB_OS=linux; unset LC_DOTLIB_THEME DOTLIB_THEME_DETECTED COLORFGBG; dotlib_palette_load; echo "T=$DOTLIB_THEME_EFF"'
  out=$(env -i HOME="$TMP/h" PATH=/usr/bin:/bin TERM=xterm-256color DOTLIB_DIR="$CLEAN" "$b" -c "$L" 2>&1)
  out2=$(env -i HOME="$TMP/h" PATH=/usr/bin:/bin TERM=xterm-256color DOTLIB_DIR="$CLEAN" "$b" --norc -i -c "$L" 2>&1 </dev/null)
  case "$out$out2" in *"$E"*) ko "bash $v · sonde écrite hors terminal" "$(printf '%s' "$out$out2" | cat -v)" ;;
    *) ok "bash $v · sonde : rien d'écrit en non interactif ni sans terminal (ssh hôte cmd, scripts)" ;; esac
  # Frappes envoyées pendant le démarrage (ici : commande, exit, puis fin de flux = Ctrl-D) : la sonde ne
  # doit pas les avaler — sinon le shell attend sans fin. On vérifie qu'il se termine de lui-même.
  printf '. "$DOTLIB_DIR/lib/dotlib.sh"; DOTLIB_OS=linux; unset LC_DOTLIB_THEME DOTLIB_THEME_DETECTED COLORFGBG; dotlib_palette_load\n' > "$TMP/rc"
  ( printf 'echo x\nexit\n' | env -i HOME="$TMP/h" TERM=xterm-256color PATH=/usr/bin:/bin DOTLIB_DIR="$CLEAN" \
      script -q /dev/null "$b" --noprofile --rcfile "$TMP/rc" -i >/dev/null 2>&1 ) & pid=$!
  i=0; while kill -0 $pid 2>/dev/null && [ $i -lt 50 ]; do sleep 0.2; i=$((i + 1)); done
  if kill -0 $pid 2>/dev/null; then pkill -P $pid 2>/dev/null; kill $pid 2>/dev/null; ko "bash $v · frappes d'avance avalées : shell bloqué"
  else ok "bash $v · frappes envoyées au démarrage : pas avalées par la sonde (le shell se termine)"; fi
  case $v in 3.*)
    res=$( ( sleep 1; printf '%s\n' ". \"\$DOTLIB_DIR/lib/dotlib.sh\"; DOTLIB_OS=linux; unset LC_DOTLIB_THEME DOTLIB_THEME_DETECTED COLORFGBG; dotlib_palette_load; echo T=\$DOTLIB_THEME_EFF"; sleep 1.5; printf 'exit\n' ) \
           | env -i HOME="$TMP/h" TERM=xterm-256color PATH=/usr/bin:/bin DOTLIB_DIR="$CLEAN" script -q /dev/null "$b" --norc --noprofile -i 2>&1 | tr -d '\r')
    case $res in *']11;?'*) ko "bash $v · sonde envoyée en 3.2" ;; *T=dark*) ok "bash $v · bash 3.2 : pas de sonde (repli)" ;; *) ko "bash $v · 3.2" "$res" ;; esac
    continue ;;
  esac
  for m in light dark none int; do
    C="$L"; C=${C%%dotlib_palette_load*}"DOTLIB_PROBE_TIME=15; DOTLIB_PROBE_TTL=0; "
    [ $m = int ] && C="$C (sleep 0.5; kill -INT \$\$) & "
    C="$C dotlib_palette_load; echo \"T=\$DOTLIB_THEME_EFF\"; stty -a | grep -o -w -e icanon -e echo | sort -u | tr '\\n' ' '; echo FIN"
    res=$( ( sleep 1; printf '%s\n' "$C"; sleep 0.5
             case $m in (light) printf '\033]11;rgb:ffff/ffff/ffff\033\\' ;; (dark) printf '\033]11;rgb:1d1d/2020/2222\007' ;; esac
             sleep 2.5; printf 'exit\n'; sleep 0.3 ) \
           | env -i HOME="$TMP/h" TERM=xterm-256color PATH=/usr/bin:/bin DOTLIB_DIR="$CLEAN" script -q /dev/null "$b" --norc --noprofile -i 2>&1 \
           | tr -d '\r' | grep -a -o -E 'T=[a-z]+|echo icanon FIN' | tr '\n' ' ')
    want=dark; [ $m = light ] && want=light
    [ "$res" = "T=$want echo icanon FIN " ] && ok "bash $v · sonde $m → $want, terminal restauré (echo, icanon)" || ko "bash $v · sonde $m" "$res"
  done
done

# Le fond mesuré prime : sur un macOS (même en clair) et malgré un verdict « light » reçu par ssh
for b in /opt/homebrew/bin/bash /usr/bin/bash; do
  [ -x "$b" ] || continue
  v=$("$b" -c 'echo ${BASH_VERSION%%(*}')
  case $v in 3.*) continue ;; esac
  for cas in "DOTLIB_OS=darwin; unset LC_DOTLIB_THEME" "DOTLIB_OS=linux; LC_DOTLIB_THEME=light"; do
    C=". \"\$DOTLIB_DIR/lib/dotlib.sh\"; $cas; unset DOTLIB_THEME_DETECTED COLORFGBG SSH_CONNECTION; DOTLIB_PROBE_TIME=15; DOTLIB_PROBE_TTL=0; dotlib_palette_load; echo \"T=\$DOTLIB_THEME_EFF\""
    res=$( ( sleep 1; printf '%s\n' "$C"; sleep 0.5; printf '\033]11;rgb:1d1d/2020/2222\033\\'; sleep 2; printf 'exit\n'; sleep 0.3 ) \
           | env -i HOME="$TMP/h" TERM=xterm-256color PATH=/usr/bin:/bin DOTLIB_DIR="$CLEAN" script -q /dev/null "$b" --norc --noprofile -i 2>&1 \
           | tr -d '\r' | grep -a -o -E 'T=[a-z]+' | tail -1)
    [ "$res" = T=dark ] && ok "bash $v · fond sombre mesuré prime ($cas) → dark" || ko "bash $v · priorité de la sonde ($cas)" "$res"
  done
done

# Mémoire de la sonde : un second shell reprend le résultat sans sonder ; dotlib_theme_set l'efface
b=/opt/homebrew/bin/bash; [ -x "$b" ] || b=/usr/bin/bash
if [ -x "$b" ] && [ "$("$b" -c 'echo $((BASH_VERSINFO[0]*10+BASH_VERSINFO[1]))')" -ge 42 ]; then
  rm -f "$CLEAN/local/cache/fond"
  P='. "$DOTLIB_DIR/lib/dotlib.sh"; DOTLIB_OS=linux; unset LC_DOTLIB_THEME DOTLIB_THEME_DETECTED COLORFGBG; DOTLIB_PROBE_TIME=15;'
  sonde() {   # sonde RÉPONSE(light|none) COMMANDE_EN_PLUS → T=… (dernière valeur)
    ( sleep 1; printf '%s\n' "$P dotlib_palette_load; ${2:-} echo T=\$DOTLIB_THEME_EFF"; sleep 0.5
      [ "$1" = light ] && printf '\033]11;rgb:ffff/ffff/ffff\033\\'; sleep 2; printf 'exit\n'; sleep 0.3 ) \
      | env -i HOME="$TMP/h" TERM=xterm-256color PATH=/usr/bin:/bin DOTLIB_DIR="$CLEAN" script -q /dev/null "$b" --norc --noprofile -i 2>&1 \
      | tr -d '\r' | grep -a -o -E 'T=[a-z]+' | tail -1
  }
  [ "$(sonde light)" = T=light ] && [ -r "$CLEAN/local/cache/fond" ] && ok "sonde : résultat mémorisé (local/cache/fond)" || ko "mémoire écrite"
  [ "$(sonde none)" = T=light ] && ok "second shell sans réponse du terminal : résultat repris de la mémoire, pas de nouvelle sonde" || ko "mémoire relue"
  sonde none 'dotlib_theme_set DOTLIB_THEME auto;' >/dev/null
  [ ! -e "$CLEAN/local/cache/fond" ] || [ "$(cut -d'|' -f3 "$CLEAN/local/cache/fond")" != light ] && ok "dotlib_theme_set : mémoire effacée (le fond sera mesuré à nouveau)" || ko "invalidation"
  rm -f "$CLEAN/local/cache/fond" "$CLEAN/local/theme.conf"
  sonde light >/dev/null
  res=$( ( sleep 1; printf '%s\n' "$P dotlib_palette_load; echo T=\$DOTLIB_THEME_EFF"; sleep 2; printf 'exit\n'; sleep 0.3 ) \
         | env -i HOME="$TMP/h" TERM=xterm TERM_PROGRAM=autre PATH=/usr/bin:/bin DOTLIB_DIR="$CLEAN" DOTLIB_PROBE_TIME=10 script -q /dev/null "$b" --norc --noprofile -i 2>&1 | tr -d '\r' | grep -a -o -E 'T=[a-z]+' | tail -1)
  [ "$res" = T=dark ] && ok "autre terminal (TERM différent) : la mémoire d'un autre terminal n'est pas reprise" || ko "clé de mémoire" "$res"
  rm -f "$CLEAN/local/cache/fond"
fi

# --- share/terminal.tsv : la forme, et surtout la variante ------------------------------------------
# L'erreur qui arriverait vraiment n'est pas une faute de frappe, c'est une variante POSÉE À L'ENVERS :
# le jeu clair dans le thème sombre. Elle ne se voit pas en lisant le fichier, elle se voit en calculant
# la luminance du fond. D'où la dernière vérification.
T="$ROOT/share/terminal.tsv"
CLES_T="bg fg curseur curseur_texte selection selection_texte"
i=0; while [ $i -lt 16 ]; do CLES_T="$CLES_T ansi$i"; i=$((i + 1)); done
out=$(awk -F'\t' -v cles="$CLES_T" '
  /^#/ || /^[[:space:]]*$/ { next }
  NF != 4 { print "colonnes: " $0; next }
  $4 !~ /^[0-9a-f]{6}$/ { print "pas du RRGGBB: " $0 }
  { vu[$1 "\t" $2 "\t" $3] = 1; pal[$1] = 1; n++ }
  END {
    split(cles, c, " ")
    for (p in pal) for (t = 1; t <= 2; t++) {
      th = (t == 1 ? "dark" : "light")
      for (k in c) if (!((p "\t" th "\t" c[k]) in vu)) print "manque " p " " th " " c[k]
    }
    if (n != 22 * 22) print "lignes: " n " au lieu de 484"
  }' "$T")
[ -z "$out" ] && ok "share/terminal.tsv : 11 palettes × 2 thèmes × 22 clés, tout en RRGGBB" || ko "terminal.tsv" "$out"
out=$(b_ /bin/bash xterm-256color 'echo $DOTLIB_PALETTES' | tr ' ' '\n' | sort | grep -v '^$' |
      comm -3 - "$(awk -F'\t' '!/^#/ && NF==4 {print $1}' "$T" | sort -u > "$TMP/pt"; echo "$TMP/pt")")
[ -z "$out" ] && ok "share/terminal.tsv : exactement les palettes de \$DOTLIB_PALETTES" || ko "palettes de terminal.tsv" "$out"
out=$(awk -F'\t' '!/^#/ && NF==4 && $3 == "bg" {
        r = strtonum("0x" substr($4,1,2)); v = strtonum("0x" substr($4,3,2)); b = strtonum("0x" substr($4,5,2))
        luma = (299*r + 587*v + 114*b) / 1000
        vu = (luma > 128 ? "light" : "dark")
        if (vu != $2) print $1 " " $2 " : fond " $4 " (luma " int(luma) ") → " vu
      }' "$T")
[ -z "$out" ] && ok "share/terminal.tsv : chaque fond est du bon côté (pas de variante inversée)" || ko "variante inversée" "$out"

# --- dotlib_theme_refresh (révision 3) -------------------------------------------------------------
b=/opt/homebrew/bin/bash; [ -x "$b" ] || b=/usr/bin/bash
if [ -x "$b" ] && [ "$("$b" -c 'echo $((BASH_VERSINFO[0]*10+BASH_VERSINFO[1]))')" -ge 42 ]; then
  # TMP_TEMOIN est passé EXPRÈS à env -i : sans lui le « defaults » factice n'a nulle part où écrire,
  # et le test « un seul appel » passerait pour la mauvaise raison — il a commencé par le faire.
  r_() { env -i HOME="$TMP/h" PATH="$TMP/faux:/usr/bin:/bin" TERM=xterm-256color DOTLIB_DIR="$CLEAN" \
           TMP_TEMOIN="${TMP_TEMOIN:-$TMP/temoin}" \
           DOTLIB_COLORS=256 DOTLIB_PROBE=0 "$b" -c ". \"\$DOTLIB_DIR/lib/dotlib.sh\"; $1" 2>&1; }
  # « defaults » factice : il laisse une trace. Un appel en trop se voit, au lieu de se deviner.
  mkdir -p "$TMP/faux"
  printf '#!/bin/sh\necho appel >> "$TMP_TEMOIN"\necho Dark\n' > "$TMP/faux/defaults"
  chmod +x "$TMP/faux/defaults"

  out=$(r_ 'DOTLIB_THEME=dark; dotlib_palette_load; dotlib_theme_refresh; echo "$? $DOTLIB_THEME_EFF"')
  [ "$out" = "1 dark" ] && ok "dotlib_theme_refresh : thème forcé → 1, rien ne bouge" || ko "refresh forcé" "$out"

  out=$(r_ 'DOTLIB_THEME=auto COLORFGBG="0;15"; dotlib_palette_load; a=$C_R_TEXT
            COLORFGBG="15;0"; dotlib_theme_refresh; r=$?
            [ "$C_R_TEXT" = "$a" ] && c=figées || c=suivent
            echo "$r $DOTLIB_THEME_EFF $DOTLIB_THEME_DETECTED $c"')
  [ "$out" = "0 dark dark suivent" ] && ok "dotlib_theme_refresh : le fond change → 0, thème reposé, C_* rechargées" \
    || ko "refresh bascule" "$out"

  out=$(r_ 'DOTLIB_THEME=auto COLORFGBG="0;15"; dotlib_palette_load
            COLORFGBG="15;0"; dotlib_theme_refresh >/dev/null
            COLORFGBG="0;15"; dotlib_theme_refresh; echo -n "$? $DOTLIB_THEME_EFF "
            DOTLIB_THEME_WATCH=0 dotlib_theme_refresh; echo "$? $DOTLIB_THEME_EFF"')
  [ "$out" = "1 dark 0 light" ] && ok "dotlib_theme_refresh : étranglé par défaut, remesure avec DOTLIB_THEME_WATCH=0" \
    || ko "refresh étranglement" "$out"

  out=$(r_ 'DOTLIB_THEME=auto COLORFGBG="15;0"; dotlib_palette_load
            unset _DOTLIB_THEME_VU; dotlib_theme_refresh; echo "$? $DOTLIB_THEME_EFF"')
  [ "$out" = "1 dark" ] && ok "dotlib_theme_refresh : fond inchangé → 1 (l'appelant ne redessine pas pour rien)" \
    || ko "refresh inchangé" "$out"

  out=$(TMP_TEMOIN="$TMP/temoin-ssh" r_ '            DOTLIB_THEME=auto; unset COLORFGBG; DOTLIB_OS=darwin SSH_CONNECTION=x
            dotlib_palette_load; unset _DOTLIB_THEME_VU; dotlib_theme_refresh; echo $?')
  [ "$out" = 1 ] && [ ! -e "$TMP/temoin-ssh" ] && ok "dotlib_theme_refresh : en ssh, rien à mesurer et aucun processus lancé" \
    || ko "refresh ssh" "$out $(cat "$TMP/temoin-ssh" 2>/dev/null)"

  n=$(TMP_TEMOIN="$TMP/temoin-forces" r_ 'DOTLIB_THEME=dark; dotlib_palette_load
      i=0; while [ $i -lt 300 ]; do dotlib_theme_refresh; i=$((i + 1)); done; echo fini' >/dev/null
      wc -l < "$TMP/temoin-forces" 2>/dev/null || echo 0)
  [ "$(echo "$n" | tr -d ' ')" = 0 ] && ok "dotlib_theme_refresh : 300 appels en thème forcé, zéro processus lancé" \
    || ko "refresh : processus lancés en thème forcé" "$n"

  # Le témoin est remis à zéro APRÈS dotlib_palette_load : la mesure du démarrage du shell est
  # légitime, c'est le débit À L'INVITE qu'on compte ici.
  n=$(TMP_TEMOIN="$TMP/temoin-etrangle" r_ 'DOTLIB_THEME=auto; unset COLORFGBG
      DOTLIB_OS=darwin; unset SSH_CONNECTION; dotlib_palette_load; : > "$TMP_TEMOIN"
      i=0; while [ $i -lt 300 ]; do dotlib_theme_refresh; i=$((i + 1)); done' >/dev/null
      wc -l < "$TMP/temoin-etrangle" 2>/dev/null || echo 0)
  [ "$(echo "$n" | tr -d ' ')" = 1 ] && ok "dotlib_theme_refresh : 300 appels à l'invite, UN seul « defaults » (étranglement)" \
    || ko "refresh : $n appels à « defaults » au lieu d'un seul"
fi

# --- bin/iterm2-couleurs (révision 3) ---------------------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  I="$ROOT/bin/iterm2-couleurs"; P="$TMP/profil.json"
  ecrire_profil() { printf '%s\n' '{"Profiles":[{"Name":"Essai","Guid":"G","Has Hotkey":true,"Window Type":1}]}' > "$P"; }
  hexa() {   # hexa FICHIER CLÉ → RRGGBB de cette clé du premier profil
    python3 -c 'import json,sys
c = json.load(open(sys.argv[1]))["Profiles"][0][sys.argv[2]]
print("".join("%02x" % round(c[x + " Component"] * 255) for x in ("Red", "Green", "Blue")))' "$1" "$2" 2>&1
  }
  ecrire_profil
  "$I" --palette gruvbox --theme auto --verifier "$P" >/dev/null 2>&1
  [ $? = 3 ] && ok "iterm2-couleurs : --verifier sur un profil sans couleurs → 3 (il y aurait à écrire)" || ko "verifier 3"
  "$I" --palette gruvbox --theme auto "$P" >/dev/null 2>&1 && ok "iterm2-couleurs : pose → 0" || ko "pose"
  av=$(cat "$P")
  "$I" --palette gruvbox --theme auto "$P" >/dev/null 2>&1
  [ "$av" = "$(cat "$P")" ] && ok "iterm2-couleurs : deuxième passage, fichier INCHANGÉ (iTerm2 ne recharge pas pour rien)" \
    || ko "iterm2-couleurs : le fichier a été réécrit à l'identique"
  "$I" --palette gruvbox --theme auto --verifier "$P" >/dev/null 2>&1
  [ $? = 0 ] && ok "iterm2-couleurs : --verifier sur un profil conforme → 0" || ko "verifier 0"
  out=$(python3 -c 'import json,sys
p = json.load(open(sys.argv[1]))["Profiles"][0]
print(" ".join(k for k in p if "Color" not in k), p.get("Use Separate Colors for Light and Dark Mode"))' "$P")
  [ "$out" = "Name Guid Has Hotkey Window Type True" ] \
    && ok "iterm2-couleurs : les clés qui ne sont pas des couleurs sont intactes et dans l'ordre" || ko "clés voisines" "$out"
  attendu_d=$(awk -F'\t' '$1=="gruvbox" && $2=="dark" && $3=="bg" {print $4}' "$ROOT/share/terminal.tsv")
  attendu_c=$(awk -F'\t' '$1=="gruvbox" && $2=="light" && $3=="bg" {print $4}' "$ROOT/share/terminal.tsv")
  [ "$(hexa "$P" 'Background Color (Dark)')" = "$attendu_d" ] &&
  [ "$(hexa "$P" 'Background Color (Light)')" = "$attendu_c" ] &&
  [ "$(hexa "$P" 'Background Color')" = "$attendu_d" ] \
    && ok "iterm2-couleurs : auto → clair dans (Light), sombre dans (Dark) et sans suffixe" || ko "jeux clair/sombre"
  ecrire_profil; "$I" --palette gruvbox --theme light "$P" >/dev/null 2>&1
  [ "$(hexa "$P" 'Background Color (Dark)')" = "$attendu_c" ] \
    && ok "iterm2-couleurs : thème forcé → la même variante dans les deux jeux" || ko "thème forcé"
  "$I" --palette inconnue "$P" >/dev/null 2>&1; [ $? = 2 ] && ok "iterm2-couleurs : palette inconnue → 2" || ko "palette inconnue"
  "$I" "$TMP/pas-la.json" >/dev/null 2>&1; [ $? = 1 ] && ok "iterm2-couleurs : fichier absent → 1" || ko "fichier absent"
  printf '{ pas du json' > "$TMP/casse.json"
  "$I" "$TMP/casse.json" >/dev/null 2>&1; [ $? = 1 ] && ok "iterm2-couleurs : JSON invalide → 1" || ko "json invalide"
  printf '%s\n' '{"Profiles":[{"Name":"A"},{"Name":"B"}]}' > "$TMP/deux.json"
  "$I" "$TMP/deux.json" >/dev/null 2>&1; [ $? = 2 ] && ok "iterm2-couleurs : deux profils sans --profil → 2" || ko "deux profils"
  "$I" --profil B "$TMP/deux.json" >/dev/null 2>&1; [ $? = 0 ] && ok "iterm2-couleurs : --profil désigne le bon" || ko "--profil"
  "$I" --profil Fantome "$TMP/deux.json" >/dev/null 2>&1; [ $? = 1 ] && ok "iterm2-couleurs : profil nommé introuvable → 1" || ko "profil introuvable"
fi

# --- share/palettes.tsv à jour ----------------------------------------------------------------------
if "$ROOT/bin/palettes-tsv" | cmp -s - "$ROOT/share/palettes.tsv"; then ok "share/palettes.tsv à jour (bin/palettes-tsv)"
else ko "share/palettes.tsv périmé : bin/palettes-tsv > share/palettes.tsv"; fi

# --- Pose (bin/deploy-local) ------------------------------------------------------------------------
W="$TMP/work"; cp -R "$ROOT" "$W"; rm -rf "$W/local"
( cd "$W" && git add -A >/dev/null 2>&1 && git -c user.name=t -c user.email=t@t commit -qm test --allow-empty ) >/dev/null 2>&1
git clone -q --bare "$W" "$TMP/depot.git"
URL="$TMP/depot.git"
field() { printf '%s' "$1" | python3 -c "import json,sys; d=json.load(sys.stdin); print($2)" 2>/dev/null; }
run() {  # run HOME options… → OUT (stdout), RC ; les étapes vont dans $TMP/err
  h=$1; shift
  OUT=$(env HOME="$h" PATH="$PATH" sh -s -- --repo-url "$URL" "$@" < "$ROOT/bin/deploy-local" 2>"$TMP/err"); RC=$?
}
H="$TMP/vierge"; mkdir -p "$H"
run "$H" --check --json
[ $RC = 4 ] && [ "$(field "$OUT" "d['status']")" = absent ] && ok "machine vierge : --check par l'entrée standard → 4 (absent)" || ko "check vierge ($RC)" "$OUT"
run "$H" --yes --json --repo-url "$TMP/nulle-part.git"
[ $RC = 6 ] && [ ! -e "$H/.dotlib" ] && ok "dépôt inaccessible → 6, rien de créé" || ko "réseau ($RC)" "$OUT"
run "$H" --yes --json
[ $RC = 0 ] && [ "$(field "$OUT" "d['state']['kind']")" = git ] && [ "$(field "$OUT" "d['state']['shallow']")" = False ] \
  && [ "$(field "$OUT" "d['state']['posed_by']")" = parc ] && ok "pose : clone complet, 0, posé par parc" || ko "pose ($RC)" "$OUT $(cat "$TMP/err")"
[ "$(printf '%s\n' "$OUT" | wc -l | tr -d ' ')" = 1 ] && ok "--json : une seule ligne sur la sortie standard" || ko "sortie json" "$OUT"
C=$(git -C "$H/.dotlib" rev-parse --short HEAD)
run "$H" --check --json --expect "$C"
[ $RC = 0 ] && ok "--check --expect (même commit) → 0" || ko "expect même ($RC)" "$OUT"
run "$H" --check --json --expect 0000000
[ $RC = 5 ] && ok "--check --expect (autre commit) → 5" || ko "expect autre ($RC)" "$OUT"
mkdir -p "$H/.dotlib/local" && echo DOTLIB_PALETTE=nord > "$H/.dotlib/local/theme.conf"
( cd "$W" && echo "# v2" >> README.md && git -c user.name=t -c user.email=t@t commit -qam v2 && git push -q "$URL" HEAD:master ) >/dev/null 2>&1
run "$H" --yes --json
[ $RC = 0 ] && [ "$(field "$OUT" "d['action']")" = update ] && [ "$(cat "$H/.dotlib/local/theme.conf")" = DOTLIB_PALETTE=nord ] \
  && ok "mise à jour par fetch, local/ conservé" || ko "mise à jour ($RC)" "$OUT"
mkdir "$H/.dotlib.lock"
run "$H" --yes --json
[ $RC = 1 ] && case $OUT in *occupé*) true ;; *) false ;; esac && ok "verrou tenu par une autre pose → 1 (occupé), rien touché" || ko "verrou ($RC)" "$OUT"
touch -t 202001010000 "$H/.dotlib.lock"
run "$H" --check --json
[ "$(field "$OUT" "d['lock_stale']")" = True ] && ok "--check : verrou abandonné signalé" || ko "verrou abandonné" "$OUT"
run "$H" --yes --json
[ $RC = 0 ] && [ ! -d "$H/.dotlib.lock" ] && ok "verrou de plus de 10 minutes repris, puis libéré" || ko "reprise verrou ($RC)" "$OUT"
mkdir "$H/.dotlib.tmp.999"; touch -t 202001010000 "$H/.dotlib.tmp.999"
run "$H" --check --json
[ "$(field "$OUT" "d['leftovers']")" = .dotlib.tmp.999 ] && ok "--check : clone temporaire orphelin signalé" || ko "restes" "$OUT"
run "$H" --yes --json
[ ! -d "$H/.dotlib.tmp.999" ] && ok "pose suivante : restes nettoyés" || ko "nettoyage restes"
echo "# modif" >> "$H/.dotlib/lib/dotlib.sh"
run "$H" --check --json
[ $RC = 3 ] && ok "fichier suivi modifié sur place → 3 (dégradé)" || ko "dirty ($RC)" "$OUT"
run "$H" --yes --json
[ $RC = 1 ] && ok "… et la pose refuse d'y toucher" || ko "pose dirty ($RC)" "$OUT"
# Récupération par un shell : clone, puis le deploy-local DU CLONE l'adopte
H="$TMP/shell"; mkdir -p "$H"
git clone -q "$URL" "$H/.dotlib.tmp.42"
OUT=$(env HOME="$H" sh "$H/.dotlib.tmp.42/bin/deploy-local" --yes --json --quiet --posed-by shell --repo-url "$URL" --from-clone "$H/.dotlib.tmp.42" 2>"$TMP/err"); RC=$?
[ $RC = 0 ] && [ -f "$H/.dotlib/lib/dotlib.sh" ] && [ ! -e "$H/.dotlib.tmp.42" ] && [ "$(field "$OUT" "d['state']['posed_by']")" = shell ] \
  && [ ! -s "$TMP/err" ] && ok "--from-clone : clone adopté (mv), posé par shell, --quiet muet" || ko "from-clone ($RC)" "$OUT $(cat "$TMP/err")"
run "$H" --check --json
[ $RC = 0 ] && ok "… état identique à une pose par parc (0)" || ko "état après shell ($RC)" "$OUT"
H="$TMP/autre"; mkdir -p "$H"
git init -q "$H/.dotlib.tmp.7" && cp -R "$ROOT/lib" "$H/.dotlib.tmp.7/" && git -C "$H/.dotlib.tmp.7" remote add origin https://example.invalid/autre.git
OUT=$(env HOME="$H" sh "$ROOT/bin/deploy-local" --yes --json --repo-url "$URL" --from-clone "$H/.dotlib.tmp.7" 2>/dev/null); RC=$?
[ $RC = 1 ] && [ ! -e "$H/.dotlib" ] && [ ! -e "$H/.dotlib.tmp.7" ] && ok "--from-clone d'un autre dépôt : refusé, rien posé, clone supprimé" || ko "from-clone étranger ($RC)" "$OUT"
# Copie sans git → clone
H="$TMP/copie"; mkdir -p "$H/.dotlib/local"; cp -R "$ROOT/lib" "$H/.dotlib/"; echo garde > "$H/.dotlib/local/x"
run "$H" --check --json
[ $RC = 3 ] && [ "$(field "$OUT" "d['kind']")" = copie ] && ok "copie sans git : dégradée (3)" || ko "copie ($RC)" "$OUT"
run "$H" --yes --json
[ $RC = 0 ] && [ -d "$H/.dotlib/.git" ] && [ "$(cat "$H/.dotlib/local/x")" = garde ] && ok "copie → clone, local/ conservé" || ko "copie → clone ($RC)" "$OUT"
run "$H" --purge --yes --json
[ ! -e "$H/.dotlib" ] && ok "--purge : tout effacé" || ko "purge ($RC)" "$OUT"

# « à jour » et « impossible de savoir » ne sont pas la même chose. On coupe l'accès au dépôt par un
# faux git : --check --remote doit répondre « reseau » (6), pas « ok » (0). Un appelant qui lit « ok »
# conclurait qu'il n'a rien à faire, alors qu'il n'en sait rien.
H="$TMP/injoignable"; mkdir -p "$H"
run "$H" --yes --json >/dev/null 2>&1
FAUXGIT=$TMP/fauxgit; mkdir -p "$FAUXGIT"
printf '#!/bin/sh\ncase "$1" in ls-remote) exit 128 ;; esac\nexec %s "$@"\n' "$(command -v git)" > "$FAUXGIT/git"
chmod 755 "$FAUXGIT/git"
OUT=$(HOME="$H" PATH="$FAUXGIT:$PATH" sh "$ROOT/bin/deploy-local" --check --remote --json 2>&1); RC=$?
[ $RC = 6 ] && [ "$(field "$OUT" "d['remote_vu']")" = False ] \
  && ok "dépôt injoignable : « impossible de savoir » (6), pas « à jour »" || ko "injoignable ($RC)" "$OUT"
OUT=$(HOME="$H" sh "$ROOT/bin/deploy-local" --check --json 2>&1); RC=$?
[ $RC != 6 ] && ok "sans --remote : aucun accès au dépôt, aucun verdict sur le distant" || ko "sans --remote ($RC)" "$OUT"

# --- js() : un octet qui n'est pas de l'UTF-8 valide ne doit pas tronquer le JSON -------------------
# Sous macOS en locale UTF-8, un tel octet fait QUITTER sed, tr, awk et cut. Un message d'erreur de git
# peut en citer un : le champ serait alors tronqué, le document invalide, et l'appelant perdrait TOUS
# les champs en silence — c'est le défaut du 28/09 (une couleur ANSI rendait le JSON illisible et
# l'interface affichait « dégradé — » sans dire pourquoi). Signalé par la session ~/.bash le 06/10.
# Le test extrait js() du script et la nourrit d'octets invalides, sous une locale UTF-8 explicite.
# Extraction de la fonction entière, quelle que soit sa longueur : de sa première ligne jusqu'à
# celle qui la ferme. Un « head -4 » se périmerait au premier retour à la ligne ajouté.
extrait_js=$(LC_ALL=C awk '/^js\(\) \{/{p=1} p{print} p && /; \}$/{exit}' "$ROOT/bin/deploy-local")
[ -n "$extrait_js" ] || ko "js() : fonction introuvable dans bin/deploy-local (test inopérant)" ""
sale=$(printf 'erreur \351\350 git: pathspec \377\376 inconnu')
OUT=$(LC_ALL=fr_FR.UTF-8 sh -c "$extrait_js
js \"\$1\"" _ "$sale" 2>/dev/null)
# le résultat doit être un champ JSON COMPLET : guillemet ouvrant, guillemet fermant, et le texte entre
case $OUT in
  '"'*'"') ok "js() : un octet non-UTF-8 ne tronque pas le champ JSON" ;;
  *) ko "js() : champ tronqué sous locale UTF-8" "$OUT" ;;
esac
case $OUT in
  *"erreur"*) ok "js() : le début du message survit" ;;
  *) ko "js() : le début du message a disparu" "$OUT" ;;
esac
case $OUT in
  *"inconnu"*) ok "js() : et la FIN aussi (c'est elle que la troncature emportait)" ;;
  *) ko "js() : la fin du message a été coupée" "$OUT" ;;
esac
# et le JSON produit par --check reste lisible quoi qu'il arrive
run "$H" --check --json
printf '%s' "$OUT" | python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null \
  && ok "--check --json : document valide au sens strict" || ko "--check --json : JSON invalide" "$OUT"

printf '\n%s%d réussis%s, %d échecs\n' "$G" "$PASS" "$N" "$FAIL"
[ $FAIL -eq 0 ]
