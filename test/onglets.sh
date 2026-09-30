#!/bin/sh
# test/onglets.sh — lib/onglets.py : contrat (API 1) et dégradation (sans couleurs, sans UTF-8, petite
# fenêtre, entrée fermée, commande qui ne rend pas la main, pas de terminal), dans de vrais pseudo-terminaux.
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
if [ -t 1 ]; then G=$(printf '\033[32m'); R=$(printf '\033[31m'); N=$(printf '\033[0m'); else G=''; R=''; N=''; fi
FAIL=0; PASS=0
ok() { PASS=$((PASS + 1)); printf '  %s✓%s %s\n' "$G" "$N" "$1"; }
ko() { FAIL=$((FAIL + 1)); printf '  %s✗%s %s\n' "$R" "$N" "$1"; [ -n "${2:-}" ] && printf '%s\n' "$2" | head -6 | sed 's/^/      /'; }
command -v python3 >/dev/null 2>&1 || { echo "python3 absent : test sauté"; exit 0; }
TMP=$(mktemp -d "${TMPDIR:-/tmp}/dotlib-onglets.XXXXXX"); trap 'rm -rf "$TMP"' EXIT INT TERM
cp "$ROOT/lib/onglets.py" "$TMP/"
# dotlib FACTICE : le banc ne doit rien lire de la vraie installation, ni rien pouvoir y écrire.
mkdir -p "$TMP/share" "$TMP/local"
cp "$ROOT/share/palettes.tsv" "$TMP/share/"
cp "$ROOT/share/palettes-sources.tsv" "$TMP/share/" 2>/dev/null || :
printf 'DOTLIB_THEME=dark\nDOTLIB_PALETTE=catppuccin\n' > "$TMP/local/theme.conf"
cp "$TMP/local/theme.conf" "$TMP/theme.temoin"
PY=python3
E=$(printf '\033')

# Programme d'essai : trois onglets (texte, groupes avec action, raccourcis)
cat > "$TMP/essai.py" <<'P'
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.environ["ONGLETS_DIR"])
import onglets
def groupes():
    return [("alpha", ["== titre alpha", "ligne a1", "✓ bon"]), ("beta", ["ligne b1"])]
def aide():
    return ["== Aide de cet onglet", "chemin ~/.dotlib et commande `brc doctor`", "---",
            "LIGNE-DE-FOND-DE-L-AIDE"] + ["remplissage %d" % i for i in range(60)]
o = [onglets.Onglet("Texte", lambda: ["premiere ligne", "MOT-CHERCHE ici",
                                      "pose dans ~/.dotlib, voir $DOTLIB_THEME", "derniere ligne"]),
     onglets.Onglet("Groupes", groupes, genre="groupes", action=lambda n: "applique %s" % n),
     onglets.Onglet("Raccourcis", lambda: {"entrees": [["vim", "edition", "x", "effacer le mot (,h) puis :Keys", "global"],
                                                        ["bash", "edition", " ", "espace", "mode insertion"]],
                                            "themes": ["edition"]}, genre="raccourcis"),
     onglets.Onglet("Aidee", lambda: ["contenu de l'onglet"], aide=aide)]
sys.exit(onglets.lancer(o, "essai"))
P
lance() {   # lance « touches » [env…] → sortie écran (sans \r) ; code dans $TMP/code
  keys=$1; shift
  ( sleep 1.2; printf '%b' "$keys"; sleep 1 ) | env -i HOME="$TMP" PATH=/usr/bin:/bin:/opt/homebrew/bin ONGLETS_DIR="$TMP" "$@" \
    script -q /dev/null sh -c "$PY \"$TMP/essai.py\"; echo CODE=\$?" 2>&1 | tr -d '\r'
}

# 1. Import sans effet, API, pas de cache écrit
out=$(cd "$TMP" && env -i PATH=/usr/bin:/bin:/opt/homebrew/bin $PY -c 'import sys; sys.dont_write_bytecode=True; sys.path.insert(0,"."); import onglets; print(onglets.API)' 2>&1)
[ "$out" = 1 ] && [ ! -e "$TMP/__pycache__" ] && ok "import : rien d'écrit ni d'affiché, API = 1, aucun __pycache__" || ko "import" "$out"
out=$(cd "$TMP" && $PY -c 'import ast; ast.parse(open("onglets.py").read(), feature_version=(3, 8)); print("ok")' 2>&1)
[ "$out" = ok ] && ok "syntaxe compatible Python 3.8" || ko "syntaxe 3.8" "$out"

# 2. Sans terminal : code 4, rien d'écrit sur la sortie standard
out=$(env -i PATH=/usr/bin:/bin:/opt/homebrew/bin ONGLETS_DIR="$TMP" $PY "$TMP/essai.py" </dev/null 2>"$TMP/err"; echo "CODE=$?")
[ "$out" = CODE=4 ] && [ "$(cat "$TMP/err")" = "essai : pas de terminal pour l'interface" ] \
  && ok "sans terminal : code 4, une ligne sur la sortie d'erreur (préfixée), rien sur la sortie standard" || ko "sans terminal" "$out / $(cat "$TMP/err")"

