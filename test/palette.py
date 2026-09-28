#!/usr/bin/env python3
"""test-palette.py — les couleurs suivent le thème du shell, et ne dépendent de rien.

    python3 test-palette.py ~/.dotlib/lib/onglets.py

Quatre situations : une palette connue rend ses index ; « xterm » (les couleurs du
terminal) ne rend rien ; un dossier dotlib inexistant ne rend rien et ne lève pas ; un
palettes.tsv illisible ou mal formé ne rend rien et ne lève pas. Cette dernière est la
garantie du contrat : le module lit un fichier, il ne doit jamais s'y casser.
"""
import os
import sys
sys.dont_write_bytecode = True
import importlib.machinery
import importlib.util
import tempfile

ROLES = ("key", "note", "path", "bad", "date")


def charger(chemin):
    chargeur = importlib.machinery.SourceFileLoader("module", chemin)
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader("module", chargeur))
    chargeur.exec_module(module)
    return module


def avec(module, **env):
    for cle in ("DOTLIB_DIR", "DOTLIB_PALETTE_EFF", "DOTLIB_THEME_EFF"):
        os.environ.pop(cle, None)
    os.environ.update(env)
    return module.palette_dotlib()


def main():
    chemin = sys.argv[1] if len(sys.argv) > 1 else "/Users/atolia/.vim/bin/vrc-interface"
    module = charger(chemin)
    if not hasattr(module, "palette_dotlib"):
        print("ÉCHEC : %s n'expose pas palette_dotlib()" % chemin); return 1
    reel = os.path.expanduser("~/.dotlib")

    if os.path.isfile(os.path.join(reel, "share", "palettes.tsv")):
        r = avec(module, DOTLIB_PALETTE_EFF="everforest", DOTLIB_THEME_EFF="dark")
        manquants = [x for x in ROLES if x not in r]
        if manquants:
            print("ÉCHEC : rôles absents pour everforest/dark : %s" % manquants); return 1
        if not all(isinstance(v, int) for v in r.values()):
            print("ÉCHEC : un index n'est pas un entier"); return 1
        clair = avec(module, DOTLIB_PALETTE_EFF="everforest", DOTLIB_THEME_EFF="light")
        if clair.get("key") == r.get("key"):
            print("ÉCHEC : le fond clair rend les mêmes couleurs que le sombre"); return 1
        print("  ok   palette lue : everforest sombre %s, clair %s"
              % (r["key"], clair["key"]))
    else:
        print("  (pas de palettes.tsv ici : cas « palette connue » sauté)")

    if avec(module, DOTLIB_PALETTE_EFF="xterm", DOTLIB_THEME_EFF="dark"):
        print("ÉCHEC : « xterm » doit laisser les couleurs du terminal"); return 1
    print("  ok   « xterm » : aucune couleur imposée")

    if avec(module, DOTLIB_DIR="/inexistant", DOTLIB_PALETTE_EFF="everforest", DOTLIB_THEME_EFF="dark"):
        print("ÉCHEC : dossier absent, il ne devrait rien rendre"); return 1
    print("  ok   dotlib absent : aucune exception, aucune couleur")

    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "share"))
    with open(os.path.join(d, "share", "palettes.tsv"), "w", encoding="utf-8") as f:
        f.write("everforest\tdark\tkey\tzz\tpas-un-entier\nligne sans tabulation\n")
    if avec(module, DOTLIB_DIR=d, DOTLIB_PALETTE_EFF="everforest", DOTLIB_THEME_EFF="dark"):
        print("ÉCHEC : fichier mal formé, il ne devrait rien rendre"); return 1
    print("  ok   palettes.tsv mal formé : aucune exception, aucune couleur")
    return 0


if __name__ == "__main__":
    sys.exit(main())
