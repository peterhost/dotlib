#!/usr/bin/env python3
"""coloration.py — decouper() colore ce qui n'est pas de la prose, et RIEN D'AUTRE.

    python3 coloration.py ~/.dotlib/lib/onglets.py [test/donnees/raccourcis-vim.tsv]

Trois choses valent d'être tenues, dans cet ordre d'importance :

1. AUCUN CARACTÈRE PERDU NI AJOUTÉ. Les fragments sont placés à l'écran l'un après l'autre, chacun à
   son abscisse : si la découpe perd un caractère, la ligne s'affiche fausse — un défaut d'affichage,
   pas seulement de couleur. On recolle donc et on compare à l'original.
2. CE QUI DOIT ÊTRE COLORÉ L'EST, avec le bon genre : séquences de touches, commandes Ex, chemins,
   options, variables du shell.
3. CE QUI NE DOIT PAS L'ÊTRE NE L'EST PAS, et c'est le plus fragile. Une grammaire trop gourmande
   repeint la phrase entière, et un volet entièrement coloré est aussi illisible qu'un volet
   entièrement blanc. Sur l'échantillon réel, on impose donc un PLAFOND : moins d'un quart des
   caractères colorés. Un test sans plafond laisserait passer exactement la régression qui compte.
"""
import sys
sys.dont_write_bytecode = True
import importlib.machinery
import importlib.util
import os

# (texte, {fragment attendu: genre attendu}) — pris de vraies descriptions, pas inventés.
CAS = [
    ("aide sur le mot sous le curseur (,h), recherche dans toute l’aide (,H)",
     {",h": "touche", ",H": "touche"}),
    ("l’aide des raccourcis (,? puis un thème avec :Keys)",
     {",?": "touche", ":Keys": "commande"}),
    ("éditer ~/.bashrc", {"~/.bashrc": "chemin"}),
    ("reporter (Dp) ou récupérer (Dg) le bloc sous le curseur",
     {"Dp": "touche", "Dg": "touche"}),
    ("suivre un lien (Entrée), revenir en arrière (Retour arrière)", {"Entrée": "touche"}),
    ("lots actifs : brc lot --liste, $BRC_LOTS, voir /etc/profile",
     {"--liste": "option", "$BRC_LOTS": "variable", "/etc/profile": "chemin"}),
    ("recharge ${HOME}/.profile", {"${HOME}": "variable", "/.profile": "chemin"}),
    # Relevés sur les VRAIS volets des deux outils, une fois la coloration posée. Chacun de ces cas
    # était peint à tort, et chacun le serait de nouveau si la grammaire se relâchait.
    ("machine   inconnue · darwin/macos · bash 5.3.15(1)-release", {}),   # ni touche ni option
    ("Modules chargés (ms)", {}),                       # une unité n'est pas une touche
    ("greffons     57/57 installés", {}),               # « /57 » n'est pas un chemin
    ("thème dark (vim n’en suit que le clair/sombre)", {}),               # ni « /sombre »
    ("........         = cd ../../..", {}),             # ni « /.. », et le terme n'est pas peint seul
    ("aligner le tableau markdown au fil de la frappe (jq)", {}),         # un OUTIL, pas une touche
]
# Volets alignés en deux colonnes : le sujet de la ligne prend la couleur des commandes. Passé en
# « terme=True », c'est-à-dire seulement sur la première ligne d'écran d'une entrée.
TERMES = [
    ("  dépôt        ~/.vim   branche master", "dépôt"),
    ("  mise à jour  aucune trace", "mise à jour"),
    ("  markdown-preview.nvim  installé", "markdown-preview.nvim"),
    (":Theme                   choisir le thème", ":Theme"),
    ("bashrc 2026.09  /Users/nom/.bash", "bashrc 2026.09"),
]
# … et ce qui n'est PAS un sujet : un nombre nu (une durée, un décompte) — c'est le module qui est le
# sujet de la ligne, et peindre le nombre inverserait l'information —, ni une phrase à simples espaces.
PAS_TERMES = [
    "      3  rc.d/15-history.sh",
    "  outils absents : fzf ruff pyright eslint",
]
# DEUX bancs, parce qu'un seul chiffre mentirait sur la moitié des cas (mesuré par la session vim sur
# ses volets réels : descriptions 4,6 %, État 13,7 %, Commandes 21,3 %, Greffons 31,5 %).
#
# Le premier banc mesure la RETENUE DE LA GRAMMAIRE sur du texte qui porte de la prose. C'est là que
# la gourmandise se voit : si une règle de trop se met à peindre des mots ordinaires, la part monte.
#
# Le second mesure une LISTE HOMOGÈNE SANS PROSE — cinquante lignes « nom␣␣␣␣état ». Sa part est haute
# par nature : le sujet occupe la moitié de chaque ligne et rien ne le dilue. Ce n'est pas un texte
# trop peint, c'est un tableau, et le peindre ainsi est JUSTE — le nom est ce que l'œil cherche. Le
# plafond y sert quand même : si une règle se mettait à peindre la colonne d'état, la part sauterait
# près de 100 %. Les deux plafonds disent donc chacun quelque chose de vrai, ce qu'un seul ne peut pas.
# Un volet aligné en deux colonnes, la forme la plus chargée PARMI CELLES QUI PORTENT DE LA PROSE — c'est là que le plafond doit mordre.
# Mesuré par la session vim sur ses propres onglets texte : 16,8 %, contre 5 % sur les descriptions.
# Un plafond éprouvé sur le seul cas léger ne protège donc rien : une règle un peu gourmande de plus
# ferait franchir la limite à ces volets-là pendant que les descriptions resteraient à 6 ou 7 %.
DEUX_COLONNES = [
    "== Configuration ==",
    "  dépôt        ~/.vim   branche master, commit 80295b3",
    "  éditeur      9.1 (Normal), niveau full   /usr/bin/vim",
    "  machine      macOS 26.6.2   git 2.55.0",
    "  greffons     57/57 installés",
    "  thème        everforest dark   fichier, thème dark (n’en suit que le clair/sombre)",
    "  mise à jour  aucune trace",
    "  ✓ aucun reste",
    "  outils absents : fzf ruff pyright eslint prettier typescript-language-server",
    "Modules chargés (ms)",
    "      0  rc.d/00-platform.sh",
    "      3  rc.d/15-history.sh",
    "      0  lots/10-navigation.sh",
    ":Keys                    l’aide des raccourcis, engendrée depuis le code (:Keys git pour un thème)",
    ":Theme                   choisir le thème et le fond (:Theme everforest light)",
    ":WatchForChangesAllFile  même surveillance, pour tous les fichiers ouverts",
    "  ls               = $_brc_ls --color=auto -F",
    "  cdhome           = cd ~",
    "  ........         = cd ../../..",
]
# De la prose, et seulement de la prose : rien ici ne doit prendre de couleur. Les parenthèses y sont
# des noms (greffon, application, plateforme), pas des touches — c'est le piège de cette grammaire.
PROSE = [
    "aperçu du document (markdown-preview, sinon Marked 2 sous macOS)",
    "aligner le tableau markdown au fil de la frappe (tabular)",
    "déplacer la ligne vers le haut / le bas (MacVim)",
    "fermer les buffers vides",
    "la sélection en minuscules, puis Capitalisées, puis MAJUSCULES",
    "vérifier les trois dépôts, puis rendre compte",
]


