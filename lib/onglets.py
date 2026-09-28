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
                action(nom) facultative, appelée par Entrée, renvoie un message (l'onglet est rechargé)

Dégradation (voulue, testée) : aucune couleur (ncurses sans couleurs, TERM=vt100…) → monochrome lisible ;
locale non UTF-8 → cadres en ASCII ; fenêtre trop petite → message ; entrée fermée → sortie ; le terminal
est toujours rendu (curses.wrapper). Rien n'est fait à l'import. Python ≥ 3.8, bibliothèque standard.
API = 1 : on ajoute, on ne retire pas, on ne change pas le sens sans changer ce numéro (voir API.md).
"""

import curses
import locale
import os
import re
import subprocess
import sys
import unicodedata

API = 1
# Les versions que ce module sert ENCORE. Un appelant sans copie de repli lit ceci pour savoir s'il
# peut s'en servir ; quand API passera à 2, la 1 y restera le temps qu'il adapte et teste.
API_COMPATIBLES = (1,)

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


def palette_dotlib():
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
    palette = os.environ.get("DOTLIB_PALETTE_EFF", "")
    fond = os.environ.get("DOTLIB_THEME_EFF", "")
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
        fond = "dark"
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


class Onglet:
    """Un onglet : un titre, de quoi produire son contenu (chargé à la première ouverture et gardé)."""

    def __init__(self, titre, produire, genre="texte", action=None):
        self.titre = titre
        self.produire = produire
        self.genre = genre
        self.action = action
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
        return self.contenu

    def recharger(self):
        self.contenu = None
        self.haut = 0
        self.charger()


class Interface:
    def __init__(self, ecran, onglets, nom=""):
        self.ecran = ecran
        self.onglets = onglets
        self.nom = nom
        self.actif = 0
        self.filtre = ""
        self.saisie = False
        self.message = ""
        self.paires = {}
        self.position = ""              # « 12/86 », écrit par pied() dans son filet
        self.utf8 = utf8()
        self.h_trait, self.v_trait = ("─", "│") if self.utf8 else ("-", "|")

    # --- couleurs : celles de base du terminal, seulement s'il en a assez ; sinon monochrome ----------
    def couleurs(self):
        """TROIS étages : la palette du shell (256 couleurs et tous les rôles présents), les couleurs
        de base du terminal, puis le monochrome. Les gardes du dernier étage ne sont pas
        décoratives : un NAS sous DSM rapporte COLORS=0 malgré des terminfo présents, et
        use_default_colors() comme init_pair() y lèvent — sans try, l'interface ne s'ouvrirait pas
        là où elle marcherait très bien en monochrome."""
        noms = (("titre", curses.COLOR_YELLOW), ("touche", curses.COLOR_CYAN), ("portee", curses.COLOR_BLUE),
                ("mauvais", curses.COLOR_RED), ("onglet", curses.COLOR_GREEN))
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
            fond = -1
        except curses.error:
            fond = curses.COLOR_BLACK
        # rôles de dotlib ↔ rôles d'ici : les touches sont des « clés », les titres des « notes »,
        # la portée un chemin grisé, le mauvais un « bad », l'onglet une date
        corresp = (("titre", "note"), ("touche", "key"), ("portee", "path"),
                   ("mauvais", "bad"), ("onglet", "date"))
        palette = palette_dotlib()
        if palette and getattr(curses, "COLORS", 8) >= 256 and all(r in palette for _, r in corresp):
            for i, (nom, role) in enumerate(corresp, start=1):
                try:
                    curses.init_pair(i, palette[role], fond)
                    self.paires[nom] = curses.color_pair(i)
                except curses.error:
                    pass
            if "match_fg" in palette and "match_bg" in palette:
                try:
                    curses.init_pair(6, palette["match_fg"], palette["match_bg"])
                    self.paires["choix"] = curses.color_pair(6)
                except curses.error:
                    pass
            return
        for i, (nom, couleur) in enumerate(noms, start=1):
            try:
                curses.init_pair(i, couleur, fond)
                self.paires[nom] = curses.color_pair(i)
            except curses.error:
                pass

    def attr(self, nom, gras=False):
        a = self.paires.get(nom, 0)
        if not a and nom in ("titre", "onglet"):      # monochrome : garder les repères lisibles
            a = curses.A_BOLD
        return a | curses.A_BOLD if gras else a

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
        if o.genre == "groupes" and o.action:
            aide = "Entrée appliquer · " + aide
        if self.saisie:
            self.ecrire(h - 1, 0, "  filtre : " + self.filtre + "_", curses.A_BOLD)
        elif self.message:
            self.ecrire(h - 1, 0, "  " + self.message, self.attr("titre", True))
        elif self.filtre:
            self.ecrire(h - 1, 0, "  filtre « %s » (Échap pour l'effacer) · %s" % (self.filtre, aide), self.attr("portee"))
        else:
            self.ecrire(h - 1, 0, "  " + aide, self.attr("portee"))

    def garder(self, textes):
        if not self.filtre:
            return textes
        f = self.filtre.lower()
        return [t for t in textes if f in t.lower()]

    def compteur(self, haut, hauteur, largeur, debut, total):
        """Mémorise « 12/86 » ; c'est pied() qui l'écrira, DANS son filet.

        Écrit ici, il était soit par-dessus la dernière ligne de contenu (et en effaçait la fin,
        précisément quand il y a beaucoup à lire), soit sur la ligne du filet — que pied() redessine
        juste après, ce qui le rendait invisible. Le filet est déjà une zone d'information."""
        self.position = " %d/%d " % (min(debut + hauteur, total), total) if total > hauteur else ''

    def colonne_gauche(self, o, noms, comptes, haut, hauteur):
        o.rang = max(0, min(o.rang, len(noms) - 1))
        colonne = min(26, max(14, max(len(t) for t in noms) + 6))
        debut = max(0, min(o.rang - hauteur + 2, len(noms) - hauteur))
        o.colonne, o.debut_noms = colonne, debut
        for i, t in enumerate(noms[debut:debut + hauteur]):
            rang = debut + i
            if rang != o.rang:
                attr = self.attr("titre", True)
            elif o.focus == "gauche":
                attr = self.paires.get("choix") or curses.A_REVERSE
            else:
                # le focus est à droite : la section choisie reste reconnaissable, sans monopoliser
                # l'attention — sinon on ne sait plus ce que l'on va déplacer
                attr = curses.A_UNDERLINE | curses.A_BOLD
            self.ecrire(haut + i, 1, t[: colonne - 6].ljust(colonne - 5), attr)
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
        comptes = [sum(1 for e in entrees if e[1] == t) for t in themes]
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
                    segments.append((x_desc, dw[j], 0))
                ecran.append(segments)
        o.haut = max(0, min(o.haut, max(0, len(ecran) - hauteur)))
        o.total_ecran = len(ecran)
        for i, segments in enumerate(ecran[o.haut:o.haut + hauteur]):
            for x, texte, attr in segments:
                self.ecrire(haut + i, x, texte, attr)
        self.compteur(haut, hauteur, largeur, o.haut, len(ecran))

    def dessiner_groupes(self, o, haut, hauteur, largeur):
        groupes = o.charger()
        if self.filtre:
            f = self.filtre.lower()
            groupes = [(n, [l for l in ls if f in l.lower()] if f not in n.lower() else ls) for n, ls in groupes]
            groupes = [(n, ls) for n, ls in groupes if ls]
        if not groupes:
            self.ecrire(haut + 1, 2, "rien ne correspond à « %s »" % self.filtre if self.filtre else "(rien à afficher)",
                        self.attr("mauvais"))
            return
        noms = [n for n, _ in groupes]
        colonne = self.colonne_gauche(o, noms, [len(ls) for _, ls in groupes], haut, hauteur)
        lignes = groupes[o.rang][1]
        o.haut = max(0, min(o.haut, max(0, len(lignes) - hauteur)))
        for i, l in enumerate(lignes[o.haut:o.haut + hauteur]):
            self.ecrire(haut + i, colonne + 2, l, self.style_ligne(l))
        self.compteur(haut, hauteur, largeur, o.haut, len(lignes))

    def style_ligne(self, l):
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
            style = self.style_ligne(l)
            morceaux = plier(l, max(1, largeur - 2))
            ecran.append((1, morceaux[0], style))
            for suite in morceaux[1:]:
                ecran.append((4, suite, style))
        o.haut = max(0, min(o.haut, max(0, len(ecran) - hauteur)))
        o.total_ecran = len(ecran)
        for i, (x, texte, style) in enumerate(ecran[o.haut:o.haut + hauteur]):
            self.ecrire(haut + i, x, texte, style)
        self.compteur(haut, hauteur, largeur, o.haut, len(ecran))

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
        except Exception as e:                       # un onglet cassé ne ferme pas l'interface
            self.ecrire(haut + 1, 2, "onglet illisible : %s" % e, self.attr("mauvais"))
        self.pied()
        self.ecran.refresh()

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

    def appliquer(self):
        o = self.onglets[self.actif]
        if o.genre != "groupes" or not o.action or not o.contenu:
            return
        groupes = o.contenu
        if self.filtre:                               # le rang porte sur la liste filtrée
            f = self.filtre.lower()
            groupes = [(n, ls) for n, ls in groupes if f in n.lower() or any(f in l.lower() for l in ls)]
        if not groupes:
            return
        nom = groupes[max(0, min(o.rang, len(groupes) - 1))][0]
        try:
            self.message = o.action(nom) or ""
        except Exception as e:
            self.message = "échec : %s" % e
        rang = o.rang
        o.recharger()
        o.rang = rang

    def boucle(self):
        rates = 0
        while True:
            self.dessiner()
            try:
                touche = self.ecran.get_wch()
                rates = 0
            except curses.error:
                # entrée fermée (tuyau, pseudo-terminal sans clavier) : sortir plutôt que tourner à vide
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


def lancer(onglets, nom=""):
    """Ouvre l'interface ; ne lève jamais d'exception de terminal. Renvoie 0 à la sortie (q) ; 4 sans terminal
    (entrée ou sortie qui n'en est pas un) ou si curses ne peut pas démarrer, avec un message d'une ligne sur la
    sortie d'erreur, préfixé par `nom` : l'appelant affiche alors son contenu à la suite, en texte. Le terminal
    est toujours rendu (curses.wrapper), y compris si un onglet lève une exception."""
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
        try:                            # souris : un terminal qui ne la gère pas ne doit rien casser
            curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
            curses.mouseinterval(0)
        except (curses.error, AttributeError):
            pass
        interface = Interface(ecran, onglets, nom)
        interface.couleurs()
        interface.boucle()

    try:
        curses.wrapper(demarrer)
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
