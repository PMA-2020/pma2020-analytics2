import logging


class Event:

    COMMENT = 'COMMENT'

    def __init__(self, rows, type, start):
        self.rows = rows
        self.type = type
        self.start = start

        if self.type != Event.COMMENT:
            times = [int(row[0]) for row in self.rows]
            self.min_time = times[0]
            self.max_time = times[-1]
            self.is_sorted = all(a <= b for a, b in zip(times, times[1:]))


    @staticmethod
    def comment(rows, start):
        t = Event(rows, Event.COMMENT, start)
        return t

    def __str__(self):
        n = len(self.rows)
        if self.type == Event.COMMENT:
            preview = self.rows[0][0]
            m = f'{self.type}(@{self.start} for {n}), preview: "{preview}"'
            return m
        else:
            delta = self.max_time - self.min_time
            m = f'{self.type}(@{self.start} for {n}), min: {self.min_time}, delta: {delta}'
            return m

    def __sub__(self, other):
        return self.max_time - other.min_time

    def __lt__(self, other):
        return self.max_time < other.min_time

    def __gt__(self, other):
        return self.min_time > other.max_time
