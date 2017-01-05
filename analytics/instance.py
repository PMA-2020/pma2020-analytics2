import glob
import logging
import os.path

from analytics.logparser import Logparser
from analytics.event import Event


class Instance:

    LOG = 'log.txt'
    XML = 'submission.xml'
    THIRTY_MIN = 1_800_800

    def __init__(self, name, prompts=None, milestones=None, tags=None, config=None):
        self.full_name = name
        self.folder = os.path.split(self.full_name)[1]

        self.xml = self.find_files(self.XML)
        self.txt = self.find_files(self.LOG)
        self.jpg = self.find_files('*.[jJ][pP][gG]', '*.[jJ][pP][eE][gG]')

        self.xml_size = self.file_size(*self.xml)
        self.txt_size = self.file_size(*self.txt)
        self.jpg_size = self.file_size(*self.jpg)

        self.prompt_data = {}
        self.milestone_data = {}
        self.tag_data = {}

        self.resumed = 0
        self.paused = 0
        self.short_break = 0
        if config:
            self.short_break_threshold = config.get('short_break_threshold', self.THIRTY_MIN)
        else:
            self.short_break_threshold = self.THIRTY_MIN

        if len(self.xml) != 1:
            logging.warning('%s - number of xml files found: %d', self.folder,
                            len(self.xml))
        else:
            self.summarize_xml(tags=tags)

        if len(self.txt) != 1:
            logging.warning('%s - number of txt files found: %d', self.folder,
                            len(self.txt))
        else:
            self.summarize_log(prompts=prompts, milestones=milestones)

    def summarize_log(self, prompts=None, milestones=None):
        full_file = os.path.join(self.full_name, self.LOG)
        parser = Logparser(full_file)

        resumed_token = None
        paused_token = None
        screen_token = None
        last_token = None

        for token in parser:
            if token.type == Event.COMMENT:
                continue

            if not token.is_sorted:
                logging.warning('In %s, token not internally chronological: %s', self.folder, str(token))
            if last_token is not None and last_token > token:
                logging.warning('In %s, out of order tokens: %s and %s', self.folder, str(last_token), str(token))

            if token.type == 'oR':
                if paused_token is None and resumed_token is None:
                    resumed_token = token
                elif paused_token is not None and resumed_token is None:
                    paused_diff = token - paused_token
                    self.update_paused(paused_diff)
                    resumed_token = token
                    paused_token = None
            elif token.type == 'oP':
                if resumed_token is None and paused_token is None:
                    logging.warning('In %s, oP found before oR: %s', self.folder, str(token))
                elif resumed_token is not None and paused_token is None:
                    resumed_diff = token - resumed_token
                    self.update_resumed(resumed_diff)
                    paused_token = token
                    resumed_token = None

            last_token = token

    def update_resumed(self, resumed_diff):
        if 0 < resumed_diff:
            self.resumed += resumed_diff

    def update_paused(self, paused_diff):
        if 0 < paused_diff:
            self.paused += paused_diff
        if 0 < paused_diff < self.short_break_threshold:
            self.short_break += paused_diff

    def summarize_xml(self, tags=None):
        full_file = os.path.join(self.full_name, self.XML)

    def find_files(self, *pattern):
        all_found = []
        for p in pattern:
            full_pattern = os.path.join(self.full_name, p)
            found = glob.glob(full_pattern)
            all_found.extend(found)
        return all_found

    @staticmethod
    def file_size(*files):
        return sum((os.path.getsize(f) for f in files))

    def __repr__(self):
        return f'Instance("{self.full_name}")'

    def __str__(self):
        return repr(self)


if __name__ == '__main__':
    name = '/Users/jpringle/Documents/odkbriefcase/ODK Briefcase Storage/forms/RJR1-Female-Questionnaire-v12/instances/uuidba5203dd-e3ea-4385-aef5-890503e8247a'
    i = Instance(name)
    print(i)
    print(i.folder)
    print(i.xml_size)
    print(i.txt_size)
    print(i.jpg_size)
    print(i.resumed)
    print(i.paused)
    print(i.short_break)
