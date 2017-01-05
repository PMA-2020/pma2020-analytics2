import csv
import logging
import re

from analytics.event import Event


class LogparserException(Exception):
    pass


class Logparser:

    def __init__(self, f):
        self.tokens = []

        with open(f, newline='') as tsvfile:
            reader = csv.reader(tsvfile, delimiter='\t')

            event_code = ''
            event_queue = []

            for i, row in enumerate(reader):
                if len(row) == 0:
                    logging.warning('Row %d empty in %s', i, f)
                elif row[0].startswith('#'):
                    t = Event.comment([row], i + 1)
                    self.tokens.append(t)
                else:
                    try:
                        self.assert_valid_entry(row)
                    except LogparserException:
                        logging.warning('Row %d incorrectly formatted in %s', i, f)
                    else:
                        this_code = row[1]
                        if this_code != event_code and event_queue:
                            t = Event(list(event_queue), event_code, i - len(event_queue) + 1)
                            self.tokens.append(t)
                            event_queue.clear()
                        event_code = this_code
                        event_queue.append(row)
            t = Event(event_queue, event_code, i + 1)
            self.tokens.append(t)


    @staticmethod
    def assert_valid_entry(row):
        try:
            timestamp_pattern = re.compile(r'\d{13}')
            timestamp = timestamp_pattern.match(row[0]) is not None

            event_pattern = re.compile(r'\w\w')
            event = event_pattern.match(row[1]) is not None

            three = row[2] != ''

            correct_length = len(row) == 4
            if not all((timestamp, event, three, correct_length)):
                raise LogparserException()
        except IndexError:
            raise LogparserException()

    def __iter__(self):
        return iter(self.tokens)

