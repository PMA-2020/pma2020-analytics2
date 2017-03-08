import glob
import json
import logging
import os.path


def lookup(form_id, src=None, package=False):
    """Return the analytics object for this form_id"""
    to_return = None
    if src:
        if package:
            f = os.path.join(os.path.split(__file__)[0], src)
        else:
            f = src
        to_return = obj_by_id(f, form_id)
    else:
        search = os.path.join(os.path.split(__file__)[0], '*.json')
        for f in glob.glob(search):
            to_return = obj_by_id(f, form_id)
            if to_return:
                break
    return to_return


def obj_by_id(f, form_id):
    to_return = None
    try:
        # Should be a list
        with open(f, encoding='utf-8') as json_data:
            obj = json.load(json_data)
            to_return = next((o for o in obj if o['form_id'] == form_id))
    except json.JSONDecodeError:
        logging.warning('File "%s" not valid JSON', f)
    except StopIteration:
        # Did not find supplied 'form_id'
        pass
    return to_return
