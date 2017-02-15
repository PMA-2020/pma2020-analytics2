import argparse
import csv
import logging
import os.path
import time

from analytics.formdata import lookup
from analytics.exception import CondenseException
from analytics.instance import Instance


def setup_logging(log_level, export_directory, log_file):
    level = getattr(logging, log_level if log_level is not None else "", None)
    if not isinstance(level, int):
        level = logging.DEBUG
    fmt = '%(asctime)s - %(levelname)s - %(message)s'
    datefmt = '%m/%d/%Y %I:%M:%S %p'
    if log_file:
        log_out = os.path.join(export_directory, log_file)
        logging.basicConfig(filename=log_out, level=level, format=fmt,
                            datefmt=datefmt)
    else:
        logging.basicConfig(level=level, format=fmt, datefmt=datefmt)


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

    overwrite_help = ('Set this flag to overwrite output CSV file, otherwise '
                      'append.')
    parser.add_argument('--overwrite', help=overwrite_help, action='store_true')

    log_help = ('Log level. One of DEBUG, INFO, WARNING, ERROR. If not set or '
                'incorrect, default is DEBUG.')
    parser.add_argument('--log_level', help=log_help)

    log_file_help = ('Log file name. Goes in "export_directory". If omitted, '
                     'then log output directs to STDERR.')
    parser.add_argument('--log_file', help=log_file_help)

    lookup_help = ('Path to form lookup file, a JSON dictionary. Overwrites '
                   'defaults. Should have format {"form_id": "MY_FORM_ID", '
                   '"form_title": "MY_FORM_TITLE", "prompts": ["PROMPT1", '
                   '"PROMPT2", ..., "PROMPTN"], "tags": ["TAG1", "TAG2", ..., '
                   '"TAGN"]} at a minimum')
    parser.add_argument('--lookup', help=lookup_help)

    config_help = 'Path to a config file, a JSON dictionary'
    parser.add_argument('--config', help=config_help)

    args = parser.parse_args()

    try:

        form_obj = lookup.lookup(args.form_id)
        if args.lookup:
            user_obj = lookup.lookup(args.form_id, src=args.lookup)
            if user_obj and form_obj:
                form_obj.update(user_obj)
            elif user_obj and not form_obj:
                form_obj = user_obj
        if not form_obj:
            raise CondenseException(f'Unable to find form information for '
                                    f'{args.form_id}. Verify supplied form id '
                                    f'and lookup data.')

        inst_dir = os.path.join(args.storage_directory,
                                'ODK Briefcase Storage', 'forms',
                                form_obj['form_title'], 'instances')
        csv_output = os.path.join(args.export_directory, args.export_filename)
        old = set()
        if not args.overwrite:
            try:
                with open(csv_output) as f:
                    r = csv.reader(f)
                    old = set(line[0] for i, line in enumerate(r) if i != 0)
            except FileNotFoundError:
                # csv output does not exist
                pass
        # Build up folders to walk
        folders = []
        for i in os.scandir(inst_dir):
            if i.is_dir() and i.name not in old:
                folders.append(i.path)
        count = len(folders)
        if args.overwrite:
            print(f'Analyzing all {count} instances downloaded into {inst_dir}')
            print(f'Intended output file with overwrite: {csv_output}')
        else:
            print(f'Analyzing new {count} instances downloaded into {inst_dir}')
            print(f'Intended output file with append: {csv_output}')
        setup_logging(args.log_level, args.export_directory, args.log_file)
        logging.info('Logging record for form_id "%s"', args.form_id)
        start_time = int(time.time())

        # DO STUFF
        if folders:
            tags = form_obj['tags'] if 'tags' in form_obj else []
            prompts = form_obj['prompts'] if 'prompts' in form_obj else []
            uncaptured_prompts = set()
            mode = 'w' if args.overwrite else 'a'
            with open(csv_output, mode=mode, newline='') as f:
                writer = csv.writer(f)
                # Common to all instances, and some logging info
                if f.tell() == 0:
                    header = [
                        'dir_uuid',
                        'log_version',
                        'log_size_kb',
                        'xml_size_kb',
                        'photo_size_kb',
                        'resumed',
                        'paused',
                        'short_break',
                        'save_count',
                        'screen_count',
                        'rS'
                    ]
                    # Get all dynamic tags
                    tag_header = tags
                    header.extend(tag_header)
                    # Get all dynamic prompts
                    for prompt in prompts:
                        chunk = [
                            f'{prompt}_CC',
                            f'{prompt}_time',
                            f'{prompt}_visits',
                            f'{prompt}_delta'
                        ]
                        header.extend(chunk)
                    writer.writerow(header)
                for folder in folders:
                    i = Instance(folder, prompts=prompts, tags=tags)
                    # Common to all instances, and some logging info
                    row = [
                        i.folder,
                        i.log_version,
                        int(i.xml_size / 1000),
                        int(i.txt_size / 1000),
                        int(i.jpg_size / 1000),
                        int(i.resumed / 1000),
                        int(i.paused / 1000),
                        int(i.short_break / 1000),
                        i.save_count,
                        i.enter_count,
                        i.relation_self_destruct
                    ]
                    # Get all dynamic tags
                    tag_chunk = []
                    for tag in tags:
                        try:
                            found_tag = i.tag_data[tag]
                            # TODO: Possibly escape the data for csv
                            # csv module may do that automatically, though
                            tag_chunk.append(found_tag)
                        except KeyError:
                            tag_chunk.append(None)
                    row.extend(tag_chunk)
                    # Get all dynamic prompts
                    for prompt in prompts:
                        chunk = []
                        try:
                            cc = i.prompt_cc[prompt]
                            chunk.append(cc)
                        except KeyError:
                            chunk.append(None)
                        try:
                            timing = int(i.prompt_data[prompt]/1000)
                            chunk.append(timing)
                        except KeyError:
                            chunk.append(None)
                        try:
                            visits = i.prompt_visits[prompt]
                            chunk.append(visits)
                        except KeyError:
                            chunk.append(None)
                        try:
                            delta = i.prompt_changes[prompt]
                            chunk.append(delta)
                        except KeyError:
                            chunk.append(None)
                        row.extend(chunk)

                    writer.writerow(row)
                    uncaptured_prompts |= i.uncaptured_prompts
            if uncaptured_prompts:
                logging.info('From instances in %s, discovered %d uncaptured prompts: %s', inst_dir, len(uncaptured_prompts), str(uncaptured_prompts))
        end_time = int(time.time())
        diff = end_time - start_time
        if diff > 300:
            diff_str = "{0:.2f} minutes".format(diff/60)
        else:
            diff_str = "{} seconds".format(diff)
        m = (f'Finished condensing data to "{csv_output}" for form_id '
             f'"{args.form_id}" after {diff_str}')
        logging.info(m)
        print(m)
    except FileNotFoundError:
        print(f'No such storage directory: {inst_dir}')
    except KeyError as e:
        print('Unknown form id {}. Check lookup.py'.format(str(e)))
    except CondenseException as e:
        print(e)
