"""lib/onglets.py — interface à onglets dans le terminal (curses), pour des outils en ligne de commande.

Socle commun de « brc interface » (bash) et « vrc interface » (vim), tiré de vrc-interface. Le module ne
sait rien des projets qui l'utilisent : il reçoit des onglets et leurs producteurs de contenu.

    import sys; sys.dont_write_bytecode = True          # aucun __pycache__ à côté du module
    sys.path.insert(0, os.path.expanduser("~/.dotlib/lib"))
    import onglets
    if onglets.API != 1: …                               # repli de l'appelant
    code = onglets.lancer([onglets.Onglet("État", lambda: onglets.sortie(["cmd"]))], "brc")

Trois genres d'onglets :
    texte       produire() → liste de lignes ; défilement, filtre de lignes
    raccourcis  produire() → {"entrees": [[source, thème, touches, description, portée]…], "themes": [ordre]}
    groupes     produire() → [(nom, [lignes]), …] : noms à gauche, lignes du choisi à droite ;
                action(nom) facultative, appelée par Entrée, renvoie un message (l'onglet est rechargé) ;
                touches={"a": ("attacher", fn), …} pour d'autres actions ; une ligne peut être une
                chaîne ou une liste de segments [(texte, rôle), …] ; rafraichir=2 pour un onglet vivant

Dégradation (voulue, testée) : aucune couleur (ncurses sans couleurs, TERM=vt100…) → monochrome lisible ;
locale non UTF-8 → cadres en ASCII ; fenêtre trop petite → message ; entrée fermée → sortie ; le terminal
est toujours rendu (curses.wrapper). Rien n'est fait à l'import. Python ≥ 3.8, bibliothèque standard.
API = 1 : on ajoute, on ne retire pas, on ne change pas le sens sans changer ce numéro (voir API.md).
"""

import curses
import locale
import os
import re
import select
import subprocess
import sys
import time
import unicodedata

API = 1
# Les versions que ce module sert ENCORE. Un appelant sans copie de repli lit ceci pour savoir s'il
# peut s'en servir ; quand API passera à 2, la 1 y restera le temps qu'il adapte et teste.
API_COMPATIBLES = (1,)
# Numéro de RÉVISION, incrémenté à chaque AJOUT au contrat (l'API, elle, ne bouge pas : un ajout ne
# casse personne). Il existe parce qu'un appelant ne pouvait pas savoir si le module qu'il a en face
# porte l'ajout dont il a besoin : « API 1 » ne distingue pas le module d'hier de celui d'aujourd'hui.
# Un appelant qui emploie une nouveauté teste « onglets.REVISION >= n » ; sans cela il tombe sur une
# TypeError, c'est-à-dire un défaut chez lui pour une insuffisance chez nous.
#   1 : API 1 d'origine · 2 : genre « groupes » et `action` au contrat, et `comptes=`
#   3 : coloration du volet de contenu — decouper(), Onglet(vocabulaire=)
#   4 : les lignes de commande peintes entières ; affectations et noms de fichiers
#   5 : aperçu d'un groupe dans une autre palette, filet « --- », sources_palette()
#   6 : Quitter(valeur) — sortir de l'interface avec une valeur, code 5, onglets.QUITTE
#   7 : Onglet(aide=) — une aide par onglet, touche « ? », grande fenêtre
#   8 : aperçu de lignes PRÉ-COLORÉES — apercu() rend {"brut": True}, couleur256(), decouper_sgr()
#   9 : Onglet(touches=, action_libelle=) plusieurs actions par onglet · Onglet(rafraichir=,
#       rafraichir_complet=, produire_complet=) onglet qui se recharge seul tant qu'il est à l'écran ·
#       lignes en SEGMENTS [(texte, rôle), …] dans « groupes » et « texte », rôles ROLES_LIGNE ·
#       avant_plan() rend le terminal le temps d'une commande · texte_ligne(), plier_segments()
REVISION = 9

class Quitter(Exception):
    """Lever ceci depuis une action FERME l'interface et rend le code 5, avec une valeur pour l'appelant.

    Pourquoi c'est au socle de le fournir : certaines choses ne peuvent se faire qu'une fois le terminal
    rendu. « tmux attach » en est le cas d'école — curses tient le terminal, donc une action ne peut pas
    s'y substituer. Le socle n'exécute RIEN : il sort proprement et rapporte ce que l'action a dit.

    Une EXCEPTION et non une valeur de retour, à dessein : une action rend déjà un message, et un objet
    rendu à sa place se confondrait avec lui. Levée, l'intention est sans ambiguïté et fonctionne aussi
    depuis une fonction appelée par l'action. Elle traverse tous les filets de ce module — ceux qui
    empêchent un onglet cassé de fermer l'interface ne doivent pas avaler un ordre de sortie.
    """

    def __init__(self, valeur=""):
        Exception.__init__(self, valeur)
        self.valeur = valeur


# Valeur de la dernière sortie par Quitter, ou None. Remise à None à CHAQUE lancer() : une valeur
# laissée là par une séance précédente serait lue comme neuve, et une mesure périmée est un souvenir.
QUITTE = None

SGR = re.compile(r"\033\[[0-9;?]*[A-Za-z]")
AIDE = "←→ onglet · ↑↓ déplacer · PgUp/PgDn page · / filtrer · r recharger · q quitter"
AIDE_ASCII = "<-/-> onglet . haut/bas deplacer . PgUp/PgDn page . / filtrer . r recharger . q quitter"
LARGEUR_MIN, HAUTEUR_MIN = 40, 10


def utf8():
    """Le terminal accepte-t-il l'UTF-8 ? D'après l'ENVIRONNEMENT, comme lib/tui.sh de ce dépôt : deux
    parties de la même bibliothèque ne peuvent pas se contredire là-dessus.

    Surtout PAS locale.getpreferredencoding() : depuis Python 3.7 (PEP 538/540) il rend « utf-8 » même
    sous LC_ALL=C, LANG=C et LC_ALL=POSIX — mesuré. Tout repli ASCII fondé sur lui est donc du code
    mort, et il ne se déclenche jamais là où il sert : un NAS, une console."""
    if os.environ.get("TERM", "") == "linux":          # console Linux : pas de semi-graphique
        return False
    ctype = os.environ.get("LC_CTYPE", "")
    lang = os.environ.get("LANG", "").upper()
    # PEP 538 : quand la locale vaut C ou POSIX, CPython RÉÉCRIT LC_CTYPE dans son propre
    # environnement avant que ce code ne tourne. Lire l'environnement ne suffit donc pas — mais le
    # remède doit être étroit, sinon il attrape un cas légitime :
    #   « C.UTF-8 » / « C.utf8 » : personne ne pose cette valeur à la main, c'est la coercition ;
    #   « UTF-8 » nu : c'est AUSSI ce que macOS et ssh transmettent pour de vrai (LC_CTYPE sans
    #   LANG). On ne le tient pour une réécriture que si LANG dit explicitement C ou POSIX.
    if ctype in ("C.UTF-8", "C.utf8"):
        return False
    if ctype == "UTF-8" and lang in ("C", "POSIX"):
        return False
    lang = os.environ.get("LC_ALL") or ctype or os.environ.get("LANG") or ""
    return "utf8" in lang.lower().replace("-", "")


def sources_palette(nom):
    """D'où vient une palette : {"git": …, "site": …}, les clés absentes quand il n'y a rien.

    Lit share/palettes-sources.tsv, une DONNÉE : une palette ajoutée là n'oblige à toucher aucun
    programme. Même garantie que le reste de ce module — ni exception, ni dépendance dure : fichier
    absent, ligne mal formée, palette inconnue → {}. Un appelant affiche ce qu'il reçoit, et rien
    s'il ne reçoit rien."""
    dossier = os.environ.get("DOTLIB_DIR") or os.path.expanduser("~/.dotlib")
    try:
        with open(os.path.join(dossier, "share", "palettes-sources.tsv"), encoding="utf-8") as f:
            for ligne in f:
                if ligne.startswith("#"):
                    continue
                champs = ligne.rstrip("\n").split("\t")
                if champs and champs[0] == nom:
                    out = {}
                    for cle, i in (("git", 1), ("site", 2)):
                        if len(champs) > i and champs[i].strip():
                            out[cle] = champs[i].strip()
                    return out
    except OSError:
        pass
    return {}


def palette_dotlib(relire=False, nom=None, theme=None):
    """Les couleurs du thème actif du shell — celui que règle « brc theme ».

    dotlib publie ses palettes en DONNÉES (share/palettes.tsv : palette, fond, rôle, hexa, index
    256 couleurs) : on lit l'index et on obtient exactement les couleurs des autres outils du shell,
    sans rien recalculer. La palette et le fond viennent des variables exportées par le shell, sinon
    de local/theme.conf ; « auto » est résolu par le shell, jamais ici.

    GARANTIE DU CONTRAT : ni exception, ni dépendance dure. Fichier absent, ligne mal formée, index
    illisible → {} → couleurs de base du terminal. C'est la première fois que ce module lit un
    fichier ; il doit pouvoir s'en passer entièrement.
    (Note : l'interface du parc SSH, elle, n'utilise PAS de palette — décision du propriétaire, et elle ne
    dépendra jamais de dotlib puisque c'est elle qui sert à le poser.)"""
    dossier = os.environ.get("DOTLIB_DIR") or os.path.expanduser("~/.dotlib")
    env_palette = os.environ.get("DOTLIB_PALETTE_EFF", "")
    env_fond = os.environ.get("DOTLIB_THEME_EFF", "")
    # `relire` : IGNORER l'environnement et croire le fichier. Les deux variables sont l'état du shell
    # AU MOMENT OÙ IL A LANCÉ l'interface : elles ne bougent plus ensuite. Quand une action change le
    # thème pendant que l'interface tourne, c'est donc le fichier qui dit la vérité et l'environnement
    # qui mentirait — sans cela, appuyer sur Entrée sur un thème ne changeait rien à l'écran.
    palette, fond = ("", "") if relire else (env_palette, env_fond)
    if nom:
        palette = nom            # aperçu : une palette DEMANDÉE, sans rien changer au réglage
    if theme in ("dark", "light"):
        fond = theme             # … et, si on le demande, dans son autre déclinaison
    if not palette or not fond:
        try:
            with open(os.path.join(dossier, "local", "theme.conf"), encoding="utf-8") as f:
                for ligne in f:
                    cle, _, valeur = ligne.strip().partition("=")
                    if cle == "DOTLIB_PALETTE" and not palette:
                        palette = valeur
                    elif cle == "DOTLIB_THEME" and not fond:
                        fond = valeur
        except OSError:
            pass
    if fond not in ("dark", "light"):
        # Le fichier peut dire « auto » : c'est le SHELL qui résout auto (il sait interroger le
        # terminal), jamais nous. On retombe donc sur le fond qu'il avait résolu et exporté.
        fond = env_fond if env_fond in ("dark", "light") else "dark"
    if not palette or palette in ("xterm", "actuel"):
        return {}                         # « les couleurs du terminal » : on n'y touche pas
    roles = {}
    try:
        with open(os.path.join(dossier, "share", "palettes.tsv"), encoding="utf-8") as f:
            for ligne in f:
                champs = ligne.rstrip("\n").split("\t")
                if len(champs) >= 5 and champs[0] == palette and champs[1] == fond:
                    roles[champs[2]] = int(champs[4])
    except (OSError, ValueError):
        return {}
    return roles


# --- lisibilité du volet de droite : reconnaître, dans une phrase, ce qui n'est pas de la prose ---
# Écrit d'après de VRAIES descriptions, pas d'après une idée de ce qu'elles pourraient contenir :
#   « aide sur le mot sous le curseur (,h), recherche dans toute l'aide (,H) »
#   « liste des buffers : ici (,be), bascule (,bt), partage horizontal (,bs) ou vertical (,bv) »
#   « l'aide des raccourcis (,? puis un thème avec :Keys) »   « éditer ~/.bashrc »
# La convention observée est la parenthèse : c'est là que vivent les séquences de touches, et c'est
# ce qu'on cherche des yeux. Le reste — chemins, options, variables du shell — se reconnaît seul.
# Principe directeur : PEINDRE PEU. Un texte entièrement coloré est aussi illisible qu'un texte
# entièrement blanc ; la couleur ne vaut que par contraste avec de la prose qui n'en a pas. C'est
# pourquoi les nombres nus ne sont pas colorés (« Marked 2 », « 3 fichiers » n'apprennent rien).

