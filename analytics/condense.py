import argparse
import json
import logging
import os
import os.path

from .lookup import lookup
from .config import config


def setup_logging(config_dict, user_dict, log_level, default_out):
    config_dict.update(user_dict)
    level = getattr(logging, log_level if log_level is not None else "",
        getattr(logging, config_dict['LOG_LEVEL'], None)
    )
    if not isinstance(level, int):
        level = logging.DEBUG

    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    datefmt = '%m/%d/%Y %I:%M:%S %p'
    if config_dict['LOG_STDERR']:
        logging.basicConfig(level=level, format=fmt, datefmt=datefmt)
    else:
        log_file = config_dict.get('LOG_FILE', default_out)
        logging.basicConfig(filename=log_file, level=level, format=fmt,
                            datefmt=datefmt)


if __name__ == '__main__':

    prog_desc = ('Condense all submissions under one form of ODK Briefcase '
                 'Storage into an intermediate data product for analysis.')
    parser = argparse.ArgumentParser(description=prog_desc)

    named = parser.add_argument_group('named arguments')

    storage_help = ('A directory with a subdirectory called "ODK Briefcase '
                    'Storage"')
    named.add_argument('--storage_directory', help=storage_help, required=True)

    form_help = ('The form id of the files to condense. Must be known to the '
                 'system or supplied')
    named.add_argument('--form_id', help=form_help, required=True)

    dir_help = 'A directory to store output and export information'
    named.add_argument('--export_directory', help=dir_help, required=True)

    out_help = 'The file to write. Should have ".csv" extension'
    named.add_argument('--export_filename', help=out_help, required=True)

    config_help = ('Path to configuration file, a JSON dictionary. Overwrites '
                   'defaults')
    parser.add_argument('--config', help=config_help)

    log_help = ('Log level. One of DEBUG, INFO, WARNING, ERROR.')
    parser.add_argument('--log', help=log_help)

    args = parser.parse_args()

    try:
        with open(args.config) as json_file:
            user_config = json.load(json_file)
    except Exception as e:
        user_config = {}

    try:
        form_title = lookup[args.form_id]
        instances_dir = os.path.join(args.storage_directory,
                                     "ODK Briefcase Storage", "forms",
                                     form_title, "instances")
        count = sum(1 for i in os.scandir(instances_dir) if i.is_dir())
        print(f'*Analyzing {count} instances downloaded into {instances_dir}')

        csv_output = os.path.join(args.export_directory, args.export_filename)
        print(f'*Intended output file: {csv_output}')

        log_output = os.path.join(args.export_directory, 'analytics.log')
        setup_logging(config, user_config, args.log, log_output)
    except FileNotFoundError:
        print(f'No such storage directory: {instances_dir}')
    except KeyError as e:
        print('Unknown form id {}. Check lookup.py'.format(str(e)))
