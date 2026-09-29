# dotlib — contrat (API 1)

Ce fichier dit ce qui est **garanti**. Tout ce qui n'y figure pas est interne et peut changer sans
préavis : ne l'utilisez pas, même si cela marche.

## Règles d'évolution

- `DOTLIB_API` (défini par `lib/dotlib.sh`) donne la version du contrat. Un appelant vérifie
  `[ "${DOTLIB_API:-0}" -ge 1 ]` et utilise son propre repli sinon.
- Dans une même version : on **ajoute** (fonction, variable, valeur), on ne **retire** ni ne
  **change le sens** de rien. Un changement incompatible fait passer à `DOTLIB_API=2`.
- Une valeur de réglage inconnue doit être traitée par l'appelant comme sa valeur par défaut :
  des valeurs peuvent s'ajouter.
- `test/contract.sh` vérifie chaque point ci-dessous ; il doit passer avant toute publication.

## Chargement

| Fichier | Rôle |
|---|---|
| `lib/dotlib.sh` | point d'entrée : plateforme, conseils d'installation, palette. Silencieux, n'écrit rien, bash 3.2+. |
| `lib/tui.sh` | interface pour outils en ligne de commande (charge le reste au besoin). |
| `share/palettes.tsv` | les palettes en données, pour les programmes qui ne sont pas en shell. |

`DOTLIB_DIR` : racine de dotlib (défaut `~/.dotlib`).

## Plateforme (`lib/platform.sh`)

- `DOTLIB_OS` : `darwin` `linux` `cygwin` `msys` `other`
- `DOTLIB_FLAVOR` : `macos` `synology` `debian` `raspbian` `osmc` `ubuntu` `wsl` `cygwin` `msys`, ou l'`ID` de `/etc/os-release`

## Conseils d'installation (`lib/hints.sh`)