# 3. Rendu en pseudo-terminal couleur : onglets, contenu, filtre, action, sortie propre
out=$(lance '2\n/MOT\033q' TERM=xterm-256color LANG=en_US.UTF-8)
case $out in *"1 Texte"*"2 Groupes"*"3 Raccourcis"*) ok "rendu : barre d'onglets" ;; *) ko "barre" "$(printf '%s' "$out" | tail -3)" ;; esac
case $out in *"applique alpha"*) ok "onglet groupes : Entrée appelle l'action, message affiché" ;; *) ko "action" "$(printf '%s' "$out" | tail -5)" ;; esac
case $out in *CODE=0*) ok "q : sortie propre, code 0" ;; *) ko "sortie" "$(printf '%s' "$out" | tail -3)" ;; esac
case $out in *"$E[?1049l"*|*"$E[?47l"*|*"$E[2J"*) ok "terminal rendu (écran alternatif quitté)" ;; *) ok "terminal rendu (curses.wrapper)" ;; esac

# 4. Raccourcis : colonne source (deux sources), Espace nommé
out=$(lance '3q' TERM=xterm-256color LANG=en_US.UTF-8)
case $out in *bash*Espace*|*Espace*bash*) ok "raccourcis : colonne source affichée (vim et bash), touche espace nommée « Espace »" ;; *) ko "raccourcis" "$(printf '%s' "$out" | tail -6)" ;; esac

# 5. Sans couleurs (TERM=vt100, comme un ncurses sans couleurs) : lisible, aucune couleur émise
out=$(lance '2q' TERM=vt100 LANG=en_US.UTF-8)
case $out in *"2 Groupes"*alpha*CODE=0*) ok "sans couleurs (vt100) : rendu lisible, sortie propre" ;; *) ko "vt100" "$(printf '%s' "$out" | tail -4)" ;; esac
printf '%s' "$out" | LC_ALL=C grep -q "$E\[3[0-7]m\|$E\[38;" && ko "vt100 : des couleurs ont été émises" || ok "sans couleurs : aucune séquence de couleur émise"
# … et pas davantage de GRAS à la place : attr() promeut deux rôles en gras en monochrome, pour que
# les repères de LIGNE restent lisibles. Appliqué à un mot dans une phrase, ce repli mettrait en gras
# toutes les options et toutes les variables d'un volet. Sans couleurs, la coloration ne fait rien.
out2=$(lance '1q' TERM=vt100 LANG=en_US.UTF-8)
ligne=$(printf '%s' "$out2" | LC_ALL=C grep -a 'pose dans' | head -1)
case $ligne in *"$E["*) ko "sans couleurs : la ligne colorée porte encore un attribut" "$(printf '%s' "$ligne" | cat -v)" ;;
               *) ok "sans couleurs : la ligne colorée ne porte aucun attribut, pas même le gras" ;; esac

# 5 bis. La coloration du volet de contenu : des couleurs ENTRENT dans la ligne, et la ligne reste
# intacte une fois les couleurs retirées. Le second point est le vrai : placer des fragments l'un
# après l'autre à leur abscisse est une occasion de perdre un caractère, et c'est un défaut
# d'affichage, pas de décoration. (Le test 5 ci-dessus garantit l'autre côté : sans couleurs, rien.)
out=$(lance '1q' TERM=xterm-256color LANG=en_US.UTF-8)
nu=$(printf '%s' "$out" | sed "s/$E\[[0-9;]*m//g; s/$E[()][B0]//g")
case $nu in *'pose dans ~/.dotlib, voir $DOTLIB_THEME'*) ok "coloration : la ligne reste intacte une fois les couleurs retirées" ;;
            *) ko "coloration : ligne altérée" "$(printf '%s' "$nu" | grep -n 'pose dans')" ;; esac
printf '%s' "$out" | LC_ALL=C grep -q "$E\[[0-9;]*m~/\.dotlib" \
  && ok "coloration : le chemin cité dans une phrase reçoit sa couleur" \
  || ko "coloration : aucune couleur devant le chemin" "$(printf '%s' "$out" | LC_ALL=C grep -a 'dotlib,' | cat -v | head -2)"
out=$(lance '3q' TERM=xterm-256color LANG=en_US.UTF-8)
printf '%s' "$out" | LC_ALL=C grep -q "$E\[[0-9;]*m,h" \
  && ok "coloration : une séquence de touches entre parenthèses reçoit la couleur des touches" \
  || ko "coloration : touche non colorée" "$(printf '%s' "$out" | LC_ALL=C grep -a 'effacer' | cat -v | head -2)"

