"""Module to contain the Instance class, representing one instance."""
import glob
import logging
import os.path
import re

from analytics.logparser import Logparser
from analytics.event import Event


class Instance:
    """The Instance class represents one instance to be analyzed.

    When an instance is analyzed, many pieces of information are pulled
    together and stored in an instance object.

    The most basic information is file sizes for photos, XML, and .txt
    documents. Next, values stored in XML tags are extracted from the
    submission.xml file. Finally, the log is parsed and several aspects are
    recorded.

    Data about the overall questionnaire:
        * Log version
        * Total resumed time
        * Total paused time
        * Total short break time (paused time if less than a threshold)
        * Total save count
        * Total prompt visit count
        * Total times a subform self-deleted (e.g. age displacement).

    Data about individual prompts:
        * Total resumed time per prompt
        * Total paused time per prompt (at the same prompt, oP -> oR)
        * Count of prompt value changes
        * Prompt visit count
        * Count of contravened constraint / required by prompt

    Class attributes:
        COUNT (int): Count that increments with each instance created
        LOG (str): log file name
        XML (str): XML submission file name
        TWO_HR (int): Two hours in milliseconds
        THIRTY_MIN (int): Thirty minutes in milliseconds
        TEN_SEC (int): Ten seconds in milliseconds
        ONE_SWIPE (int): The length of time for one swipe, arbitrarily set

    TODO:
        * Support for milestones (first time a prompt is seen)
        * Support for config (to override default cutoffs)
    """

    COUNT = 0
    LOG = 'log.txt'
    XML = 'submission.xml'
    TWO_HR = 7_200_000
    THIRTY_MIN = 1_800_000
    TEN_SEC = 10_000
    ONE_SWIPE = 400

    def __init__(self, name, prompts=None, tags=None):
        """Initialize and analyze an instance.

        All analysis happens in during object initialization.

        Some instance variables are initialized in other methods.

        Args:
            prompts (seq of str): Prompt names to analyze from log.txt
            tags (seq of str): XML tag names to extract from submission.xml
        """
        self.full_name = name
        self.folder = os.path.split(self.full_name)[1]

        # Initialize thresholds
        self.initialize_constants()

        Instance.COUNT += 1
        logging.debug("[%s] Beginning work (%d)", self.folder, self.COUNT)

        # General file size information
        self.summarize_file_sizes()

        # Individual XML tag information
        self.tags = tags if tags else []
        self.tag_data = {}

        self.summarize_xml()

        # Overall questionnaire data
        self.log_version = None
        self.resumed = 0
        self.paused = 0
        self.short_break = 0
        self.save_count = 0
        self.enter_count = 0
        self.relation_self_destruct = 0
        # Individual prompt information
        self.prompts = prompts if prompts else []
        self.prompt_resumed = {}
        self.prompt_paused = {}
        self.prompt_cc = {}
        self.prompt_visits = {}
        self.prompt_changes = {}
        self.prompt_value = {}
        self.uncaptured_prompts = set()

        self.summarize_log()

    def initialize_constants(self):
        """Initialize constants and thresholds for analysis."""
        self.short_break_threshold = self.THIRTY_MIN
        self.event_threshold = self.ONE_SWIPE
        self.relation_threshold = self.TEN_SEC

    def summarize_file_sizes(self):
        """Get the sizes of various files in bytes."""
        self.xml = self.find_files(self.XML)
        self.txt = self.find_files(self.LOG)
        self.jpg = self.find_files('*.[jJ][pP][gG]', '*.[jJ][pP][eE][gG]')

        self.xml_size = self.file_size(*self.xml)
        self.txt_size = self.file_size(*self.txt)
        self.jpg_size = self.file_size(*self.jpg)


    def find_files(self, *pattern):
        """Look for the given patterns in the instance directory.

        Args:
            *pattern (str): Any number of patterns to search for

        Returns:
            Returns all found files that match any of the supplied patterns.
        """
        all_found = []
        for p in pattern:
            full_pattern = os.path.join(self.full_name, p)
            found = glob.glob(full_pattern)
            all_found.extend(found)
        return all_found

    @staticmethod
    def file_size(*files):
        """Return the total size in bytes of all the supplied files.

        Args:
            *files (str): Any number of paths to files

        Returns:
            An integer containing sum of file sizes
        """
        return sum((os.path.getsize(f) for f in files))

    def summarize_xml(self):
        """Get needed information from 'submission.xml'.

        The XML file is read into memory and each tag that is found in the
        document gets its value saved in a dictionary of tag data.
        """
        if len(self.xml) != 1:
            logging.error('[%s] Number of xml files found: %d', self.folder,
                          len(self.xml))
            return
        if not self.tags:
            return

        full_file = os.path.join(self.full_name, self.XML)
        with open(full_file, encoding='utf-8') as open_file:
            s = open_file.read()
            for tag in self.tags:
                pattern = f'<{tag}>([^<>]+)</{tag}>'
                match = re.search(pattern, s)
                if match:
                    value = match.group(1)
                    self.tag_data[tag] = value

    def summarize_log(self):
        """Get needed information from log.txt.

        This is where the bulk of the work is done. The log is read into
        memory. It is parsed into discrete events and analyzed step by step.
        Along the way, other information (e.g. overall questionnaire level) is
        saved to the instance.
        """
        if len(self.txt) != 1:
            logging.error('[%s] Number of txt files found: %d', self.folder,
                          len(self.txt))
            return

        full_file = os.path.join(self.full_name, self.LOG)
        parser = Logparser(full_file, event_threshold=self.event_threshold,
                           relation_threshold=self.relation_threshold)

        self.log_version = parser.version

        resumed_token = None
        paused_token = None
        enter_token = None
        last_token = None

        for token in parser:

            if last_token and resumed_token and last_token > token:
                logging.warning('[%s] Out of order tokens: %s and %s', self.folder, str(last_token), str(token))
            if token.stage == Event.ERROR:
                logging.warning('[%s] Unknown event: %s', self.folder, str(token))

            # Track onResume -> onPause
            if token.code == 'oR':
                if paused_token is None and resumed_token is None:
                    resumed_token = token
                elif paused_token is not None and resumed_token is None:
                    paused_diff = token - paused_token
                    self.update_paused(paused_diff)
                    resumed_token = token
                    paused_token = None
            elif token.code == 'oP':
                if resumed_token is None and paused_token is None:
                    logging.warning('In %s, oP found before oR: %s', self.folder, str(token))
                elif resumed_token is not None and paused_token is None:
                    resumed_diff = token - resumed_token
                    if resumed_diff > self.TWO_HR:
                        logging.warning('[%s] Resumed time greater than 2hr between %s and %s', self.folder, resumed_token, token)
                    self.update_resumed(resumed_diff)
                    paused_token = token
                    resumed_token = None

            # Track time in each question
            if token.code == 'oR' or token.code == 'EP':
                if token.stage == Event.QUESTION:
                    enter_token = token
            elif token.code == 'oP' or token.code == 'LP':
                if token.stage == Event.QUESTION:
                    self.screen_time(enter_token, token)
                    enter_token = None

            # Track visits
            if token.code == 'EP':
                if token.stage == Event.QUESTION:
                    self.screen_visit(token)
                    self.enter_count += 1

            # Track certain events
            # Contravene a constraint
            if token.code == 'CC':
                if token.stage == Event.QUESTION:
                    self.screen_cc(token)
            # Save form count
            elif token.code == 'SF':
                self.save_count += 1
            # Track rS, happens in HQ when related FQ age is moved out of 15-49
            elif token.code == 'rS':
                self.relation_self_destruct += 1

            # Track value of each entry
            self.update_prompt_value(token)

            # End of loop
            last_token = token

    def update_prompt_value(self, token):
        for entry, prompt in zip(token, token.prompts()):
            xpath = entry[2]
            value = entry[3]
            if xpath not in self.prompt_value:
                self.prompt_value[xpath] = value
                if value != '':
                    try:
                        self.prompt_changes[prompt] += 1
                    except KeyError:
                        self.prompt_changes[prompt] = 1
            elif self.prompt_value[xpath] != value:
                self.prompt_value[xpath] = value
                try:
                    self.prompt_changes[prompt] += 1
                except KeyError:
                    self.prompt_changes[prompt] = 1

    def screen_cc(self, cc_token):
        for p in cc_token.prompts():
            self.update_screen_cc(p)

    def update_screen_cc(self, prompt):
        if prompt in self.prompts:
            if prompt in self.prompt_cc:
                self.prompt_cc[prompt] += 1
            else:
                self.prompt_cc[prompt] = 1

    def screen_visit(self, enter_token):
        for p in enter_token.prompts():
            self.update_screen_visits(p)

    def update_screen_visits(self, prompt):
        if prompt in self.prompts:
            if prompt in self.prompt_visits:
                self.prompt_visits[prompt] += 1
            else:
                self.prompt_visits[prompt] = 1
        else:
            self.uncaptured_prompts.add(prompt)

    def screen_time(self, enter_token, leave_token):
        if enter_token and leave_token and leave_token.stage == Event.QUESTION:
            time_diff = leave_token - enter_token
            e, l = set(enter_token.prompts()), set(leave_token.prompts())
            if not e & l:
                logging.warning('[%s] Unmatched enter/exit tokens: %s, %s', self.folder, str(enter_token), str(leave_token))
            for p in e & l:
                self.update_screen_time(p, time_diff)

    def update_screen_time(self, prompt, time_diff):
        if prompt in self.prompts:
            if prompt in self.prompt_resumed:
                self.prompt_resumed[prompt] += time_diff
            else:
                self.prompt_resumed[prompt] = time_diff

    def update_resumed(self, resumed_diff):
        if 0 < resumed_diff:
            self.resumed += resumed_diff

    def update_paused(self, paused_diff):
        if 0 < paused_diff:
            self.paused += paused_diff
        if 0 < paused_diff < self.short_break_threshold:
            self.short_break += paused_diff

    def __repr__(self):
        """Get the representation of this instance."""
        return f'Instance("{self.full_name}")'

    def __str__(self):
        """Get the string representation of this instance."""
        return repr(self)

