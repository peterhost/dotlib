# dotlib — règles de travail

Bibliothèque d'interface partagée (couleurs, affichage, conseils d'installation), utilisée par
`~/.bash`, `~/.vim` et le parc SSH. Elle est posée en `~/.dotlib` sur toutes les machines par
l'outil `parc`, et récupérée d'elle-même par `~/.bash` si elle manque.

**Ce dépôt est PUBLIC.** Tout ce qui y entre est visible par n'importe qui, pour toujours : une
poussée ne se rattrape pas, réécrire l'historique ne retire rien des clones ni des caches.

## Qui décide quoi

- La **session du parc SSH** (`~/.ssh`) est mainteneuse : elle tient la branche principale, relit
  chaque changement et pousse. Elle arbitre quand deux projets veulent la même chose autrement.
- Les **sessions `~/.bash` et `~/.vim`** codent ici et proposent. Rien n'arrive dans la branche
  principale sans relecture.
- **Pierre ne lance pas de session dans ce dépôt** : ce sont nos sessions qui y travaillent, de
  façon coordonnée. Les décisions qui l'engagent (visibilité, licence, identité publique) sont les
  siennes, et se demandent avant, pas après.
- Un mainteneur qui s'évapore n'est pas un mainteneur : **tout ce qui fait la gouvernance vit dans
  des fichiers de ce dépôt** — ce fichier, `API.md`, `DECISIONS.md`, les tests. Critère : n'importe
  qui doit pouvoir reprendre dotlib en lisant le dépôt, sans rien savoir d'une conversation.

## Rien de personnel, jamais

Interdits, y compris dans un test, un exemple, un commentaire ou un message de commit : adresse IP,
adresse MAC, adresse de courriel, chemin de home nommé (`/Users/<nom>`), nom d'une machine réelle,
nom d'un réseau, nom d'un dépôt privé. Pour un exemple, les noms réservés à la documentation :
`example.com`, `example.invalid`, `192.0.2.1` (RFC 2606 et 5737).

`sh test/anti-fuite.sh` **avant chaque poussée**, sans exception. Il fonctionne à deux étages :

1. des **motifs génériques**, dans le dépôt, qui ne nomment personne et protègent n'importe quel
   contributeur ;
2. une liste de **littéraux interdits** (les vrais noms de machines et de comptes) tenue **hors du
   dépôt**, dans `~/.dotlib/local/mots-interdits`, jamais suivie par git.

Le deuxième étage est ainsi fait exprès : **écrire la liste des vrais noms dans le dépôt publierait
exactement ce qu'elle protège.** L'erreur a déjà été commise dans un dépôt voisin — un test qui
contenait la liste des machines, poussé en public. Un vrai nom de machine peut entrer en collision
avec un terme parfaitement légitime — le nom d'une distribution Linux, par exemple, qu'on cite
forcément là où les systèmes sont énumérés. Ce cas s'autorise par chemin, dans la liste privée, et
nulle part ailleurs : le mot reste interdit partout sauf là où il ne désigne pas la machine.

**Identité des commits** : uniquement `…@users.noreply.github.com`, auteur et validateur. La
configuration est posée localement dans ce dépôt (`git config user.email`), pas globalement. Le test
refuse toute autre forme dans l'historique.

Le crochet `bin/hooks/pre-push` (installé par `make hooks`) lance les tests avant une poussée. Il ne
protège que la machine où il est posé : il ne remplace ni le test lancé à la main, ni la relecture.

## Le contrat

`API.md` est le contrat, et il fait foi. `DOTLIB_API` en donne la version. Les noms publics (`tui_*`,
`dotlib_*`, `C_*`, `T_*`) sont promis aux autres dépôts : on en **ajoute**, on n'en retire ni n'en
change le sens sans changer la version et prévenir les deux autres sessions. Un changement qui casse
un appelant n'est pas un détail d'implémentation.

## Portabilité

Ce code tourne sur des machines qu'on ne choisit pas : macOS, Debian, Synology (DSM), Raspberry Pi.

- `sh` POSIX pour ce qui doit tourner partout (`bin/deploy-local`), **bash 3.2** pour le reste : pas
  de tableaux associatifs, pas de `${x^^}`, pas de `readarray`.
- Aucune option GNU qui n'existe pas en BSD (`sed -i`, `grep -P`, `date -d`…).
- `TERM=dumb` et l'absence totale de couleurs doivent rester des cas NORMAUX, pas des erreurs.
- Rien ne suppose un terminal : une session non interactive charge la bibliothèque sans rien afficher.

## Deux leçons apprises à la dure

**Ne cherchez jamais un processus avec `ps | grep <motif>`.** Deux fois de suite, dans le parc, la
même détection a été fausse : d'abord parce que le motif cherché se trouvait dans le texte du script
envoyé par ssh, visible dans `ps` comme argument du shell distant — la détection répondait « oui »
partout ; ensuite parce que `grep` trouvait sa propre ligne de commande, de façon **intermittente**,
selon que `ps` l'avait vu naître ou non. Ce qui marche : prendre la liste une seule fois
(`liste=$(ps ax)`), puis comparer dans le shell (`case "$liste" in *"$nom"*`), sur une chaîne qui
n'apparaît nulle part dans le script. Et si `ps` ne répond rien, répondre « je ne sais pas » et
refuser d'agir, plutôt que conclure « rien ne tourne ».

**Un banc d'essai local voit toute la machine.** Un test qui cherche un processus, un fichier dans
`$HOME` ou un port, trouvera ce qui tourne à côté. Les tests doivent fabriquer ce qu'ils observent
(liste de processus factice, `$HOME` factice), sinon ils dépendent de l'humeur de la machine — et un
test qui échoue une fois sur deux ne protège plus rien.

## La pose

`bin/deploy-local` pose et met à jour, sur la machine où il tourne. Invariants à ne pas casser :

- **clone complet** (jamais `--depth`) : un clone superficiel donne un dépôt différent, et l'état
  mentirait ; `--from-clone` vérifie l'origine et refuse un clone superficiel ;
- **un seul verrou** (`~/.dotlib.lock`, `mkdir` atomique, repris après 10 minutes) : `~/.bash` peut
  vouloir combler une absence au moment précis où `parc` pose. Les deux passent par ce verrou ;
- **`mv` atomique** et retour arrière si la mise en place échoue ; `local/` est conservé ;
- **`--check` envoyable sur l'entrée standard** (`ssh hôte sh -s -- --check --json`) : il doit
  fonctionner sur une machine vierge, où rien n'est installé ;
- **aucun réseau au démarrage d'un shell.** `~/.bash` ne comble une absence qu'en arrière-plan, au
  plus une fois par jour, et ne met jamais à jour : la mise à jour appartient à `parc`.

## Avant de proposer un changement

`make check` (contrat) **et** `sh test/anti-fuite.sh` doivent passer. Une décision qui engage les
trois dépôts s'écrit dans `DECISIONS.md`, avec sa date et sa raison — pas seulement le quoi, le
**pourquoi** : c'est ce qui manque toujours six mois plus tard.