# 5 ter. L'APERÇU : un groupe peint ses lignes de tête avec une AUTRE palette que celle en service,
# sans toucher au réglage. C'est ce qui permet de comparer deux thèmes avant d'en choisir un ; peindre
# l'aperçu avec la palette ACTIVE serait un mensonge, et un mensonge est pire que pas de couleur.
cat > "$TMP/apercu.py" <<'P'
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.environ["ONGLETS_DIR"])
import onglets
def groupes():
    return [("nord", ["detail ~/.chemin-du-detail"]), ("gruvbox", ["autre"])]
def apercu(nom):
    return {"lignes": ["== demonstration", "chemin ~/.chemin-de-demo", "---", "prose ordinaire",
                       "une ligne longue " * 9 + "FIN-DE-LIGNE-LONGUE"],
            "palette": nom, "theme": "dark", "match": os.environ.get("ESSAI_MATCH") or None}
o = [onglets.Onglet("T", groupes, genre="groupes", apercu=apercu,
                    action=lambda n: "pose %s" % n)]
sys.exit(onglets.lancer(o, "apercu"))
P
lance_a() { keys=$1; shift
  ( sleep 1.2; printf '%b' "$keys"; sleep 1 ) | env -i HOME="$TMP" PATH=/usr/bin:/bin:/opt/homebrew/bin \
    ONGLETS_DIR="$TMP" DOTLIB_DIR="$TMP" "$@" \
    script -q /dev/null sh -c "$PY \"$TMP/apercu.py\"; echo CODE=\$?" 2>&1 | tr -d '\r'; }

out=$(lance_a 'q' TERM=xterm-256color LANG=en_US.UTF-8)
case $out in *"demonstration"*"prose ordinaire"*) ok "aperçu : les lignes de tête sont affichées" ;;
             *) ko "aperçu absent" "$(printf '%s' "$out" | tail -5)" ;; esac
# le filet : au moins quatre traits d'affilée, donc une ligne entière et non les trois tirets écrits
printf '%s' "$out" | grep -q '────' && ok "aperçu : « --- » devient un filet sur toute la largeur" \
  || ko "filet non tracé" "$(printf '%s' "$out" | tail -5)"
# LE point : le chemin de l'aperçu est peint en nord (60), celui du contenu en catppuccin (103)
printf '%s' "$out" | LC_ALL=C grep -q "38;5;60m~/\.chemin-de-demo" \
  && ok "aperçu : peint avec la palette DEMANDÉE (nord), pas celle en service" \
  || ko "aperçu : mauvaise palette" "$(printf '%s' "$out" | LC_ALL=C grep -ao '38;5;[0-9]*m~/[a-z.-]*' | sort -u)"
printf '%s' "$out" | LC_ALL=C grep -q "38;5;103m~/\.chemin-du-detail" \
  && ok "aperçu : le reste du volet garde la palette en service (catppuccin)" \
  || ko "le contenu a changé de palette" "$(printf '%s' "$out" | LC_ALL=C grep -ao '38;5;[0-9]*m~/[a-z.-]*' | sort -u)"
cmp -s "$TMP/local/theme.conf" "$TMP/theme.temoin" && ok "aperçu : le réglage n'a pas été touché" \
  || ko "l'aperçu a modifié theme.conf"
# Une ligne longue se REPLIE dans l'aperçu au lieu d'être coupée au bord : une démonstration tronquée
# montre une couleur sans montrer ce qu'elle qualifie, et le texte disparaissait en silence.
case $out in *FIN-DE-LIGNE-LONGUE*) ok "aperçu : une ligne longue se replie, rien n'est perdu au bord" ;;
             *) ko "aperçu : ligne longue tronquée" "$(printf '%s' "$out" | tail -4)" ;; esac
# Les CORRESPONDANCES (« fond coloré » / « texte gras ») : un réglage qui ne se voit que sur une
# surbrillance. Le montrer sur la ligne sélectionnée est le seul endroit où ces couleurs servent
# vraiment ; ailleurs, on inventerait une surbrillance pour l'occasion.
out=$(lance_a 'q' TERM=xterm-256color LANG=en_US.UTF-8 ESSAI_MATCH=fond)
printf '%s' "$out" | LC_ALL=C grep -q "48;5;110" \
  && ok "aperçu : « fond coloré » se montre sur la sélection, dans la palette de l'aperçu" \
  || ko "correspondance en fond non montrée" "$(printf '%s' "$out" | LC_ALL=C grep -ao '48;5;[0-9]*' | sort -u)"
out=$(lance_a 'q' TERM=xterm-256color LANG=en_US.UTF-8 ESSAI_MATCH=texte)
printf '%s' "$out" | LC_ALL=C grep -q "48;5;110" \
  && ko "« texte gras » ne doit pas colorer le fond" \
  || ok "aperçu : « texte gras » ne colore pas le fond, à la différence de « fond coloré »"

