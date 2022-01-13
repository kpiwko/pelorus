#!/usr/bin/python3
import logging
import os
import sys
import time

from collector_jira import JiraFailureCollector
from collector_servicenow import ServiceNowFailureCollector
from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY

import pelorus

REQUIRED_CONFIG = {
    "ServiceNow": ["USERNAME", "TOKEN", "SERVER"],
    "JiraBasicAuth": ["USERNAME", "TOKEN", "SERVER"],
    "JiraTokenAuth": ["TOKEN", "SERVER"],
}


class TrackerFactory:
    @staticmethod
    def getCollector(
        tracker_api,
        tracker_provider,
        username,
        token,
        jql,
        projects,
        types,
        priorities,
        age,
    ):
        if tracker_provider == "jira":
            return JiraFailureCollector(
                tracker_api, username, token, jql, projects, types, priorities, age
            )
        if tracker_provider == "servicenow":
            return ServiceNowFailureCollector(username, token, tracker_api)


if __name__ == "__main__":

    logging.info("===== Starting Failure Collector =====")
    if pelorus.missing_configs(REQUIRED_CONFIG):
        print("This program will exit.")
        sys.exit(1)

    username = os.environ.get("USERNAME")
    token = os.environ.get("TOKEN")
    tracker_api = os.environ.get("SERVER")
    tracker_provider = os.environ.get("PROVIDER", pelorus.DEFAULT_TRACKER)
    jql = os.environ.get("JQL")
    projects = os.environ.get("PROJECTS")
    types = os.environ.get("TYPES", pelorus.DEFAULT_JIRA_TYPES)
    priorities = os.environ.get("PRIORITIES", pelorus.DEFAULT_JIRA_PRIORITIES)
    age = os.environ.get("AGE")

    logging.info("Server: {}".format(tracker_api))
    start_http_server(8080)

    collector = TrackerFactory.getCollector(
        tracker_api,
        tracker_provider,
        username,
        token,
        jql,
        projects,
        types,
        priorities,
        age,
    )
    REGISTRY.register(collector)

    while True:
        time.sleep(1)
    logging.info("===== Exit Failure Collector =====")
