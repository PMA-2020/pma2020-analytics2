"""The module to define the Logparser and ParserHelper classes."""
import csv
import logging
import os.path
import re

from analytics.event import Event


class Logparser:
    """Class to define methods for parsing log files."""

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
            if first and first[0].startswith('#'):
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

        A ParserHelper object is used to maintain state during parsing.

        Args:
            reader (csv.reader): An iterator with the lines of the log.

        Returns:
            A list of Events.
        """
        events = []
        helper = ParserHelper(self.event_threshold, self.relation_threshold,
                              self.folder)
        for i, row in enumerate(reader):
            if not self.is_valid_entry(row, i, self.folder):
                continue
            row[0] = int(row[0])
            result = helper.parse_next_row(row, i)
            if result:
                events.extend(result)
        result = helper.finalize()
        if result:
            events.extend(result)
        return events

    @staticmethod
    def is_valid_entry(row, ind=None, folder=None):
        """Return true iff the supplied row is a valid log row.

        Args:
            ind (int): The line number where the row is found.
            folder (str): The folder where the instance is found.
        """
        valid = False
        if not row:
            if ind is not None and folder is not None:
                logging.warning('[%s] Empty line: %d', folder, ind + 1)
        elif row[0].startswith('#') and ind == 0:
            # Do not display an warning message
            pass
        elif len(row) != 4:
            if ind is not None and folder is not None:
                logging.warning('[%s] Line with incorrect length: %d', folder,
                                ind + 1)
        else:
            timestamp_pattern = re.compile(r'\d{13}')
            timestamp = timestamp_pattern.match(row[0]) is not None

            event_pattern = re.compile(r'\w\w')
            event = event_pattern.match(row[1]) is not None

            xpath = row[2] != ''

            if all((timestamp, event, xpath)):
                valid = True
            elif ind is not None and folder is not None:
                logging.warning('[%s] Incorrectly formatted line: %d', folder,
                                ind + 1)
        return valid

    @staticmethod
    def get_version(line):
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
    """Class to store state whilst parsing logs."""

    def __init__(self, event_threshold, relation_threshold, folder):
        """Initialize state for parsing logs.

        Args:
            event_threshold (int): The number of milliseconds where to split
                a normal "event."
            relation_threshold (int): The number of milliseconds where to
                split discrete relation update events.
            folder (str): The folder (usually uuid) where this instance is
                stored.
        """
        self.event_threshold = event_threshold
        self.relation_threshold = relation_threshold
        self.folder = folder

        self.cur_event = None
        self.last_resume = None
        self.prev_non_relation = None

    def parse_next_row(self, row, line):
        """Parse the next row from a log.

        Things we check for:
            Splitting an event based on time when the code is the same
            Two onResumes occuring without onPause in the middle
                If this happens we insert an oP just before the second oR
            Within one code, the log line times must be increasing

        Args:
            row (list): The row that has four fields. First entry is the
                timestamp as an integer.
            line (int): The line number in the log where this entry was found.
        """
        to_return = []
        if self.cur_event is None:
            self.cur_event = Event(row, line)
        else:
            this_time = row[0]
            this_code = row[1]
            time_split = self.is_time_split(this_time)
            code_change = self.is_code_change(this_code)
            if time_split or code_change:
                self.update_previous(line)
                self.check_repeatable(time_split, code_change, line)
                self.check_increasing()
                pause = self.check_resume(this_code, line)
                to_extend = self.replace_with_next(row, line, pause)
                to_return.extend(to_extend)
            else:
                self.cur_event.add_row(row, line)
        return to_return

    def update_previous(self, line):
        """Update state to store the event for future parsing.

        To parse successfully, we must remember the last onResume event in
        order to match oR -> oP pairs. If there is a missing onPause, then the
        last non-relation event is used to create a false onPause. Thus, the
        last non-relation event is remembered as well.

        Args:
            line (int): The line number in the log where this entry was found.
                Only used for logging.
        """
        if self.cur_event.code == 'oR':
            self.last_resume = self.cur_event
        elif self.cur_event.code == 'oP':
            self.last_resume = None
        if self.cur_event.code not in Event.relations:
            if self.prev_non_relation is None and self.cur_event.code != 'oR':
                msg = '[%s] First non-relation event not oR at line %d'
                logging.warning(msg, self.folder, line + 1)
            self.prev_non_relation = self.cur_event

    def check_repeatable(self, time_split, code_change, line):
        """Check if a timesplit occurs within a non-repeatable event.

        A repeatable event is something like SF (save form) where the event
        can happend multiple times in a row. Other events, such as EP (enter
        prompt) should not happen multiple times in a row.

        This function only generates a logging message if the improper
        conditions are found.

        Args:
            time_split (bool): Was there a time split between current event
                and the next line?
            code_change (bool): Was there a code change between teh current
                event and the next line?
            line (int): The line number in the log where this entry was found.
        """
        if time_split and not code_change and not \
                self.cur_event.is_repeatable():
            msg = '[%s] Event split (%s) based on time threshold at line %d'
            logging.warning(msg, self.folder, self.cur_event.code, line + 1)

    def check_increasing(self):
        """Check if the timestamps in an event are increasing.

        By increasing, we mean monotonically increasing, i.e. not decreasing.

        This function only generates a logging message if the improper
        conditions are found.
        """
        if not self.cur_event.increasing:
            msg = '[%s] Event times not increasing at lines %d-%d'
            start = self.cur_event.line + 1
            end = start + len(self.cur_event)
            logging.warning(msg, self.folder, start, end)

    def check_resume(self, this_code, line):
        """Check if there are is an onResume without a matching onPause.

        If the row under consideration is an oR, then we make sure the last
        onResume has a matching onPause. If that matching onPause is missing,
        we create an onPause immediately after the previous non-relation event.

        Args:
            this_code (str): The two letter code for this row
            line (int): The line number in the log where this entry was found.

        Returns:
            An onPause event if needed to have matching oR -> oP. Otherwise,
            returns None.
        """
        to_return = None
        if this_code == 'oR' and self.last_resume is not None:
            msg = '[%s] oR, oR without oP at line %d'
            logging.warning(msg, self.folder, line + 1)
            to_return = self.prev_non_relation.create_pause_next()
        return to_return

    def replace_with_next(self, row, line, pause):
        """Replace current event with the new Event from the next row.

        Args:
            row (list): A row from the log. The time must come as int.
            line (int): The line number in the log where this entry was found.
            pause (analytics.Event): The inserted onPause (if included). Could
                be None.

        Returns:
            A list with the current event and if it is not None, the inserted
            onPause. If there is an articial onPause event to be added, it is
            included.
        """
        to_return = [self.cur_event]
        if pause is not None:
            to_return.append(pause)
        self.cur_event = Event(row, line)
        return to_return

    def is_code_change(self, code):
        """Return true iff the input does not match the current code."""
        code_change = self.cur_event.code != code
        return code_change

    def is_time_split(self, time):
        """Return true iff the input is a time split based on a threshold."""
        if self.cur_event.code in Event.relations:
            threshold = self.relation_threshold
        else:
            threshold = self.event_threshold
        time_split = time - self.cur_event.start_time > threshold
        return time_split

    def finalize(self):
        """Return the current event from the end of the log.

        This method is called at the end of parsing the log. Any event that is
        stored in this ParserHelper instance is returned (with an onPause if
        necessary) in order to complete parsing.

        Returns:
            A list with the current event and if it is not None, the inserted
            onPause. If there is an articial onPause event to be added, it is
            included.
        """
        line = self.cur_event.line + len(self.cur_event) + 1
        self.update_previous(line)
        self.check_increasing()
        pause = self.check_resume('oR', line)
        to_return = [self.cur_event]
        if pause is not None:
            to_return.append(pause)
        return to_return