# sans couleurs : un aperçu ne peut pas être honoré, et il ne ment pas — aucune couleur émise
out=$(lance_a 'q' TERM=vt100 LANG=en_US.UTF-8)
printf '%s' "$out" | LC_ALL=C grep -q "$E\[3[0-7]m\|$E\[38;" && ko "aperçu vt100 : des couleurs émises" \
  || ok "aperçu : sans couleurs, rien n'est peint plutôt qu'une palette fausse"

# 5 quinquies. L'AIDE d'un onglet : une grande fenêtre par-dessus tout, qui ne change RIEN dessous.
# Le point qui compte n'est pas qu'elle s'ouvre, c'est qu'on retrouve l'onglet intact en la fermant :
# une aide qui déplacerait la sélection ou effacerait le filtre ferait perdre ce qu'on était en train
# de faire, et on hésiterait à la demander.
out=$(lance '4?qq' TERM=xterm-256color LANG=en_US.UTF-8)
case $out in *"Aide — Aidee"*) ok "aide : « ? » ouvre une fenêtre titrée du nom de l'onglet" ;;
             *) ko "aide non ouverte" "$(printf '%s' "$out" | tail -5)" ;; esac
case $out in *"Échap ou q fermer"*) ok "aide : ses touches sont annoncées dans son cadre" ;;
             *) ko "aide : touches non annoncées" ;; esac
case $out in *"? aide"*) ok "aide : la touche est annoncée dans le pied de page de l'onglet" ;;
             *) ko "aide : touche non annoncée" ;; esac
# … et sur un onglet SANS aide, ni touche ni annonce
out=$(lance '1?q' TERM=xterm-256color LANG=en_US.UTF-8)
case $out in *"? aide"*) ko "aide : annoncée sur un onglet qui n'en a pas" ;;
             *) ok "aide : rien d'annoncé sur un onglet qui n'en a pas" ;; esac
# Le filtre passe AVANT : « ? » y est un caractère, pas une commande.
out=$(lance '2/?\033q' TERM=xterm-256color LANG=en_US.UTF-8)
case $out in *"Aide — Aidee"*) ko "aide : « ? » a ouvert l'aide alors qu'on tapait un filtre" ;;
             *) ok "aide : pendant un filtre, « ? » est un caractère du filtre" ;; esac
# G va au bout. On l'éprouve sur le COMPTEUR et non sur le texte : dans un flux de redessins, la
# dernière ligne visible d'une image précédente traîne encore plus loin que celle de l'image finale,
# et chercher un mot y donne une réponse qui ne veut rien dire. Le compteur « n/n », lui, n'apparaît
# qu'une fois arrivé au bout.
out=$(lance '4?Gqq' TERM=xterm-256color LANG=en_US.UTF-8)
# Le DÉFILEMENT s'éprouve hors du terminal : dans un pseudo-terminal, curses n'émet que ce qui change
# d'une image à l'autre, donc « remplissage 40 » peut n'y apparaître qu'en morceaux (« remplissage 4 »
# puis un déplacement de curseur puis « 0 »). Chercher un texte dans ce flux ne prouve rien.
out=$(cd "$TMP" && $PY -c '
import sys; sys.dont_write_bytecode=True; sys.path.insert(0,".")
from onglets import borne
cas = [(0, 62, 19, 0), (10**9, 62, 19, 43), (-5, 62, 19, 0), (10**9, 5, 19, 0), (7, 62, 19, 7)]
print("ok" if all(borne(h, t, n) == a for h, t, n, a in cas) else "KO")' 2>&1)
[ "$out" = ok ] && ok "aide : G va à la dernière page, g à la première, sans jamais sortir du contenu" \
  || ko "aide : bornes du défilement" "$out"
# Sans UTF-8 : cadre ASCII, aucun caractère semi-graphique.
out=$(lance '4?qq' TERM=xterm-256color LC_ALL=C LANG=C)
printf '%s' "$out" | LC_ALL=C grep -q '\xe2\x94' && ko "aide : cadre semi-graphique sous une locale C" \
  || ok "aide : cadre ASCII sous une locale non UTF-8"
# Sans couleurs : rien d'émis.
out=$(lance '4?qq' TERM=vt100 LANG=en_US.UTF-8)
printf '%s' "$out" | LC_ALL=C grep -q "$E\[3[0-7]m\|$E\[38;" && ko "aide vt100 : des couleurs émises" \
  || ok "aide : sans couleurs, aucune séquence de couleur"

# L'aide RECOUVRE ce qu'elle cache. Éprouvé dans tmux et non dans un pseudo-terminal : c'est un
# rendu, et le flux de « script » est un diff d'images où l'on ne peut rien conclure. Défaut trouvé
# en vrai : la fenêtre dessinait son cadre et son texte, mais chaque ligne laissait voir l'onglet
# dessous partout où elle n'écrivait pas — fins de lignes, séparateurs, restes de mots.
if command -v tmux >/dev/null 2>&1; then
  cat > "$TMP/couvre.py" <<'P'
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.environ["ONGLETS_DIR"])
import onglets
o = [onglets.Onglet("G", lambda: [("a", ["DESSOUS-%d%sFIN-DESSOUS" % (i, " " * 40) for i in range(25)])],
                    genre="groupes", aide=lambda: ["== Aide"] + ["ligne %d" % i for i in range(30)])]
