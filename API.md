# dotlib — contrat (API 1)

Ce fichier dit ce qui est **garanti**. Tout ce qui n'y figure pas est interne et peut changer sans
préavis : ne l'utilisez pas, même si cela marche.

## Règles d'évolution

- `DOTLIB_API` (défini par `lib/dotlib.sh`) donne la version du contrat. Un appelant vérifie
  `[ "${DOTLIB_API:-0}" -ge 1 ]` et utilise son propre repli sinon.
- Dans une même version : on **ajoute** (fonction, variable, valeur), on ne **retire** ni ne
  **change le sens** de rien. Un changement incompatible fait passer à `DOTLIB_API=2`.
- `DOTLIB_REVISION` est incrémenté à chaque AJOUT, l'API ne bougeant pas. Un appelant vérifie
  `[ "${DOTLIB_REVISION:-1}" -ge 2 ]` avant d'employer une nouveauté. Côté shell, ce numéro compte
  plus encore que côté Python : `dotlib_pill -p BAD x T` sur un dotlib ancien prend `-p` pour un nom
  de couleur et rend une pastille fausse **sans lever d'erreur** — une dégradation silencieuse, qui ne
  se voit qu'une fois déployée.

      1 : API 1 d'origine
      2 : `dotlib_utf8`, `dotlib_pill -p` et `-c`, arrondis par défaut, `share/palettes-sources.tsv`
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
- `dotlib_utf8` → 0 si le terminal accepte l'UTF-8, 1 sinon, d'après l'environnement (`LC_ALL`, sinon
  `LC_CTYPE`, sinon `LANG` ; `TERM=linux` → non). **La règle n'existe qu'ici** : `tui.sh` y prend ses
  glyphes et la pastille ses arrondis. Deux copies d'une même règle finissent par diverger.
- `dotlib_pill [-p] [-c] COULEUR ICÔNE TEXTE` → `DOTLIB_PILL` : une pastille (icône sur fond coloré,
  texte sur fond neutre). `COULEUR` : `BAD` `NOTE` `KEY` `NUM` `DATE`, ou `RRGGBB`/index 256.
  8 couleurs : inversé ; sans couleur : `[TEXTE]`.
  - **arrondis Powerline (U+E0B6/U+E0B4) par défaut** dès que le terminal peut les afficher : locale
    UTF-8, pas la console. `DOTLIB_PILL_ROUND=0` les coupe, `=1` les force. Le défaut ne pouvait pas
    dépendre de `DOTLIB_TERM=warp` : **en ssh, l'hôte ne sait pas à quel terminal il parle** et aucune
    variable ne traverse ssh vers les NAS, alors que c'est le terminal qui AFFICHE qui dessine ces
    glyphes — l'hôte distant n'a donc rien à savoir, et rien à installer. Un terminal dont la police
    n'a pas ces glyphes montre des carrés : `DOTLIB_PILL_ROUND=0` dans son `local/` le règle.
  - `-p` : pour une INVITE. Chaque suite de séquences est entourée de `\001` `\002`, afin que readline
    ne les compte pas dans la largeur de la ligne. Ce sont bien `\001`/`\002` et non `\[ \]` : les
    crochets ne sont interprétés que pendant l'expansion de `PS1` par bash, donc pas dans du texte
    produit par une substitution de commande — le cas d'une pastille recalculée à chaque invite.
    **Invariant garanti et testé : retirer les marqueurs rend exactement la pastille ordinaire.**
  - `-c` : cœur clignotant (SGR 5), pour un état qu'on ne doit pas oublier. Certains terminaux
    l'ignorent : c'est un renfort, jamais le seul signe.

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
    4 : les lignes de commande se peignent entières ; affectations et noms de fichiers reconnus
    5 : `Onglet(apercu=)`, repère `---`, `sources_palette()`
    6 : `Quitter(valeur)` — sortir de l'interface avec une valeur, code 5, `onglets.QUITTE`
    7 : `Onglet(aide=)` — une aide par onglet, touche « ? », grande fenêtre

Un appelant teste `onglets.API in (les versions qu'il sait utiliser)`, ou lit `API_COMPATIBLES`.
**Le nom de ces deux attributs ne changera pas** : un garde-fou qui lit un attribut inexistant ne
trouve rien et dégrade EN SILENCE, ce qui ne se voit qu'une fois déployé sur toutes les machines.
Quand l'API passera à 2, la 1 restera dans `API_COMPATIBLES` le temps que les appelants adaptent et
testent — l'un d'eux n'a aucune copie de repli.

### Ce qui est garanti

