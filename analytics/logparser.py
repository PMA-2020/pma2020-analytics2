import csv
import logging
import os.path
import re

from analytics.event import Event


class LogparserException(Exception):
    pass


class Logparser:

    def __init__(self, f, event_threshold=0, relation_threshold=60_000):
        self.file = f
        self.event_threshold = event_threshold
        self.relation_threshold = relation_threshold
        self.folder = os.path.split(os.path.split(f)[0])[1]
        self.version = None
        self.events = self.capture_events()

    def capture_events(self):
        events = []
        with open(self.file, newline='') as tsvfile:
            reader = csv.reader(tsvfile, delimiter='\t')

            event_code = ''
            event_queue = []
            event_start = 0
            last_time = 0
            event_increasing = True
            event_min = 9_999_999_999_999
            event_max = 0

            prev = None
            last_oR = None

            for i, row in enumerate(reader):
                if len(row) == 0:
                    logging.warning('[%s] Empty line: %d', self.folder, i+1)
                elif row[0].startswith('#') and i == 0:
                    # search for version number
                    comment = row[0]
                    match = re.search(r'v\d\.\d$', comment)
                    if match:
                        self.version = match.group()
                    else:
                        logging.warning('[%s] No logging version in first line', self.folder)
                else:
                    try:
                        self.assert_valid_entry(row)
                    except LogparserException:
                        logging.warning('[%s] Incorrectly formatted line: %d', self.folder, i + 1)
                    else:
                        this_time = int(row[0])
                        this_code = row[1]

                        if event_code in Event.relations:
                            time_split = this_time - event_start > self.relation_threshold
                        else:
                            time_split = this_time - event_start > self.event_threshold
                        code_change = this_code != event_code
                        if time_split and not code_change:
                            if event_code not in Event.multiples:
                                logging.warning('[%s] Event split (%s) based on time threshold at line %d', self.folder, event_code, i + 1)
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
                            events.append(t)
                            # Reset values for the next event
                            event_queue.clear()
                            event_start = this_time
                            last_time = 0
                            event_increasing = True
                            event_min = 9_999_999_999_999
                            event_max = 0
                            if t.stage == Event.QUESTION:
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
        return iter(self.events)

    def __str__(self):
        return f'Version: {self.version}, event count: {len(self.events)}'