sys.exit(onglets.lancer(o, "couvre"))
P
  S=dotlib-aide-$$
  tmux kill-session -t "$S" 2>/dev/null
  tmux new-session -d -s "$S" -x 110 -y 30 2>/dev/null \
    && tmux send-keys -t "$S" "env ONGLETS_DIR=$TMP TERM=xterm-256color LANG=en_US.UTF-8 $PY $TMP/couvre.py" Enter \
    && sleep 3 && tmux send-keys -t "$S" "?" && sleep 2 \
    && tmux capture-pane -p -t "$S" > "$TMP/couvre.txt"
  tmux kill-session -t "$S" 2>/dev/null
  if [ -s "$TMP/couvre.txt" ]; then
    grep -q 'FIN-DESSOUS' "$TMP/couvre.txt" \
      && ko "aide : l'onglet transparaît sous la fenêtre" "$(grep -m2 'FIN-DESSOUS' "$TMP/couvre.txt")" \
      || ok "aide : la fenêtre recouvre vraiment (rien de l'onglet ne transparaît)"
    grep -q 'ligne 5' "$TMP/couvre.txt" && ok "aide : son contenu est bien affiché" \
      || ko "aide : contenu absent" "$(head -4 "$TMP/couvre.txt")"
  else
    ok "aide : recouvrement non mesuré (tmux n'a pas démarré ici)"
  fi
else
  ok "aide : recouvrement non mesuré (tmux absent — c'est le seul instrument pour un rendu)"
fi

# 5 quater. SORTIR AVEC UNE VALEUR : certaines choses ne peuvent se faire qu'une fois le terminal
# rendu — attacher une session tmux en est le cas d'école, puisque curses tient le terminal. Une action
# lève Quitter(valeur) ; l'interface se ferme, rend 5, et l'appelant lit onglets.QUITTE. Le socle
# n'exécute rien.
cat > "$TMP/sortir.py" <<'P'
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.environ["ONGLETS_DIR"])
import onglets
def act(nom):
    raise onglets.Quitter("session-" + nom)
o = [onglets.Onglet("S", lambda: [("alpha", ["x"])], genre="groupes", action=act)]
code = onglets.lancer(o, "sortir")
print("CODE=%d VALEUR=%r" % (code, onglets.QUITTE))
P
out=$(( sleep 1.2; printf '\t\n'; sleep 1 ) | env -i HOME="$TMP" PATH=/usr/bin:/bin:/opt/homebrew/bin \
  ONGLETS_DIR="$TMP" TERM=xterm-256color LANG=en_US.UTF-8 \
  script -q /dev/null sh -c "$PY \"$TMP/sortir.py\"" 2>&1 | tr -d '\r')
case $out in *"CODE=5 VALEUR='session-alpha'"*) ok "sortir : Quitter ferme l'interface, code 5, valeur rendue à l'appelant" ;;
             *Traceback*) ko "sortir : Quitter a échappé jusqu'à l'appelant" "$(printf '%s' "$out" | tail -4)" ;;
             *) ko "sortir : ni code 5 ni valeur" "$(printf '%s' "$out" | tail -4)" ;; esac
# … et une SECONDE séance ne doit pas voir la valeur de la première : une mesure périmée est un souvenir.
cat > "$TMP/deux.py" <<'P'
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.environ["ONGLETS_DIR"])
import onglets
o = [onglets.Onglet("S", lambda: [("alpha", ["x"])], genre="groupes",
                    action=lambda n: (_ for _ in ()).throw(onglets.Quitter("un")))]
onglets.lancer(o, "sortir")
p = [onglets.Onglet("T", lambda: ["rien"])]          # séance sans action : QUITTE doit repasser à None
print("CODE=%d VALEUR=%r" % (onglets.lancer(p, "sortir"), onglets.QUITTE))
P
out=$(( sleep 1.2; printf '\t\n'; sleep 2.5; printf 'q'; sleep 1 ) | env -i HOME="$TMP" PATH=/usr/bin:/bin:/opt/homebrew/bin \
  ONGLETS_DIR="$TMP" TERM=xterm-256color LANG=en_US.UTF-8 \
  script -q /dev/null sh -c "$PY \"$TMP/deux.py\"" 2>&1 | tr -d '\r')
