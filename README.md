# PMA Analytics for Python

The repository is named `pma2020-analytics2` because this is the second pass at 
writing analytics tools. The first pass was done in `R`. The Python package is 
simply called `analytics`. The functionality is provided as a command-line 
tool.

*Note: the repository name and the package name are different!*

## Pre-requisites

PMA Analytics makes use of Python 3.6. Install [Python 3.6][1]. 

[1]: https://www.python.org/downloads/


## Examples

Example usage:

```
python -m analytics.condense --storage_directory ~/Documents/odkbriefcase/ --form_id HQ-rjr1-v25 --export_directory . --export_filename out.csv
```

## Updates

```
python -m pip install https://github.com/jkpr/pma2020-analytics2/zipball/master --upgrade
```


### Bugs

Submit bug reports to James Pringle at `jpringleBEAR@jhu.edu` minus the BEAR.