- `dotlib_have CMD` → 0 si la commande existe
- `dotlib_pkg_of CMD` → nom du paquet qui la fournit
- `dotlib_install_hint CMD` → commande d'installation adaptée (brew, apt, opkg…)
- `dotlib_need CMD…` → 0 si tout est là, sinon un message par outil manquant (sortie d'erreur) et 1

## Couleurs (`lib/palette.sh`)

Réglage de l'utilisateur, commun à tous les outils : `$DOTLIB_DIR/local/theme.conf`, lignes `CLÉ=valeur`
(une variable d'environnement du même nom l'emporte).

| Clé | Valeurs | Défaut |
|---|---|---|
| `DOTLIB_PALETTE` | `catppuccin` `gruvbox` `nord` `solarized` `tokyonight` `everforest` `edge` `lucius` `papercolor` `pencil` `xterm` (`actuel` : ancien nom de `xterm`, accepté en lecture) | `catppuccin` |
| `DOTLIB_THEME` | `auto` `dark` `light` | `auto` |
| `DOTLIB_MATCH` | `fond` `texte` (surlignage des correspondances) | `fond` |

Fonctions :

- `dotlib_palette_load` → définit les variables ci-dessous. Profondeur : `DOTLIB_COLORS` (`0` `8` `256` `16m`)
  si l'appelant la fixe, sinon déduite de `TERM`, `COLORTERM` et `NO_COLOR`.
- `dotlib_theme_set CLÉ VALEUR` → enregistre le réglage, recharge ; 2 si clé ou valeur inconnue.
- `dotlib_pill COULEUR ICÔNE TEXTE` → `DOTLIB_PILL` : une pastille (icône sur fond coloré, texte sur fond
  neutre), sans `\[ \]` (pas pour PS1). `COULEUR` : `BAD` `NOTE` `KEY` `NUM` `DATE`. Arrondis si
  `DOTLIB_PILL_ROUND=1` (défaut : seulement si `DOTLIB_TERM=warp`). 8 couleurs : inversé ; sans couleur : `[TEXTE]`.

Variables (vides sans couleur) :

- base, qui suivent le thème du terminal : `C_RESET C_BOLD C_DIM C_UL C_REV C_BLACK C_RED C_GREEN C_YELLOW C_BLUE C_MAGENTA C_CYAN C_WHITE C_GREY`
- sens : `C_OK C_WARN C_ERR C_INFO`
- rôles, selon la palette : `C_R_NUM` (numéros) `C_R_DATE` `C_R_TEXT` `C_R_MATCH` (correspondance) `C_R_KEY` (noms) `C_R_PATH` `C_R_BAD` `C_R_NOTE`
- `DOTLIB_PALETTES` : la liste des palettes
- **exportées**, pour les programmes lancés depuis le shell (vim…) : `DOTLIB_THEME_EFF` (`dark` `light`, « auto » résolu) et `DOTLIB_PALETTE_EFF`

## Interface (`lib/tui.sh`)

`tui_title` `tui_info` `tui_ok` `tui_warn` `tui_err` `tui_die TEXTE [code]` `tui_confirm "Q ?" [o|n]`
`tui_ask VAR "Q" [défaut]` `tui_menu VAR "Titre" [défaut] -- choix…` (→ `TUI_INDEX`) `tui_need CMD…` `tui_table`
(colonnes séparées par des tabulations, sur l'entrée standard).
Variables : `TUI_INTERACTIVE`, `TUI_YES` (entrée), `TUI_OK TUI_KO TUI_WARN TUI_PTR`, et
`T_RESET T_BOLD T_DIM T_UL T_REV T_RED T_GREEN T_YELLOW T_BLUE T_MAGENTA T_CYAN T_GREY`
(vides si la sortie n'est pas un terminal).

## `share/palettes.tsv`

`palette <TAB> thème <TAB> rôle <TAB> RRGGBB <TAB> index256`. Rôles : `num date text match_fg match_bg key
path bad note surface text_on_surface crust`. Des lignes et des rôles peuvent s'ajouter.

## Pose (`bin/deploy-local`)

Contrat de pose des modules tiers : options `--check` `--json` `--yes` `--dry-run` `--quiet` `--purge`
`--from-clone` `--posed-by` `--expect` `--remote` ; une ligne JSON sur la sortie standard avec `--json` ;
codes 0 conforme, 1 erreur ou occupé, 2 usage, 3 dégradé, 4 absent, 5 mise à jour disponible,
6 dépôt inaccessible (réseau), 7 outil manquant sur la machine (git) — 7 est distinct de 6 :
il se règle en une commande, que le message donne.

## Interface à onglets (`lib/onglets.py`, Python ≥ 3.8)

Socle commun de `brc interface` et `vrc interface`. Rien à l'import : ni terminal, ni processus, ni
fichier. L'appelant pose `sys.dont_write_bytecode = True` avant d'importer (aucun `__pycache__` dans
`~/.dotlib` : un `.pyc` porte le chemin absolu de son source, donc un nom de compte).

### Version, et pourquoi il n'y aura pas de rupture sèche

`onglets.API` — entier, vaut `1`.
`onglets.API_COMPATIBLES` — tuple des versions que ce module sert encore, vaut `(1,)`.

Un appelant teste `onglets.API in (les versions qu'il sait utiliser)`, ou lit `API_COMPATIBLES`.
**Le nom de ces deux attributs ne changera pas** : un garde-fou qui lit un attribut inexistant ne
trouve rien et dégrade EN SILENCE, ce qui ne se voit qu'une fois déployé sur toutes les machines.
Quand l'API passera à 2, la 1 restera dans `API_COMPATIBLES` le temps que les appelants adaptent et
testent — l'un d'eux n'a aucune copie de repli.

### Ce qui est garanti

- `onglets.lancer(onglets, nom="")` → `0` à la sortie ; `4` si l'entrée ou la sortie n'est pas un terminal,
  ou si curses ne démarre pas, avec une ligne « `nom` : … » sur la sortie d'erreur (l'appelant
  affiche alors son contenu à la suite). Jamais d'exception de terminal ; le terminal est toujours
  rendu, y compris si un onglet lève.
- `onglets.Onglet(titre, produire, genre="texte", comptes=True)` — `comptes=False` retire le nombre
  affiché à côté de chaque nom dans la colonne de gauche : un décompte de lignes ne veut rien dire
  pour un groupe qui est un RÉGLAGE (« catppuccin 6 » n'informe de rien). — `produire` est un appelable sans argument, appelé à la
  PREMIÈRE ouverture de l'onglet et gardé (`r` recharge). Une exception d'un producteur n'emporte
  pas l'interface : l'onglet affiche « illisible ».
  - `genre="texte"` : `produire()` → liste de lignes ;
  - `genre="groupes"` : `produire()` → `[(nom, [lignes]), …]` — les noms à gauche, les lignes du
    choisi à droite. `action(nom)` facultative, appelée par Entrée, rend un message ; l'onglet est
    rechargé et **les couleurs relues** (une action peut changer le thème du shell).
  - `genre="raccourcis"` : `produire()` → `{"entrees": [[source, thème, touches, description,
    portée], …], "themes": [ordre de référence]}`. Les thèmes présents sont rangés selon `themes`,
    les autres à la suite. **Les colonnes au-delà de la cinquième sont ignorées** : n'en ajoutez pas
    une sixième en comptant qu'elle arrive. L'ordre des thèmes est une DONNÉE que vous fournissez ;
    le module ne le calcule ni ne le devine jamais.
- `onglets.sortie(commande, cwd=None, env=None, delai=60)` → lignes sans couleurs ni séquences d'échappement.
  `NO_COLOR=1`, **le vrai `TERM` est conservé** (un `TERM=dumb` change ce que certains programmes
  annoncent : vim y déduit un terminal sans couleurs et rapporte un autre thème que le sien).
  L'entrée est FERMÉE (sans quoi une commande qui lit son entrée fige l'interface). Jamais
  d'exception : commande absente, droit refusé, trop longue → une ligne entre parenthèses.
  **Le délai de 60 s ne suffit pas à un producteur qui lance un autre programme** : un état qui
  démarre vim deux fois et teste un accès réseau dépasse la minute sur un NAS. Relevez `delai=`.
- `onglets.utf8()` → booléen, sans curses, testable seul. Décide d'après l'ENVIRONNEMENT
  (`LC_ALL`, sinon `LC_CTYPE`, sinon `LANG`, contient « utf…8 »), et `TERM=linux` → faux d'office.
  Ne jamais utiliser `locale.getpreferredencoding()` : depuis Python 3.7 il rend `utf-8` même sous
  `LC_ALL=C` (PEP 538/540), donc tout repli ASCII fondé sur lui est du code mort.
- `onglets.ordonner(presents, reference)` → les présents dans l'ordre de référence, les autres à la suite.

### Mise en forme des lignes (genre « texte »)

Quatre repères, en tête de ligne, et pas un de plus :

| repère | sens | forme ASCII |
|---|---|---|
| `==` | titre de section | `==` |
| `✓` | bon | `+` |
| `✗` | mauvais | `x` |
| `!` | avertissement | `!` |

### Dégradation — garantie et testée

Sans couleurs (`has_colors()` faux, `COLORS < 8`, `COLOR_PAIRS` insuffisant : c'est le cas d'un NAS
sous DSM, qui rapporte `COLORS=0` malgré des terminfo présents) → monochrome lisible, repères en
gras. Locale non UTF-8 → cadres ASCII et textes **translittérés** (`edition`, `themes`), jamais des
points d'interrogation. Fenêtre plus petite que 40×10 → un message, pas une exception. Entrée fermée
(tuyau, pseudo-terminal sans clavier) → sortie après 20 échecs, jamais de boucle à vide.

### Touches

←→ Tab Maj-Tab `1`…`9` (onglets) · ↑↓ `j` `k` · PgUp PgDn Espace · `g` `G` · `/` filtre (Échap
l'efface) · Entrée (action) · `r` recharger · `q` quitter.

### Hors contrat, expérimental

`lire_tsv()` : utilisable, mais non garanti — aucun appelant ne s'en sert. On ne garde pas un nom
dont personne n'a besoin.

(Le genre `groupes` et `action` sont entrés au contrat le 29/09, après avoir tourné dans
`brc interface` sur une vraie machine. C'est la règle : on ne grave pas une intention, on grave ce
qui a été éprouvé. Leur entrée est un AJOUT, donc toujours l'API 1.)

### Obtenir et mettre à jour dotlib

Un seul poseur, celui-ci ; plusieurs déclencheurs.

- **Absence** — comblée automatiquement, sans question : cloner le dépôt public dans un dossier
  temporaire, puis exécuter le `bin/deploy-local` **du clone** (`--yes --from-clone <dossier>`),
  qui prend le verrou, refuse un clone superficiel, conserve `local/` et met en place. Ne recopiez
  jamais de code de pose.
- **Mise à jour** — jamais automatique, jamais au démarrage d'un shell ou d'un éditeur :
  `brc maj` / `vrc maj`, appelant `~/.dotlib/bin/deploy-local --yes --posed-by bash|vim`, le plan
  affiché d'abord puis confirmation. Sans terminal, la partie dotlib est SAUTÉE et annoncée : on ne
  met pas à jour le dépôt d'un autre projet sans témoin. Elle passe en dernier, et son échec ne doit
  pas faire échouer la mise à jour de l'appelant.
- `--posed-by parc|shell|bash|vim` : information seulement, jamais prise en compte dans un verdict.
