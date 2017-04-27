"""Module to store all custom exceptions."""


class CondenseException(Exception):
    """Custom exception for use in condense module."""

    pass


class LookupException(Exception):
    """Custom exception for use in lookup submodule."""

    pass


class LogparserException(Exception):
    """Custom exception for use during the parsing of the log into events."""

    pass
