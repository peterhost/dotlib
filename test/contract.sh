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

printf '\n%s%d réussis%s, %d échecs\n' "$G" "$PASS" "$N" "$FAIL"
[ $FAIL -eq 0 ]
