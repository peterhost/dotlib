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
