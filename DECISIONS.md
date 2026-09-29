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