# Noms de touches écrits en mots : sans cette petite liste, « (Entrée) » passerait pour de la prose.
TOUCHES_MOTS = ("Entrée", "Entree", "Espace", "Tab", "Échap", "Echap", "Retour", "Suppr",
                "haut", "bas", "gauche", "droite")

MOTIFS = (
    ("commande", re.compile(r"`[^`]+`")),                          # `du code entre accents graves`
    ("commande", re.compile(r"(?<![\w:])::?[A-Za-z][\w!]*")),        # :Keys, :Tabularize — commandes Ex
    # La touche « leader » hors parenthèses : « ,? », « ,ev ». Exigences volontairement étroites
    # (précédée d'un blanc ou d'une parenthèse, trois caractères au plus, aucun espace) pour qu'une
    # virgule de phrase française — toujours suivie d'un espace — n'entre jamais là-dedans.
    ("touche",   re.compile(r"(?<=[\s(])[,;][^\s,;)]{1,3}(?=[\s,;)]|$)")),
    # Un chemin, et non n'importe quoi qui porte une barre oblique. Mesuré sur de vraies lignes :
    # « 57/57 installés » et « le clair/sombre » donnaient « /57 » et « /sombre » pour des chemins.
    # Donc : « ~/… » toujours ; sinon il faut deux segments (/usr/bin/vim) ou un point (/.profile),
    # et jamais un chiffre juste après la barre.
    ("chemin",   re.compile(r"~/[\w.\-/]*\w"
                           r"|/[A-Za-z_][\w.\-]*(?:/[\w.\-]+)+"
                           r"|/\.[A-Za-z][\w.\-]*"      # /.profile — mais pas « /.. » de « cd ../.. »
                           r"|/[A-Za-z_][\w.\-]*\.[A-Za-z][\w.\-]*"
                           # relatif, mais seulement s'il porte une extension : « rc.d/00-platform.sh »,
                           # « lots/10-navigation.sh ». Sans cette exigence, « clair/sombre » et
                           # « et/ou » deviendraient des chemins.
                           r"|(?<![\w/])[\w.\-]+/[\w.\-/]*\.[A-Za-z]\w*")),
    # Une option commence un mot : elle est précédée d'un blanc, d'une parenthèse, d'un « = » ou
    # d'une virgule, sinon de rien du tout. Mesuré : « bash 5.3.15(1)-release » donnait « -release ».
    ("option",   re.compile(r"(?<![^\s(=,])--?[A-Za-z][\w-]*")),      # --json, -v
    # Un nom de fichier sans barre oblique : « tunnels.conf », « 00-platform.sh ». Liste d'extensions
    # volontairement courte — celles d'un fichier qu'on ouvre ou qu'on édite. « tar.gz » et « .pdf »
    # n'y sont pas : ils apparaissent dans de la prose qui parle de FORMATS, pas de fichiers.
    ("chemin",   re.compile(r"(?<![\w/.])[\w][\w.\-]*\.(conf|cfg|ini|sh|bash|zsh|py|lua|vim|nvim"
                           r"|json|ya?ml|tsv|csv|log|md|txt|rc)\b")),
    ("variable", re.compile(r"\$\{?\w+\}?")),                        # $EDITOR, ${HOME}
    # Une affectation se peint avec sa valeur : « TERM=xterm-256color », « BRC_FORCE_COLOR=1 ». Le nom
    # est exigé en MAJUSCULES — c'est la convention des variables d'environnement, et cela évite de
    # prendre « --color=auto » (dont l'option est déjà peinte) ou un « x=y » de prose pour un réglage.
    ("variable", re.compile(r"(?<![\w-])[A-Z][A-Z0-9_]*=[^\s,;)»\"']+")),
)
# La parenthèse doit être PRÉCÉDÉE D'UN BLANC. Sans cela, le « (s) » de « 54 installé(s) » passait
# pour la touche « s » — une marque de pluriel collée au mot, pas quelque chose qu'on tape. Dans les
# vraies descriptions, une touche entre parenthèses suit toujours un espace : « le curseur (,h) ».
_PAREN = re.compile(r"(?:(?<=\s)|(?<=^))\(([^()\s]{1,14})\)")
# Le TERME défini, dans un volet aligné en deux colonnes — la forme dominante des onglets « texte » :
#   « dépôt        ~/.vim   branche master »   « LargeFile              installé »
#   « :Keys        l'aide des raccourcis »     « mise à jour  aucune trace »
# C'est ce que le propriétaire appelle « la commande » : le mot qu'on cherche des yeux à gauche. Le
# séparateur est l'alignement lui-même (deux espaces au moins), ce qui distingue un terme d'une
# phrase, où les mots sont séparés par un seul espace. Le terme peut en contenir (« mise à jour »),
# d'où la limite de longueur : au-delà, c'est de la prose et non une étiquette.
# UNE LIGNE DE COMMANDE SE PEINT ENTIÈRE, commande et arguments. Demande du propriétaire, sur un cas
# relevé dans un volet : « brew install pstree » n'était pas peint du tout, alors que c'est exactement
# ce qu'on cherche des yeux pour le recopier. « Peindre peu, mais pas moins non plus. »
#
# Trois façons de reconnaître le DÉBUT d'une invocation, et pas une de plus :
#   1. un mot du vocabulaire de l'appelant — il l'a déclaré, on lui fait confiance, même seul ;
#   2. un nom de la liste ci-dessous, mais SEULEMENT s'il est suivi d'un argument. Sans cette
#      exigence, « git 2.55.0 » d'une ligne de version se mettrait à ressembler à une commande ;
#   3. un mot d'allure technique (il porte un tiret, un point, un souligné ou un chiffre) suivi d'une
#      OPTION : « arp-scan -l ». Une option ne suit qu'une commande, c'est un indice sûr, et l'allure
#      technique évite de prendre « sauf -S » pour une invocation.
#
# La liste ne cherche pas l'exhaustivité : ce sont les gestionnaires de paquets et la poignée d'outils
# qui apparaissent dans un conseil d'installation ou de dépannage — là où un volet dit quoi taper.
COMMANDES = frozenset("""
brew port apt apt-get dpkg dnf yum pacman apk opkg ipkg synopkg pip pip3 pipx npm gem cargo
sudo doas git ssh scp rsync tmux vim nvim nano make curl wget tar unzip chmod chown ln mkdir
sh bash zsh python python3 perl awk sed grep defaults launchctl systemctl service
""".split())

# Ce qui suit un nom de la liste générique doit RESSEMBLER À UN ARGUMENT, faute de quoi la commande
# n'en est pas une. Défaut relevé sur une vraie ligne : « vim fournit déjà cette syntaxe » se peignait
# comme une invocation, parce que « fournit » a la forme d'un argument. Or « vim » est autant un mot
# de phrase qu'une commande — comme « port », « service », « make » ou « go ». On exige donc que le
# premier argument soit une option, un chemin, ou l'un de ces verbes : ce sont eux qui font qu'une
# suite de mots est un ordre et non une phrase.
VERBES = frozenset("""
install reinstall uninstall add remove rm purge update upgrade refresh search list info show
clone pull push fetch checkout commit status diff log init tap link unlink
run start stop restart reload enable disable config set get doctor clean build test
""".split())

# La prose s'arrête ici. Ces mots ne sont jamais l'argument d'une commande : sans cette barrière,
# « via sudo si besoin » ferait de « si besoin » les arguments de sudo. C'est la seule façon simple de
# distinguer une suite d'arguments d'une phrase, les deux étant faites de mots séparés par des espaces.
BARRIERES = frozenset("""
si et ou puis dans pour avec sans sauf sur sous par de du des le la les un une au aux en ne pas
est sont via comme quand donc mais car ni que qui il elle on nous vous y ici plus moins tout tous
ce ces son sa ses leur leurs cette autre autres meme seul aussi selon depuis vers chez entre
""".split())
_ARG = re.compile(r"[-<\[/~$A-Za-z0-9_.][\w.\-/=<>\[\]$~*?{}:,]*$")
# Le PREMIER argument ne commence pas par un chiffre : « git 2.55.0 » est une version, pas une
# invocation, et sans cette exigence toute ligne « outil version » se peindrait comme du code.
_ARG1 = re.compile(r"[-<\[/~$A-Za-z_]")
_OPTION_SEULE = re.compile(r"--?[A-Za-z][\w-]*$")
_TECHNIQUE = re.compile(r"[a-z][a-z0-9_.+-]*$")
FIN_DE_MEMBRE = ",;:)»\"'"
DEBUT_DE_MEMBRE = "(«\"'"


def _noyau(brut):
    """Le mot sans la ponctuation qui l'entoure, et de combien on a rogné à gauche."""
    gauche = len(brut) - len(brut.lstrip("(«\"'"))
    reste = brut[gauche:]
    # Le « : » initial d'une commande Ex fait partie du mot : il n'est pas de la ponctuation, et le
    # retirer faisait de « :Theme » un « Theme » que plus rien ne distinguait d'un nom quelconque.
    prefixe = ""
    if reste[:1] == ":" and reste[1:2].isalpha():
        prefixe, reste = ":", reste[1:]
    return prefixe + reste.strip("().,;:«»\"'…·"), gauche


def _argument_vrai(mot):
    """Le premier mot après une commande : option, paramètre à remplacer, chemin, ou verbe d'action.

    Volontairement exigeant : c'est lui qui distingue un ordre d'une phrase. « vim fournit » n'en a
    pas, « brew install » en a un."""
    if _OPTION_SEULE.match(mot) or mot in VERBES:
        return True
    if mot[:1] in "<[" and mot[-1:] in ">]":       # <nom>, [options] — un paramètre à remplacer
        return True
    return "/" in mot or mot.startswith(("~", "$")) or bool(re.search(r"\.[a-z]{1,5}$", mot))


def _lignes_de_commande(texte, vocabulaire):
    """Les intervalles (début, fin) des invocations trouvées dans le texte."""
    mots = list(re.finditer(r"\S+", texte))
    spans, i = [], 0
    while i < len(mots):
        noyau, rogne = _noyau(mots[i].group())
        depart = mots[i].start() + rogne
        declare = noyau in vocabulaire
        if noyau in ("sudo", "doas") and i + 2 < len(mots):
            # transparents : « sudo apt install x » se juge sur « apt install », pas sur « sudo apt »
            apres, _ = _noyau(mots[i + 2].group())
            if _noyau(mots[i + 1].group())[0] in COMMANDES and _argument_vrai(apres):
                spans_sudo = True
            else:
                spans_sudo = False
        else:
            spans_sudo = False
        suivant, _ = _noyau(mots[i + 1].group()) if i + 1 < len(mots) else ("", 0)
        ouvre = False
        ex = noyau[:1] == ":" and len(noyau) > 1 and noyau[1].isalpha()
        if declare or spans_sudo:
            ouvre = True
        # Une commande Ex emmène ses PARAMÈTRES : « :Theme <nom> <fond> » peignait la commande et
        # laissait ses paramètres en blanc, soit l'îlot qu'on veut éviter. Même exigence que pour les
        # autres — un vrai argument —, sans quoi « tapez :Keys puis choisissez » se peindrait.
        elif ex and suivant and suivant not in BARRIERES and _argument_vrai(suivant):
            ouvre = True
        elif (noyau in COMMANDES and suivant and suivant not in BARRIERES
              and _ARG.match(suivant) and _ARG1.match(suivant) and _argument_vrai(suivant)):
            ouvre = True
        elif (_TECHNIQUE.match(noyau) and re.search(r"[-_.0-9]", noyau)
              and _OPTION_SEULE.match(suivant or "")):
            ouvre = True
        if not ouvre:
            i += 1
            continue
        fin, j = mots[i].start() + rogne + len(noyau), i
        # On étend tant que le mot suivant est un argument : pas un mot de la prose, pas un mot
        # accentué (une commande et ses arguments sont en ASCII), et rien qui ferme le membre de phrase.
        # Bornes larges à dessein : ce sont les BARRIÈRES (mot de prose, accent, ponctuation, deux
        # espaces) qui arrêtent une invocation, pas un compte. Serrées, elles coupaient au milieu de
        # « ssh -f -N -o ExitOnForwardFailure=yes … » et laissaient un îlot de couleur — pire que rien.
        while j + 1 < len(mots) and j - i < 12 and fin - depart < 90:
            # Le caractère qui SUIT le mot, et non son dernier : c'est la virgule après « tar » qui
            # dit que le membre de phrase est fini, et elle est hors du mot.
            if fin < len(texte) and texte[fin] in FIN_DE_MEMBRE:
                break
            brut = mots[j + 1].group()
            if brut[:1] in DEBUT_DE_MEMBRE:
                break
            # Deux espaces et plus : c'est le séparateur de colonnes d'un volet aligné, donc la
            # frontière entre ce qu'on tape et son explication. Une invocation ne la franchit jamais.
            if mots[j + 1].start() - fin >= 2:
                break
            arg, _ = _noyau(brut)
            if not arg or arg in BARRIERES:
                break
            try:
                arg.encode("ascii")
            except UnicodeEncodeError:
                break
            if not _ARG.match(arg):
                break
            j += 1
            coupe = brut.rstrip(",;:)»\"'…·")
            # Le point final d'une phrase n'appartient pas à la commande : « leur brc reload. »
            # peignait le point avec, ce qui se voyait à l'écran.
            if len(coupe) > 1 and coupe.endswith("."):
                coupe = coupe[:-1]
            fin = mots[j].start() + len(coupe)
        # Un nom de la liste générique n'est peint que s'il a VRAIMENT reçu un argument : sans cela,
        # « Formats : tar, tar.gz… » peignait « tar » tout seul au milieu d'une phrase. Un mot du
        # vocabulaire, lui, est peint seul — l'appelant l'a déclaré comme une commande de son monde.
        if (declare and fin > depart) or j > i:
            spans.append((depart, fin))
        i = max(j + 1, i + 1)
    return spans


