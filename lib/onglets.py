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
AIDE = "←→/Tab onglet · ↑↓ déplacer · PgUp/PgDn page · / filtrer · r recharger · q quitter"
AIDE_ASCII = "<-/->/Tab onglet . haut/bas deplacer . PgUp/PgDn page . / filtrer . r recharger . q quitter"
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
        noms = (("titre", curses.COLOR_YELLOW), ("touche", curses.COLOR_CYAN), ("portee", curses.COLOR_BLUE),
                ("mauvais", curses.COLOR_RED), ("onglet", curses.COLOR_GREEN))
        self.paires = dict((n, 0) for n, _ in noms)
        try:
            if not curses.has_colors():
                return
            curses.start_color()
            if curses.COLORS < 8 or curses.COLOR_PAIRS <= len(noms):
                return
        except curses.error:
            return
        try:
            curses.use_default_colors()
            fond = -1
        except curses.error:
            fond = curses.COLOR_BLACK
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
        x = 1
        place = l - (len(self.nom) + 3 if self.nom else 1)
        for i, o in enumerate(self.onglets):
            etiquette = " %d %s " % (i + 1, o.titre)
            if x + len(etiquette) > place:      # débordement : on le DIT, au lieu d'escamoter la fin
                self.ecrire(0, min(x, place - 1), "\u203a" if self.utf8 else ">", self.attr("mauvais"))
                break
            attr = curses.A_REVERSE | curses.A_BOLD if i == self.actif else self.attr("onglet")
            self.ecrire(0, x, etiquette, attr)
            x += len(etiquette) + 1
        if self.nom:
            self.ecrire(0, max(x + 1, l - len(self.nom) - 2), self.nom, self.attr("portee"))
        self.ecrire(1, 0, self.h_trait * (l - 1), self.attr("portee"))

    def pied(self):
        h, l = self.ecran.getmaxyx()
        self.ecrire(h - 2, 0, self.h_trait * (l - 1), self.attr("portee"))
        if self.position:                        # après le filet, donc visible
            self.ecrire(h - 2, max(0, l - len(self.position) - 2), self.position, self.attr("portee"))
        aide = AIDE if self.utf8 else AIDE_ASCII
        o = self.onglets[self.actif]
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
        for i, t in enumerate(noms[debut:debut + hauteur]):
            rang = debut + i
            attr = curses.A_REVERSE if rang == o.rang else self.attr("titre", True)
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
        largeur_touches = min(34, max([8] + [len(e[2]) for e in lignes]) + 2)
        o.haut = max(0, min(o.haut, max(0, len(lignes) - hauteur)))
        for i, e in enumerate(lignes[o.haut:o.haut + hauteur]):
            source, _, touches, description, portee = e[:5]
            x = colonne + 2
            if largeur_src:
                self.ecrire(haut + i, x, source, self.attr("portee"))
                x += largeur_src
            # filet : une source qui enverrait le caractère espace au lieu de son nom
            self.ecrire(haut + i, x, (touches if touches.strip() else "Espace")[: largeur_touches - 1],
                        self.attr("touche", True))
            x += largeur_touches
            texte = description + ("  (%s)" % portee if portee and portee != "global" else "")
            self.ecrire(haut + i, x, texte)
        self.compteur(haut, hauteur, largeur, o.haut, len(lignes))

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
        o.haut = max(0, min(o.haut, max(0, len(lignes) - hauteur)))
        for i, l in enumerate(lignes[o.haut:o.haut + hauteur]):
            self.ecrire(haut + i, 1, l, self.style_ligne(l))
        self.compteur(haut, hauteur, largeur, o.haut, len(lignes))

    def dessiner(self):
        self.ecran.erase()
        h, l = self.ecran.getmaxyx()
        if l < LARGEUR_MIN or h < HAUTEUR_MIN:
            self.ecrire(0, 0, "fenêtre trop petite (%dx%d, il faut %dx%d) — agrandissez, ou q"
                        % (l, h, LARGEUR_MIN, HAUTEUR_MIN), curses.A_BOLD)
            self.ecran.refresh()
            return
        self.barre()
        self.position = ""              # un onglet qui tient à l'écran n'hérite pas du compteur du précédent
        haut, hauteur = 2, max(1, h - 4)
        o = self.onglets[self.actif]
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
    def deplacer(self, pas):
        o = self.onglets[self.actif]
        if o.genre in ("raccourcis", "groupes"):
            o.rang = max(0, o.rang + pas)
            o.haut = 0
        else:
            o.haut = max(0, o.haut + pas)

    def page(self, sens):
        h, _ = self.ecran.getmaxyx()
        o = self.onglets[self.actif]
        o.haut = max(0, o.haut + sens * max(1, h - 6))

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
            elif touche == "\t" or touche == curses.KEY_RIGHT:
                self.actif = (self.actif + 1) % len(self.onglets)
            elif touche == curses.KEY_BTAB or touche == curses.KEY_LEFT:
                self.actif = (self.actif - 1) % len(self.onglets)
            elif isinstance(touche, str) and touche in "123456789":
                n = int(touche) - 1
                if n < len(self.onglets):
                    self.actif = n
            elif touche in (curses.KEY_DOWN, "j"):
                self.deplacer(1)
            elif touche in (curses.KEY_UP, "k"):
                self.deplacer(-1)
            elif touche in (curses.KEY_NPAGE, " "):
                self.page(1)
            elif touche == curses.KEY_PPAGE:
                self.page(-1)
            elif touche == "g":
                o = self.onglets[self.actif]
                o.haut = o.rang = 0
            elif touche == "G":
                o = self.onglets[self.actif]
                o.haut = o.rang = 10 ** 6
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
