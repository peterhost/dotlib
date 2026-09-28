#!/usr/bin/env python3
"""test-pliage.py — plier() ne perd aucun caractère et ne dépasse jamais la largeur.

    python3 test-pliage.py ~/.dotlib/lib/onglets.py

Cinq formes de texte × cinq largeurs, dont un mot plus long que la colonne (coupe nette
attendue) et une largeur dérisoire (on tronque, faute de place). Sort 0, ou la raison.
"""
import sys
sys.dont_write_bytecode = True
import importlib.machinery
import importlib.util

TEXTES = [
    "nouvel onglet en dernier (=t), fermer l’onglet (=w)",
    "Ctrl-h / Ctrl-j / Ctrl-k / Ctrl-l",
    "court",
    "abcdefghijklmnopqrstuvwxyz0123456789",      # un seul mot, plus long que la colonne
    "mot " * 30,
]
LARGEURS = (3, 10, 12, 26, 34, 80)


def main():
    chemin = sys.argv[1] if len(sys.argv) > 1 else "/Users/atolia/.vim/bin/vrc-interface"
    chargeur = importlib.machinery.SourceFileLoader("module", chemin)
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader("module", chargeur))
    chargeur.exec_module(module)
    if not hasattr(module, "plier"):
        print("ÉCHEC : %s n'expose pas plier()" % chemin)
        return 1
    for texte in TEXTES:
        for largeur in LARGEURS:
            morceaux = module.plier(texte, largeur)
            if not morceaux:
                print("ÉCHEC : pliage vide pour %r à %d" % (texte[:30], largeur)); return 1
            trop = [m for m in morceaux if len(m) > largeur]
            if trop:
                print("ÉCHEC : dépassement à %d : %r" % (largeur, trop[0])); return 1
            if largeur >= 8 and "".join(morceaux).replace(" ", "") != texte.replace(" ", ""):
                print("ÉCHEC : caractères perdus pour %r à %d" % (texte[:30], largeur)); return 1
    print("  ok   pliage : rien perdu, rien qui dépasse (%d textes × %d largeurs)"
          % (len(TEXTES), len(LARGEURS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
