"""Define a CLI to get analytics metadata."""
import argparse
import glob
import json
import os.path


def get_formdata():
    """Search package data to get all relevant analytics information."""
    all_data = []
    search = os.path.join(os.path.split(__file__)[0], '*.json')
    for path in glob.glob(search):
        try:
            with open(path, encding='utf-8') as json_data:
                obj = json.load(json_data)
                for singleton in obj:
                    data = {}
                    data['form_title'] = singleton.get('form_title', None)
                    data['form_id'] = singleton.get('form_id', None)
                    all_data.append(data)
        except json.JSONDecodeError:
            pass
    return all_data


def formdata_cli():
    """Run simple CLI to get information of supported analytics."""
    prog_desc = ('Get lookup information for analytics')
    parser = argparse.ArgumentParser(description=prog_desc)

    form_title_help = 'Show the supported form titles'
    parser.add_argument('-f', '--form_title', action='store_true',
                        help=form_title_help)

    form_id_help = 'Show the supported form ids'
    parser.add_argument('-i', '--form_id', action='store_true',
                        help=form_id_help)

    args = parser.parse_args()

    all_data = get_formdata()
    for form in all_data:
        show = []
        if args.form_title:
            show.append(form['form_title'])
        if args.form_id:
            show.append(form['form_id'])
        if not any(i is None for i in show):
            print(*show, sep='\t')


if __name__ == '__main__':
    formdata_cli()
