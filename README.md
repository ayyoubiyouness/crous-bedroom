# Bouge ETL

11/11/2022

## V1

### Objectif

>Le code présent dans ce repository consiste en une technologie d'ETL permettant d'extraire des données de diverses sources (API / Scrapping), de transformer et traiter ces données puis de les intégrer dans la base de données Bouge. L'objectif de ce projet est de construire une infrastructure permettant de régulièrement mettre à jour / enrichir le produit Bouge.

### Technologies

- Python `3.9.13`.
- Poetry : librairie python en charge de la gestion des autres librairies python. Installation via `pip install poetry`, puis `poetry install` pour installer le reste des librairies.
- Prefect : librairie python permettant de construire des ETL ([documentation](https://docs.prefect.io/concepts/overview/)). La lecture de la documentation est fortement recommandée pour comprendre les différents concepts. Parmi ces concepts, deux principaux sont à retenir : la **task**, similaire à une fonction python, qui correspond à une étape de traitement de l'ETL; le **flow** qui est une entité qui englobe les tasks, et qui leur fournit un environnement d'exécution. Pour information, chaque étape de l'ETL consistera en un flow, qui eux-mêmes seront englobés dans un flow principal qui définira l'ETL (le point d'entrée pour l'exécution du code).

### Architecture de l'ETL

Le code actuel permettant de facilement construire des ETL (Extract Transform Load) à partir de briques déjà construites. Le code a été pensé pour créer un ETL par source à laquelle on souhaite se connecter. Dans la version **V1** du code, l'unique source disponible est [finishers](https://www.finishers.com/).

Un diagramme d'architecture de l'ETL a été conçu et est disponible [ici](https://www.figma.com/file/lwoGBd1HYb99WXOUFFzlpz/Bouge-ETL?node-id=0%3A1&t=MmPNnOWQm03PXhsB-0).

![Architecture de l'ETL](/assets/architecture_etl.png)

Chaque couleur correspond à une étape de l'ETL : extract (violet), différents transform (vert) et load (bleu). Pour chaque étape, il faudra créer autant de tasks que nécessaire, que l'on incluera dans des flows spécifiques. Par exemple pour la source `finishers` on retrouve une task d'extract `task_extract_finishers.py` associé à un flow d'extract `flow_extract_finishers.py`, et ce pour chaque étape.

**Points à retenir :**

- Chaque source de données aura une étape d'**extract spécifique**, _i.e_ il s'agira d'une étape manuelle consistant en un script qui se connectera à une API pour récupérer de la donnée ou qui réalisera du scrapping. Cette étape a pour objectif de récupérer les données à intégrer en base, filtrer sur les données que l'on souhaite garder, potentiellement faire une première mise en forme de la donnée (surtout pour le scrapping).

- Chaque source de données aura une étape de **transform spécifique**, _i.e_ étape manuelle durant laquelle on passe de données au format fourni par l'API ou le scrapping à un format normalisé. Divers modèles de classes python correspondant aux tables de la BDD ont été développé dans le fichier `src/models/db.py`. Ceci nous permet de passer de données brutes à des données correspondant aux entités propres à Bouge. (Poi, Address, Activity, etc...). Dans chacune de ces classes python, des méthodes de traitement / normalisation ont été développé pour créer de la donnée propre à partir de donnée brute. Par exemple, dans la classe `src/models/db.py/Address` une méthode permet de valider que le code insee extrait est bien dans le bon format (string d'une longueur de 5 caractères). Ces classes héritent des méthodes des classes [Pydantic](#https://pydantic-docs.helpmanual.io/) (librairie python similaire aux _dataclasses_ permettant de normaliser facilement des instances d'une classe Python, cf la documentation). À noter que dans le fichier `src/models/db.py` pour chaque classe il y a une version "pydantic" de la classe (par exemple `Address`) qui implémente les méthodes de normalisation que l'on utilise dans les étapes de transform, et une version "sqlalchemy" (par exemple `AddressSQL`) qui correspond aux objects que l'on poussera en base en utilisant l'ORM SQLAlchemy. Enfin, il est important de renvoyer en sortie des flows de transform spécifiques une liste de modèles définis dans `src/models/db.py`. Par exemple, pour `finishers`, la sortie de `flow_transform_finishers.py` renvoie une liste de modèles `[Poi(...), Address(...), Activity(...), AddressPoi(...), ...]`. Ceci est obligatoire et attendu en entrée du transform générique dont parle plus bas.

- Une étape de **transform générique** : chaque ETL partagera la même étape de transform générique, qui, à partir des modèles extraits par les transforms spécifiques précédents, appliquera différentes transformations propre aux modèles dans `src/models/db.py`. En résumé, l'étape de transform spécifique consiste à passer de données brutes à des données sous formes de modèles Python (correspondant aux entités de la DB Bouge.), puis l'étape de transform générique se charge d'appliquer les transformations relatives à ces modèles Python. Par exemple, pour les objets de la classe `Address` on retrouve une méthode de transform qui récupère l'addresse exacte à partir de coordonnées GPS (reverse geocoding). ⚠️ Point important, les méthodes de transform générique au sein des modèles doivent être préfixées par `transform_`, _i.e_ dans la classe `Address` on trouve la méthode `transform_get_address()`.

- Une étape de **load générique** : chaque ETL partagera la même étape de load générique, qui se charge de transformer les objets des classes "pydantic" (par exemple Address), en objets des classes "sqlalchemy" (par exemple AddressSQL). Une fois cette conversion faite, les objets sont poussés en base de données.


_**NB: Pour le moment, les tasks et flows génériques sont fonctionnels et ne doivent pas subir de modifications. Ces scripts peuvent être ré-utilisés tels quels pour chaque nouvel ETL.**_

_**NB: En fonction des sources de données, il faudra potentiellement créer de nouveaux modèles permettant de modéliser les entités de la source en objets python et d'y intégrer des méthodes de normalisation. Par exemple, pour `finishers`, deux classes (Event et Race) ont été créé dans `src/models/generic.py` pour modéliser les événements et les courses finishers. Pour chaque nouvelle source, il peut être intéressant de venir créer de nouveaux modèles dans ce fichier pour faciliter le traitement de la donnée en Python.**_

Représentation de l'ETL Finishers 👇🏻

![Détails de l'étape de transform](/assets/details_transform.png)

#### Détails techniques

Généralement pour chaque nouvel ETL, l'ordre d'exécution des flows est le suivant :

1) Étape d'extract réalisée de manière séquentielle (on attend que toutes les données soient extraites avant de passer à la suite).
2) Étape de transform spécifiques réalisée de manière concurrentielle / parallèle. Chaque entité que l'on traite peut être traitée indépendamment des autres. Par exemple, pour `finishers`, dans l'étape d'extract on extrait des événements / Event (chaque événement contient au moins une course / Race). On exécute un flow de transform spécifique (`flow_transform_finishers`) par événement extrait, et ce de manière parallèle car ils sont indépendants entre eux.
3) Étape de transform générique, qui prend en entrée tous les modèles générés par les transforms spécifiques, et qui est réalisé de manière séquentielle (_i.e_ on traite chaque entité l'un après l'autre). Ce n'est pas optimisé pour le moment, on pourrait le faire de manière concurrente.
4) Étape de load, exécutée de manière séquentielle. Sur ce point, pour des raisons de partage de ressources (DB), on doit réaliser cette étape de manière séquentielle (car la DB a été mal configurée, les ids des lignes que l'on créé en base sont générés par la DB et non par les valeurs qu'on lui envoie...). C.f [identity](https://www.postgresqltutorial.com/postgresql-tutorial/postgresql-identity-column/). 

### Architecture du code

#### Flows & Tasks

➪ Les **tasks** sont stockées dans le dossier `src/etl/tasks`. Au sein de ce dossier, on retrouve un dossier `generic` qui contiendra l'ensemble des tasks génériques et communes à tous les ETLs. Ensuite, on retrouvera autant de dossiers que des sources existantes. Pour le moment, dans la V1, un seul autre dossier est présent est s'appelle `finishers`. Chacun de ces dossiers spécifiques contiendra les tasks spécifiques à la source en question.

➪ Les **flows** sont stockés dans le dossier `src/etl/flows`. Même structure que pour les tasks mais au niveau des flows. A priori, seuls des flows de transforms spécifiques sont à ajouter dans de nouveaux dossiers spécifiques aux nouvelles sources.


#### Models

➪ Les modèles / classes python correspondant à des entités de la DB Bouge. sont stockés dans le fichier `src/models/db.py`.
➪ Les modèles / classes python génériques (_i.e_ non liés à Bouge, autrement dit, liés à des sources de données externes) sont stockés dans le fichier `src/models/generic.py`. Par exemple, c'est ici que l'on retrouve les classes **Race** et **Event** correspondant aux courses et événements de  `finishers`.

#### Services

➪ Les services / méthodes python propres à chacune des sources sont stockés dans des fichiers spécifiques au nom de celles-ci. Par exemple, pour `finishers`, on retrouve le fichier `src/services/finishers.py`, qui gère toute la logique de traitement de données propre à cette source. C'est au sein de ce fichier que la plus part du code doit se trouver, de sorte à ce que les tasks et flows soient très concis et simples à lire.

➪ Les services / méthodes python génériques (_i.e_ non liés à Bouge, autrement dit, liés à des sources de données externes) sont stockés dans le fichier `src/services/generic.py`. Par exemple, c'est ici que l'on retrouve des méthodes utiles à tout le projet. Ce fichier sera potentiellement rapatrié dans `src/utils/` par la suite.

#### Utils

➪ Le dossier `src/utils` est un dossier qui contiendra différents scripts utiles à tout le projet, et qui ne trouvent pas leur place ailleurs dans le projet. On y retrouve notamment un fichier `db.py` qui s'occupe de toutes les différentes intéractions / requêtes à la DB PostgreSQL.

#### Tests

➪ Le dossier `tests` contient tous les scripts de tests. On y teste de manière unitaire toutes les fonctionnalités que l'on a développé dans les étapes précédemment mentionnées. Pour fonctionner, ces scripts doivent être préfixés par `test_` de la même manière que les méthodes qu'il contient. C'est la librairie `pytest` qui se charge d'exécuter ces tests (à chaque push sur Github). Par la suite, une commande `test` sera ajoutée au fichier Makefile, pour pouvoir lancer les tests avec la commande `make test`.

#### Deploiement

➪ **VPS** : l'ensemble du projet est déployé sur un serveur virtuel (_VPS B1ms ~17$/mois_) Azure Cloud.
➪ **Dockerfile** : une image docker, copiée d'une image Prefect, a été développée pour définir les différents containers.
➪ **Docker Compose** : une fichier `docker-compose.yml` a été développé pour créer les différents containers responsables de faire tourner l'application (_c.f plus bas dans la section **Back**_).
➪ **Makefile** : une fichier Makefile est disponible pour exécuter 2 différentes commandes : `make docker` pour build l'image docker (nécessaire dès qu'un changement est apporté au sein du dossier `src/`, `make register-finishers-flow` pour créer un déploiement d'un ETL accessible sur le front (c.f le concept de déploiement dans la documentation de Prefect).
➪ **prefect.sh** : script bash en charge d'instancier les différents containers définis dans le `docker-compose.yml`.

### Produits

#### Front

➪ L'interface front de Prefect est accessible à l'addresse suivante : http://51.11.240.139:4200/runs. On peut y monitorer les différentes exécutions d'ETL, voir les logs, modifier la programmation d'exécution d'un ETL, voir les différents ETL enregistrés ou encore lancer manuellement l'exécution d'un ETL.

#### Back

Globalement le code présent sur Github est hébergé sur un VPS Azure Cloud. C'est ce serveur qui va exécuter le code au sein d'un Docker Container défini dans le fichier `docker-compose.yml`. 

Dans ce docker-compose sont définis 3 containers : `postgres` pour la DB PostgreSQL requise par Prefect pour stocker les logs des exécutions d'ETL (toutes les données qui sont visibles sur le front sont stockées dans cette base de données locale), `prefect-server` qui gère l'application front, et `prefect-agent` qui définit un processus qui attend que l'on demande d'exécuter un ETL (il reste toujours à l'écoute de lancements, envoyés par le front via un call API).

### Utilisation du code

Voici les principales commandes à exécuter pour mettre le service en place sur le serveur.

#### Tests en local

⚠️ Il est important de tester le code en local avant tout push sur Github. Pour se faire, il faut ouvrir 3 fenêtres de terminal :

**Terminal 1 | Lancement du front**  
Permet d'accéder à l'interface UI de Prefect, accessible sur `http://localhost:4200/`

➪ `prefect server start`

**Terminal 2 | Lancement du back**  
Définit un agent qui va écouter les demandes d'exécution du code. C'est sur ce terminal que seront exécutés les ETL, et donc c'est ici que l'on retrouvera les logs des exécutions.

➪ `prefect agent start -q daily`

**Terminal 3 | Lancement des runs (optionnel)**  
Terminal qui permet de lancer des runs via manuellement. L'autre option est de lancer les runs depuis l'UI.

➪ `prefect deployment build src/etl/flows/<source>/flow_etl_<source>.py:etl -n dev -t <source> -ib process/process-dev -q daily --timezone 'Europe/Paris' # Permet de définir un nouvel ETL, à exécuter à chaque changement du code`

➪ `prefect deployment apply etl-deployment.yaml # Permet d'enregistrer le nouvel ETL sur l'UI, et donc de le rendre accessible via l'UI`

➪ `prefect deployment run etl-<source>/dev # Demande une exécution de l'ETL`

⚠️ _Important : veiller à remplacer `<source>` par le nom de la source liée à l'ETL (par exemple `finishers`)._


#### Déploiement
➪ Récupération du code sur Github (_actuellement le code est hostée sur mon espace JeanSavary, il devra être hostée dans l'environnement de travail de Bouge._)

```bash
cd bouge-etl

git pull origin main # retrieve code from github
```

➪ Lancement du service

```bash
make docker # build the Docker image

bash prefect.sh start # execute the .sh file, build 3 containers

make register-finishers-flow # register the flow related to finishers
```
## TODO

### Good practices

➪ Pour tout ajout d'une nouvelle source, il faut :
1) Créer une nouvelle branche : `git checkout -b etl-<source>` (remplacer `<source>` par le nom de la source, ajouter des underscores si la source est composée de plusieurs mots).
2) Développer le code nécessaire, faire les commits et les push sur cette nouvelle branche.
3) Tester le code via les commandes mentionnées plus haut.
4) Faire une pull-request sur la branche `dev` depuis la nouvelle branche.
5) Ajouter un collaborateur comme **assignee** de la pull-request pour une review du code. Une fois la review terminée, le code sera mergé sur `dev` et puis sur `main` une fois l'ensemble des tests fonctionnels réalisés.

💪🏼 Bon courage !

### Updates

 - [x] Add row to RegisteredPoi when an event is uploaded to DB
 - [ ] Add name / title to Activity table
 - [ ] Add workflow that publish to ECR after passing tests
 - [ ] If an event has been updated (_i.e sha256 different_), don't duplicate the POI, update it based on the `orignal_id` (+ keep track of changes ?)
 - [ ] Add missing tests
 - [ ] Add new ETL from already developped scrapping scripts

### Additions

- [ ] Add a new source from an existing scrapping script.