_TERME = re.compile(r"[ \t]*(\S[^\t]{0,31}?)[ \t]{2,}\S")


def _touche(contenu):
    """Le contenu d'une parenthèse est-il une séquence de touches ? Vrai s'il porte un caractère de
    ponctuation qu'on tape (« ,h », « Ctrl-x », « 'b »), s'il nomme une touche en mots, ou s'il est
    d'un seul caractère (« o », « # », « * »). Faux pour « (tabular) » et « (MacVim) », qui sont des
    noms — et faux, mesuré sur de vraies lignes, pour « (1) » d'un numéro de version et « (ms) »
    d'une unité : un nombre nu n'est pas une touche, et deux minuscules sont un mot."""
    if contenu in TOUCHES_MOTS:
        return True
    if contenu.isdigit():
        return False
    if len(contenu) == 1:
        return True
    if len(contenu) == 2:
        return not contenu.isalpha() or contenu != contenu.lower()
    return bool(re.search(r"[,;:'\"@<>/\-]", contenu))


def decouper(texte, vocabulaire=(), terme=False):
    """Découpe un texte en [(fragment, genre)] — genre : commande, touche, chemin, option, variable,
    ou terme, ou "" pour la prose, qui garde la couleur par défaut du terminal.

    `terme=True` : cette ligne commence une entrée, donc sa première colonne — si la ligne est alignée
    en deux colonnes — est le sujet défini. À ne pas passer sur une ligne de repli.

    `vocabulaire` : les noms que l'appelant sait être des commandes chez lui. Le socle ne peut pas
    les deviner : il ne sait pas ce qui est une commande dans SON monde. Sans terminal, sans couleurs
    et sans curses : c'est une fonction de texte, donc testable seule."""
    trouves = []

    def libre(d, f):
        return not any(a < f and d < b for a, b, _ in trouves)

    # En PREMIER, parce qu'il prime : dans « ~/.bashrc   le fichier principal », ce qui est à gauche
    # est le sujet de la ligne avant d'être un chemin. Réservé à la PREMIÈRE ligne d'écran d'une
    # entrée (« terme=True ») : sur une ligne de repli, ou dans la description d'un raccourci — où
    # deux espaces séparent le texte de sa portée —, la règle repeindrait une phrase entière.
    if terme:
        m = _TERME.match(texte)
        # Un nombre nu n'est pas un sujet : « 3  lots/10-navigation.sh » énonce une durée, et c'est le
        # module qui est le sujet. Peindre le nombre inverserait l'information.
        if m and not m.group(1).strip("0123456789.,:").strip() == "":
            trouves.append((m.start(1), m.end(1), "terme"))
    # Après le sujet (qui prime : dans « tunnel edit   ouvrir… », ce qui est à gauche est le sujet
    # avant d'être une invocation), avant les motifs (une invocation se peint ENTIÈRE, on ne veut pas
    # que « --port » y forme un îlot d'une autre couleur).
    for debut, fin in _lignes_de_commande(texte, set(vocabulaire)):
        if libre(debut, fin):
            trouves.append((debut, fin, "commande"))

    for m in _PAREN.finditer(texte):
        contenu = m.group(1)
        if contenu.startswith(":"):
            continue                                   # (:Keys) → laissé au motif des commandes
        if _touche(contenu) and libre(m.start(1), m.end(1)):
            trouves.append((m.start(1), m.end(1), "touche"))
    for genre, motif in MOTIFS:
        for m in motif.finditer(texte):
            if libre(m.start(), m.end()):
                trouves.append((m.start(), m.end(), genre))
    mots = set(v for v in vocabulaire if v and len(v) > 1)
    if mots:
        for m in re.finditer(r"[\w.\-]+", texte):
            if m.group() in mots and libre(m.start(), m.end()):
                trouves.append((m.start(), m.end(), "commande"))
    trouves.sort()
    out, curseur = [], 0
    for debut, fin, genre in trouves:
        if debut > curseur:
            out.append((texte[curseur:debut], ""))
        out.append((texte[debut:fin], genre))
        curseur = fin
    if curseur < len(texte):
        out.append((texte[curseur:], ""))
    return out or [(texte, "")]


