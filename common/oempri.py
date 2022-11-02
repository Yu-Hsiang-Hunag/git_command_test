# ==================================================================================================================== #
# Script Name: jira_lib
#
# Description: OEMPRI jira library
# ==================================================================================================================== #
import logging
import sys
import re

try:
    from jira import JIRA, JIRAError
except ImportError:
    logging.error("Please Install JIRA Module")


class OEMPRI(object):
    logger = logging.getLogger("OEMPRI")
    logging.getLogger("requests").setLevel(logging.WARNING)

    pri_dict = {
        "summary": "summary",
        "priority": "priority",
        "components": "components",
        "status": "status",
        "sku": "customfield_11528",
        "part_number": "customfield_11527",
        "reviewers": "customfield_11532",
        "review_notes": "customfield_11531",
        "duedate": "duedate",
        "tac": "customfield_11822",
        "work_package": "customfield_11832",
        "assignee": "assignee",
        "customers": "customfield_11529",
        "log_directory": "customfield_11831",
        "eco": "customfield_12615",
        "description": "description",
        "eco_test_history": "customfield_13010",
        "eco_reviewer": "customfield_13011"
    }

    

    # OEMPRI (key) - 13429 (id)
    def __init__(self, username=None, password=None, ticket=None):
        try:
            print("=====Initial start=====")
            self.jira = self.authorization(username, password)
            self.set_issue(ticket)
        except Exception as e:
            logging.error(e)
            logging.error("JIRA connection not working, quitting...")
            raise ValueError

    def authorization(self, username, password):
        try:
            print("=====Authorization start=====")
            return JIRA(server='https://issues.sierrawireless.com/', basic_auth=(username, password))
        except JIRAError as e:
            self.logger.error("JIRA: %s" % e.message)
            sys.exit(1)
        except KeyError as e:
            self.logger.error('JIRA credentials not known for "%s", please enter JIRA credentials (--login)' % e.message)
            sys.exit(1)

    def set_issue(self, ticket):
        try:
            print("=====Set_issue start=====")
            self.issue = self.jira.issue(ticket)
            print("Issue: ", self.issue)
            print("=======slide=====")
            print("Issue fields: ", self.issue.fields)
            self.fields = {
                "Project": self.issue.fields.project,
                "Type": self.issue.fields.issuetype,
                "Summary": self.issue.fields.summary,
                "Components": self.issue.fields.components,
                "Status": self.issue.fields.status,
                "SKU": self.issue.fields.customfield_11528,
                "Part Number": self.issue.fields.customfield_11527,
                "Reviewers": self.issue.fields.customfield_11532,
                "Review-Notes": self.issue.fields.customfield_11531,
                "Due Date": self.issue.fields.duedate,
                "Work Package": self.issue.fields.customfield_11832,
                "Assignee": self.issue.fields.assignee,
                "Reporter": self.issue.fields.reporter,
                "Customers": self.issue.fields.customfield_11529,
                "Description": self.issue.fields.description,
            }
            # field doesn't exist
            if str(self.fields["Type"]) == "Customer PRI":
                self.fields["TAC"] = self.issue.fields.customfield_11822
                self.fields["ECO"] = self.issue.fields.customfield_12615
                self.fields["Log Directory"] = self.issue.fields.customfield_11831
                # self.fields["ECO Reviewer"] = self.issue.fields.customfield_13011, been removed
                self.fields["ECO Test History"] = self.issue.fields.customfield_13010
                self.fields["SKU Tracker"] = self.issue.fields.customfield_12616
        except JIRAError:
            self.issue = None
            self.fields = None

    def get_issue(self):
        bar = "-" * len(str(self.issue))
        self.logger.info(bar)
        self.logger.info(self.issue)
        self.logger.info(bar)
        for field in sorted(self.fields.keys()):
            self.logger.info("%s = %s" % (field.rjust(20), repr(self.fields[field])))

    def create_issue(self, issuetype, summary, description, watcher_list=None, **fieldargs):
        fields_dict = {
            'project': {'key': 'OEMPRI'},
            'issuetype': {'name': issuetype},
            'summary': summary,
            'description': description,
        }

        for field in fieldargs:
            if str(field).lower() == "components" or str(field).lower() == "customers":
                if str(fieldargs[field]) == "":
                    fields_dict[self.pri_dict[field]] = []
                else:
                    args = re.split(', ', fieldargs[field])
                    component = []
                    for item in args:
                        if str(field).lower() == "components":
                            component.append({'name': item})
                        else:
                            component.append(item)
                    fields_dict[self.pri_dict[field]] = component
            else:
                fields_dict[self.pri_dict[field]] = fieldargs[field]
        self.logger.debug("Fields: %s" % str(fields_dict))

        try:
            issue = self.jira.create_issue(fields=fields_dict)
            issue = str(issue)
            self.logger.debug("Issue: %s" % issue)
            self.set_issue(issue)
            self.get_issue()

            # add watcher if the list is not None
            if watcher_list is not None:
                for watcher in watcher_list:
                    try:
                        self.add_watcher(watcher)
                    except JIRAError:
                        self.logger.error("skip adding watcher: %s" % watcher)

        except JIRAError as e:
            self.logger.error("Failed Creating Issue: %s" % e.text)
            issue = None

        return issue

    def update_issue(self, issue=None, comment=None, **fieldargs):
        fields_dict = {}
        for field in fieldargs:
            if str(field) == "components" or str(field) == "customers" or str(field) == "reviewers":
                if str(fieldargs[field]) == "":
                    fields_dict[self.pri_dict[field]] = []
                else:
                    args = re.split(', ', fieldargs[field])
                    component = []
                    for item in args:
                        if str(field) == "components" or str(field) == "reviewers":
                            component.append({'name': item})
                        else:
                            component.append(item)
                    fields_dict[self.pri_dict[field]] = component
            else:
                fields_dict[self.pri_dict[field]] = fieldargs[field]
        self.logger.debug("Fields: %s" % str(fields_dict))

        #total_watcher = self.watcher_list()

        # remove watcher list
        #for watches in total_watcher:
        #    self.remove_watcher(watches)

        try:
            if issue is None:
                if comment is None:
                    self.issue.update(fields=fields_dict)
                else:
                    self.issue.update(fields=fields_dict, comment=comment)
            else:
                if comment is None:
                    self.jira.issue(issue).update(fields=fields_dict)
                else:
                    self.jira.issue(issue).update(fields=fields_dict, comment=comment)
            self.logger.debug("Updated Fields: %s" % str(fields_dict))
        except JIRAError as e:
            self.logger.error("Failed Updating Fields: %s" % e.text)

        # add watcher list
        #for watches in total_watcher:
        #    self.add_watcher(watches)

    def transition_issue(self, state, issue=None, comment=None, **fieldargs):

        transition_id = None
        transition_state = None
        new_state = None

        # assign issue as self.issue if it's not set
        if issue is None:
            issue = self.issue
        self.logger.info("Current State: %s" % issue.fields.status)

        #total_watcher = self.watcher_list()

        #for watch in total_watcher:
        #    self.remove_watcher(watch)

        # retrieve the transition states
        transition_states = self.jira.transitions(issue)
        for current_state in transition_states:
            if state == current_state['name']:
                transition_id = current_state['id']
                transition_state = current_state['name']
                new_state = current_state["to"]["name"]
        self.logger.debug("Transition ID: %s" % transition_id)
        self.logger.info("Transition State: %s" % transition_state)

        fields_dict = {}
        for field in fieldargs:
            if str(field) == "components" or str(field) == "customers":
                if str(fieldargs[field]) == "":
                    fields_dict[self.pri_dict[field]] = []
                else:
                    args = re.split(', ', fieldargs[field])
                    component = []
                    for item in args:
                        if str(field) == "components":
                            component.append({'name': item})
                        else:
                            component.append(item)
                    fields_dict[self.pri_dict[field]] = component
            else:
                fields_dict[self.pri_dict[field]] = fieldargs[field]
        self.logger.debug("Fields: %s" % str(fields_dict))

        if len(fieldargs) > 0:
            fields = fields_dict
        else:
            fields = None

        try:
            self.jira.transition_issue(issue, state, fields=fields, comment=comment)
            self.logger.info("Current State (new): %s" % new_state)
            self.logger.debug("Updated: %s" % str(fields))
        except JIRAError as e:
            self.logger.debug("Failed Transition (state, fields): %s" % e.text)
            self.logger.debug("Retrying without Fields...")
            try:
                self.jira.transition_issue(issue, state)
                self.logger.info("Current State (new): %s" % new_state)
                self.update_issue(issue=issue, fields=fields, comment=comment)
                self.logger.debug("Updated: %s" % str(fields))
            except JIRAError as e:
                self.update_issue(issue=issue, fields=fields, comment=comment)
                self.logger.error("Failed Update: %s" % e.text)

        #for watch in total_watcher:
        #    self.add_watcher(watch)

    def search_issues(self, search_string=None, **search_key):
        issue_list = []

        jira_dict = {
            "summary": "summary",
            "priority": "priority",
            "components": "components",
            "status": "status",
            "type": "issuetype",
            "sku": "cf[11528]",
            "part_number": "cf[11527]",
            "reviewers": "cf[11532]",
            "review_notes": "cf[11531]",
            "duedate": "duedate",
            "tac": "cf[11822]",
            "work_package": "cf[11832]",
            "factory_firmware": "cf[11833]",
            "manufacturing_driver": "cf[11834]",
            "configuration_tool": "cf[11835]",
            "download_tool": "cf[11836]",
            "credential_tool": "cf[11837]",
            "assignee": "assignee",
            "external_issue_id": "cf[10310]",
            "customers": "Customers",
            "legacy_issue_id": "cf[11574]",
            "log_directory": "cf[11831]",
        }
        search = 'project=OEMPRI'

        if search_string is not None:
            search += " AND %s " % search_string

        for key in search_key:
            if "cf[" in jira_dict[key]:
                search += ' AND %s ~ "%s" ' % (jira_dict[key], search_key[key])
            else:
                search += ' AND %s="%s" ' % (jira_dict[key], search_key[key])
        self.logger.debug("Search Key: %s" % search)
        try:
            issues = self.jira.search_issues(search)
        except JIRAError as e:
            logging.error("%s" % e.text)
            issues = []

        for issue in issues:
            issue_list.append(str(issue.key))

        return issue_list

    def add_attachment(self, attachment_file, filename=None):
        self.logger.info("Attachment File: %s" % attachment_file)
        print("============================")
        print("Attachfile", attachment_file)
        try:
            with open(attachment_file, 'rb') as f:
                self.jira.add_attachment(issue=self.issue, attachment=f, filename=filename)
            self.logger.info("Added Attachment: %s" % attachment_file)
        except JIRAError:
            print(JIRAError)
            self.logger.error("Failed Adding Attachment: %s" % attachment_file)

    def list_attachment(self):
        file_list = []
        for attachment in self.issue.fields.attachment:
            file_list.append(attachment.filename)
        return file_list

    def get_attachment(self, filename, dest):
        for attachment in self.issue.fields.attachment:
            if attachment.filename == filename:
                file = attachment.get()
                with open( dest + '//' + filename, 'wb') as f:
                    f.write(file)

    def add_comment(self, content=None):
        if content is not None:
            self.jira.add_comment(self.issue, content)
            self.logger.debug("Add Comment: %s" % content)

    def add_watcher(self, username):
        self.jira.add_watcher(self.issue, username)

    def remove_watcher(self, username):
        self.jira.remove_watcher(self.issue, username)

    def assign_user(self, username):
        self.jira.assign_issue(self.issue, username)

    def watcher_list(self):
        ticket_watcher = []
        watchers = self.jira.watchers(self.issue)
        for watch in watchers.watchers:
            matching_names = self.jira.search_users(watch)
            name = ""
            for names in matching_names:
                if str(watch) == str(names):
                    name = names.name
            if name != "":
                ticket_watcher.append(name)
        return ticket_watcher

    def add_reviewer(self, reviewers):
        current_reviewers = self.fields["Reviewers"] + reviewers.split(",")
        review_list = ""

        for reviewer in current_reviewers:
            matching_names = self.jira.search_users(str(reviewer).lstrip(" "))
            name = ""
            for names in matching_names:
                if str(reviewer).lstrip(" ") == str(names):
                    name = names.name

                if str(reviewer).lstrip(" ").lower() == str(names.name).lower():
                    name = names.name

            if name != "":
                review_list += name + ","

        review_list = review_list.rstrip(",")
        self.update_issue(reviewers=review_list)

    def create_subtask(self, reviewer=None):
        if reviewer is not None:
            field_reviewers = reviewer.split(",")
            self.add_reviewer(reviewer)
        else:
            field_reviewers = self.fields["Reviewers"]

        description = "Please refer to %s for the requested changes. This ticket is for approval." \
                      "\n\nFor any comments, please add them to %s." \
                      "\n\n*Note*" \
                      "\nApprove Button Location:" \
                      "\n1. At the top of this ticket" \
                      "\n2. [...] button besides your name in %s under Sub-Tasks" % (self.issue, self.issue, self.issue)

        subtask = {
            'summary': "REVIEW %s - %s" % (str(self.issue), str(self.fields["Summary"])),
            'issuetype': {'name': 'Review'},
            'parent': {'id': self.issue.id},
            'project': {'key': 'OEMPRI'},
            'duedate': self.fields["Due Date"],
            'description': description,
            'components': [{'name': self.fields["Components"][0].name}],
        }

        for reviewers in field_reviewers:
            matching_names = self.jira.search_users(str(reviewers).lstrip(" "))
            name = ""
            for names in matching_names:
                if str(reviewers).lstrip(" ") == str(names):
                    name = names.name

                if str(reviewers).lstrip(" ").lower() == str(names.name).lower():
                    name = names.name

            if name != "":
                self.jira.add_watcher(self.issue, name)
                subtask['assignee'] = {'name': name}
                search = "project=OEMPRI and issuetype=Review and parent=%s and assignee=%s" % (str(self.issue), name)

                # search for subtasks
                subtask_issues = self.jira.search_issues(search)
                self.logger.info("%s Sub-Task: %s" % (self.issue, subtask_issues))

                # check if sub-task exists
                if len(subtask_issues) > 0:
                    for sub_issue in subtask_issues:
                        subtask_issue = self.jira.issue(sub_issue)
                        # open ticket and update information
                        if str(subtask_issue.fields.status) == "Closed":
                            self.transition_issue("Reopen", subtask_issue)
                            subtask_issue.update(comment="Re-opening Sub-Task, PRI Rebuilt and Tested.\r\nPlease Review and approve.")
                        else:
                            comment = "PRI Rebuilt and Tested.\r\nPlease Review and Approve."
                            subtask_issue.update(comment=comment)
                else:
                    try:
                        self.logger.info("Create Sub-Task (%s): %s" % (self.issue, name))
                        child = self.jira.create_issue(fields=subtask)
                        self.logger.info("New Sub-Task: %s" % child.key)
                    except JIRAError:
                        self.logger.error("Failed Creating Sub-Task (%s) for %s" % (self.issue, name))

            else:
                self.logger.error("Unable to find %s" % reviewers)


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)-5s: %(message)s', datefmt='%Y-%m-%d_%H:%M:%S', level=logging.DEBUG)