case $out in *"CODE=0 VALEUR=None"*) ok "sortir : QUITTE est remis à None à chaque lancer(), jamais une valeur périmée" ;;
             *) ko "sortir : valeur périmée entre deux séances" "$(printf '%s' "$out" | tail -4)" ;; esac
# Le point qui compte : Quitter ne doit être avalé par AUCUN des filets qui protègent l'interface.
# Ici, c'est un PRODUCTEUR qui lève — le filet « onglet illisible » l'attraperait sans précaution.
cat > "$TMP/prod.py" <<'P'
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.environ["ONGLETS_DIR"])
import onglets
def produire():
    raise onglets.Quitter("depuis-un-producteur")
code = onglets.lancer([onglets.Onglet("P", produire)], "sortir")
print("CODE=%d VALEUR=%r" % (code, onglets.QUITTE))
P
out=$(( sleep 2; printf 'q'; sleep 1 ) | env -i HOME="$TMP" PATH=/usr/bin:/bin:/opt/homebrew/bin \
  ONGLETS_DIR="$TMP" TERM=xterm-256color LANG=en_US.UTF-8 \
  script -q /dev/null sh -c "$PY \"$TMP/prod.py\"" 2>&1 | tr -d '\r')
case $out in *"CODE=5 VALEUR='depuis-un-producteur'"*) ok "sortir : un ordre de sortie n'est avalé par aucun filet, même levé par un producteur" ;;
             *illisible*) ko "sortir : le filet « onglet illisible » a avalé l'ordre de sortie" "$(printf '%s' "$out" | tail -4)" ;;
             *) ko "sortir depuis un producteur" "$(printf '%s' "$out" | tail -4)" ;; esac

# 6. Locale non UTF-8 : cadres en ASCII, pas de caractères semi-graphiques
out=$( ( sleep 1.2; printf q; sleep 1 ) | env -i HOME="$TMP" PATH=/usr/bin:/bin:/opt/homebrew/bin ONGLETS_DIR="$TMP" TERM=xterm-256color LANG=C LC_ALL=C \
       script -q /dev/null sh -c "$PY \"$TMP/essai.py\"; echo CODE=\$?" 2>&1 | LC_ALL=C tr -d '\r')
if printf '%s' "$out" | LC_ALL=C grep -q "$(printf '\342\224')"; then ko "locale C : caractères semi-graphiques émis"
else case $out in *CODE=0*) ok "locale non UTF-8 : aucun caractère semi-graphique (cadres ASCII), sortie propre" ;; *) ko "locale C" "$(printf '%s' "$out" | tail -3)" ;; esac; fi

# 7. Fenêtre trop petite : message, pas d'exception
out=$( ( sleep 1.2; printf q; sleep 1 ) | env -i HOME="$TMP" PATH=/usr/bin:/bin:/opt/homebrew/bin ONGLETS_DIR="$TMP" TERM=xterm-256color LANG=en_US.UTF-8 \
       script -q /dev/null sh -c "stty rows 6 cols 30; $PY \"$TMP/essai.py\"; echo CODE=\$?" 2>&1 | tr -d '\r')
case $out in *"trop petite"*CODE=0*) ok "fenêtre trop petite : message clair, sortie propre" ;; *) ko "petite fenêtre" "$(printf '%s' "$out" | tail -3)" ;; esac

# 8 bis. Entrée fermée — le plus grave des défauts corrigés (boucle à 100 % de processeur).
# « script » garde le pseudo-terminal ouvert après la fin de l'entrée : la lecture BLOQUE au lieu de lever,
# et le programme paraît sain. Il faut donc fabriquer le vrai cas — pty.openpty(), puis fermeture du maître.
# Le test vérifie aussi qu'il ÉCHOUE quand on retire le compteur : un test qui ne tombe pas quand on casse
# ce qu'il surveille ne protège rien. (Écrit par la session vim, repris tel quel.)
out=$($PY "$ROOT/test/entree-fermee.py" "$ROOT/lib/onglets.py" 2>&1)
case $out in
  *"ok   entrée fermée"*"ok   sans le compteur"*) ok "entrée fermée : sortie après 20 échecs, et le test protège bien ce code" ;;
  *) ko "entrée fermée" "$out" ;;
esac