- `onglets.Quitter(valeur)` — exception à LEVER depuis une action pour fermer l'interface et rendre la
  main avec une valeur. `lancer()` rend alors **`5`**, le terminal est rendu, et `onglets.QUITTE` porte
  la valeur. **Le module n'exécute rien** : il sort proprement et rapporte.
  - à quoi cela sert : certaines choses ne peuvent se faire qu'une fois le terminal rendu. `tmux
    attach` en est le cas d'école — curses tient le terminal, donc aucune action ne peut s'y
    substituer. L'appelant, lui, le peut après le retour de `lancer()` ;
  - une **exception** et non une valeur de retour : une action rend déjà un message, et un objet rendu
    à sa place se confondrait avec lui. Levée, l'intention est sans ambiguïté, et elle fonctionne aussi
    depuis une fonction appelée par l'action ;
  - **elle traverse tous les filets** de ce module. Ceux qui empêchent un onglet cassé de fermer
    l'interface (« onglet illisible ») avaleraient sinon un ordre de sortie, et l'interface resterait
    ouverte en affichant une erreur — un test le vérifie, y compris depuis un producteur ;
  - `onglets.QUITTE` est remis à `None` à **chaque** `lancer()` : une valeur laissée par une séance
    précédente serait lue comme neuve.
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
    rechargé et **les couleurs relues à partir du FICHIER de réglage**, en ignorant
    `DOTLIB_PALETTE_EFF` et `DOTLIB_THEME_EFF` : ces variables sont l'état du shell au moment où il a
    lancé l'interface et ne bougent plus ensuite, si bien qu'appuyer sur Entrée sur un thème ne
    changeait rien à l'écran. Si le fichier dit « auto », le fond résolu par le shell est conservé —
    c'est lui qui sait interroger le terminal, jamais ce module.
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
- `onglets.borne(haut, total, hauteur)` → première ligne à afficher, ramenée dans le possible. Publique
  parce qu'elle est la seule façon d'éprouver un défilement SANS terminal : dans un pseudo-terminal,
  curses n'émet que les caractères qui changent d'une image à l'autre, donc chercher un texte dans le
  flux ne prouve rien sur ce qui est à l'écran.
- `onglets.sources_palette(nom)` → `{"git": …, "site": …}`, clés absentes s'il n'y a rien, `{}` si la
  palette est inconnue ou le fichier illisible. Lit `share/palettes-sources.tsv`, une DONNÉE : une
  palette ajoutée là n'oblige à toucher aucun programme.
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
| `---` | filet sur toute la largeur | `---` |

Le filet est un repère et non un dessin à faire soi-même : écrire « ──── » à la main donne des
« [?] » sous une locale non UTF-8, et c'est au socle de choisir le caractère selon le terminal.

### L'aide d'un onglet

`Onglet(..., aide=fonction)` — `fonction()` ne prend aucun argument et rend une liste de lignes.
La touche **`?`** ouvre une grande fenêtre par-dessus tout l'onglet ; `Échap` ou `q` la ferme.
Sans `aide=`, la touche n'existe pas et rien n'est annoncé : un outil qui n'en veut pas ne change pas.

- le contenu se **plie, se colore et porte les mêmes repères** que les onglets « texte » (`==`, `✓`,
  `✗`, `!`, `---`), et reçoit le `vocabulaire` de l'onglet : une aide est du texte de cet outil, pas
  un objet à part avec ses propres règles ;
- elle est **chargée à la première ouverture et gardée**, comme un producteur ; une aide qui lève
  s'affiche comme « aide illisible : … » et ne ferme pas l'onglet ;
- elle défile : `↑↓` `j` `k`, `PgUp`/`PgDn`, `Espace`, `g`, `G`, avec un compteur `n/n` ;
- **elle ne touche à rien dessous** : sélection, défilement et filtre de l'onglet sont retrouvés
  intacts à la fermeture. C'est ce qui fait qu'on ose la demander au milieu d'une recherche ;
- **`?` pendant un filtre `/` est un caractère du filtre**, pas une ouverture : la saisie passe avant ;
- la fenêtre prend neuf dixièmes de l'écran, et **tout l'écran** en dessous de 60 colonnes ou
  16 lignes : des marges sur un terminal étroit ne laisseraient plus rien pour le texte ;
- sans couleurs, cadre sans couleur ; sans UTF-8, cadre ASCII.

### Aperçu d'un groupe dans une autre palette

`Onglet(..., apercu=fonction)` — `fonction(nom_du_groupe)` rend `None`, ou :

    {"lignes": [...], "palette": "nord", "theme": "dark"|"light"|None, "match": "fond"|"texte"|None}

Ces lignes sont peintes **avec la palette demandée**, en tête du volet de droite et **hors
défilement** : c'est une zone de comparaison, et passer d'un thème au suivant ne doit pas la faire
bouger sous les yeux. Un filet la sépare du contenu ordinaire, qui défile en dessous et garde la
palette **en service**, comme tout le reste de l'interface.

Garanties, dans l'ordre où elles comptent :

- **le réglage n'est JAMAIS touché.** On lit une palette, on l'applique à un bloc de paires à part,
  et le fichier de thème reste ce qu'il est tant que l'utilisateur n'a pas validé par Entrée ;
- **quand l'aperçu ne peut pas être honoré** — moins de 256 couleurs, pas assez de paires, palette
  inconnue —, le bloc s'affiche **sans couleur**, et non avec celles en service : montrer la palette
  ACTIVE en prétendant montrer une autre serait un mensonge, et un mensonge est pire que l'absence
  de couleur ;
- `"match"` se montre sur **la ligne sélectionnée** de la colonne de gauche. C'est le seul endroit
  où les couleurs de correspondance servent pour de vrai ; les montrer ailleurs obligerait à
  inventer une surbrillance pour l'occasion ;
- une fenêtre trop courte (moins de six lignes de contenu) n'affiche pas d'aperçu plutôt que de
  couper le volet en deux ; un producteur d'aperçu qui lève ne fait pas tomber l'onglet ;
- **les lignes se replient**, elles ne sont pas coupées au bord : une démonstration tronquée montre
  une couleur sans montrer ce qu'elle qualifie. Le bloc est borné en lignes d'ÉCRAN — la moitié de la
  hauteur disponible au plus —, donc une ligne longue coûte plusieurs lignes du bloc.

**Les plafonds de sobriété mesurés plus bas sont ceux du banc d'essai de ce dépôt, pas une contrainte
imposée à votre contenu** : rien n'est jamais refusé ni tronqué à l'exécution. Un volet de
démonstration qui dépasserait 30 % de caractères peints ne pose donc aucun problème.

### Coloration du volet de contenu

Le volet de droite (ou le volet unique) n'est plus d'une seule couleur. Dans chaque ligne, ce qui
n'est pas de la prose est reconnu et coloré selon un rôle de la palette du shell :

| ce qui est reconnu | exemples | rôle de palette |
|---|---|---|
| le sujet d'une ligne alignée en deux colonnes (séparateur : deux espaces ou plus) | `dépôt`, `mise à jour`, `LargeFile`, `:Theme` | `num` |
| une invocation, commande ET arguments, peinte d'un seul tenant | `brew install pstree`, `arp-scan -l`, `git clone …`, `brc doctor` | `num` |
| séquence de touches entre parenthèses, ou touche « leader » | `(,h)`, `(Ctrl-x)`, `(Dp)`, `(Entrée)`, `,ev` | `key` — la même que la colonne des touches |
| commande Ex, ou code entre accents graves, ou mot du `vocabulaire` | `:Keys`, `` `git status` ``, `brc` | `num` |
| chemin, ou nom de fichier à extension connue | `~/.bashrc`, `/etc/profile`, `tunnels.conf` | `path` |
| option | `--json`, `-v` | `date` |
| variable du shell, ou affectation avec sa valeur | `$EDITOR`, `${HOME}`, `TERM=xterm-256color` | `note` |
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
| liste homogène sans prose (`nom␣␣␣␣état`, `durée␣␣chemin`) | 44 % | 55 % | la part du SUJET dans un tableau |

**À quoi le plafond s'applique importe autant que sa valeur.** Sur une liste homogène, le sujet
occupe la moitié de chaque ligne et rien ne le dilue : 31 % n'y est pas un texte trop peint, c'est
un tableau, et le peindre ainsi est juste — le nom est ce que l'œil cherche. Qui mesurerait un tel
volet avec le plafond de la prose croirait à une régression et « corrigerait » une grammaire qui a
raison. Le plafond y sert quand même : si une règle se mettait à peindre la colonne d'état
avec le sujet, la part sauterait près de 100 %. Il est calibré sur les volets RÉELS les plus denses
(le volet d'état du shell est mesuré à 49 %, où chaque ligne est une durée et un chemin) : un
plafond fixé sous la réalité accuserait une grammaire qui a raison.

**Une ligne qui porte déjà un repère (`==`, `✓`, `✗`, `!`) n'est pas recolorée** : son sens est dans
sa couleur d'ensemble, et repeindre ses mots la lui ferait perdre.

**Une invocation se peint entière** — commande et arguments d'un seul tenant, parce que c'est ce
qu'on recopie : un îlot de couleur au milieu d'une commande est pire que pas de couleur du tout.
Trois façons de la reconnaître, et pas une de plus : un mot de votre `vocabulaire` (même seul) ; un
nom de la petite liste `COMMANDES` — gestionnaires de paquets et outils qui apparaissent dans un
conseil d'installation —, mais seulement s'il reçoit un **vrai** argument : une option, un chemin,
ou un verbe d'action (`install`, `clone`, `update`…). Sans cette exigence, « git 2.55.0 » se mettait
à ressembler à du code, et « vim fournit déjà cette syntaxe » à une invocation — car `vim`, `port`,
`make` ou `go` sont autant des mots de phrase que des commandes. `sudo` est transparent : c'est la
commande qui le suit qui décide. Troisième ouverture : un mot d'allure technique suivi d'une option
(`arp-scan -l`),
parce qu'une option ne suit qu'une commande. Elle s'arrête à un mot de prose, à un mot accentué, à
une ponctuation qui ferme le membre de phrase, et **au séparateur de deux espaces d'un volet
aligné** : ce qu'on tape ne déborde jamais sur son explication.

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
