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
            with open(path, encoding='utf-8') as json_data:
                obj = json.load(json_data)
                for singleton in obj:
                    data = {}
                    data['form_title'] = singleton.get('form_title', '')
                    data['form_id'] = singleton.get('form_id', '')
                    data['created'] = singleton.get('created', '')
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

    date_help = 'Show the date the form was added. Not very useful alone.'
    parser.add_argument('-d', '--date', action='store_true', help=date_help)

    args = parser.parse_args()
    show_all = not any((args.form_title, args.form_id, args.date))

    all_data = get_formdata()
    title_width = max(len(str(i['form_title'])) for i in all_data)
    id_width = max(len(str(i['form_id'])) for i in all_data)
    date_width = max(len(str(i['created'])) for i in all_data)
    for form in all_data:
        show = []
        if show_all or args.form_title:
            block = '{s:{w}}'.format(s=form['form_title'], w=title_width)
            show.append(block)
        if show_all or args.form_id:
            block = '{s:{w}}'.format(s=form['form_id'], w=id_width)
            show.append(block)
        if show_all or args.date:
            block = '{s:{w}}'.format(s=form['created'], w=date_width)
            show.append(block)
        line = '    '.join(show)
        if not line.isspace():
            print(line)


if __name__ == '__main__':
    formdata_cli()