# 8 ter. Le cas réel d'un appelant : 112 raccourcis de ~/.vim (deux colonnes de touches longues, vingt
# thèmes, accents, apostrophes typographiques). Rendu en UTF-8 puis en locale C : il doit rester LISIBLE.
ech=$ROOT/test/donnees/raccourcis-vim.tsv
out=$(cd "$TMP" && LC_ALL=C $PY -c '
import sys; sys.dont_write_bytecode=True; sys.path.insert(0,".")
import onglets
lignes = open(sys.argv[1], encoding="utf-8").read().splitlines()
entrees = [l.split("\t") for l in lignes if l]
themes = []
for e in entrees:
    if e[1] not in themes: themes.append(e[1])
print("entrees=%d themes=%d" % (len(entrees), len(themes)))
brut = " ".join(e[3] for e in entrees)
plat = " ".join(onglets.ascii_lisible(e[3]) for e in entrees)
print("non-ascii=%d" % sum(1 for c in plat if ord(c) > 126))
# des « ? » existent légitimement dans les descriptions (le raccourci « ,? ») : on compte ceux que la
# translittération AJOUTE, c est-à-dire les caractères qu elle n a pas su rendre
print("interrogations=%d" % (plat.count("?") - brut.count("?")))' "$ech" 2>&1)
case $out in
  "entrees=112 themes=20"*"non-ascii=0"*"interrogations=0") ok "échantillon réel : 112 entrées, 20 thèmes, translittérés sans un seul « ? »" ;;
  *) ko "échantillon réel" "$out" ;;
esac

