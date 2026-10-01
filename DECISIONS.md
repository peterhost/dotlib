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
- **Un onglet reçoit des SENS, jamais des couleurs : les lignes en segments plutôt que du SGR brut**
  (01/10/2026). La session bash demandait, pour le poste de pilotage de sa forge, d'accepter des lignes
  pré-colorées en SGR dans le volet qui défile — vert pour vivant, gris pour arrêté, rouge pour un état
  à remède, jaune pour une alerte — comme l'aperçu de la révision 8 sait déjà le faire. Refusé, et
  remplacé par des segments `[(texte, rôle), …]` avec six rôles publiés. Deux raisons, l'une technique
  et l'autre de fond. **Technique** : dans un volet qui défile, du SGR casse trois choses à la fois — le
  filtre chercherait la chaîne de l'utilisateur dans les octets d'échappement, le pliage couperait au
  milieu d'une séquence, les décomptes compteraient des caractères invisibles. Le `brut` de la révision
  8 ne marche que parce qu'un aperçu ne défile pas, ne se filtre pas et ne se plie pas : c'est une
  vitrine de trois lignes, pas une liste. **De fond** : ces quatre couleurs ne sont pas des couleurs,
  ce sont des états. Reçues comme des couleurs, elles ne suivraient pas le thème et ne se dégraderaient
  pas là où il n'y a pas de couleurs — or c'est exactement là que tournent les machines contraintes.
  L'appelant dit ce que la chose EST, le socle choisit comment le montrer. Les noms publiés sont ceux
  du sens (`bon`, `mauvais`, `avertir`, `discret`, `vedette`, `commande`) et non les noms internes des
  rôles de palette, qui nomment leur origine (« onglet » pour le vert) et non leur sens. La session
  bash a accepté le même jour : « ils valent mieux que du SGR ».
- **Les touches du socle ne se prêtent pas, et le refus est bruyant** (01/10/2026). Avec plusieurs
  actions par onglet (`touches={"a": ("attacher", fn), …}`), un onglet pouvait demander `r` — déjà
  « recharger », annoncé dans le pied de TOUS les onglets. Trois issues possibles : laisser l'onglet
  l'emporter (une touche qui recharge dans trois onglets et répare dans le quatrième, le pied disant la
  même chose partout), l'ignorer en silence (une touche morte qui ne se voit qu'une fois déployée — on
  connaît, c'est `ONGLETS_API` qui lisait un attribut inexistant), ou refuser. **Refus à la
  CONSTRUCTION de l'onglet** : avant curses, reproductible, et le message nomme les touches libres pour
  que l'appelant n'ait pas à les deviner. Une erreur franche au premier lancement vaut mieux qu'un
  piège qui survit au déploiement.
- **`avant_plan()` : rendre le terminal sans fermer l'interface** (01/10/2026). `Quitter` existait déjà
  pour ce qui ne peut se faire qu'hors de curses, et c'est juste pour « attacher une session tmux » —
  on ne revient pas. Mais pour une commande dont on veut voir le résultat avant de continuer, il fallait
  sortir, lancer, puis relancer `lancer()` : donc reconstruire les onglets et perdre la sélection. Le
  socle rend donc le terminal le temps d'une commande, puis reprend l'onglet là où il était. Deux
  détails qui n'en sont pas : la souris est DÉSARMÉE pendant ce temps (sinon la commande reçoit les
  rapports de molette comme des caractères dans son invite), et « [Entrée] pour revenir » est
  indispensable — sans attente, l'interface se redessine par-dessus la sortie de la commande, et le
  travail est fait mais invisible, ce qui revient à ne pas l'avoir fait.
- **Un onglet vivant ne coûte que quand on le regarde, et une entrée fermée fait toujours sortir**
  (01/10/2026). `rafraichir=2` recharge l'onglet AFFICHÉ toutes les deux secondes : le socle n'arme un
  délai d'attente du clavier que pour celui-là, et dort autrement — rien ne justifie de lancer des
  commandes pour une liste que personne n'a sous les yeux. Le piège était ailleurs, et invisible du
  dehors : `get_wch` lève la MÊME erreur de curses quand le délai expire et quand l'entrée ne donnera
  plus rien, or la boucle comptait ces erreurs pour détecter une entrée fermée et sortait au bout de
  vingt. Un onglet vivant aurait donc quitté tout seul au bout de quarante secondes. Distinguer les deux
  par le temps écoulé ne suffit pas — se tromper d'un côté fait sortir une interface vivante, de l'autre
  tourner une boucle à 100 % de processeur, qui est le défaut le plus grave que la session vim avait
  trouvé. Le signe employé ne dépend pas d'une mesure : un terminal au repos n'a RIEN à lire, une entrée
  fermée est « prête à lire » et ne rend rien. On ne lit jamais l'octet — savoir qu'il y en a un suffit,
  le prendre le volerait au clavier.
