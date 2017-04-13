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
        handlers = [logging.FileHandler(log_out, mode='w', encoding='utf-8')]
        logging.basicConfig(handlers=handlers, level=level, format=fmt,
                            datefmt=datefmt)
    else:
        logging.basicConfig(level=level, format=fmt, datefmt=datefmt)


def analytics_header(prompts, tags):
    # Common to all instances, and some logging info
    header = [
        'dir_uuid',
        'log_version',
        'xml_size_kb',
        'log_size_kb',
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
    return header


def analytics_instance_row(instance, prompts, tags):
    # Data common to all instances
    row = [
        instance.folder,
        instance.log_version,
        int(instance.xml_size / 1000),
        int(instance.txt_size / 1000),
        int(instance.jpg_size / 1000),
        int(instance.resumed / 1000),
        int(instance.paused / 1000),
        int(instance.short_break / 1000),
        instance.save_count,
        instance.enter_count,
        instance.relation_self_destruct
    ]
    # Get all dynamic tags
    tag_chunk = []
    for tag in tags:
        try:
            found_tag = instance.tag_data[tag]
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
    return row


def previously_analyzed(path):
    found = set()
    try:
        with open(path, newline='', encoding='utf-8') as out:
            reader = csv.reader(out)
            found = set(line[0] for i, line in enumerate(reader) if i != 0)
    except FileNotFoundError:
        # csv output does not exist
        pass
    return found


def schema_mismatch(path, header):
    with open(path, newline='', encoding='utf-8') as out:
        reader = csv.reader(out)
        line = next(reader)
        return line != header


def analytics_to_csv(path, overwrite, instances_dir, prompts, tags)
    # ---------- STEP 1: SETUP ----------
    header = analytics_header(prompts, tags)
    old = set()
    if not overwrite:
        if schema_mismatch(path, header):
            msg = 'Analytics file schema mismatch. Use "overwrite" option.'
            raise CondenseException(msg)
        old = previously_analyzed(path)
    folders = []
    for item in os.scandir(instances_dir):
        if item.is_dir() and item.name not in old:
            folders.append(item.path)
    count = len(folders)
    if count == 0:
        print('All up to date. No new instances to analyze.')
        return
    if overwrite:
        print(f'Analyzing all {count} instances', end=' ')
        print(f'downloaded into {instances_dir}')
        print(f'Intended output file with overwrite: {path}')
    else:
        print(f'Analyzing new {count} instances', end=' ')
        print(f'downloaded into {instances_dir}')
        print(f'Intended output file with append: {path}')
    mode = 'w' if overwrite else 'a'
    uncaptured_prompts = set()
    # ---------- STEP 2: RUN ----------
    with open(path, mode=mode, newline='', encoding='utf-8') as out:
        writer = csv.writer(out)
        if out.tell() == 0:
            writer.writerow(header)
        for folder in folders:
            instance = Instance(folder, prompts=prompts, tags=tags)
            row = analytics_instance_row(instance, prompts, tags)
            writer.writerow(row)
            uncaptured_prompts |= i.uncaptured_prompts
    if uncaptured_prompts:
        msg = 'From instances in %s, discovered %d uncaptured prompts: %s'
        logging.info(msg, instances_dir, len(uncaptured_prompts),
                     str(uncaptured_prompts))


def condense_cli():
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
    parser.add_argument('--overwrite', help=overwrite_help,
                        action='store_true')

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

    setup_logging(args.log_level, args.export_directory, args.log_file)
    try:
        # TODO: fix the try catch
        # TODO fix lookup.lookup to work with None src and throw exception
        form_obj = lookup.lookup(args.form_id, src=args.lookup)
        form_title = form_obj['form_title']
        instances_dir = os.path.join(args.storage_directory,
                                     'ODK Briefcase Storage', 'forms',
                                     form_title, 'instances')
        csv_output = os.path.join(args.export_directory, args.export_filename)

        logging.info('Create logging record for form_id "%s"', args.form_id)
        overwrite = args.overwrite
        prompts = form_obj['prompts'] if 'prompts' in form_obj else []
        tags = form_obj['tags'] if 'tags' in form_obj else []
        start_time = int(time.time())
        analytics_to_csv(csv_output, overwrite, instances_dir, prompts, tags)
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
    except:
        # TODO fix formatting here
    if not form_obj:
        msg = (f'Unable to find form information for {args.form_id}. Verify '
               f'supplied form id and lookup data.')
        print(msg)
    else:
    except FileNotFoundError:
        print(f'No such storage directory: {inst_dir}')
    except KeyError as e:
        print('Unknown form id {}. Check lookup.py'.format(str(e)))
    except CondenseException as e:
        print(e)


if __name__ == '__main__':
    condense_cli()

