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
`onglets.REVISION` — entier, incrémenté à chaque AJOUT au contrat ; l'API ne bouge pas pour autant.

Un ajout ne casse personne, mais **un appelant qui emploie une nouveauté doit pouvoir savoir si le
module qu'il a en face la porte** : « API 1 » ne distingue pas le module d'hier de celui
d'aujourd'hui. D'où ce numéro. Le cas s'est produit : un appelant a passé un paramètre ajouté la
veille à un module plus ancien, et a récolté une `TypeError` — un défaut chez lui pour une
insuffisance chez nous. Testez `onglets.REVISION >= n` avant d'employer une nouveauté, ou
construisez sans elle.

    1 : API 1 d'origine
    2 : genre « groupes » et `action` au contrat, paramètre `comptes=`
    3 : coloration du volet de contenu — `decouper()`, `Onglet(vocabulaire=)`

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
- `onglets.Onglet(titre, produire, genre="texte", comptes=True, vocabulaire=None)` —
  `vocabulaire` : les noms que CET onglet sait être des commandes (`("brc", "doctor")`), pour qu'ils
  prennent la couleur des commandes quand une description les cite. Le module ne les devine pas : lui
  seul ignore ce qui est une commande dans votre monde. Facultatif, et sans lui le reste de la
  coloration fonctionne. — `comptes=False` retire le nombre
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
- `onglets.decouper(texte, vocabulaire=(), terme=False)` → `[(fragment, genre), …]`, genre parmi
  `touche`, `commande`, `chemin`, `option`, `variable`, `terme`, ou `""` pour la prose.
  `terme=True` n'est à passer que sur la PREMIÈRE ligne d'écran d'une entrée (le module le fait pour
  vous) : ailleurs, la règle des deux colonnes repeindrait une phrase entière. Sans curses, sans terminal :
  c'est une fonction de texte, donc testable seule. **Le recollement des fragments rend exactement le
  texte d'entrée** — c'est l'invariant qui compte, puisque les fragments sont posés à l'écran chacun à
  son abscisse. Voir « Coloration du volet de contenu » plus bas.

### Mise en forme des lignes (genre « texte »)

Quatre repères, en tête de ligne, et pas un de plus :

| repère | sens | forme ASCII |
|---|---|---|
| `==` | titre de section | `==` |
| `✓` | bon | `+` |
| `✗` | mauvais | `x` |
| `!` | avertissement | `!` |

### Coloration du volet de contenu

Le volet de droite (ou le volet unique) n'est plus d'une seule couleur. Dans chaque ligne, ce qui
n'est pas de la prose est reconnu et coloré selon un rôle de la palette du shell :

| ce qui est reconnu | exemples | rôle de palette |
|---|---|---|
| le sujet d'une ligne alignée en deux colonnes (séparateur : deux espaces ou plus) | `dépôt`, `mise à jour`, `LargeFile`, `:Theme` | `num` |
| séquence de touches entre parenthèses, ou touche « leader » | `(,h)`, `(Ctrl-x)`, `(Dp)`, `(Entrée)`, `,ev` | `key` — la même que la colonne des touches |
| commande Ex, ou code entre accents graves, ou mot du `vocabulaire` | `:Keys`, `` `git status` ``, `brc` | `num` |
| chemin | `~/.bashrc`, `/etc/profile` | `path` |
| option | `--json`, `-v` | `date` |
| variable du shell | `$EDITOR`, `${HOME}` | `note` |
| tout le reste | la prose | couleur par défaut du terminal |

Le principe est de **peindre peu** : la couleur ne vaut que par contraste avec de la prose qui n'en a
pas. Un volet entièrement coloré est aussi illisible qu'un volet entièrement blanc, et c'est pourquoi
les nombres nus ne sont pas colorés (« Marked 2 », « 3 fichiers » n'apprennent rien) et qu'une
parenthèse qui contient un NOM (`(tabular)`, `(MacVim)`, `(jq)`) ou un numéro (`bash 5.3.15(1)`)
reste de la prose. Chaque cas de ce tableau a été **mesuré sur les vrais volets** des deux outils,
et les erreurs relevées là sont devenues des cas de test : `/57` de « 57/57 », `/sombre` de
« clair/sombre », `/..` de « cd ../.. », `-release` d'un numéro de version, `(ms)` d'une unité. Un test mesure cette
sobriété, et il le fait sur **trois formes de contenu**, parce qu'un seul chiffre mentirait sur la
moitié des cas :

| forme | part peinte | plafond | ce que le chiffre veut dire |
|---|---|---|---|
| descriptions de raccourcis | 5 % | 25 % | la retenue sur de la prose |
| volet à deux colonnes portant de la prose (état, commandes, journaux) | 22 % | 30 % | là où la gourmandise se verrait d'abord |
| liste homogène sans prose (`nom␣␣␣␣état`, cinquante lignes) | 31 % | 45 % | la part du SUJET dans un tableau |

**À quoi le plafond s'applique importe autant que sa valeur.** Sur une liste homogène, le sujet
occupe la moitié de chaque ligne et rien ne le dilue : 31 % n'y est pas un texte trop peint, c'est
un tableau, et le peindre ainsi est juste — le nom est ce que l'œil cherche. Qui mesurerait un tel
volet avec le plafond de la prose croirait à une régression et « corrigerait » une grammaire qui a
raison. Le plafond de 45 % y sert quand même : si une règle se mettait à peindre la colonne d'état
avec le sujet, la part sauterait près de 100 %.

**Une ligne qui porte déjà un repère (`==`, `✓`, `✗`, `!`) n'est pas recolorée** : son sens est dans
sa couleur d'ensemble, et repeindre ses mots la lui ferait perdre.

**Deux limites connues, qu'il vaut mieux garder que corriger.** Dans « aussi -b et 'b », `-b` est
peint comme une option alors que c'est une touche, et `'b` n'est pas peint : deux touches voisines,
deux traitements, aucun juste. C'est indécidable hors contexte, et toute règle qui rattraperait `-b`
repeindrait de vraies options — l'erreur deviendrait plus fréquente et plus trompeuse que celle-là.
De même, un sujet de plus de 32 caractères (`:WatchForChangesWhileInThisBuffer`) perd le rôle
« terme » ; s'il commence par `:` il reste peint comme une commande, et le résultat est juste à
l'œil. Ce ne sont pas des défauts à réparer : ce sont des cas où le remède coûte plus que le mal.

Pour que le sujet d'une ligne soit reconnu, **séparez les deux colonnes par au moins deux espaces**
(`"  %-16s  %s"`, et non `"  %-16s %s"` : un seul espace, sur un nom qui remplit la colonne, ne
laisse aucun séparateur). C'est la seule chose à faire côté appelant, et elle vaut pour les deux
outils — c'est là que se joue la cohérence entre eux.

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
