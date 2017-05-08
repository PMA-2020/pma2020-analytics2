"""Module to contain the Instance class, representing one ODK instance."""
import glob
import logging
import os.path
import re

from analytics.logparser import Logparser
from analytics.event import Event


class Instance:  # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods
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
            name (str): The path to the folder containing all instance info
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
        self.prompt_short_break = {}
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
        for i in pattern:
            full_pattern = os.path.join(self.full_name, i)
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
            contents = open_file.read()
            for tag in self.tags:
                pattern = f'<{tag}>([^<>]+)</{tag}>'
                match = re.search(pattern, contents)
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
            msg = '[%s] Number of txt files found: %d'
            logging.error(msg, self.folder, len(self.txt))
            return

        full_file = os.path.join(self.full_name, self.LOG)
        parser = Logparser(full_file, event_threshold=self.event_threshold,
                           relation_threshold=self.relation_threshold)
        self.log_version = parser.version
        state = LogParseState()
        for event in parser:
            self.check_event_order(event, state)
            self.track_resume_pause(event, state)
            self.track_question_resumed_time(event, state)
            self.track_countables(event)
            self.track_prompt_value(event)

    def check_event_order(self, event, state):
        """Check if the event is out of order with the analysis state.

        Sends a message to logging if incorrect conditions are observed.

        Args:
            event (Event): The next event to analyze
            state (LogParseState): The state of the log-event analysis
        """
        if state.prev_event and state.prev_event > event:
            msg = '[{}] Out of order events: {} and {}'
            msg = msg.format(self.folder, state.prev_event, event)
            logging.warning(msg)

    def track_resume_pause(self, event, state):
        """Track state in relation to onResume and onPause.

        Track that onResume should precede onPause. They should not be
        multiple (several in a series).

        Buried here is tracking the short break time for individual prompts.

        Args:
            event (Event): The next event to analyze
            state (LogParseState): The state of the log-event analysis
        """
        # Track onResume -> onPause
        if event.code == 'oR':
            if state.last_pause is None and state.last_resume is None:
                state.last_resume = event
            elif state.last_pause and state.last_resume is None:
                self.screen_short_break_time(state.last_pause, event)
                paused_diff = event - state.last_pause
                self.update_paused(paused_diff)
                state.last_resume = event
                state.last_pause = None
            elif state.last_resume and state.last_pause is None:
                msg = '[{}] Still oR, oR ({} and {}) without oP'
                msg = msg.format(self.folder, state.last_resume, event)
                logging.warning(msg)
        elif event.code == 'oP':
            if state.last_pause is None and state.last_resume is None:
                msg = '[%s] Before first oR, found oP: %s'
                logging.warning(msg, self.folder, str(event))
            elif state.last_resume and state.last_pause is None:
                resumed_diff = event - state.last_resume
                self.update_resumed(resumed_diff)
                state.last_resume = None
                state.last_pause = event
                if resumed_diff > self.TWO_HR:
                    msg = '[{}] Large resumed time (>2hr) between {} and {}'
                    msg = msg.format(self.folder, state.last_resume, event)
                    logging.warning(msg)
            elif state.last_pause and state.last_resume is None:
                msg = '[{}] oP, oP ({} and {}) without oR'
                msg = msg.format(self.folder, state.last_pause, event)
                logging.warning(msg)

    def track_question_resumed_time(self, event, state):
        """Track resumed time for questionnaire prompts.

        This modifies the state object based on the events that are
        observed.

        Args:
            event (Event): The next event to analyze
            state (LogParseState): The state of the log-event analysis
        """
        # Track time in each question
        if event.code == 'oR' or event.code == 'EP':
            if event.stage == Event.QUESTION:
                state.last_enter = event
        elif event.code == 'oP' or event.code == 'LP':
            if event.stage == Event.QUESTION:
                self.screen_time(state.last_enter, event)
                state.last_enter = None

    def track_countables(self, event):
        """Track miscellaneous events that are counted.

        Currently we track counts of
            * Total screen visits
            * Visits to each prompt
            * Contravene constraint (CC) for each prompt
            * Save forms
            * Relation self-destructs

        Args:
            event (Event): The next event to analyze
        """
        # Track visits
        if event.code == 'EP':
            if event.stage == Event.QUESTION:
                self.screen_visit(event)
                self.enter_count += 1

        # Contravene a constraint
        if event.code == 'CC':
            if event.stage == Event.QUESTION:
                self.screen_cc(event)

        # Save form count
        elif event.code == 'SF':
            self.save_count += 1

        # Track rS, happens in HQ when related FQ age is moved out of 15-49
        elif event.code == 'rS':
            self.relation_self_destruct += 1

    def track_prompt_value(self, event):
        """Track the value of each prompt over the course of the log.

        The value saved at each prompt is tracked in order to count the number
        of times that value changes. We only track substantive changes, not
        when the value is first entered.

        Args:
            event (Event): The next event to analyze
        """
        for entry, prompt in zip(event, event.prompts()):
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

    def screen_cc(self, cc_event):
        """Track code CC from given event.

        Args:
            cc_event (Event): The next event to analyze
        """
        for prompt in cc_event.prompts():
            self.update_screen_cc(prompt)

    def update_screen_cc(self, prompt):
        """Update the CC count for the supplied prompt.

        Args:
            prompt (str): The name of the prompt (simplified xpath, ODK name)
        """
        if prompt in self.prompt_cc:
            self.prompt_cc[prompt] += 1
        else:
            self.prompt_cc[prompt] = 1

    def screen_visit(self, enter_event):
        """Track a screen visit for the given event.

        Args:
            enter_event (Event): The next event to analze
        """
        for prompt in enter_event.prompts():
            self.update_screen_visits(prompt)

    def update_screen_visits(self, prompt):
        """Update the screen visit count for the given prompt.

        If the prompt is not in the list of prompts to track, we add the
        supplied prompt to the "uncaptured prompts" instance variable for
        reporting later.

        Args:
            prompt (str): The name of the prompt (simplified xpath, ODK name)
        """
        if prompt in self.prompt_visits:
            self.prompt_visits[prompt] += 1
        else:
            self.prompt_visits[prompt] = 1
        if prompt not in self.prompts:
            self.uncaptured_prompts.add(prompt)

    def screen_short_break_time(self, pause, resume):
        """Track short break time for the given events.

        Args:
            pause (Event): An onPause event
            resume (Event): A subsequent onResume event
        """
        if pause.stage == Event.QUESTION and resume.stage == Event.QUESTION:
            time_diff = resume - pause
            if 0 < time_diff < self.short_break_threshold:
                pause_prompts = set(pause.prompts())
                resume_prompts = set(resume.prompts())
                for prompt in pause_prompts & resume_prompts:
                    self.update_screen_short_break_time(prompt, time_diff)

    def update_screen_short_break_time(self, prompt, time_diff):
        """Update the short break time for the given prompt.

        Args:
            prompt (str): The name of the prompt (simplified xpath, ODK name)
            time_diff (int): The amount to add to short break time for prompt.
        """
        if prompt in self.prompt_short_break:
            self.prompt_short_break[prompt] += time_diff
        else:
            self.prompt_short_break[prompt] = time_diff

    def screen_time(self, enter_event, leave_event):
        """Track resumed screen time.

        Args:
            enter_event (Event): An event for entering a prompt (oR, EP)
            leave_event (Event): An event for leaving a prompt (oP, LP)
        """
        if enter_event and leave_event and leave_event.stage == Event.QUESTION:
            time_diff = leave_event - enter_event
            enter_prompts = set(enter_event.prompts())
            leave_prompts = set(leave_event.prompts())
            if not enter_prompts & leave_prompts:
                logging.warning('[%s] Unmatched enter/exit event: %s, %s',
                                self.folder, str(enter_event),
                                str(leave_event))
            for prompt in enter_prompts & leave_prompts:
                self.update_screen_time(prompt, time_diff)

    def update_screen_time(self, prompt, time_diff):
        """Update the resumed screen time for the given prompt.

        Args:
            prompt (str): The name of the prompt (simplified xpath, ODK name)
            time_diff (int): The amount to add to resumed time for prompt.
        """
        if prompt in self.prompt_resumed:
            self.prompt_resumed[prompt] += time_diff
        else:
            self.prompt_resumed[prompt] = time_diff

    def update_resumed(self, resumed_diff):
        """Update the overall resumed time for the questionnaire.

        Args:
            resumed_diff (int): The amount to update by
        """
        if resumed_diff > 0:
            self.resumed += resumed_diff

    def update_paused(self, paused_diff):
        """Update the overall paused time for the questionnaire.

        If the amount is less than the short break threshold it is added to
        that quantity as well.

        Args:
            paused_diff (int): The amount to update by
        """
        if paused_diff > 0:
            self.paused += paused_diff
        if 0 < paused_diff < self.short_break_threshold:
            self.short_break += paused_diff

    def __repr__(self):
        """Get the representation of this instance."""
        return f'Instance("{self.full_name}")'

    def __str__(self):
        """Get the string representation of this instance."""
        return repr(self)


class LogParseState:  # pylint: disable=too-few-public-methods
    """A class to track the state during parsing."""

    def __init__(self):
        """Initialize parsing state."""
        self.last_resume = None
        self.last_pause = None
        self.last_enter = None
        self.prev_event = None
