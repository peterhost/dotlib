#!/usr/bin/env python3
"""test-entree-fermee.py — l'interface sort quand son entrée se ferme, au lieu de tourner à vide.

    python3 test-entree-fermee.py ~/.dotlib/lib/onglets.py

Le cas : un pseudo-terminal dont le MAÎTRE est fermé pendant que le programme lit.
`get_wch()` lève alors `curses.error` à chaque appel ; sans le compteur d'échecs de
`Interface.boucle()`, la boucle tourne à 100 % de processeur et ne rend jamais la main.
On ne peut pas le reproduire avec `script` : il garde le maître ouvert, la lecture
BLOQUE au lieu de lever, et le programme paraît sain.

Deux temps, et le second est le plus important :
  1. avec le module tel quel     → le programme doit sortir vite, code 0 ;
  2. avec le compteur RETIRÉ     → le programme doit rester bloqué (sinon ce test
     ne protège rien : il passerait aussi bien sans le code qu'il surveille).

Sortie : « ok » et code 0, ou la raison de l'échec et code 1.
"""
import os
import pty
import re
import subprocess
import sys
import tempfile
import time

DELAI = 15          # large : on mesure « ça sort » ou « ça ne sort pas », pas une durée
PILOTE = '''
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, %r)
import onglets
sys.exit(onglets.lancer([onglets.Onglet("Un", lambda: ["une ligne"])], "essai"))
'''


def lancer_avec_entree_fermee(dossier_module):
    """Lance l'interface sur un pseudo-terminal dont on ferme le maître. Rend
    (code, secondes) ou (None, secondes) si le programme n'a pas rendu la main."""
    maitre, esclave = pty.openpty()
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(PILOTE % dossier_module)
        pilote = f.name
    debut = time.time()
    p = subprocess.Popen([sys.executable, pilote], stdin=esclave, stdout=esclave,
                         stderr=subprocess.DEVNULL, env=dict(os.environ, TERM="xterm"))
    os.close(esclave)
    time.sleep(0.5)          # laisser curses démarrer
    os.close(maitre)         # ici, toute lecture rend EOF : get_wch lève
    try:
        code = p.wait(timeout=DELAI)
    except subprocess.TimeoutExpired:
        p.kill(); p.wait()
        code = None
    os.unlink(pilote)
    return code, time.time() - debut


def sans_compteur(source):
    """Une copie du module privée de sa sortie sur entrée fermée."""
    texte = open(source, encoding="utf-8").read()
    mute, n = re.subn(r"\n(\s+)if rates > 20:\n\s+return\n", r"\n", texte)
    if n != 1:
        return None, "le compteur d'échecs n'a pas été trouvé (%d correspondance(s))" % n
    d = tempfile.mkdtemp()
    open(os.path.join(d, "onglets.py"), "w", encoding="utf-8").write(mute)
    return d, None


def main():
    source = os.path.abspath(sys.argv[1] if len(sys.argv) > 1
                             else os.path.expanduser("~/.dotlib/lib/onglets.py"))
    if not os.path.isfile(source):
        print("module introuvable : %s" % source); return 1

    code, duree = lancer_avec_entree_fermee(os.path.dirname(source))
    if code is None:
        print("ÉCHEC : l'interface n'a pas rendu la main en %d s, entrée fermée "
              "(boucle à vide ?)" % DELAI); return 1
    if code != 0:
        print("ÉCHEC : sortie avec le code %s au lieu de 0 (en %.1f s)" % (code, duree)); return 1
    print("  ok   entrée fermée : sortie en %.1f s, code 0" % duree)

    d, erreur = sans_compteur(source)
    if erreur:
        print("ÉCHEC : %s" % erreur); return 1
    code, duree = lancer_avec_entree_fermee(d)
    if code is not None:
        print("ÉCHEC : sans le compteur, l'interface est sortie quand même (code %s en %.1f s) : "
              "ce test ne protège donc rien" % (code, duree)); return 1
    print("  ok   sans le compteur, l'interface reste bloquée : le test protège bien ce code")
    return 0


if __name__ == "__main__":
    sys.exit(main())