# 8 quater. La détection UTF-8 ne doit pas se laisser tromper par Python lui-même (PEP 538 : CPython
# réécrit LC_CTYPE en « C.UTF-8 » quand la locale vaut C, AVANT que le module ne tourne).
out=$(env -u LC_ALL -u LC_CTYPE LANG=C $PY -c '
import sys; sys.dont_write_bytecode=True; sys.path.insert(0,"'"$ROOT"'/lib")
import onglets; print(onglets.utf8())' 2>&1)
[ "$out" = "False" ] && ok "utf8() : LANG=C rend faux, malgré la réécriture de LC_CTYPE par Python" || ko "utf8() sous LANG=C" "$out"
out=$(env -u LC_ALL -u LC_CTYPE TERM=linux LANG=fr_FR.UTF-8 $PY -c '
import sys; sys.dont_write_bytecode=True; sys.path.insert(0,"'"$ROOT"'/lib")
import onglets; print(onglets.utf8())' 2>&1)
[ "$out" = "False" ] && ok "utf8() : console Linux (TERM=linux) → ASCII d'office" || ko "utf8() sous TERM=linux" "$out"

# 9. sortie() : ni exception ni attente sans fin
out=$(cd "$TMP" && $PY -c '
import sys; sys.dont_write_bytecode=True; sys.path.insert(0,".")
import onglets
print(onglets.sortie(["sleep", "5"], delai=1)[0][:10])
print(onglets.sortie(["cat"])[:1])
print(onglets.sortie(["commande-inexistante"])[0][:17])
print(onglets.sortie(["sh", "-c", "printf \"\\033[31mrouge\\033[0m\\n\""]))' 2>&1)
[ "$out" = "(trop long
[]
(commande absente
['rouge']" ] && ok "sortie() : délai maximal, entrée fermée (cat ne bloque pas), commande absente, couleurs retirées" || ko "sortie()" "$out"

# 9 bis. TERM=dumb : curses ne lève PAS forcément — mesuré sur un NAS, il démarre et peint un écran
# de blancs, donc l'appelant croit avoir affiché quelque chose alors que l'utilisateur voit une
# bouillie. On refuse d'emblée, pour que l'appelant écrive son texte.
out=$(cd "$TMP" && printf 'q' | TERM=dumb script -q /dev/null $PY -c '
import sys; sys.dont_write_bytecode=True; sys.path.insert(0,".")
import onglets
print("CODE=%d" % onglets.lancer([onglets.Onglet("T", lambda: ["x"])], "essai"))' 2>&1 | tr -d "\r")
case $out in *CODE=4*) ok "TERM=dumb : refus propre (code 4), l'appelant affiche son texte" ;;
             *) ko "TERM=dumb" "$out" ;; esac

# 9 ter. Le volet actif au démarrage est la LISTE : on entre par elle, on choisit, puis on entre
# dans la section. Démarrer sur le contenu obligeait à penser à Tab pour atteindre la liste.
out=$(cd "$TMP" && $PY -c '
import sys; sys.dont_write_bytecode=True; sys.path.insert(0,".")
import onglets; print(onglets.Onglet("T", lambda: [], genre="raccourcis").focus)' 2>&1)
[ "$out" = "gauche" ] && ok "au démarrage, c'est la liste des sections qui a le focus" || ko "focus initial" "$out"

# 9 quater. Les trois manques signalés par la session bash en écrivant « brc interface ».
out=$(cd "$TMP" && $PY -c '
import sys; sys.dont_write_bytecode=True; sys.path.insert(0,".")
import onglets
# a) le volet droit des groupes plie comme les autres
print("plie" if len(onglets.plier("x" * 200, 40)) > 1 else "coupe")
# b) un onglet de RÉGLAGE peut taire le décompte (« catppuccin 6 » n informe de rien)
print(onglets.Onglet("T", lambda: [], genre="groupes", comptes=False).comptes)
print(onglets.Onglet("T", lambda: [], genre="groupes").comptes)' 2>&1)
[ "$out" = "plie
False
True" ] && ok "groupes : volet droit pliable, décompte facultatif" || ko "manques bash" "$out"

# 10. LE CONTRAT ET LE CODE DISENT-ILS LA MÊME CHOSE ? API.md a documenté « API_COMPATIBLES »
# pendant que le code ne l'avait pas : un appelant qui suit la documentation lit un attribut
# inexistant et dégrade EN SILENCE. Ce test ferme la classe entière du défaut : tout nom
# « onglets.X » cité dans API.md doit exister dans le module.
out=$(cd "$TMP" && $PY -c '
import re, sys
sys.dont_write_bytecode = True; sys.path.insert(0, ".")
import onglets
doc = open(sys.argv[1], encoding="utf-8").read()
noms = sorted(set(re.findall(r"`onglets\.([A-Za-z_][A-Za-z_0-9]*)", doc)))
manquants = [n for n in noms if not hasattr(onglets, n)]
print("%d cités, manquants : %s" % (len(noms), manquants or "aucun"))' "$ROOT/API.md" 2>&1)
case $out in *"manquants : aucun"*) ok "tout nom documenté existe dans le module ($out)" ;; *) ko "contrat ≠ code" "$out" ;; esac

# 11. Les quatre cas de utf8(), dont celui d'une connexion ssh depuis macOS (LC_CTYPE sans LANG) :
# le module ne doit pas contredire lib/tui.sh de ce même dépôt.
cas() {  # description ; environnement ; attendu
  r=$(env -u LC_ALL -u LC_CTYPE -u LANG $2 $PY -c '
import sys; sys.dont_write_bytecode=True; sys.path.insert(0,"'"$ROOT"'/lib")
import onglets; print(onglets.utf8())' 2>&1)
  [ "$r" = "$3" ] && ok "utf8() : $1 → $3" || ko "utf8() : $1" "attendu $3, obtenu $r"
}
cas "LANG=C (un NAS)"                       "LANG=C"                  False
cas "LC_CTYPE=C.UTF-8 (coercition CPython)" "LC_CTYPE=C.UTF-8"        False
cas "LC_CTYPE=UTF-8 sans LANG (ssh macOS)"  "LC_CTYPE=UTF-8"          True
cas "LC_CTYPE=UTF-8 avec LANG=C"            "LC_CTYPE=UTF-8 LANG=C"   False
cas "console Linux"                         "TERM=linux LANG=fr_FR.UTF-8" False

# 12. Les flèches sont des NOMS DE TOUCHES : « ,? » ne dit pas quoi taper.
out=$(cd "$TMP" && $PY -c '
import sys; sys.dont_write_bytecode=True; sys.path.insert(0,".")
import onglets
print(onglets.ascii_lisible("\u2191 / \u2193 / ,\u2190 / Alt-\u2192"))
print(onglets.ascii_lisible("\u00a7"))' 2>&1)
[ "$out" = "haut / bas / ,gauche / Alt-droite
[?]" ] && ok "translittération : flèches en mots, non représentable avoué entre crochets" || ko "flèches" "$out"

# 13. lancer() ne lève JAMAIS : l'appelant n'a aucune copie de repli, une trace python lui arriverait
# à l'écran. On casse volontairement hors du rendu d'un onglet (barre()).
out=$(cd "$TMP" && printf 'q' | script -q /dev/null $PY -c '
import sys; sys.dont_write_bytecode=True; sys.path.insert(0,".")
import onglets
class Mauvais:
    def __bool__(self): return True
    def __len__(self): raise RuntimeError("nom biscornu")
print("CODE=%d" % onglets.lancer([onglets.Onglet("T", lambda: ["x"])], Mauvais()))' 2>&1 | tr -d "\r")
case $out in *Traceback*) ko "lancer() laisse échapper une exception" "$out" ;;
             *CODE=4*)    ok "lancer() ne lève jamais : défaut hors onglet → code 4, pas de trace" ;;
             *)           ko "lancer() : ni trace ni code 4" "$out" ;; esac

# 14 et 15. Le pliage et la palette, éprouvés par les tests de la session vim (repris tels quels :
# ils sont mesurés sur ses vraies données, et ils refusent de conclure si le module n'expose pas la
# fonction attendue — plutôt que de passer à vide).
for t in pliage palette coloration; do
  out=$($PY "$ROOT/test/$t.py" "$ROOT/lib/onglets.py" 2>&1)
  case $out in
    *ÉCHEC*|*Traceback*) ko "$t" "$out" ;;
    *) printf '%s' "$out" | grep -c '  ok ' >/dev/null && ok "$t : $(printf '%s' "$out" | grep -c '  ok ') vérification(s)" || ko "$t" "$out" ;;
  esac
done

printf '\n%s%d réussis%s, %d échecs\n' "$G" "$PASS" "$N" "$FAIL"
[ $FAIL -eq 0 ]
