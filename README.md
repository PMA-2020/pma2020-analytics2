# PMA Analytics for Python

The repository is named `pma2020-analytics2` because this is the second pass at
writing analytics tools. The first pass was done in `R`. The Python package is
simply called `analytics`. The functionality is provided as a command-line
tool.

*Note: the repository name and the package name are different!*

Some of the data that is extracted:
* Specific XML tags from the submitted instance
* Total active screen time during the whole survey
* Short break time during the whole survey
* File sizes of photos, submission, and log
* Total swiping events

Also, five data points for each known prompt in the log are recorded. Each column name suffix and description is below.
- `_c` for the number of times a constraint/required was invoked on the prompt.
- `_t` for the active screen time spent on the prompt.
- `_v` for the total number of visits to the prompt.
- `_d` for the total number of times the answer changed on the prompt.
- `_b` for short break time associated with the prompt.

*All times are in millseconds.*

## Pre-requisites

PMA Analytics makes use of Python 3.6. Install [Python 3.6][1].

[1]: https://www.python.org/downloads/

## Installation

Install via pip with

```
python3 -m pip install https://github.com/jkpr/pma2020-analytics2/zipball/master
```


## Examples

All required arguments are named to follow the same pattern as ODK Briefcase.

Example usage:

```
python3 -m analytics.condense --storage_directory ~/Documents/odkbriefcase/ --form_id HQ-rjr1-v25 --export_directory . --export_filename hq-out.csv
```

A JSON file can be supplied through the `--lookup` option of the `condense`
command-line interface. The file should have the proper format: a list of JSON
objects with properties

* `form_id` (string) form id
* `form_title` (string) form title
* `prompts` (list of string) prompts in the `log.txt` files
* `tags` (list of string) names of XML tags from `submission.xml` files

Put something in `prompts` in order to get information about number of visits
and time spent at that prompt. Put something in `tags` to get the actual value
in the submission, e.g. `<your_name>Jane Doe</your_name>`

An example is given below.

```
[
  {
    "form_id": "HQ-rjr1-v12",
    "form_title": "RJR1-Household-Questionnaire-v12",
    "prompts": [
      ...
      "hh_duplicate_check",
      "duplicate_warning",
      "resubmit_reasons",
      "duplicate_warning_hhmember",
      "available",
      "consent_start",
      "consent",
      "begin_interview",
      ...
    ],
    "tags": [
      ...
      "your_name",
      "start",
      "end",
      "deviceid",
      "HHQ_result"
      ...
    ]
  }
]
```

## Supported ODK forms

The `analytics.formdata` subpackage has a command line interface to display the supported form titles and form ids. Use:

```
python3 -m analytics.formdata
```

Then pipe to `grep` to filter results. For example, in order to see the supported forms for Uganda round 5, use

```
python3 -m analytics.formdata | grep UGR5
```


## Understanding the logging

As analytics runs, it emits logging messages. The standard levels, in order of increasing severity, are `DEBUG`, `INFO`, `WARNING`, and `ERROR`. Analytics uses all of these to convey specific meaning.

### `DEBUG`

Information that is useful for debugging. Analytics uses `DEBUG` to say which instance (folder) is currently being analyzed.

### `INFO`

High-level information about the running program.

* What form id is being analyzed.
* When the analysis completes

### `WARNING`

When `WARNING` is about the logs, it typically means something with the potential to be problematic has occurred. Usually, however, this is not a cause for concern.

### `ERROR`

This is used when something happens that prevents the analytics from completing its task.

* The analytics file column headers do not match what data is to be appended.
* Some problem with the file prevents its analysis (e.g. corrupt file).

## Updates

```
python3 -m pip install https://github.com/jkpr/pma2020-analytics2/zipball/master --upgrade
```


### Bugs

Submit bug reports to James Pringle at `jpringleBEAR@jhu.edu` minus the BEAR.

---

# PMA Analytics dans Python

The repository is named `pma2020-analytics2` because this is the second pass at
writing analytics tools. The first pass was done in `R`. The Python package is
simply called `analytics`. The functionality is provided as a
tool.

*Note: the repository name and the package name are different!*

## Pre-requisites


Le référentiel est nommé `pma2020-analytics2` car il s'agit du deuxième phase dans l’écriture des outils d'analyse. Le premier passage s'est fait dans `R`. Le package Python est
simplement appelé `analytics`. La fonctionnalité est fournie en tant que ligne de commande
.

