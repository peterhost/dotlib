# dotlib

Petite bibliothèque partagée par des configurations personnelles (shell, éditeur, outils) :
couleurs cohérentes (palettes, thème clair / sombre / automatique), messages et menus pour des outils
en ligne de commande, conseils d'installation selon le système. bash 3.2 et plus, sans `tput`,
sans aucune dépendance ; se dégrade proprement (256 couleurs, 8 couleurs, console, `TERM=dumb`).

```sh
. ~/.dotlib/lib/dotlib.sh          # plateforme, conseils d'installation, palette
dotlib_palette_load
printf '%s42%s\n' "$C_R_NUM" "$C_RESET"
dotlib_theme_set DOTLIB_PALETTE nord
```

Le contrat (ce qui est garanti) est dans [API.md](API.md), les décisions dans [DECISIONS.md](DECISIONS.md).

## Installation

```sh
git clone https://github.com/peterhost/dotlib ~/.dotlib
# ou, sur une machine distante : ssh HÔTE 'sh -s -- --yes' < ~/.dotlib/bin/deploy-local
```

Rien n'est écrit hors de `~/.dotlib`. Les réglages de l'utilisateur vivent dans `~/.dotlib/local/`
(non suivi).

## Tests

```sh
make check        # test/contract.sh : API, palettes, pose
make hooks        # installe le crochet pre-push (tests avant chaque poussée)
```
