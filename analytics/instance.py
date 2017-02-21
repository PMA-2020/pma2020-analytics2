import glob
import logging
import os.path
import re

from analytics.logparser import Logparser
from analytics.event import Event


class Instance:

    LOG = 'log.txt'
    XML = 'submission.xml'
    TWO_HR = 7_200_000
    THIRTY_MIN = 1_800_000
    TEN_SEC = 10_000
    ONE_SWIPE = 400
    INSTANCE = 0

    def __init__(self, name, prompts=None, milestones=None, tags=None, config=None):
        self.full_name = name
        self.folder = os.path.split(self.full_name)[1]

        Instance.INSTANCE += 1
        logging.debug("[%s] Beginning work (%d)", self.folder, self.INSTANCE)


        self.xml = self.find_files(self.XML)
        self.txt = self.find_files(self.LOG)
        self.jpg = self.find_files('*.[jJ][pP][gG]', '*.[jJ][pP][eE][gG]')

        self.xml_size = self.file_size(*self.xml)
        self.txt_size = self.file_size(*self.txt)
        self.jpg_size = self.file_size(*self.jpg)

        self.prompts = prompts if prompts else []
        self.milestones = milestones if milestones else []
        self.tags = tags if tags else []

        self.prompt_data = {}
        self.prompt_cc = {}
        self.prompt_visits = {}
        self.prompt_changes = {}
        self.prompt_value = {}
        self.uncaptured_prompts = set()

        self.milestone_data = {}
        self.tag_data = {}

        self.resumed = 0
        self.paused = 0
        self.short_break = 0

        self.save_count = 0
        self.enter_count = 0
        self.relation_self_destruct = 0

        self.log_version = None

        if config:
            self.short_break_threshold = config.get('short_break_threshold', self.THIRTY_MIN)
            self.event_threshold = config.get('event_threshold', self.ONE_SWIPE)
            self.relation_threshold = config.get('relation_threshold', self.TEN_SEC)
        else:
            self.short_break_threshold = self.THIRTY_MIN
            self.event_threshold = self.ONE_SWIPE
            self.relation_threshold = self.TEN_SEC

        if len(self.xml) != 1:
            logging.info('[%s] Number of xml files found: %d', self.folder,
                            len(self.xml))
        else:
            self.summarize_xml()

        if len(self.txt) != 1:
            logging.info('[%s] Number of txt files found: %d', self.folder,
                            len(self.txt))
        else:
            self.summarize_log()

    def summarize_log(self):
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
            if prompt in self.prompt_data:
                self.prompt_data[prompt] += time_diff
            else:
                self.prompt_data[prompt] = time_diff

    def update_resumed(self, resumed_diff):
        if 0 < resumed_diff:
            self.resumed += resumed_diff

    def update_paused(self, paused_diff):
        if 0 < paused_diff:
            self.paused += paused_diff
        if 0 < paused_diff < self.short_break_threshold:
            self.short_break += paused_diff

    def summarize_xml(self):
        if not self.tags:
            return

        full_file = os.path.join(self.full_name, self.XML)
        with open(full_file) as open_file:
            s = open_file.read()
            for tag in self.tags:
                pattern = f'<{tag}>([^<>]+)</{tag}>'
                match = re.search(pattern, s)
                if match:
                    value = match.group(1)
                    self.tag_data[tag] = value

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
    name = '/Users/jpringle/Documents/odkbriefcase/ODK Briefcase Storage/forms/RJR1-Female-Questionnaire-v12/instances/uuid1ea1776c-45e8-465c-b6a8-5ac5e031cf9b'
    prompts = ['structure', 'heard_implants', 'witness_auto', 'birthdate', 'fp_final_decision', 'facility_fp_discussion', 'heard_withdrawal', 'heard_pill', 'EA', 'heard_female_sterilization', 'pregnancy_desired', 'fp_told_other_methods', 'bus_cur_marr', 'name_check', 'visited_by_health_worker', 'last_time_sex_value', 'bus_rec_birth', 'wait_birth_some', 'fp_side_effects', 'recent_birth', 'begin_interview', 'pregnant', 'age', 'births_live_all', 'location_confirmation', 'heard_rhythm', 'fp_ad_label', 'school', 'times_visited', 'heard_male_condoms', 'consent_start', 'fp_ad_tv', 'visited_fac_some', 'available', 'more_children_some', 'husband_cohabit_now', 'privacy_warn', 'age_at_first_use_children', 'heard_IUD', 'heard_emergency', 'firstname', 'fp_ad_prompt', 'system_date_check', 'consent', 'fp_obtain_desired', 'heard_injectables', 'bus_prompt', 'FQ_age', 'Section_4', 'heard_male_sterilization', 'birth_last_note', 'birth_events', 'marriage_history', 'collect_water_dry_value', 'current_method_check', 'afsq', 'collect_water_wet', 'Section_1', 'age_note', 'first_method_check', 'current_method', 'level2', 'heard_LAM', 'system_date', 'birth_desired', 'photo_of_home', 'future_prompt', 'aquainted', 'child_alive', 'fp_ad_magazine', 'age_at_first_sex', 'heard_other', 'heard_female_condoms', 'age_at_first_use', 'marital_status', 'menstrual_period', 'your_name', 'Section_3', 'level1', 'fp_ad_radio', 'return_to_provider', 'Section_2', 'other_wives', 'fp_provider', 'FRS_result', 'current_user', 'photo_confirmation', 'heard_beads', 'first_method', 'thankyou', 'location', 'collect_water_wet_value', 'household', 'collect_water_dry', 'birth_note', 'fp_provider_check', 'privacy_warn2', 'menstrual_period_value', 'bday_note', 'refer_to_relative', 'location_prompt', 'first_birth', 'your_name_check', 'penultimate_birth', 'last_time_sex', 'ltsq', 'level3', 'begin_using', 'visited_fac_none', 'husband_cohabit_start_recent', 'fees_12months']
    i = Instance(name, prompts=prompts)
    print(i)
    print(i.folder)
    print(i.xml_size)
    print(i.txt_size)
    print(i.jpg_size)
    print(i.resumed)
    print(i.paused)
    print(i.short_break)
    print(i.prompt_data)
    print(i.prompt_cc)
    print(i.prompt_visits)
    print(i.uncaptured_prompts)