* Remarque: le nom du référentiel et le nom du package sont différents! *



PMA Analytics utilise  Python 3.6. Installer [Python 3.6][1].

[1]: https://www.python.org/downloads/

## Installation

Installer via pip avec

```
python3 -m pip install https://github.com/jkpr/pma2020-analytics2/zipball/master
```


## Exemples

All required arguments are named to follow the same pattern as dans .
Tous les arguments requis sont nommés selon la même méthode que dans l’application ODK Briefcase.


Example usage:

```
python3 -m analytics.condense --storage_directory ~/Documents/odkbriefcase/ --form_id HQ-rjr1-v25 --export_directory . --export_filename hq-out.csv

```



Un fichier JSON peut être fourni via l’option `--lookup` de l’interface de la ligne de commande. ` ‘condense`. Le fichier doit avoir le format approprié: une liste d’objets JSON avec leurs propriétés

* `form_id` (chaîne) id du formulaire
* `form_title` (string) titre du formulaire
* `prompts` (liste de string) invites dans les fichiers` log.txt`
* `tags` (liste de string) noms des balises XML à partir des fichiers` submission.xml`


Put something in `prompts` in order to get information about number of visits
and time spent at that prompt. Put something in `tags` to get the actual value
in the submission, e.g. `<your_name>Jane Doe</your_name>`

An example is given below.

Mettez quelque chose dans les "invites" afin d'obtenir des informations sur le nombre de visites
et le temps passé à cette invite. Mettez quelque chose dans `tags` pour obtenir la valeur réelle
dans la soumission, par exemple `<votre_nom> Jane Doe </ votre_nom> '

Un exemple est donné ci-dessous.

```
[
  {
    "form_id": "HQ-rjr1-v12",
    "form_title": "RJR1-Household-Questionnaire-v12",
    "prompts": [
      ...
      "hh_duplicate_check",
      "duplicate_warning",
      "resubmit_reasons",
      "duplicate_warning_hhmember",
      "available",
      "consent_start",
      "consent",
      "begin_interview",
      ...
    ],
    "tags": [
      ...
      "your_name",
      "start",
      "end",
      "deviceid",
      "HHQ_result"
      ...
    ]
  }
]
```

## Formulaires prises en change dans ODK

Le sous-package `analytics.formdata` a une interface de ligne de commande permettant d'afficher les titres et les identifiants  (id) des formulaires pris en charge. Utiliser:

```
python3 -m analytics.formdata
```

Puis dirigez vous vers `grep` pour filtrer les résultats. Par exemple, pour consulter les formulaires pris en charge pour Ouganda round 5, utiliser:

```
python3 -m analytics.formdata | grep UGR5
```

## Comprendre le logging

As analytics runs, it emits logging messages. The standard levels, in order of increasing severity, are `DEBUG`, `INFO`, `WARNING`, and `ERROR`. Analytics uses all of these to convey specific meaning.

Lorsque Analytics s'exécute, il émet des messages de logging ( journalisation). Les niveaux standard, par ordre croissant de sévérité, sont `DEBUG`,` INFO`, `WARNING` et` ERROR`. Analytics utilise tous ces éléments pour transmettre un message de signification spécifique.


### `DEBUG`

Information utile pour le déboggage. Analytics utilise `DEBUG` pour indiquer quelle instance (dossier) est en cours d'analyse.


### `INFO`

Informations de haut niveau sur le programme en cours.

* Quel identifiant de formulaire est en cours d'analyse.
* Quand l'analyse est terminée


### `WARNING`

Le message `WARNING` signifie généralement que quelque chose de potentiellement problématique s'est produit. Toutefois, cela n’est généralement pas inquiétant.


### `ERROR`

Ceci est utilisé lorsque quelque chose empêche l’analyse d’achever sa tâche.

* Les en-têtes de colonne du fichier d'analyse ne correspondent pas aux données à ajouter.
* Un problème avec le fichier empêche son analyse (fichier corrompu, par exemple).


## Mise à jour

```
python3 -m pip install https://github.com/jkpr/pma2020-analytics2/zipball/master --upgrade
```


### Bugs

Soumettez les rapports de bugs à James Pringle à l'adresse `jpringleBEAR @ jhu.edu
