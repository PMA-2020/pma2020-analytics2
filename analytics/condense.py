"""High level functions to generate analytics file for PMA2020 ODK."""

import argparse
import csv
import itertools
import logging
import os.path
import time

from analytics.formdata import lookup
from analytics.exception import CondenseException
from analytics.exception import LookupException
from analytics.instance import Instance


def setup_logging(log_level, export_directory, log_file):
    """Initialize logging when condense module is run as main.

    Args:
        log_level (str): The logging level, e.g. DEBUG
        export_directory (str): The path to the analytics export directory
        log_file (str): The path where to save the log. Use None for STDERR.
    """
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
    """Get the analytics header for the resultant CSV file.

    Args:
        prompts (seq of str): The prompts to capture from log.txt files
        tags (seq of str): The XML tags to extract from submission.xml files

    Returns:
        A list of headers (str) to be used in the CSV.
    """
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
            f'{prompt}_delta',
            f'{prompt}_sb'
        ]
        header.extend(chunk)
    return header


def analytics_instance_row(instance, prompts, tags):
    """Convert an instance object to a row for the CSV.

    Args:
        instance (analytics.Instance): An instance object
        prompts (seq of str): The prompts to capture from log.txt files
        tags (seq of str): The XML tags to extract from submission.xml files

    Returns:
        A list of values to be used as a row of the CSV.
    """
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
            tag_chunk.append(found_tag)
        except KeyError:
            tag_chunk.append(None)
    row.extend(tag_chunk)
    # Get all dynamic prompts
    for prompt in prompts:
        chunk = []
        try:
            this_cc = instance.prompt_cc[prompt]
            chunk.append(this_cc)
        except KeyError:
            chunk.append(None)
        try:
            timing = int(instance.prompt_resumed[prompt]/1000)
            chunk.append(timing)
        except KeyError:
            chunk.append(None)
        try:
            visits = instance.prompt_visits[prompt]
            chunk.append(visits)
        except KeyError:
            chunk.append(None)
        try:
            delta = instance.prompt_changes[prompt]
            chunk.append(delta)
        except KeyError:
            chunk.append(None)
        try:
            short_break = int(instance.prompt_short_break[prompt]/1000)
            chunk.append(short_break)
        except KeyError:
            chunk.append(None)
        row.extend(chunk)
    return row


def previously_analyzed(path):
    """Get the instance uuids (folders) that are already in the CSV.

    Args:
        path (str): The path to where the CSV is

    Returns:
        A set of instance uuids that were found in the CSV. Empty set if no
        file.
    """
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
    """Return True if the supplied and CSV headers are not compatible.

    Args:
        path (str): The path to where the CSV is
        header (seq of str): A header to match against

    Returns:
        True if and only if there would be problems combining data. Thus, if
        the CSV does not exist, returns False, for example.
    """
    mismatch = False
    try:
        with open(path, mode='r', newline='', encoding='utf-8') as out:
            reader = csv.reader(out)
            try:
                line = next(reader)
                for i, j in itertools.zip_longest(line, header):
                    if i != j:
                        msg = f'Header mismatch at {i} (CSV) and {j} (new)'
                        logging.error(msg)
                        mismatch = True
                        break
            except StopIteration:
                # Empty file?
                pass
    except FileNotFoundError:
        pass
    return mismatch


def analytics_folders_setup(path, overwrite, instances_dir, header):
    """Initialize the folders to analyze for analytics.

    Args:
        path (str): The path for the resultant CSV
        overwrite (bool): True iff the any existing CSV should be overwritten
        instances_dir (str): The parent directory containing all instances
        header (seq of str): A header to match CSV against

    Returns:
        A list of folders to analyze.
    """
    folders = []
    old = set()
    if not overwrite:
        if schema_mismatch(path, header):
            msg = 'Analytics file schema mismatch. Use "overwrite" option.'
            raise CondenseException(msg)
        old = previously_analyzed(path)
    for item in os.scandir(instances_dir):
        if item.is_dir() and item.name not in old:
            folders.append(item.path)
    count = len(folders)
    if count == 0:
        print('All up to date. No new instances to analyze.')
    elif overwrite:
        print(f'Analyzing all {count} instances', end=' ')
        print(f'downloaded into {instances_dir}')
        print(f'Intended output file with overwrite: {path}')
    else:
        print(f'Analyzing new {count} instances', end=' ')
        print(f'downloaded into {instances_dir}')
        print(f'Intended output file with append: {path}')
    return folders


def analytics_to_csv(path, overwrite, instances_dir, prompts, tags):
    """Write analytics to CSV.

    Args:
        path (str): The path for the resultant CSV
        overwrite (bool): True iff the any existing CSV should be overwritten
        instances_dir (str): The parent directory containing all instances
        prompts (seq of str): The prompts to capture from log.txt files
        tags (seq of str): The XML tags to extract from submission.xml files
    """
    # ---------- STEP 1: SETUP ----------
    header = analytics_header(prompts, tags)
    folders = analytics_folders_setup(path, overwrite, instances_dir, header)
    if not folders:
        return
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
            uncaptured_prompts |= instance.uncaptured_prompts
    if uncaptured_prompts:
        msg = 'From instances in %s, discovered %d uncaptured prompts: %s'
        logging.info(msg, instances_dir, len(uncaptured_prompts),
                     str(uncaptured_prompts))


def condense_cli_args():
    """Get CLI arguments."""
    prog_desc = ('Condense all submissions under one form of ODK Briefcase '
                 'Storage into an intermediate data product for analysis.')
    parser = argparse.ArgumentParser(description=prog_desc)

    named = parser.add_argument_group('named arguments')

    storage_help = ('A directory with a subdirectory called "ODK Briefcase '
                    'Storage".')
    named.add_argument('--storage_directory', help=storage_help, required=True)

    form_help = ('The form id of the files to condense. Must be known to the '
                 'system or supplied.')
    named.add_argument('--form_id', help=form_help, required=True)

    dir_help = 'A directory to store output and export information.'
    named.add_argument('--export_directory', help=dir_help, required=True)

    out_help = 'The file to write. Should have ".csv" extension.'
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

    storage_literal_help = ('Include to interpret --storage_directory as the '
                            'folder containing all instances.')
    parser.add_argument('-s', '--storage_literal', help=storage_literal_help,
                        action='store_true')

    args = parser.parse_args()
    return args


def condense_cli():
    """Run the CLI for condense, the main entry point for PMA analytics."""
    args = condense_cli_args()
    setup_logging(args.log_level, args.export_directory, args.log_file)
    instances_dir = args.storage_directory
    try:
        form_obj = lookup.lookup(args.form_id, src=args.lookup)
        form_title = form_obj['form_title']
        if not args.storage_literal:
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
        msg = (f'Finished condensing data to "{csv_output}" for form_id '
               f'"{args.form_id}" after {diff_str}')
        logging.info(msg)
        print(msg)
    except FileNotFoundError:
        msg = (f'Unable to find ODK instances directory: "{instances_dir}". '
               f'Check --storage_directory and --storage_literal arguments.')
        print(msg)
    except LookupException as e:
        print(e)
    except CondenseException as e:
        print(e)


if __name__ == '__main__':
    condense_cli()
