# dotlib

L'endroit **neutre et public** où vivent les réglages que plusieurs configurations personnelles
doivent partager — aujourd'hui le thème (clair / sombre / automatique) et la table des palettes,
lus par la configuration du shell comme par celle de l'éditeur.

Pourquoi un dépôt à part, plutôt qu'un dossier dans l'une d'elles : un réglage commun doit être
lisible sur **toutes** les machines, y compris celles où l'autre configuration n'ira jamais — un
compte partagé avec quelqu'un d'autre, une machine dédiée. Ce dépôt étant public, il s'y installe
sans clé, sans agent et sans rien à autoriser, ce qu'un dépôt privé ne permet pas.

Il fournit aussi une petite couche d'affichage pour les outils en ligne de commande (messages,
menus, couleurs de rôle) et des conseils d'installation selon le système. **Disons-le franchement :
cette couche n'a qu'un usager à ce jour, la configuration du shell.** Elle est ici parce qu'elle
accompagne naturellement la palette, pas parce qu'une foule d'outils l'attend.

bash 3.2 et plus, `sh` POSIX pour la pose, aucune dépendance, aucun processus lancé ; se dégrade
proprement (256 couleurs, 8 couleurs, console, `TERM=dumb`, absence totale de couleur).

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
make check        # test/*.sh : contrat (API, palettes, pose), interface à onglets, anti-fuite
make hooks        # installe le crochet pre-push (tests avant chaque poussée)
```

## Licence

MIT — voir `LICENSE`.
