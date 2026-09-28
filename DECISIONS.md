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
