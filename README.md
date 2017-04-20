# PMA Analytics for Python

The repository is named `pma2020-analytics2` because this is the second pass at
writing analytics tools. The first pass was done in `R`. The Python package is
simply called `analytics`. The functionality is provided as a command-line
tool.

*Note: the repository name and the package name are different!*

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