# Une liste homogène : le cas de l'onglet des greffons de vim, cinquante-sept lignes de cette forme.
TABLEAU = ["  %-22s %s" % (n, e) for n, e in (
    ("LargeFile", "installé"), ("ale", "installé"), ("bufexplorer", "installé"),
    ("catppuccin", "installé"), ("csv.vim", "installé"), ("ctrlp.vim", "installé"),
    ("edge", "installé"), ("everforest", "installé"), ("friendly-snippets", "installé"),
    ("fzf.vim", "installé"), ("golden-ratio", "installé"), ("goyo.vim", "installé"),
    ("html5.vim", "installé"), ("limelight.vim", "installé"), ("markdown-preview.nvim", "installé"),
    ("nerdcommenter", "installé"), ("nerdtree", "installé"), ("scss-syntax.vim", "écarté"))]


def main():
    if len(sys.argv) < 2:                      # pas de chemin par défaut : un chemin en dur porte
        print("usage : %s <chemin du module> [échantillon]" % sys.argv[0])   # un nom de compte
        raise SystemExit(2)
    chemin = sys.argv[1]
    chargeur = importlib.machinery.SourceFileLoader("module", chemin)
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader("module", chargeur))
    chargeur.exec_module(module)
    for nom in ("decouper", "MOTIFS"):
        if not hasattr(module, nom):       # refuser de conclure plutôt que de passer à vide
            print("ÉCHEC : %s n'expose pas %s" % (chemin, nom)); return 1

    for texte, attendus in CAS + [(p, {}) for p in PROSE]:
        morceaux = module.decouper(texte)
        if "".join(f for f, _ in morceaux) != texte:
            print("ÉCHEC : texte altéré par la découpe : %r" % texte); return 1
        obtenus = dict((f, g) for f, g in morceaux if g)
        for fragment, genre in attendus.items():
            if obtenus.get(fragment) != genre:
                print("ÉCHEC : %r attendait %r en « %s », obtenu %r"
                      % (texte, fragment, genre, obtenus.get(fragment))); return 1
        if not attendus and obtenus:
            print("ÉCHEC : de la prose a été colorée dans %r : %r" % (texte, obtenus)); return 1
    print("  ok   coloration : %d cas et %d phrases de prose, rien perdu, rien peint à tort"
          % (len(CAS), len(PROSE)))

    # Le vocabulaire de l'appelant : sans lui, un nom de commande est de la prose ; avec lui, il prend
    # la couleur des commandes. Et il ne doit pas mordre sur un mot voisin.
    m = dict((f, g) for f, g in module.decouper("vérifier avec brc doctor, sans brcx", ("brc", "doctor")) if g)
    if m != {"brc": "commande", "doctor": "commande"}:
        print("ÉCHEC : vocabulaire de l'appelant : %r" % m); return 1
    if any(g for _, g in module.decouper("vérifier avec brc doctor")):
        print("ÉCHEC : sans vocabulaire, ces noms devraient rester de la prose"); return 1
    print("  ok   coloration : vocabulaire de l'appelant pris en compte, et lui seul")

    for ligne, attendu in TERMES:
        genres = dict((f, g) for f, g in module.decouper(ligne, (), True) if g)
        if genres.get(attendu) != "terme":
            print("ÉCHEC : %r attendait le sujet %r, obtenu %r" % (ligne, attendu, genres)); return 1
    for ligne in PAS_TERMES:
        if any(g == "terme" for _, g in module.decouper(ligne, (), True)):
            print("ÉCHEC : %r n'a pas de sujet à peindre" % ligne); return 1
    # Et la règle ne s'applique qu'à la première ligne d'écran : sans « terme=True », rien. Sans cette
    # limite, la description d'un raccourci — où deux espaces séparent le texte de sa portée — verrait
    # sa phrase entière repeinte.
    if any(g == "terme" for _, g in module.decouper(TERMES[0][0])):
        print("ÉCHEC : un sujet a été peint sans terme=True"); return 1
    print("  ok   coloration : le sujet des volets en deux colonnes, et seulement sur sa première ligne")

    # Le plafond, sur l'échantillon réel s'il est là.
    echantillon = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "donnees", "raccourcis-vim.tsv")
    if not os.path.exists(echantillon):
        print("  ok   coloration : pas d'échantillon ici, plafond non mesuré")
        return 0
    total = peints = lignes = 0
    with open(echantillon, encoding="utf-8") as f:
        for ligne in f:
            colonnes = ligne.rstrip("\n").split("\t")
            if len(colonnes) < 4 or not colonnes[3]:
                continue
            lignes += 1
            for fragment, genre in module.decouper(colonnes[3]):
                total += len(fragment)
                if genre:
                    peints += len(fragment)
    if not lignes:
        print("ÉCHEC : échantillon illisible : %s" % echantillon); return 1
    part = 100.0 * peints / max(1, total)
    if part > 25:
        print("ÉCHEC : %.0f %% des caractères colorés sur %d descriptions — grammaire trop gourmande, "
              "le volet redevient illisible" % (part, lignes)); return 1
    print("  ok   coloration : %.0f %% des caractères peints sur %d vraies descriptions (plafond 25 %%)"
          % (part, lignes))

    total = peints = 0
    for l in DEUX_COLONNES:
        for fragment, genre in module.decouper(l, (), True):
            total += len(fragment)
            if genre:
                peints += len(fragment)
    part = 100.0 * peints / max(1, total)
    if part > 30:
        print("ÉCHEC : %.0f %% des caractères colorés dans un volet à deux colonnes — c'est le cas le "
              "plus chargé, et il franchit le plafond avant les descriptions" % part); return 1
    print("  ok   coloration : %.0f %% peints sur un volet à deux colonnes portant de la prose "
          "(plafond 30 %%)" % part)

    total = peints = 0
    for l in TABLEAU:
        for fragment, genre in module.decouper(l, (), True):
            total += len(fragment)
            if genre:
                peints += len(fragment)
    part = 100.0 * peints / max(1, total)
    if part > 45:
        print("ÉCHEC : %.0f %% dans une liste homogène sans prose — au-delà, ce n'est plus le sujet "
              "qui est peint mais la colonne d'état avec lui" % part); return 1
    print("  ok   coloration : %.0f %% peints dans une liste homogène sans prose, où la part est haute "
          "par nature (plafond 45 %%)" % part)
    return 0


if __name__ == "__main__":
    sys.exit(main())
