# Journal des décisions

La gouvernance vit dans ce dépôt, pas dans la mémoire de qui que ce soit : n'importe qui doit
pouvoir reprendre dotlib en lisant API.md, CLAUDE.md, ce journal et les tests.

- **Dépôt public.** Rien de personnel ni de propre à une installation : ni nom de machine, ni
  adresse, ni chemin de dossier personnel, ni identifiant. Un test le vérifie avant chaque publication.
- **Le dépôt fait foi.** Pose par clone complet (jamais superficiel) ou par avance rapide ; aucune
  autre voie (pas d'archive). Toute modification de l'installation se fait sous verrou.
- **Contrat versionné** (API.md, `DOTLIB_API`) : on ajoute, on ne retire pas ; un changement
  incompatible change de version.
- **Réglages utilisateur communs** dans `~/.dotlib/local/` (thème, palette).
- **Palette par défaut : catppuccin.** « actuel » renommée « xterm » (ancien nom accepté).
- **Les utilisateurs de dotlib gardent un repli** : aucun n'échoue si dotlib est absent.
- **Licence MIT** (28/09/2026), titulaire « Peter Host ». Une bibliothèque d'interface n'a rien à
  protéger : la licence la plus simple évite d'avoir à y revenir.
- **Identité publique des commits** : `284082+peterhost@users.noreply.github.com`, auteur ET
  validateur, posée dans la configuration LOCALE du dépôt. Une adresse écrite dans les métadonnées
  d'un commit est publique pour toujours — réécrire l'historique ne la retire ni des clones ni des
  caches. Le test anti-fuite refuse toute autre forme.
- **Branche publique `main`** (et non `master`) : c'est ce que crée GitHub. `deploy-local` clonait
  `--branch master` et échouait avec le code 6, ce qui aurait fait croire à un problème de réseau
  sur chaque machine au lieu d'un nom de branche.
- **Mainteneur** : la session du parc SSH tient la branche principale et relit ; les sessions
  `~/.bash` et `~/.vim` codent et proposent. La gouvernance vit dans des fichiers (CLAUDE.md,
  API.md, ce journal, les tests), pas dans une conversation : un mainteneur qui s'évapore n'en
  est pas un.
- **Le volet de contenu est coloré par le socle, et PEU** (29/09/2026). Demande du propriétaire :
  « le blanc convient, mais il ne faut pas que TOUT soit blanc ». Le socle reconnaît lui-même, dans
  chaque ligne, le sujet d'un volet aligné en deux colonnes, les séquences de touches, les commandes,
  les chemins, les options et les variables ; le reste garde la couleur par défaut. C'est le socle
  qui le fait, et non chaque appelant, pour que `brc ui` et `vrc ui` se ressemblent sans avoir à se
  coordonner. La sobriété est une DÉCISION, pas un réglage : un volet entièrement coloré est aussi
  illisible qu'un volet entièrement blanc, et un test échoue au-delà d'un quart des caractères peints
  sur un échantillon réel — sans ce plafond, la grammaire redeviendrait gourmande au premier ajout.
  **Une seule obligation pour les appelants : séparer les deux colonnes d'un volet aligné par au
  moins deux espaces.** C'est le seul indice qui distingue un sujet d'une phrase, où les mots sont
  séparés par un seul espace.
- **Où vit quoi : dotlib porte ce qu'on LIT en commun, pas ce qui modifie une machine** (29/09/2026).
  Question posée à propos d'un outil qui patche une police de terminal pour lui ajouter les glyphes
  arrondis. Il n'entre pas ici, et la raison vaut au-delà du cas : ce dépôt est **public** (documenter
  la modification d'une police non redistribuable n'y a pas sa place), il doit tourner sur des machines
  qu'on ne choisit pas **sans aucune dépendance** (un patcheur veut fontforge : ce serait la première
  dépendance dure), et il **n'est pas une bibliothèque à la recherche d'usagers**. La frontière :
  dotlib porte ce que plusieurs configurations doivent LIRE en commun — un réglage, une palette, une
  donnée ; ce qui MODIFIE une machine reste chez celui qui l'administre. `DOTLIB_PILL_ROUND` est du
  premier côté, l'outil qui patche la police du second. Un outil extérieur peut CONSEILLER de poser ce
  réglage, il ne l'écrit pas lui-même.
- **Les arrondis de la pastille sont le défaut, et ne dépendent plus du terminal DÉCLARÉ** (29/09/2026).
  Ils n'apparaissaient que si `DOTLIB_TERM=warp`, donc jamais à travers ssh. Erreur de raisonnement et
  non oubli : **c'est le terminal qui AFFICHE qui dessine ces glyphes**, pas l'hôte qui les émet.
  L'hôte distant n'a donc rien à savoir ni rien à installer — et il ne PEUT rien savoir, puisque aucune
  variable ne traverse ssh vers les NAS. D'où un défaut fondé sur ce qui est vérifiable partout : la
  locale est en UTF-8 et ce n'est pas la console. `DOTLIB_PILL_ROUND=0` dans le `local/` d'une machine
  dont la police n'a pas ces glyphes.
- **`DOTLIB_REVISION` côté shell, comme `REVISION` côté Python** (29/09/2026). `DOTLIB_API` ne
  distingue pas le dotlib d'hier de celui d'aujourd'hui, et un appelant ne pouvait donc pas savoir si
  l'ajout dont il a besoin est là. Côté shell, l'absence se paie plus cher : `dotlib_pill -p BAD x T`
  sur une version ancienne prend `-p` pour un nom de couleur et rend une pastille fausse **sans lever
  d'erreur**. Une dégradation silencieuse vaut moins qu'une erreur franche.
