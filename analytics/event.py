import re


class Event:

    RELATION = 'RELATION'
    BOOKEND = 'BOOKEND'
    QUESTION = 'QUESTION'
    ERROR = 'ERROR'

    bookend_codes = {'BF', 'FF'}
    bookends = {'uC', 'BF', 'FF', 'null'}
    relations = {'rC', 'rV', 'rS'}
    multiples = {'rV', 'rS', 'SF', 'FF', 'LF'}

    def __init__(self, rows, code, line, start, increasing, min, max):
        self.rows = rows
        self.code = code
        self.line = line
        self.min = min
        self.max = max
        self.start = start
        self.increasing = increasing

        self.delta = self.max - self.min

        locations = set(r[2] for r in self.rows)
        if self.code in self.relations:
            self.stage = Event.RELATION
        elif self.code in self.bookend_codes or locations & self.bookends:
            self.stage = self.BOOKEND
        elif locations.isdisjoint(self.bookends):
            self.stage = self.QUESTION
        else:
            self.stage = self.ERROR

    def add_pause(self):
        next_event = Event(list(self.rows), 'oP', self.line + 0.5, self.max + 1, self.increasing, self.max + 1, self.max + 1)
        return next_event

    def prompts(self):
        for row in self.rows:
            full_prompt = row[2]
            found = re.search(r'(^|/)([^/]+)\[1\]$', full_prompt)
            if found:
                yield found.group(2)
            else:
                yield full_prompt

    def __str__(self):
        n = len(self.rows)
        m = f'{self.code}(@{self.line} for {n})'
        return m

    def __iter__(self):
        return iter(self.rows)

    def __sub__(self, other):
        return self.max - other.min

    def __lt__(self, other):
        return self.max < other.min

    def __gt__(self, other):
        return self.min > other.max

    def __le__(self, other):
        return self.max <= other.min

    def __ge__(self, other):
        return self.min >= other.max
