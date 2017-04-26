"""The module to define the Logparser class."""
import csv
import logging
import os.path
import re

from analytics.event import Event


class Logparser:
    """Class to define methods for parser log files."""

    def __init__(self, path, event_threshold=0, relation_threshold=60_000):
        """Parse a log and save results in this instance.

        The log file is parsed into events and stored as a list.

        Args:
            path (str): The path to where to find the log file
            event_threshold (int): The number of milliseconds where to split
                a normal "event."
            relation_threshold (int): The number of milliseconds where to
                split discrete relation update events.
        """
        self.file = path
        self.event_threshold = event_threshold
        self.relation_threshold = relation_threshold
        self.folder = os.path.split(os.path.split(path)[0])[1]
        self.version = None

        self.events = []
        try:
            self.events = self.capture_events_from_file()
        except csv.Error:
            logging.error('[%s] Abandoned due to file parsing error',
                          self.folder)

    def capture_events_from_file(self):
        """Parse Events from file and get log version."""
        events = []
        with open(self.file, newline='', encoding='utf-8') as tsvfile:
            reader = csv.reader(tsvfile, delimiter='\t')
            first = next(reader)
            if len(first) != 0 and first[0].startswith('#'):
                self.version = self.get_version(first[0])
            if self.version is None:
                logging.warning('[%s] No logging version in first line',
                                self.folder)
            tsvfile.seek(0)
            events = self.capture_events(reader)
        return events

    def capture_events(self, reader):
        """Split the log from file into events and store those events.

        The stream of events are split based on time thresholds and event code
        switching.

        Things we check for:
            Splitting an event based on time when the code is the same
            Two onResumes occuring without onPause in the middle
                If this happens we insert an oP just before the second oR
            Within one code, the log line times must be increasing


        Args:
            reader (csv.reader): An iterator with the lines of the log.

        Returns:
            A list of Events.
        """
        events = []

        helper = ParserHelper(self.event_threshold, self.relation_threshold)

        prev = None
        last_oR = None

        for i, row in enumerate(reader):
            if not self.is_valid_entry(row, i, self.folder):
                continue

            # TODO: Work with ParserHelper and updated Event
            row[0] = int(row[0])
            this_time = int(row[0])
            this_code = row[1]

            time_split = helper.is_time_split()
            code_change = helper.is_code_change()
            if time_split and not code_change:
                if event_code not in Event.multiples:
                    msg = ('[%s] Event split (%s) based on time threshold at '
                           'line %d')
                    logging.warning(msg, self.folder, event_code, i + 1)
            if (code_change or time_split) and event_queue:
                line = i - len(event_queue) + 1
                t = Event(list(event_queue), event_code, line,
                            event_start, event_increasing, event_min,
                            event_max)
                if last_oR and event_code == 'oR':
                    logging.warning('[%s] oR, oR without oP at line %d', self.folder, i + 1)
                    next_event = prev.add_pause()
                    events.append(next_event)
                elif event_code == 'oP':
                    last_oR = None
                elif not last_oR and event_code == 'oR':
                    last_oR = t
                events.append(t)
                # Reset values for the next event
                event_queue.clear()
                event_start = this_time
                last_time = 0
                event_increasing = True
                event_min = 9_999_999_999_999
                event_max = 0
                if t.stage == Event.QUESTION or event_code == 'oR':
                    prev = t

            event_min = min(event_min, this_time)
            event_max = max(event_max, this_time)
            this_increase = this_time > last_time
            event_increasing = event_increasing and this_increase
            event_code = this_code
            event_queue.append(row)

        line = i - len(event_queue) + 1
        t = Event(list(event_queue), event_code, line, event_start,
                    event_increasing, event_min, event_max)
        events.append(t)
        return events

    @staticmethod
    def is_valid_entry(row, ind=None, folder=None):
        """Return true iff the supplied row is a valid log row.

        Args:
            ind (int): The line number where the row is found.
            folder (str): The folder where the instance is found.
        """
        valid = False
        if len(row) == 0:
            if ind is not None and folder is not None:
                logging.warning('[%s] Empty line: %d', folder, ind+1)
        elif row[0].startswith('#') and i == 0:
            pass
        else:
            timestamp_pattern = re.compile(r'\d{13}')
            timestamp = timestamp_pattern.match(row[0]) is not None

            event_pattern = re.compile(r'\w\w')
            event = event_pattern.match(row[1]) is not None

            xpath = row[2] != ''

            correct_length = len(row) == 4

            if all((timestamp, event, xpath, correct_length)):
                valid = True
            elif ind is not None and folder is not None:
                logging.warning('[%s] Incorrectly formatted line: %d', folder,
                                ind + 1)
        return valid

    def get_version(self, line):
        """Get the version number for the logging.

        Args:
            line (str): The log entry that contains the version stamp.

        Returns:
            The version code found (str), or None if not found.
        """
        version = None
        match = re.search(r'v\d\.\d$', line)
        if match:
            version = match.group()
        return version

    def __iter__(self):
        """Return an iterator over the parsed events."""
        return iter(self.events)

    def __repr__(self):
        """Get the representation of this instance."""
        return f'Logparser({self.file})'

    def __str__(self):
        """Get the string representation of this instance."""
        return f'Version: {self.version}, event count: {len(self.events)}'


class ParserHelper():
    def __init__(self, event_threshold, relation_threshold):
        self.event_threshold = event_threshold
        self.relation_threshold = relation_threshold

        self.event_code = ''
        self.event_queue = []
        self.event_start = 0
        self.last_time = 0
        self.event_increasing = True
        self.event_min = 9_999_999_999_999
        self.event_max = 0

    def is_code_change(self, code):
        code_change = self.event_code != code
        return code_change

    def is_time_split(self, time):
        if self.event_code in Event.relations:
            threshold = self.relation_threshold
        else:
            threshold = self.event_threshold
        time_split = time - self.event_start > threshold
        return time_split
