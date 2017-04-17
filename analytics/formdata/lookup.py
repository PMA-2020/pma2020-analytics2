"""Functions for retrieving analytics metadata."""
import glob
import json
import logging
import os.path


def lookup(form_id, src=None):
    """Return the analytics object for this form_id.

    Uses src if supplied, otherwise searches in package files.

    Args:
        form_id (str): The form id to get information for
        src (str): Path to a file with analytics information

    Returns:
        The first matching analytics form id

    Throws:
        KeyError: If form_id not found among source or supplied files.
    """
    to_return = None
    if src:
        to_return = obj_by_id(src, form_id)
    else:
        search = os.path.join(os.path.split(__file__)[0], '*.json')
        for path in glob.glob(search):
            to_return = obj_by_id(path, form_id)
            if to_return:
                break
    if to_return:
        return to_return
    else:
        msg = (f'Unable to find form information for {form_id}. Verify '
               f'supplied form id and lookup data.')
        raise KeyError(msg)


def obj_by_id(path, form_id):
    """Search for analytics object in the given path.

    Args:
        path (str): Path to the file to search (should be JSON formatted)
        form_id (str): The form id to get information for

    Returns:
        The analytics object, if found, else None
    """
    to_return = None
    try:
        with open(path, encoding='utf-8') as json_data:
            obj = json.load(json_data)
            to_return = next((o for o in obj if o['form_id'] == form_id))
    except json.JSONDecodeError:
        logging.warning('File "%s" not valid JSON', path)
    except StopIteration:
        # Did not find supplied 'form_id'
        pass
    return to_return
