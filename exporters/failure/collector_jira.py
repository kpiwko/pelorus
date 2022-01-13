import logging
from datetime import datetime

import pytz
from failure.collector_base import AbstractFailureCollector, TrackerIssue
from jira import JIRA

import pelorus


class JiraFailureCollector(AbstractFailureCollector):
    """
    Jira implementation of a FailureCollector
    """

    def __init__(
        self,
        server,
        user,
        token,
        jql,
        projects,
        types,
        priorities,
        age,
    ):
        super().__init__(server)
        if jql is not None:
            logging.debug(
                "Provided JQL query jql={}, ignoring values of projects={}, types={}, priorities={} and age={}".format(
                    jql, projects, types, priorities, age
                )
            )

        else:
            jql = "type IN ({}) AND priority IN ({})".format(types, priorities)
            if projects is not None:
                jql = "project IN ({}) AND ".format(projects) + jql
            if age is not None:
                jql = jql + " AND updated >= {}".format(str(age))
            logging.debug("Constructed JQL query '{}'".format(jql))

        self.jql = jql

        self.basic_auth = None
        self.token_auth = None
        if user is not None:
            logging.debug("Using Basic Auth to access JIRA at {}".format(self.server))
            self.basic_auth = (user, token)
        elif token is not None:
            logging.debug(
                "Using JIRA Access Token to access JIRA at {}".format(self.server)
            )
            self.token_auth = token
        else:
            msg = "Need to provide either user and apikey or token to authenticate"
            logging.error(msg)
            raise ValueError(msg)

    def search_issues(self):
        # TODO FIXME This may need to be modified to allow setting up API/Agile API details and custom certs
        options = {"server": self.server}
        # Connect to Jira
        jira = None
        if self.basic_auth is not None:
            jira = JIRA(options, basic_auth=self.basic_auth)
        else:
            jira = JIRA(options, token_auth=self.token_auth)

        jira_issues = jira.search_issues(self.jql, maxResults=False)
        critical_issues = []
        for issue in jira_issues:
            logging.debug(issue)
            logging.debug(
                "Found issue opened: {}, {}: {}".format(
                    str(issue.fields.created), issue.key, issue.fields.summary
                )
            )
            # Create the JiraFailureMetric
            created_ts = self.convert_timestamp(issue.fields.created)
            resolution_ts = None
            if issue.fields.resolutiondate:
                logging.debug(
                    "Found issue close: {}, {}: {}".format(
                        str(issue.fields.resolutiondate),
                        issue.key,
                        issue.fields.summary,
                    )
                )
                resolution_ts = self.convert_timestamp(issue.fields.resolutiondate)
            tracker_issue = TrackerIssue(
                issue.key, created_ts, resolution_ts, self.get_app_name(issue)
            )
            critical_issues.append(tracker_issue)

        return critical_issues

    def convert_timestamp(self, date_time):
        """Convert a Jira datetime with TZ to UTC"""
        # The time retunred by Jira has a TZ, so convert to UTC
        utc = datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%S.%f%z").astimezone(
            pytz.utc
        )
        # Change the datetime to a string
        utc_string = utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        # convert to timestamp
        return pelorus.convert_date_time_to_timestamp(utc_string)

    def get_app_name(self, issue):
        app_label = pelorus.get_app_label()
        for label in issue.fields.labels:
            if label.startswith("%s=" % app_label):
                return label.replace("%s=" % app_label, "")
        return "unknown"