def couleur256(r, g, b):
    """Le plus proche des 256 indices d'un terminal, pour une couleur 24 bits.

    Pourquoi convertir plutôt qu'employer la vraie couleur : curses ne sait la changer qu'avec
    can_change_color(), que presque aucun terminal n'accorde — et qui modifierait la palette du
    terminal lui-même, donc l'affichage de tout ce qui l'entoure. Un aperçu n'a pas à repeindre
    l'écran de l'utilisateur pour se montrer.

    Deux candidats sont comparés : le cube 6×6×6 (16-231) et la rampe de gris (232-255). Le gris
    gagne souvent sur les couleurs peu saturées — fonds de barres de statut, justement — et l'oublier
    donnait des gris bleutés là où le thème en voulait des neutres."""
    niveaux = (0, 95, 135, 175, 215, 255)

    def proche(v):
        return min(range(6), key=lambda i: abs(niveaux[i] - v))

    ri, gi, bi = proche(r), proche(g), proche(b)
    cube = (16 + 36 * ri + 6 * gi + bi,
            (niveaux[ri] - r) ** 2 + (niveaux[gi] - g) ** 2 + (niveaux[bi] - b) ** 2)
    moyen = (r + g + b) // 3
    i = min(23, max(0, (moyen - 8 + 5) // 10))
    v = 8 + 10 * i
    gris = (232 + i, (v - r) ** 2 + (v - g) ** 2 + (v - b) ** 2)
    return (cube if cube[1] <= gris[1] else gris)[0]


# Les séquences qu'on sait lire dans une ligne PRÉ-COLORÉE : couleurs 256, couleurs 24 bits, gras,
# remise à zéro. Tout le reste (soulignement, inverse, clignotement…) est ignoré sans bruit : mieux
# vaut une ligne juste en couleur et plate en attributs qu'un refus d'afficher.
_SGR_BRUT = re.compile(r"\033\[([0-9;]*)m")


def decouper_sgr(ligne):
    """Découpe une ligne pré-colorée en [(texte, fond, texte_couleur, gras)].

    `fond` et `texte_couleur` : un index 256, ou None pour « celle du terminal ». Les couleurs 24 bits
    sont ramenées au plus proche des 256 (voir couleur256). Fonction de texte : ni curses, ni terminal,
    donc éprouvable seule."""
    out, pos, fg, bg, gras = [], 0, None, None, False
    for m in _SGR_BRUT.finditer(ligne):
        if m.start() > pos:
            out.append((ligne[pos:m.start()], bg, fg, gras))
        pos = m.end()
        codes = [c for c in m.group(1).split(";") if c != ""] or ["0"]
        i = 0
        while i < len(codes):
            try:
                c = int(codes[i])
            except ValueError:
                i += 1
                continue
            if c == 0:
                fg, bg, gras = None, None, False
            elif c == 1:
                gras = True
            elif c == 22:
                gras = False
            elif c in (38, 48) and i + 1 < len(codes):
                cible = "fg" if c == 38 else "bg"
                if codes[i + 1] == "5" and i + 2 < len(codes):
                    v = int(codes[i + 2]); i += 2
                elif codes[i + 1] == "2" and i + 4 < len(codes):
                    v = couleur256(int(codes[i + 2]), int(codes[i + 3]), int(codes[i + 4])); i += 4
                else:
                    i += 1
                    continue
                if cible == "fg":
                    fg = v
                else:
                    bg = v
            elif c == 39:
                fg = None
            elif c == 49:
                bg = None
            i += 1
    if pos < len(ligne):
        out.append((ligne[pos:], bg, fg, gras))
    return [x for x in out if x[0]]


def borne(haut, total, hauteur):
    """Première ligne à afficher, ramenée dans le possible : jamais négative, jamais au-delà de la
    dernière page. Sortie du dessin pour être éprouvée sans terminal — dans un pseudo-terminal, curses
    n'émet que les caractères qui CHANGENT d'une image à l'autre, donc chercher un texte dans le flux
    ne prouve rien sur ce qui est à l'écran."""
    return max(0, min(haut, max(0, total - hauteur)))


def plier(texte, largeur):
    """Replie un texte sur autant de lignes d'écran qu'il en faut, en coupant sur les espaces.

    Tronquer perdait la fin des descriptions : mesuré sur les 112 raccourcis de ~/.vim, à 76 colonnes
    — un tmux partagé en deux, une console — 86 entrées sur 112 perdaient du texte, jusqu'à 98
    caractères. Or la fin d'une description est justement ce qui dit à quoi sert le raccourci, et une
    liste de touches tronquée retire à l'utilisateur une touche qu'il ne peut plus connaître.
    Un mot plus long que la largeur est coupé net : mieux vaut une coupure qu'une ligne qui déborde.
    (Fonction de la session vim, mesurée chez elle, reprise telle quelle.)"""
    if largeur < 8:                       # place dérisoire : on ne plie pas, on coupe
        return [texte[: max(1, largeur)]]
    morceaux = []
    reste = texte
    while reste:
        if len(reste) <= largeur:
            morceaux.append(reste)
            break
        coupe = reste.rfind(" ", 0, largeur + 1)
        if coupe <= 0:
            coupe = largeur
        morceaux.append(reste[:coupe].rstrip())
        reste = reste[coupe:].lstrip()
    return morceaux or [""]


def ascii_lisible(texte):
    """Translittère plutôt que de remplacer par des « ? ». « édition » → « edition », pas « ?dition » :
    sur les machines où la dégradation sert, cinq thèmes sur vingt devenaient illisibles."""
    for typo, plat in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
                       ("\u00ab", '"'), ("\u00bb", '"'), ("\u00b7", "-"), ("\u2014", "-"),
                       ("\u2013", "-"), ("\u2026", "..."), ("\u00a0", " "),
                       # Les flèches sont des NOMS DE TOUCHES, pas de la décoration : « ,? » ne dit
                       # pas quoi taper. Des mots, et non « ^ v < > » qui se confondraient avec de
                       # vraies touches (« ,< » et « ,> » existent).
                       ("\u2191", "haut"), ("\u2193", "bas"), ("\u2190", "gauche"), ("\u2192", "droite")):
        texte = texte.replace(typo, plat)
    plat = unicodedata.normalize("NFD", texte)
    plat = "".join(c for c in plat if not unicodedata.combining(c))
    # Ce qui reste n'est pas représentable : on l'AVOUE entre crochets. Un « ? » nu se lirait comme
    # la touche « ? », ce qui est pire que de ne rien dire — au milieu d'une liste de touches surtout.
    # Les glyphes Powerline (zone privée E0B0-E0BF : arrondis, flèches, séparateurs) deviennent des
    # ESPACES, pas des « [?] » : ils ne portent aucun sens, ils dessinent une bordure. Les avouer
    # entre crochets ferait du bruit là où il n'y a rien à dire.
    plat = "".join(" " if 0xE0B0 <= ord(c) <= 0xE0BF else c for c in plat)
    return "".join(c if ord(c) < 127 else "[?]" for c in plat)


def sortie(commande, cwd=None, env=None, delai=60):
    """La sortie d'une commande, sans couleurs, ou son erreur : jamais d'exception, jamais d'attente sans fin
    (entrée fermée, délai maximal). NO_COLOR=1 suffit à obtenir du texte nu ; le vrai TERM est gardé (un
    TERM=dumb change ce que certains programmes annoncent, par exemple le thème de vim)."""
    e = dict(os.environ, NO_COLOR="1")
    if env:
        e.update(env)
    try:
        r = subprocess.run(commande, cwd=cwd, env=e, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=delai)
        texte = r.stdout.decode("utf-8", "replace")
    except FileNotFoundError:
        return ["(commande absente : %s)" % commande[0]]
    except subprocess.TimeoutExpired:
        return ["(trop long, abandonné après %d s : %s)" % (delai, " ".join(commande))]
    except OSError as err:
        return ["(impossible de lancer %s : %s)" % (commande[0], err)]
    return [SGR.sub("", l).rstrip() for l in texte.splitlines()]


def lire_tsv(lignes, colonnes=5):
    """Lignes « a<TAB>b<TAB>… » → listes d'au moins `colonnes` champs (les autres sont ignorées)."""
    return [l.split("\t")[:colonnes] for l in lignes if len(l.split("\t")) >= colonnes]


def ordonner(presents, reference):
    """Les thèmes présents, dans l'ordre de référence, puis ceux hors référence dans l'ordre rencontré."""
    vus = []
    for t in presents:
        if t not in vus:
            vus.append(t)
    rangés = [t for t in reference if t in vus]
    return rangés + [t for t in vus if t not in rangés]


# Rôles qu'une LIGNE peut demander pour un de ses morceaux, et le rôle de palette correspondant.
# Pourquoi des noms de SENS et non des couleurs : un appelant qui écrirait « vert » ne suivrait pas le
# thème et ne se dégraderait pas là où il n'y a pas de couleurs — or c'est précisément là que ses
# machines tournent (un NAS rapporte COLORS=0). Il dit ce que la chose EST, le socle choisit comment
# le montrer. Les noms internes (« onglet » pour le vert, « titre » pour le jaune) ne sont pas
# publiables tels quels : ils nomment leur origine, pas leur sens.
ROLES_LIGNE = {"bon": "onglet", "mauvais": "mauvais", "avertir": "titre",
               "discret": "portee", "vedette": "touche", "commande": "commande"}

# Touches que le socle emploie partout, et qu'un onglet ne peut donc pas s'approprier : une touche qui
# recharge dans trois onglets et répare dans le quatrième est un piège, et le pied l'annonce partout.
# Refusé à la CONSTRUCTION de l'onglet (donc avant curses, et de façon reproductible) plutôt que
# silencieusement ignoré : une touche morte qui ne se voit qu'une fois déployée, on connaît.
TOUCHES_RESERVEES = tuple("qQrRgGjk/?123456789 \t\n\r\x1b\x02\x04\x06\x15\x7f\b")


def texte_ligne(ligne):
    """Le texte nu d'une ligne, qu'elle soit une chaîne ou une liste de segments [(texte, rôle), …].

    Le filtre, les décomptes et les repères de ligne travaillent là-dessus : ils doivent voir ce que
    l'utilisateur LIT, pas la façon dont c'est peint."""
    if isinstance(ligne, str):
        return ligne
    return "".join(t for t, _ in ligne)


def _recoller(caracteres):
    """[(caractère, rôle), …] → [(texte, rôle), …] en recollant ce qui a le même rôle."""
    segments = []
    for c, role in caracteres:
        if segments and segments[-1][1] == role:
            segments[-1] = (segments[-1][0] + c, role)
        else:
            segments.append((c, role))
    return segments


def plier_segments(segments, largeur):
    """plier(), mais pour une ligne en segments : chaque caractère emporte son rôle au pli.

    Replier le texte seul puis recoller les rôles ne marche pas — plier() retire les blancs au point
    de coupure, donc les positions ne se retrouvent plus. On plie donc les caractères eux-mêmes, avec
    la même règle, pour que les deux genres de lignes se replient identiquement."""
    caracteres = [(c, role) for texte, role in segments for c in texte]
    if largeur < 8:                       # place dérisoire : on ne plie pas, on coupe (comme plier)
        return [_recoller(caracteres[: max(1, largeur)])]
    lignes = []
    while caracteres:
        if len(caracteres) <= largeur:
            lignes.append(_recoller(caracteres))
            break
        coupe = -1
        for i in range(min(largeur, len(caracteres) - 1), -1, -1):
            if caracteres[i][0] == " ":
                coupe = i
                break
        if coupe <= 0:
            coupe = largeur
        tete = caracteres[:coupe]
        while tete and tete[-1][0] == " ":
            tete.pop()
        lignes.append(_recoller(tete))
        caracteres = caracteres[coupe:]
        while caracteres and caracteres[0][0] == " ":
            caracteres.pop(0)
    return lignes or [[]]


class Onglet:
    """Un onglet : un titre, de quoi produire son contenu (chargé à la première ouverture et gardé)."""

    def __init__(self, titre, produire, genre="texte", action=None, comptes=True, vocabulaire=None,
                 apercu=None, aide=None, touches=None, action_libelle=None,
                 rafraichir=0, rafraichir_complet=0, produire_complet=None):
        self.titre = titre
        # Les noms que CET onglet sait être des commandes, pour qu'ils prennent leur couleur quand une
        # description les cite. Le socle ne les devine pas : lui seul ignore ce qui est une commande
        # dans le monde de l'appelant. Facultatif — sans lui, le reste de la coloration marche.
        self.vocabulaire = tuple(vocabulaire or ())
        self.produire = produire
        self.genre = genre
        self.comptes = comptes      # False : pas de nombre à côté des noms (groupe de réglage)
        self.action = action
        # D'AUTRES actions que Entrée : {"a": ("attacher", fn), …}, fn(nom) ayant le contrat d'action.
        # Le libellé sert au pied et à l'aide : une touche dont on ne sait pas ce qu'elle fait n'existe
        # pas plus qu'une touche absente.
        self.touches = dict(touches or {})
        for t, paire in self.touches.items():
            if not isinstance(t, str) or len(t) != 1:
                raise ValueError("onglet « %s » : « %r » n'est pas une touche d'un seul caractère" % (titre, t))
            if t in TOUCHES_RESERVEES:
                raise ValueError("onglet « %s » : la touche « %s » est réservée au socle (%s) — libres : %s"
                                 % (titre, t, "q Q r R g G j k / ? chiffres Tab Entrée Échap espace Ctrl",
                                    " ".join(c for c in "abcdefhilmnopstuvwxyz" if c not in TOUCHES_RESERVEES)))
            if not (isinstance(paire, (tuple, list)) and len(paire) == 2 and callable(paire[1])):
                raise ValueError("onglet « %s » : touche « %s » attend (libellé, fonction)" % (titre, t))
        # Ce que fait Entrée, en mots. Sans lui le pied dit « appliquer », qui ne dit rien quand il y a
        # cinq actions à côté.
        self.action_libelle = action_libelle
        # Onglet VIVANT : rechargé tous les `rafraichir` secondes, et seulement quand il est à l'écran.
        # Un onglet qu'on ne regarde pas ne coûte rien : le socle n'arme un délai d'attente du clavier
        # que pour l'onglet affiché, et dort autrement. `produire_complet` est appelé à la place de
        # `produire` toutes les `rafraichir_complet` secondes : le socle ne sait pas ce que « complet »
        # veut dire chez l'appelant, donc c'est l'appelant qui le dit — plutôt que de changer la
        # signature de produire(), dont dépendent tous les onglets déjà écrits.
        self.rafraichir = max(0, rafraichir or 0)
        self.rafraichir_complet = max(0, rafraichir_complet or 0)
        self.produire_complet = produire_complet
        self.dernier_chargement = 0.0
        self.dernier_complet = 0.0
        # aide() → liste de lignes, montrée par « ? » dans une grande fenêtre. Chargée à la première
        # ouverture et gardée, comme un producteur. Sans elle, la touche n'existe pas.
        self.aide = aide
        self.aide_contenu = None
        self.aide_haut = 0
        # apercu(nom_du_groupe) → {"lignes": [...], "palette": "nord", "theme": "light"} ou None.
        # Le socle peint ces lignes-là, et elles seules, avec la palette demandée.
        self.apercu = apercu
        self.contenu = None
        self.total_ecran = 0            # lignes d'écran du dernier rendu (pages, G, compteur)
        # On entre par la LISTE, on choisit une section, puis on entre dedans : c'est l'ordre naturel
        # de l'usage. Démarrer sur le contenu obligeait à penser à Tab pour atteindre la liste.
        self.focus = "gauche"           # deux volets : « gauche » (la liste) ou « droite » (le contenu)
        self.colonne = 0                # abscisse du séparateur, publiée par le rendu (souris)
        self.hauteur = 1                # hauteur visible, publiée par le rendu (pages)
        self.debut_noms = 0             # première section affichée à gauche (clic)
        self.rang = 0               # sélection dans la colonne de gauche
        self.haut = 0               # première ligne affichée

    def charger(self):
        if self.contenu is None:
            self.contenu = self.produire()
            self.dernier_chargement = self.dernier_complet = time.monotonic()
        return self.contenu

    def recharger(self):
        self.contenu = None
        self.haut = 0
        self.charger()

    def recharger_en_place(self, complet=False):
        """Recharge le contenu en GARDANT la sélection, le défilement et le volet actif.

        C'est ce qui sépare un onglet vivant d'un onglet qui clignote : un rechargement toutes les
        deux secondes qui ramène en haut de la liste rend l'onglet inutilisable, et une action qui
        fait sauter la sélection oblige à retrouver sa place après chaque geste. Les bornes sont
        laissées au dessin, qui seul connaît le nombre de lignes et la hauteur réelle."""
        produire = self.produire_complet if (complet and self.produire_complet) else self.produire
        self.contenu = produire()
        maintenant = time.monotonic()
        self.dernier_chargement = maintenant
        if complet:
            self.dernier_complet = maintenant
        return self.contenu


class Interface:
    def __init__(self, ecran, onglets, nom=""):
        self.ecran = ecran
        self.onglets = onglets
        self.nom = nom
        self.actif = 0
        self.filtre = ""
        self.aide_ouverte = False       # la grande fenêtre d'aide recouvre tout, sans rien changer dessous
        self.saisie = False
        self.message = ""
        self.paires = {}
        self.position = ""              # « 12/86 », écrit par pied() dans son filet
        self.utf8 = utf8()
        self.h_trait, self.v_trait = ("─", "│") if self.utf8 else ("-", "|")
        self.coins = ("┌", "┐", "└", "┘") if self.utf8 else ("+", "+", "+", "+")

    # --- couleurs : celles de base du terminal, seulement s'il en a assez ; sinon monochrome ----------
    def couleurs(self, relire=False):
        """TROIS étages : la palette du shell (256 couleurs et tous les rôles présents), les couleurs
        de base du terminal, puis le monochrome. Les gardes du dernier étage ne sont pas
        décoratives : un NAS sous DSM rapporte COLORS=0 malgré des terminfo présents, et
        use_default_colors() comme init_pair() y lèvent — sans try, l'interface ne s'ouvrirait pas
        là où elle marcherait très bien en monochrome."""
        noms = self.BASE
        # DEUX choses distinctes, et les confondre était un défaut : « apercu » est le jeu de paires
        # EN COURS D'EMPLOI (non nul seulement pendant le tracé du bloc), « cache » garde le dernier
        # jeu construit pour n'appeler init_pair() qu'au changement de palette. Un seul attribut pour
        # les deux, et le tracé, en se terminant, effaçait le cache : le dessin suivant retombait
        # silencieusement sur la palette en service.
        self.apercu = None
        self.cache_apercu, self.cache_nom = None, None
        self.cache_brut = {}            # (texte, fond) → paire, pour les lignes pré-colorées
        self.fond = curses.COLOR_BLACK                 # posé avant les retours anticipés (sans couleurs)
        self.paires = dict((n, 0) for n, _ in noms)
        self.paires["choix"] = 0        # surbrillance de la sélection (la paire des correspondances)
        try:
            if not curses.has_colors():
                return
            curses.start_color()
            if curses.COLORS < 8 or curses.COLOR_PAIRS <= len(noms) + 1:
                return
        except curses.error:
            return
        try:
            curses.use_default_colors()
            self.fond = -1
        except curses.error:
            self.fond = curses.COLOR_BLACK
        fond = self.fond
        corresp = self.ROLES
        palette = palette_dotlib(relire)
        if palette and getattr(curses, "COLORS", 8) >= 256 and all(r in palette for _, r in corresp):
            for i, (nom, role) in enumerate(corresp, start=1):
                try:
                    curses.init_pair(i, palette[role], fond)
                    self.paires[nom] = curses.color_pair(i)
                except curses.error:
                    pass
            if "match_fg" in palette and "match_bg" in palette:
                try:
                    curses.init_pair(len(corresp) + 1, palette["match_fg"], palette["match_bg"])
                    self.paires["choix"] = curses.color_pair(len(corresp) + 1)
                except curses.error:
                    pass
            return
        for i, (nom, couleur) in enumerate(noms, start=1):
            try:
                curses.init_pair(i, couleur, fond)
                self.paires[nom] = curses.color_pair(i)
            except curses.error:
                pass

    def couleurs_apercu(self, nom, theme=None, match=None):
        """Les paires d'un APERÇU : peindre un bloc avec une palette qui n'est PAS en service.

        Rend un jeu sans couleurs plutôt que les paires en service quand l'aperçu est impossible
        (moins de 256 couleurs, pas assez de paires, palette inconnue) : montrer les couleurs de la
        palette ACTIVE en prétendant montrer une autre serait un mensonge, et un mensonge est pire
        que l'absence de couleur. Le réglage n'est JAMAIS touché : on lit une palette, on l'applique
        à un bloc de paires à part, et le fichier de thème reste ce qu'il est."""
        if self.cache_nom == (nom, theme, match):
            return self.cache_apercu
        vide = dict((n, 0) for n, _ in self.BASE)
        vide["choix"] = 0
        jeu = vide
        try:
            if (curses.has_colors() and getattr(curses, "COLORS", 8) >= 256
                    and curses.COLOR_PAIRS > self.DECALAGE + len(self.ROLES)):
                palette = palette_dotlib(True, nom, theme)
                if palette and all(r in palette for _, r in self.ROLES):
                    jeu = dict(vide)
                    fond = self.fond
                    for i, (role_ici, role) in enumerate(self.ROLES, start=self.DECALAGE):
                        curses.init_pair(i, palette[role], fond)
                        jeu[role_ici] = curses.color_pair(i)
                    if match and "match_fg" in palette:
                        i = self.DECALAGE + len(self.ROLES)
                        if match == "texte":       # correspondances en TEXTE coloré et gras
                            curses.init_pair(i, palette["match_fg"], fond)
                            jeu["choix"] = curses.color_pair(i) | curses.A_BOLD
                        elif "match_bg" in palette:                       # … ou en FOND coloré
                            curses.init_pair(i, palette["match_fg"], palette["match_bg"])
                            jeu["choix"] = curses.color_pair(i)
        except curses.error:
            jeu = vide
        self.cache_nom, self.cache_apercu = (nom, theme, match), jeu
        return jeu

    def paire_brute(self, fg, bg):
        """Une paire de couleurs pour une ligne PRÉ-COLORÉE, allouée à la demande et gardée.

        Rend None quand on ne peut pas tenir la promesse — moins de 256 couleurs, ou plus de paires
        libres. L'appelant écrit alors le texte NU. Une couleur approchée au hasard serait pire que
        pas de couleur : l'aperçu d'un thème n'a d'intérêt que s'il montre le thème."""
        if fg is None and bg is None:
            return 0
        cle = (fg, bg)
        if cle in self.cache_brut:
            return self.cache_brut[cle]
        try:
            if not curses.has_colors() or getattr(curses, "COLORS", 8) < 256:
                return None
            n = self.DECALAGE_BRUT + len(self.cache_brut)
            if n >= curses.COLOR_PAIRS:
                return None
            curses.init_pair(n, self.fond if fg is None else fg, self.fond if bg is None else bg)
            attr = curses.color_pair(n)
        except curses.error:
            return None
        self.cache_brut[cle] = attr
        return attr

    def jeu(self):
        """Les paires à employer : celles de l'aperçu pendant son tracé, celles en service sinon."""
        return self.apercu or self.paires

    def attr(self, nom, gras=False):
        a = self.jeu().get(nom, 0)
        if not a and nom in ("titre", "onglet"):      # monochrome : garder les repères lisibles
            a = curses.A_BOLD
        return a | curses.A_BOLD if gras else a

    # Genre reconnu par decouper() ↔ paire de couleurs. Une touche garde EXACTEMENT la couleur de
    # la colonne des touches : « (,h) » dans une phrase et « ,h » dans la colonne sont la même chose,
    # et rien ne serait plus troublant que deux couleurs pour cela. Un chemin prend le rôle « path »
    # de la palette, une commande le rôle « num », une variable la couleur des titres.
    GENRES = {"touche": "touche", "chemin": "portee", "option": "onglet",
              "commande": "commande", "variable": "titre", "terme": "commande"}

    # Correspondance rôle d'ici ↔ rôle de la palette du shell : les touches sont des « clés », les
    # titres des « notes », la portée un chemin grisé, le mauvais un « bad », l'onglet une date.
    BASE = (("titre", curses.COLOR_YELLOW), ("touche", curses.COLOR_CYAN), ("portee", curses.COLOR_BLUE),
            ("mauvais", curses.COLOR_RED), ("onglet", curses.COLOR_GREEN), ("commande", curses.COLOR_MAGENTA))
    ROLES = (("titre", "note"), ("touche", "key"), ("portee", "path"),
             ("mauvais", "bad"), ("onglet", "date"), ("commande", "num"))
    DECALAGE = 8        # les paires d'aperçu vivent au-dessus de celles en service, sans les toucher
    DECALAGE_BRUT = 16  # et celles des lignes pré-colorées au-dessus des deux, allouées à la demande

    def peindre(self, x, texte, fond=0, vocabulaire=(), terme=False):
        """Rend une ligne déjà pliée sous forme de segments [(x, fragment, attr)].

        `fond` non nul = la ligne entière a déjà un sens (titre, verdict bon ou mauvais) : on n'y
        touche pas. Repeindre les mots d'une ligne rouge ferait perdre le rouge, qui est l'information.
        Sans couleurs, tous les attributs valent 0 et l'affichage est identique au caractère près."""
        if fond:
            return [(x, texte, fond)]
        segments, position = [], x
        for fragment, genre in decouper(texte, vocabulaire, terme):
            if not self.utf8:
                fragment = ascii_lisible(fragment)      # avant de compter : « … » vaut trois colonnes
            # Les PAIRES, et non attr() : celle-ci promeut « titre » et « onglet » en gras quand il
            # n'y a pas de couleurs, pour que les repères de ligne restent lisibles. Sur un mot au
            # milieu d'une phrase, ce repli mettrait en gras chaque option et chaque variable d'un
            # volet entier. Sans couleurs, la coloration ne doit RIEN faire du tout.
            attr = self.jeu().get(self.GENRES[genre], 0) if genre else 0
            if segments and segments[-1][2] == attr:    # recoller ce qui a la même couleur
                x0, avant, _ = segments[-1]
                segments[-1] = (x0, avant + fragment, attr)
            else:
                segments.append((position, fragment, attr))
            position += len(fragment)
        return segments

    def peindre_roles(self, x, segments):
        """Segments (texte, rôle) → segments d'écran [(x, texte, attr)].

        Un rôle None vaut « texte nu, sans grammaire » : l'appelant qui décrit lui-même sa ligne la
        décrit en entier, et une couleur surprise au milieu d'un relevé qu'il a composé serait du
        bruit. Qu'il demande « commande » s'il en veut une."""
        sortie, position = [], x
        for texte, role in segments:
            if not self.utf8:
                texte = ascii_lisible(texte)       # avant de compter : « … » vaut trois colonnes
            if role is None:
                attr = 0
            else:
                cle = ROLES_LIGNE.get(role)
                if cle is None:                    # défaut de l'appelant : bruyant, jamais une couleur fausse
                    raise ValueError("rôle de ligne inconnu : %r — connus : %s"
                                     % (role, ", ".join(sorted(ROLES_LIGNE))))
                # les PAIRES et non attr() : sans couleurs, la coloration ne fait RIEN du tout. Avec
                # attr(), « bon » et « avertir » passeraient en gras et « mauvais » non — le plus
                # grave des quatre serait le seul à ne rien montrer.
                attr = self.jeu().get(cle, 0)
            if sortie and sortie[-1][2] == attr:   # recoller ce qui a la même couleur
                x0, avant, _ = sortie[-1]
                sortie[-1] = (x0, avant + texte, attr)
            else:
                sortie.append((position, texte, attr))
            position += len(texte)
        return sortie

    def ligne_ecran(self, o, ligne, x, retrait, utile):
        """Une ligne de contenu → la ou les lignes d'écran qu'elle occupe, pliée.

        Un seul chemin pour les trois endroits qui affichent du contenu (volet de contenu, volet droit
        d'un groupe, fenêtre d'aide) : le même pliage, les mêmes repères, les mêmes rôles. Ils étaient
        écrits trois fois, et l'aperçu brut a montré ce que cela coûte — une correction sur deux."""
        if self.filet(ligne):
            return [[(x, self.h_trait * max(1, utile), self.attr("portee"))]]
        if not isinstance(ligne, str):
            morceaux = plier_segments(ligne, max(1, utile))
            return [self.peindre_roles(x if i == 0 else retrait, m) for i, m in enumerate(morceaux)]
        style = self.style_ligne(ligne)
        morceaux = plier(ligne, max(1, utile))
        ecran = [self.peindre(x, morceaux[0], style, o.vocabulaire, True)]
        for suite in morceaux[1:]:
            ecran.append(self.peindre(retrait, suite, style, o.vocabulaire))
        return ecran

    def rendre(self, o, ecran, haut, hauteur, largeur):
        """Le défilement, le compteur et le tracé, une seule fois pour les trois genres."""
        o.haut = max(0, min(o.haut, max(0, len(ecran) - hauteur)))
        o.total_ecran = len(ecran)
        for i, segments in enumerate(ecran[o.haut:o.haut + hauteur]):
            for x, texte, attr in segments:
                self.ecrire(haut + i, x, texte, attr)
        self.compteur(haut, hauteur, largeur, o.haut, len(ecran))

    # --- dessin -----------------------------------------------------------------------------------------
    def ecrire(self, y, x, texte, attr=0):
        h, l = self.ecran.getmaxyx()
        if y < 0 or y >= h or x >= l:
            return
        texte = texte[: max(0, l - x - 1)]
        if not self.utf8:
            texte = ascii_lisible(texte)
        try:
            self.ecran.addstr(y, x, texte, attr)
        except curses.error:
            pass

    def barre(self):
        h, l = self.ecran.getmaxyx()
        etiquettes = [" %d %s " % (i + 1, o.titre) for i, o in enumerate(self.onglets)]
        besoin = sum(len(e) + 1 for e in etiquettes) + 1
        # Le nom de l'appelant est ACCESSOIRE, les onglets ne le sont pas : quand tout ne tient pas,
        # c'est le nom qui cède la place, et le repère de débordement ne vient plus s'y coller.
        avec_nom = bool(self.nom) and besoin + len(self.nom) + 2 <= l
        place = l - (len(self.nom) + 3) if avec_nom else l - 1
        x = 1
        for i, etiquette in enumerate(etiquettes):
            if x + len(etiquette) > place:      # débordement : on le DIT, au lieu d'escamoter la fin
                self.ecrire(0, min(x, place - 1), "\u203a" if self.utf8 else ">", self.attr("mauvais"))
                break
            attr = curses.A_REVERSE | curses.A_BOLD if i == self.actif else self.attr("onglet")
            self.ecrire(0, x, etiquette, attr)
            x += len(etiquette) + 1
        if avec_nom:
            self.ecrire(0, max(x + 1, l - len(self.nom) - 2), self.nom, self.attr("portee"))
        self.ecrire(1, 0, self.h_trait * (l - 1), self.attr("portee"))

    def pied(self):
        h, l = self.ecran.getmaxyx()
        self.ecrire(h - 2, 0, self.h_trait * (l - 1), self.attr("portee"))
        if self.position:                        # après le filet, donc visible
            self.ecrire(h - 2, max(0, l - len(self.position) - 2), self.position, self.attr("portee"))
        aide = AIDE if self.utf8 else AIDE_ASCII
        o = self.onglets[self.actif]
        if self.deux_volets(o):
            # sans cela, on ne sait pas ce que les flèches vont déplacer
            aide = ("[%s] Tab change de volet · " % ("liste" if o.focus == "gauche" else "contenu")) + aide
        if o.genre == "groupes" and (o.action or o.touches):
            sep = " · " if self.utf8 else " . "
            propres = []
            if o.action:
                propres.append("Entrée " + (o.action_libelle or "appliquer"))
            propres += ["%s %s" % (t, libelle) for t, (libelle, _) in o.touches.items()]
            # Les touches de l'onglet d'abord : ce sont les seules que l'utilisateur ne peut pas
            # deviner, et ce sont elles qui agissent. L'aide générale cède la place si tout ne tient
            # pas, et « ? » montre la liste entière.
            aide = sep.join(propres) + sep + aide
        if o.aide:
            # annoncée là où les touches sont annoncées : une aide qu'on ne sait pas demander n'existe pas
            aide = ("? aide · " if self.utf8 else "? aide . ") + aide
        if self.saisie:
            self.ecrire(h - 1, 0, "  filtre : " + self.filtre + "_", curses.A_BOLD)
        elif self.message:
            self.ecrire(h - 1, 0, "  " + self.message, self.attr("titre", True))
        elif self.filtre:
            self.ecrire(h - 1, 0, "  filtre « %s » (Échap pour l'effacer) · %s" % (self.filtre, aide), self.attr("portee"))
        else:
            self.ecrire(h - 1, 0, "  " + aide, self.attr("portee"))

    def lignes_touches(self, o):
        """Les actions de CET onglet, en tête de son aide : le pied les tronque quand elles sont cinq,
        et une touche qu'on ne peut pas lire en entier quelque part n'est pas vraiment offerte."""
        if not (o.action or o.touches):
            return []
        lignes = ["== Touches de cet onglet"]
        if o.action:
            lignes.append("  Entrée   %s" % (o.action_libelle or "appliquer"))
        for t, (libelle, _) in o.touches.items():
            lignes.append("  %-8s %s" % (t, libelle))
        return lignes + ["---"]

    def garder(self, textes):
        if not self.filtre:
            return textes
        f = self.filtre.lower()
        return [t for t in textes if f in texte_ligne(t).lower()]

    def compteur(self, haut, hauteur, largeur, debut, total):
        """Mémorise « 12/86 » ; c'est pied() qui l'écrira, DANS son filet.

        Écrit ici, il était soit par-dessus la dernière ligne de contenu (et en effaçait la fin,
        précisément quand il y a beaucoup à lire), soit sur la ligne du filet — que pied() redessine
        juste après, ce qui le rendait invisible. Le filet est déjà une zone d'information."""
        self.position = " %d/%d " % (min(debut + hauteur, total), total) if total > hauteur else ''

    def colonne_gauche(self, o, noms, comptes, haut, hauteur, choix=None):
        """`comptes` à None : aucun nombre à côté des noms. Un décompte de lignes ne veut rien dire
        pour un groupe qui est un RÉGLAGE — « catppuccin 6 » n'informe de rien."""
        o.rang = max(0, min(o.rang, len(noms) - 1))
        marge = 6 if comptes else 3
        colonne = min(26, max(14, max(len(t) for t in noms) + marge))
        debut = max(0, min(o.rang - hauteur + 2, len(noms) - hauteur))
        o.colonne, o.debut_noms = colonne, debut
        for i, t in enumerate(noms[debut:debut + hauteur]):
            rang = debut + i
            if rang != o.rang:
                attr = self.attr("titre", True)
            elif o.focus == "gauche":
                # `choix` fourni : un groupe qui fait l'aperçu d'un réglage de CORRESPONDANCES montre
                # ici à quoi il ressemble. C'est le seul endroit où ces couleurs servent pour de vrai
                # — la surbrillance de la sélection — donc le seul endroit où la montrer ne ment pas.
                attr = choix or self.paires.get("choix") or curses.A_REVERSE
            else:
                # le focus est à droite : la section choisie reste reconnaissable, sans monopoliser
                # l'attention — sinon on ne sait plus ce que l'on va déplacer
                attr = curses.A_UNDERLINE | curses.A_BOLD
            self.ecrire(haut + i, 1, t[: colonne - marge].ljust(colonne - marge + 1), attr)
            if comptes:
                self.ecrire(haut + i, colonne - 4, "%3d" % comptes[rang], self.attr("portee"))
        for y in range(hauteur):
            self.ecrire(haut + y, colonne, self.v_trait, self.attr("portee"))
        return colonne

    def dessiner_raccourcis(self, o, haut, hauteur, largeur):
        d = o.charger()
        entrees = d["entrees"]
        if self.filtre:
            f = self.filtre.lower()
            entrees = [e for e in entrees if f in " ".join(e).lower()]
        themes = ordonner([e[1] for e in entrees], d.get("themes") or [])
        if not themes:
            self.ecrire(haut + 1, 2, "rien ne correspond à « %s »" % self.filtre if self.filtre else "(aucun raccourci)",
                        self.attr("mauvais"))
            return
        comptes = [sum(1 for e in entrees if e[1] == t) for t in themes] if o.comptes else None
        colonne = self.colonne_gauche(o, themes, comptes, haut, hauteur)
        lignes = [e for e in entrees if e[1] == themes[o.rang]]
        # Colonne des sources : décidée d'après TOUTES les entrées de l'onglet, jamais d'après celles
        # que le filtre retient. Sinon elle apparaît et disparaît pendant qu'on tape, et tout le texte
        # glisse de quelques colonnes sous les doigts de l'utilisateur.
        toutes = o.contenu.get("entrees", []) if isinstance(o.contenu, dict) else []
        sources = set(e[0] for e in toutes)
        largeur_src = 0 if len(sources) <= 1 else max(len(x) for x in sources) + 1
        # La colonne des touches ne prend jamais plus du tiers de la largeur : sinon, sur 76
        # colonnes, « Ctrl-h / Ctrl-j / Ctrl-k / Ctrl-l » lui réserve 34 colonnes et étouffe la
        # description, qui se replie alors sur quatre lignes pour rien.
        largeur_touches = min(34, max(largeur // 3, 10), max([8] + [len(e[2]) for e in lignes]) + 2)
        # Une entrée occupe désormais AUTANT DE LIGNES D'ÉCRAN que son texte en demande : touches et
        # description se replient chacune de leur côté et se juxtaposent par index, de sorte que la
        # suite d'une liste de touches reste sous les touches. Le défilement porte donc sur ces
        # lignes d'écran et non plus sur les entrées : sinon o.haut, g/G et le compteur ne veulent
        # plus rien dire.
        ecran = []
        x_touches = colonne + 2 + largeur_src
        x_desc = x_touches + largeur_touches
        for e in lignes:
            source, _, touches, description, portee = e[:5]
            # filet : une source qui enverrait le caractère espace au lieu de son nom
            tw = plier(touches if touches.strip() else "Espace", max(1, largeur_touches - 1))
            texte = description + ("  (%s)" % portee if portee and portee != "global" else "")
            dw = plier(texte, max(1, largeur - x_desc - 1))
            for j in range(max(len(tw), len(dw))):
                segments = []
                if j == 0 and largeur_src:
                    segments.append((colonne + 2, source, self.attr("portee")))
                if j < len(tw):
                    segments.append((x_touches, tw[j], self.attr("touche", True)))
                if j < len(dw):
                    segments.extend(self.peindre(x_desc, dw[j], 0, o.vocabulaire))
                ecran.append(segments)
        self.rendre(o, ecran, haut, hauteur, largeur)

    def dessiner_groupes(self, o, haut, hauteur, largeur):
        groupes = o.charger()
        if self.filtre:
            f = self.filtre.lower()
            groupes = [(n, [l for l in ls if f in texte_ligne(l).lower()] if f not in n.lower() else ls)
                       for n, ls in groupes]
            groupes = [(n, ls) for n, ls in groupes if ls]
        if not groupes:
            self.ecrire(haut + 1, 2, "rien ne correspond à « %s »" % self.filtre if self.filtre else "(rien à afficher)",
                        self.attr("mauvais"))
            return
        noms = [n for n, _ in groupes]
        comptes = None if not o.comptes else [len(ls) for _, ls in groupes]
        o.rang = max(0, min(o.rang, len(noms) - 1))
        bloc, jeu = self.preparer_apercu(o, noms[o.rang])
        colonne = self.colonne_gauche(o, noms, comptes, haut, hauteur, jeu and jeu.get("choix"))
        lignes = groupes[o.rang][1]
        # Le volet droit plie comme les autres : sans cela, la description d'un groupe était coupée
        # au bord dès 91 colonnes. La suite est décalée de trois colonnes, comme pour le genre texte.
        haut, hauteur = self.bloc_apercu(o, bloc, jeu, colonne, haut, hauteur, largeur)
        o.hauteur = hauteur         # les pages portent sur ce qui DÉFILE, pas sur l'aperçu
        ecran = []
        for l in lignes:
            ecran.extend(self.ligne_ecran(o, l, colonne + 2, colonne + 5, largeur - colonne - 3))
        self.rendre(o, ecran, haut, hauteur, largeur)

    def preparer_apercu(self, o, groupe):
        """Ce que le groupe demande, et les paires correspondantes — avant tout tracé, parce que la
        colonne de gauche en a besoin pour montrer les correspondances."""
        if not o.apercu:
            return None, None
        try:
            bloc = o.apercu(groupe) or {}
        except Quitter:
            raise
        except Exception:                      # un producteur d'aperçu ne fait pas tomber l'onglet
            return None, None
        if not bloc.get("lignes"):
            return None, None
        return bloc, self.couleurs_apercu(bloc.get("palette"), bloc.get("theme"), bloc.get("match"))

    def bloc_apercu(self, o, bloc, jeu, colonne, haut, hauteur, largeur):
        """L'APERÇU d'un groupe : quelques lignes en tête du volet, peintes avec une AUTRE palette.

        En tête et hors défilement, à dessein : c'est une zone de comparaison, et passer d'un thème
        au suivant ne doit pas la faire bouger sous les yeux. Elle ne change RIEN au réglage — on lit
        une palette, on l'applique à un bloc de paires à part, et le fichier de thème reste ce qu'il
        est tant que l'utilisateur n'a pas validé.

        Rend le haut et la hauteur de ce qui reste pour le contenu qui défile."""
        if not bloc:
            return haut, hauteur
        if hauteur < 6:                        # trop court pour couper le volet en deux : pas d'aperçu
            return haut, hauteur
        largeur_utile = max(1, largeur - colonne - 3)
        maxi = max(1, (hauteur - 2) // 2)
        # Les lignes d'aperçu se REPLIENT comme le reste, au lieu d'être coupées au bord : une
        # démonstration tronquée montre une couleur sans montrer ce qu'elle qualifie, et le texte
        # disparaissait en silence. C'est donc le nombre de lignes d'ÉCRAN qui borne le bloc.
        if bloc.get("brut"):
            # Lignes PRÉ-COLORÉES : affichées telles quelles, sans la grammaire. Une barre de statut
            # est faite de fonds précis et d'arrondis ; nos rôles ne savent pas la reproduire, et un
            # aperçu qui montrerait autre chose que la barre réelle serait pire qu'absent.
            lignes = list(bloc["lignes"])[: max(1, (hauteur - 2) // 2)]
            for i, brute in enumerate(lignes):
                x = colonne + 2
                for texte, bg, fg, gras in decouper_sgr(brute):
                    attr = self.paire_brute(fg, bg)
                    if attr is None:
                        attr = 0            # promesse intenable : texte nu, jamais une couleur fausse
                    elif gras:
                        attr |= curses.A_BOLD
                    if not self.utf8:
                        texte = ascii_lisible(texte)
                    self.ecrire(haut + i, x, texte[: max(0, largeur_utile - (x - colonne - 2))], attr)
                    x += len(texte)
            self.ecrire(haut + len(lignes), colonne + 2, self.h_trait * largeur_utile, self.attr("portee"))
            return haut + len(lignes) + 1, hauteur - len(lignes) - 1
        self.apercu = jeu
        try:
            ecran = []
            for l in bloc["lignes"]:
                ecran.extend(self.ligne_ecran(o, l, colonne + 2, colonne + 5, largeur_utile))
                if len(ecran) >= maxi:
                    break
            ecran = ecran[:maxi]
            for i, segments in enumerate(ecran):
                for x, texte, attr in segments:
                    self.ecrire(haut + i, x, texte, attr)
        finally:
            self.apercu = None                 # le reste de l'interface garde la palette EN SERVICE
        self.ecrire(haut + len(ecran), colonne + 2, self.h_trait * largeur_utile, self.attr("portee"))
        return haut + len(ecran) + 1, hauteur - len(ecran) - 1

    @staticmethod
    def filet(l):
        """Une ligne de trois tirets et plus, et rien d'autre : un FILET sur toute la largeur.

        Cinquième repère, ajouté parce qu'un appelant ne peut pas le faire lui-même sans se tromper :
        écrire « ──── » à la main donne des « [?] » sous une locale non UTF-8, et c'est au socle de
        choisir le caractère selon le terminal."""
        nu = texte_ligne(l).strip()
        return len(nu) >= 3 and set(nu) <= set("-\u2500")

    def style_ligne(self, l):
        # Une ligne en SEGMENTS a déjà dit ce que chacun de ses morceaux est : lui appliquer en plus un
        # style de ligne entière effacerait précisément ce qu'elle décrit.
        if not isinstance(l, str):
            return 0
        nu = l.strip()
        if nu.startswith("=="):
            return self.attr("titre", True)
        if nu.startswith(("✗", "x ")) or "MANQUANT" in l or nu.startswith("!"):
            return self.attr("mauvais")
        if nu.startswith(("✓", "+ ")):
            return self.attr("onglet")
        return 0

    def dessiner_texte(self, o, haut, hauteur, largeur):
        lignes = self.garder(o.charger())
        if not lignes:
            self.ecrire(haut + 1, 2, "(rien à afficher)", self.attr("portee"))
            return
        # Même pliage : une ligne trop longue se replie, la suite décalée de trois colonnes pour
        # qu'on voie qu'elle appartient à la précédente. Les états et les journaux produisent
        # couramment des lignes de 90 à 110 caractères (chemin, branche, commit, thème sur une ligne).
        ecran = []
        for l in lignes:
            ecran.extend(self.ligne_ecran(o, l, 1, 4, largeur - 2))
        self.rendre(o, ecran, haut, hauteur, largeur)

    def dessiner(self):
        self.ecran.erase()
        h, l = self.ecran.getmaxyx()
        if l < LARGEUR_MIN or h < HAUTEUR_MIN:
            # le message doit tenir DANS la fenêtre qu'il décrit : mesuré à 34 colonnes, il était
            # coupé au milieu (« fenetre trop petite (34x12, il fa »)
            for i, morceau in enumerate(plier("fenêtre trop petite : %dx%d, il faut %dx%d — agrandis, ou q"
                                              % (l, h, LARGEUR_MIN, HAUTEUR_MIN), max(8, l - 1))[:max(1, h)]):
                self.ecrire(i, 0, morceau, curses.A_BOLD)
            self.ecran.refresh()
            return
        self.barre()
        self.position = ""              # un onglet qui tient à l'écran n'hérite pas du compteur du précédent
        haut, hauteur = 2, max(1, h - 4)
        o = self.onglets[self.actif]
        o.hauteur = hauteur             # publiée pour les pages et la souris
        if o.contenu is None:
            self.ecrire(haut + 1, 2, "chargement…" if self.utf8 else "chargement...", self.attr("portee"))
            self.pied()
            self.ecran.refresh()
            try:
                o.charger()
            except Quitter:
                raise
            except Exception as e:                   # un producteur cassé ne ferme pas tout
                o.contenu = ["onglet illisible : %s" % e]
            self.ecran.erase()
            self.barre()
        try:
            if o.genre == "raccourcis":
                self.dessiner_raccourcis(o, haut, hauteur, l)
            elif o.genre == "groupes":
                self.dessiner_groupes(o, haut, hauteur, l)
            else:
                self.dessiner_texte(o, haut, hauteur, l)
        except Quitter:
            raise
        except Exception as e:                       # un onglet cassé ne ferme pas l'interface
            self.ecrire(haut + 1, 2, "onglet illisible : %s" % e, self.attr("mauvais"))
        if self.aide_ouverte:
            self.dessiner_aide(o, h, l)
        self.pied()
        self.ecran.refresh()

    def dessiner_aide(self, o, h, l):
        """L'aide de l'onglet, par-dessus tout le reste. Elle ne touche à RIEN dessous : ni sélection,
        ni défilement, ni filtre. On la ferme et on retrouve l'onglet exactement comme on l'a laissé.

        Neuf dixièmes de l'écran quand il y a la place, tout l'écran quand il n'y en a pas : des marges
        sur un terminal étroit ne laisseraient plus rien pour le texte, et c'est le texte qu'on vient
        lire."""
        if o.aide_contenu is None:
            try:
                o.aide_contenu = list(o.aide() or [])
            except Quitter:
                raise
            except Exception as e:                   # une aide cassée ne ferme pas l'onglet
                o.aide_contenu = ["aide illisible : %s" % e]
        hg, hd, bg, bd = self.coins
        x0 = 0 if l < 60 else max(1, l // 20)
        y0 = 0 if h < 16 else 1
        larg, haut = l - 2 * x0, h - 2 * y0 - 1
        cadre = self.attr("portee")
        self.ecrire(y0, x0, (hg + self.h_trait * max(0, larg - 2) + hd)[:larg], cadre)
        self.ecrire(y0, x0 + 2, (" Aide — %s " % o.titre)[: max(0, larg - 4)], self.attr("titre", True))
        interieur = max(1, haut - 2)
        # Le contenu se plie, se colore et porte les mêmes repères que les onglets « texte » : une
        # aide est du texte de cet outil, pas un objet à part qui aurait ses propres règles.
        ecran = []
        for ligne in self.lignes_touches(o) + o.aide_contenu:
            ecran.extend(self.ligne_ecran(o, ligne, x0 + 2, x0 + 4, larg - 4))
        o.aide_haut = borne(o.aide_haut, len(ecran), interieur)
        for i in range(interieur):
            # EFFACER d'abord toute la largeur intérieure. Sans cela, chaque ligne n'écrivait que ses
            # propres caractères et laissait voir l'onglet dessous partout ailleurs — des fins de
            # lignes, un séparateur, des restes de mots au milieu du texte d'aide. Une fenêtre qui
            # recouvre doit recouvrir : curses ne le fait pas pour nous, il n'y a qu'un seul plan.
            self.ecrire(y0 + 1 + i, x0, self.v_trait + " " * max(0, larg - 2) + self.v_trait, cadre)
            for x, texte, attr in (ecran[o.aide_haut + i] if o.aide_haut + i < len(ecran) else []):
                self.ecrire(y0 + 1 + i, x, texte[: max(0, x0 + larg - 2 - x)], attr)
        touches = ("↑↓ PgUp/PgDn g G défiler · Échap ou q fermer" if self.utf8
                   else "haut/bas PgUp/PgDn g G defiler . Echap ou q fermer")
        pied = (bg + self.h_trait * 2 + " " + touches + " " + self.h_trait * larg)[: max(1, larg - 1)] + bd
        self.ecrire(y0 + haut - 1, x0, pied, cadre)
        if len(ecran) > interieur:
            self.ecrire(y0 + haut - 1, max(x0, x0 + larg - 14),
                        " %d/%d " % (min(o.aide_haut + interieur, len(ecran)), len(ecran)), cadre)

    # --- boucle -----------------------------------------------------------------------------------------
    def deux_volets(self, o):
        return o.genre in ("raccourcis", "groupes")

    def deplacer(self, pas, o=None):
        """Déplace CE QUI A LE FOCUS : la section à gauche, le contenu à droite.

        Avant, les flèches ne touchaient que la sélection de section : une section plus longue que
        la fenêtre — 86 entrées, 175 lignes d'écran après pliage — n'était tout simplement pas
        lisible jusqu'au bout."""
        o = o or self.onglets[self.actif]
        if self.deux_volets(o) and o.focus == "gauche":
            o.rang = max(0, o.rang + pas)
            o.haut = 0                  # nouvelle section : on la lit depuis le début
        else:
            o.haut = max(0, min(o.haut + pas, max(0, o.total_ecran - 1)))

    def page(self, sens, fraction=1):
        o = self.onglets[self.actif]
        self.deplacer(sens * max(1, int(o.hauteur * fraction)), o)

    def bord(self, fin):
        o = self.onglets[self.actif]
        if self.deux_volets(o) and o.focus == "gauche":
            o.rang = 10 ** 6 if fin else 0
            o.haut = 0
        else:
            o.haut = max(0, o.total_ecran - o.hauteur) if fin else 0

    def defiler_cote(self, o, cote, pas):
        """Défiler un volet SANS lui donner le focus : c'est ce qu'on attend d'une molette."""
        if cote == "gauche":
            o.rang = max(0, o.rang + pas)
            o.haut = 0
        else:
            o.haut = max(0, min(o.haut + pas, max(0, o.total_ecran - 1)))

    def souris(self):
        """Molette et clic. NON ÉPROUVÉE : on ne peut pas injecter un événement souris depuis un
        script (une séquence SGR envoyée par tmux est relue comme des touches ordinaires, ce qui
        fait changer d'onglet et croire à un défaut). À essayer à la main."""
        try:
            _, x, y, _, etat = curses.getmouse()
        except curses.error:
            return
        o = self.onglets[self.actif]
        deux = self.deux_volets(o)
        cote = "gauche" if (deux and x <= o.colonne) else "droite"
        haut_zone = 2
        if etat & getattr(curses, "BUTTON4_PRESSED", 0x80000):
            self.deplacer(-3, o) if cote == o.focus else self.defiler_cote(o, cote, -3)
        elif etat & getattr(curses, "BUTTON5_PRESSED", 0x200000):
            self.deplacer(3, o) if cote == o.focus else self.defiler_cote(o, cote, 3)
        elif etat & getattr(curses, "BUTTON1_PRESSED", 0x2):
            if deux:
                o.focus = cote
            if cote == "gauche" and haut_zone <= y < haut_zone + o.hauteur:
                o.rang = max(0, o.debut_noms + (y - haut_zone))
                o.haut = 0

    def appliquer(self, touche=None):
        """Lance l'action de Entrée (touche=None) ou celle d'une touche propre à l'onglet.

        Même contrat dans les deux cas : la fonction reçoit le nom du groupe choisi, rend un message
        ou lève Quitter. Et dans les deux cas l'onglet est rechargé EN PLACE — une action qui ferait
        sauter la sélection obligerait à retrouver sa place après chaque geste."""
        o = self.onglets[self.actif]
        if o.genre != "groupes" or not o.contenu:
            return
        agir = o.action if touche is None else (o.touches.get(touche) or (None, None))[1]
        if not agir:
            return
        groupes = o.contenu
        if self.filtre:                               # le rang porte sur la liste filtrée
            f = self.filtre.lower()
            groupes = [(n, ls) for n, ls in groupes if f in n.lower() or any(f in l.lower() for l in ls)]
        if not groupes:
            return
        nom = groupes[max(0, min(o.rang, len(groupes) - 1))][0]
        try:
            self.message = agir(nom) or ""
            # une action peut CHANGER le thème du shell : sans cela, le nouveau réglage ne se verrait
            # qu'à la réouverture de l'interface
            self.couleurs(True)
        except Quitter:
            raise                        # un ordre de sortie n'est pas un échec d'action
        except Exception as e:
            self.message = "échec : %s" % e
        try:
            o.recharger_en_place()
        except Quitter:
            raise
        except Exception as e:
            self.message = "%s (et le rechargement a échoué : %s)" % (self.message, e)

    def echeance(self, o):
        """Recharge l'onglet AFFICHÉ si son intervalle est écoulé. Lui seul : un onglet qu'on ne
        regarde pas ne doit rien coûter, et rien ne justifie de lancer des commandes pour une liste
        que personne n'a sous les yeux."""
        if not o.rafraichir:
            return
        maintenant = time.monotonic()
        complet = bool(o.rafraichir_complet and o.produire_complet
                       and maintenant - o.dernier_complet >= o.rafraichir_complet)
        if not complet and maintenant - o.dernier_chargement < o.rafraichir:
            return
        try:
            o.recharger_en_place(complet)
        except Quitter:
            raise
        except Exception as e:
            # Un producteur qui échoue toutes les deux secondes noierait le pied de messages et
            # relancerait sans fin ce qui vient d'échouer. On ARRÊTE le rafraîchissement et on le dit :
            # « R » reste là pour réessayer quand la cause est levée.
            o.rafraichir = 0
            self.message = "rafraîchissement arrêté (%s) — R pour réessayer" % e

    def boucle(self):
        rates = 0
        while True:
            o_vu = self.onglets[self.actif]
            try:
                self.echeance(o_vu)
            except Quitter:
                raise
            self.dessiner()
            # Délai d'attente du clavier UNIQUEMENT pour un onglet vivant affiché : sans cela, la
            # boucle se réveillerait pour rien dans tous les autres cas.
            attente = o_vu.rafraichir
            try:
                self.ecran.timeout(int(max(0.1, attente) * 1000) if attente else -1)
            except curses.error:
                attente = 0
            depart = time.monotonic()
            try:
                touche = self.ecran.get_wch()
                rates = 0
            except curses.error:
                # Deux causes pour la MÊME erreur, et il faut les distinguer : le délai qui expire
                # (normal, on redessine) et l'entrée fermée (tuyau, pseudo-terminal sans clavier), où
                # il faut sortir plutôt que tourner à 100 % de processeur. Deux signes concordants :
                # l'entrée n'est pas à la fin de son fichier, et l'attente a bien duré.
                if attente and not _entree_morte() and time.monotonic() - depart >= attente * 0.5:
                    continue
                rates += 1
                if rates > 20:
                    return
                continue
            except KeyboardInterrupt:
                return
            self.message = ""
            if self.saisie:
                if touche in ("\n", "\r", curses.KEY_ENTER):
                    self.saisie = False
                elif touche == "\x1b":
                    self.saisie = False
                    self.filtre = ""
                elif touche in ("\x7f", "\b", curses.KEY_BACKSPACE, 263):
                    self.filtre = self.filtre[:-1]
                elif isinstance(touche, str) and touche.isprintable():
                    self.filtre += touche
                for o in self.onglets:
                    o.haut = 0
                continue
            # L'aide ouverte prend TOUT le clavier : elle recouvre l'écran, il serait trompeur que
            # des touches agissent sur ce qu'on ne voit plus. Elle ne se ferme que sur Échap ou q, et
            # rend l'onglet exactement comme il était — rien dessous n'a bougé.
            if self.aide_ouverte:
                o = self.onglets[self.actif]
                if touche in ("q", "Q", "\x1b", "?"):
                    self.aide_ouverte = False
                elif touche in (curses.KEY_DOWN, "j"):
                    o.aide_haut += 1
                elif touche in (curses.KEY_UP, "k"):
                    o.aide_haut = max(0, o.aide_haut - 1)
                elif touche in (curses.KEY_NPAGE, " ", "\x06"):
                    o.aide_haut += max(1, self.ecran.getmaxyx()[0] - 6)
                elif touche in (curses.KEY_PPAGE, "\x02"):
                    o.aide_haut = max(0, o.aide_haut - max(1, self.ecran.getmaxyx()[0] - 6))
                elif touche == "g":
                    o.aide_haut = 0
                elif touche == "G":
                    o.aide_haut = 10 ** 9      # borné au dessin, qui seul connaît le nombre de lignes
                continue
            if touche == "?" and self.onglets[self.actif].aide:
                self.aide_ouverte = True
                continue
            if touche in ("q", "Q"):
                return
            elif touche == "\x1b":
                self.filtre = ""
            elif touche == "/":
                self.saisie = True
                self.filtre = ""
            elif touche in ("\n", "\r", curses.KEY_ENTER):
                self.appliquer()
            elif touche in ("\t", curses.KEY_BTAB):
                # Tab passe d'un volet à l'autre quand il y en a deux ; sinon il garde son ancien
                # effet (onglet suivant), pour ne pas devenir une touche morte.
                o = self.onglets[self.actif]
                if self.deux_volets(o):
                    o.focus = "droite" if o.focus == "gauche" else "gauche"
                else:
                    self.actif = (self.actif + (1 if touche == "\t" else -1)) % len(self.onglets)
            elif touche == curses.KEY_RIGHT:
                self.actif = (self.actif + 1) % len(self.onglets)
            elif touche == curses.KEY_LEFT:
                self.actif = (self.actif - 1) % len(self.onglets)
            elif touche == curses.KEY_MOUSE:
                self.souris()
            elif isinstance(touche, str) and touche in "123456789":
                n = int(touche) - 1
                if n < len(self.onglets):
                    self.actif = n
            elif touche in (curses.KEY_DOWN, "j"):
                self.deplacer(1)
            elif touche in (curses.KEY_UP, "k"):
                self.deplacer(-1)
            elif touche in (curses.KEY_NPAGE, " ", "\x06"):     # Ctrl-f
                self.page(1)
            elif touche in (curses.KEY_PPAGE, "\x02"):          # Ctrl-b
                self.page(-1)
            elif touche == "\x04":                              # Ctrl-d : demi-page
                self.page(1, 0.5)
            elif touche == "\x15":                              # Ctrl-u : demi-page
                self.page(-1, 0.5)
            elif touche == "g":
                self.bord(False)
            elif touche == "G":
                self.bord(True)
            elif touche == curses.KEY_RESIZE:
                continue                        # la fenêtre a changé : le prochain dessin relit tout
            elif touche in ("r", "R"):
                self.onglets[self.actif].recharger()
                self.message = "onglet rechargé"
            elif isinstance(touche, str) and touche in self.onglets[self.actif].touches:
                # EN DERNIER : le socle garde ses touches, un onglet ne peut pas les lui reprendre.
                # La construction de l'Onglet refuse déjà les réservées, ceci en est le filet.
                self.appliquer(touche)


# L'interface ouverte, s'il y en a une. Elle est forcément UNIQUE (une seule par processus, dans
# lancer()), et avant_plan() a besoin de l'écran sans que l'appelant ait à le faire circuler jusqu'à
# ses actions — il n'y a rien à transmettre, donc rien à oublier de transmettre.
_INTERFACE = None


def _entree_morte():
    """Vrai si l'entrée standard est à la fin de son fichier — tuyau fermé, pseudo-terminal sans
    clavier. C'est ce qui DISTINGUE une attente qui expire normalement d'une entrée qui ne donnera
    plus jamais rien, et il fallait un signe qui ne dépende pas d'une mesure de temps : une attente
    armée qui rend la main vite est un indice, pas une preuve, et se tromper d'un côté fait sortir une
    interface vivante, de l'autre tourner une boucle à 100 % de processeur.

    Un terminal au repos n'a RIEN à lire ; une entrée fermée, elle, est « prête à lire » et ne rend
    rien. On ne lit donc jamais vraiment : savoir qu'il y a quelque chose suffit, et prendre l'octet
    le volerait au clavier."""
    try:
        fd = sys.stdin.fileno()
    except (AttributeError, ValueError, OSError):
        return False
    try:
        pret, _, _ = select.select([fd], [], [], 0)
    except (OSError, ValueError, select.error):
        return False
    return bool(pret)


def _armer_souris(actif=True):
    """Arme ou désarme les rapports de souris. Désarmer avant de rendre le terminal n'est pas un
    détail : sinon le programme lancé en avant-plan reçoit les rapports de molette comme des
    caractères, et son invite se remplit de « \x1b[M ». Un terminal qui ne gère pas la souris ne doit
    rien casser dans les deux sens."""
    try:
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION if actif else 0)
        if actif:
            curses.mouseinterval(0)
    except (curses.error, AttributeError):
        pass


def avant_plan(argv, cwd=None, env=None, attendre=True):
    """REND le terminal, lance la commande en avant-plan, puis reprend l'interface là où elle était.

    Pour une commande qui a besoin du terminal : elle peut écrire, poser une question « o/N », ouvrir
    un éditeur. Appelable depuis une action. Rend le code de sortie de la commande.

    Pourquoi dans le socle, alors que Quitter existe déjà : Quitter FERME l'interface et rend la main à
    l'appelant, ce qui est juste pour « attacher une session tmux » (on ne revient pas) mais pas pour
    une commande dont on veut voir le résultat avant de continuer — il fallait relancer lancer(), donc
    reconstruire les onglets et perdre la sélection. Ici on revient exactement où l'on était.

    Le terminal est TOUJOURS rendu à l'interface, même si la commande explose : la restauration est
    dans un finally. Hors interface (aucune ouverte), la commande est simplement lancée."""
    inter = _INTERFACE
    if inter is None:                      # appelé hors curses : rien à sauver, rien à restaurer
        try:
            return subprocess.call(list(argv), cwd=cwd, env=env)
        except OSError as e:
            sys.stderr.write("%s\n" % e)
            return 127
    code = 127
    try:
        curses.def_prog_mode()             # garder le mode « programme » pour y revenir tel quel
        _armer_souris(False)
        curses.endwin()
        try:
            code = subprocess.call(list(argv), cwd=cwd, env=env)
        except OSError as e:
            sys.stderr.write("%s\n" % e)
        if attendre:
            # Sans cela, l'interface se redessine par-dessus la sortie de la commande avant qu'on ait
            # pu la lire : le travail est fait et invisible, ce qui revient à ne pas l'avoir fait.
            sys.stdout.write("\n[Entrée] pour revenir à l'interface ")
            sys.stdout.flush()
            try:
                sys.stdin.readline()
            except (OSError, ValueError, KeyboardInterrupt):
                pass
    finally:
        curses.reset_prog_mode()
        _armer_souris(True)
        try:
            curses.update_lines_cols()     # la commande a pu changer la taille de la fenêtre
        except (curses.error, AttributeError):
            pass
        inter.ecran.clearok(True)          # repartir d'un écran vierge : le terminal porte autre chose
        inter.ecran.redrawwin()
        inter.ecran.refresh()
    return code


def lancer(onglets, nom=""):
    """Ouvre l'interface ; ne lève jamais d'exception de terminal. Renvoie 0 à la sortie (q) ; 4 sans terminal
    (entrée ou sortie qui n'en est pas un) ou si curses ne peut pas démarrer, avec un message d'une ligne sur la
    sortie d'erreur, préfixé par `nom` : l'appelant affiche alors son contenu à la suite, en texte. Le terminal
    est toujours rendu (curses.wrapper), y compris si un onglet lève une exception.

    5 si une action a levé Quitter : le terminal est rendu, et onglets.QUITTE porte la valeur donnée.
    L'appelant fait alors ce qui ne peut se faire qu'hors de curses (attacher une session, par
    exemple) ; ce module n'exécute rien."""
    global QUITTE, _INTERFACE
    QUITTE = None                        # jamais la valeur d'une séance précédente
    if not onglets or not sys.stdin.isatty() or not sys.stdout.isatty():
        print("%s : pas de terminal pour l'interface" % (nom or "interface"), file=sys.stderr)
        return 4
    # TERM=dumb : curses ne lève pas forcément — mesuré sur un NAS, il démarre et peint un écran de
    # blancs, donc l'appelant croit avoir affiché quelque chose. Un terminal qui ne sait pas placer
    # le curseur ne peut pas porter une interface : on refuse, et l'appelant écrit son texte.
    if os.environ.get("TERM", "") in ("", "dumb"):
        print("%s : terminal sans capacités (TERM=%s) — affichage en texte"
              % (nom or "interface", os.environ.get("TERM") or "vide"), file=sys.stderr)
        return 4
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass

    def demarrer(ecran):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        ecran.keypad(True)
        _armer_souris(True)
        global _INTERFACE
        interface = Interface(ecran, onglets, nom)
        interface.couleurs()
        _INTERFACE = interface
        try:
            interface.boucle()
        finally:
            _INTERFACE = None          # plus d'interface ouverte : avant_plan() ne doit pas y croire

    try:
        curses.wrapper(demarrer)
    except Quitter as q:                 # avant le filet général : c'est un ordre, pas une panne
        QUITTE = q.valeur
        return 5
    except curses.error as e:
        print("%s : terminal trop limité pour l'interface (%s)" % (nom or "interface", e), file=sys.stderr)
        return 4
    except Exception as e:                       # noqa: BLE001
        # « lancer() ne lève jamais » sans réserve. Tout ce qui n'est pas le rendu d'un onglet
        # (barre, pied, colonne de gauche, un défaut à venir de ce module) remonterait sinon chez
        # l'appelant, qui n'a aucun repli et afficherait une trace python à l'utilisateur.
        print("%s : interface interrompue (%s: %s)" % (nom or "interface", type(e).__name__, e), file=sys.stderr)
        return 4
    return 0
