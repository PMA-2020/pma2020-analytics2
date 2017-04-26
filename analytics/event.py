"""Module to define the Event class."""
import re

from analytics.exception import LogparserException


class Event:  # pylint: disable=too-many-instance-attributes
    """The Event class for capturing discrete events in a log file.

    Class attributes:
        RELATION (str): Constant for a type of event--an operation in form
            relations
        BOOKEND (str): Constant for a type of event--beginning or end of a
            questionnaire
        QUESTION (str): Constant for a type of event--a question prompt
        relations (set of str): Codes for a form relation event
        bookend (set of str): Codes for a bookend event
        bookend_xpaths (set of str): Log xpaths for a bookend event
        multiples (set of str): Codes that can correctly be repeated in a log
    """

    RELATION = 'RELATION'
    BOOKEND = 'BOOKEND'
    QUESTION = 'QUESTION'

    relations = {'rC', 'rV', 'rS'}
    bookends = {'BF', 'FF'}
    bookend_xpaths = {'uC', 'BF', 'FF', 'null'}
    multiples = {'rS', 'SF', 'CC'}

    def __init__(self, row, line):
        """Initialize the event with a single row.

        Args:
            row (list): A row from the log. The time must come as int
            line (int): The line number in the log where this row comes from
        """
        self.rows = [row]
        self.line = line

        self.code = row[1]
        self.start_time = row[0]
        self.max_time = row[0]
        self.min_time = row[0]
        self.increasing = True
        xpath = row[2]
        self.stage = self.get_stage(self.code, xpath)

    @property
    def delta(self):
        """Return time delta for this event."""
        return self.max_time - self.min_time

    @staticmethod
    def get_stage(code, xpath):
        """Get the stage of the questionnaire this event comes from.

        Returns:
            One of Event.QUESTION, Event.RELATION, Event.BOOKEND.
        """
        stage = Event.QUESTION
        if code in Event.relations:
            stage = Event.RELATION
        elif code in Event.bookends or xpath in Event.bookend_xpaths:
            stage = Event.BOOKEND
        return stage

    def add_row(self, row, line):
        """Add a row from the log to this event instance.

        Args:
            row (list): A row from the log. The time must come as int
            line (int): The line number in the log where this row comes from
        """
        this_time = row[0]
        this_code = row[1]

        if this_code != self.code:
            msg = 'Codes must all be the same. Had {}. Added {}. @{}'
            msg = msg.format(self.code, this_code, line + 1)
            raise LogparserException(msg)

        self.max_time = max(self.max_time, this_time)
        self.min_time = min(self.min_time, this_time)

        if self.increasing and this_time < self.last_time():
            self.increasing = False

    def copy(self):
        """Make a copy of this event."""
        rows = []
        for row in self.rows:
            rows.append(list(row))
        first_row = rows.pop(0)
        copy = Event(first_row, self.line)
        for row in rows:
            copy.add_row(row, self.line)
        return copy

    def set_code(self, code):
        """Set the code for this event."""
        for row in self.rows:
            row[1] = code
        self.code = code

    def set_time(self, time):
        """Set the time for this event."""
        for row in self.rows:
            row[0] = time
        self.start_time = time
        self.max_time = time
        self.min_time = time
        self.increasing = True

    def last_time(self):
        """Get the time of the last line in this event."""
        last_row = self.rows[-1]
        last_time = last_row[0]
        return last_time

    def create_pause_next(self):
        """Create a onPause event immediately after this event."""
        next_event = self.copy()
        next_event.set_code('oP')
        next_event.set_time(self.max_time + 1)
        next_event.line = self.line + len(self.rows) + 0.5
        return next_event

    def prompts(self):
        """Get the prompts contained in this event.

        Yields:
            The next prompt, extracted from the xpath, for this event.
        """
        for row in self.rows:
            xpath = row[2]
            found = re.search(r'(^|/)([^/]+)\[1\]$', xpath)
            if found:
                yield found.group(2)
            else:
                yield xpath

    def __str__(self):
        """Get the string representation of this instnace."""
        n_row = len(self.rows)
        msg = f'{self.code}(@{self.line} for {n_row})'
        return msg

    def __iter__(self):
        """Return an iterator over the rows in this event."""
        return iter(self.rows)

    def __sub__(self, other):
        """Subtract the times from this Event with another."""
        return self.max_time - other.min_time

    def __lt__(self, other):
        """Return true iff this Event occurs before the other."""
        return self.max_time < other.min_time

    def __gt__(self, other):
        """Return true iff this Event occurs after the other."""
        return self.min_time > other.max_time

    def __le__(self, other):
        """Return true iff this Event is not later than the other."""
        return self.max_time <= other.min_time

    def __ge__(self, other):
        """Return true iff this Event is not earlier than the other."""
        return self.min_time >= other.max_time
