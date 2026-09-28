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
