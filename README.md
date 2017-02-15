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

## Updates

```
python3 -m pip install https://github.com/jkpr/pma2020-analytics2/zipball/master --upgrade
```


### Bugs

Submit bug reports to James Pringle at `jpringleBEAR@jhu.edu` minus the BEAR.
