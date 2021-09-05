#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Tuisku Polvinen <tumipo@utu.fi>
#
# hubreg.py - GitHub registration and collaborator invitation handler
#   2021-08-23  Initial version.
#   2021-08-30  (JTa) Now uses schooner package.
#   2021-09-05  (JTa) Chanced Git registration call from PendingGitHubRegistrations
#               into GitRegistration.register_repository()
#
# 
# PROCESS 
# 
#   1)  Student creates GitHub account, preferrably named as UTU ID. 
#   2)  Student creates a repository 'DTE20068-3002' and makes it private. 
#   3)  Student invites 'dtek0068@github.com' to be a collaborator. 
#   4)  Student registers the GitHub account at 
#       https://schooner.utu.fi/register.html
#       Page creates submission in 'draft' state (content = account name). 
#   5)  Background task 'hubreg.py' runs every minute and looks for 'draft' 
#       submissions for 'handler' = 'HUBREG' (and for which the assignment 
#       deadline has not passed). Content will have the student's GitHub
#       account name, as mentioned above.
#       Once found, it looks for a pending invitation from recorded GitHub 
#       account name. If found, accepts invite, updates enrollee.github and 
#       sets submission.state = 'accepted'. 
#   6)  An email is sent to confirm successful assignment completion. 
#   7)  [OPTIONAL] An issue is created to student's repository, with content 
#       that explains how exercises are handled. 
 
#from operator import sub
import os
import sys
import time
import logging
import logging.handlers 
 
import psycopg
import requests
from requests.api import patch 

# Add parent directory to the search path
# But not as the zero index... because it could be important for 3rd party
# code that may rely on sys.path documentation conformance:
#
#       As initialized upon program startup, the first item of this list,
#       path[0], is the directory containing the script that was used to
#       invoke the Python interpreter.
#
sys.path.insert(
    1,
    os.path.normpath(
        os.path.join(
            os.path.dirname(
                os.path.realpath(
                    os.path.join(
                        os.getcwd(),
                        os.path.expanduser(__file__)
                    )
                )
            ),
            ".." # "Parent", relative to this script
        )
    )
)

from schooner.util      import AppConfig
from schooner.util      import Lockfile
from schooner.util      import LogDBHandler
from schooner.api       import GitRegistration
from schooner.api       import PendingGitHubRegistrations
 
SCRIPTNAME  = os.path.basename(__file__) 
CONFIG_FILE = "app.conf"


if __name__ == '__main__': 
 
    script_start_time = time.time()
    cfg = AppConfig(CONFIG_FILE, "hubreg")

    #
    # Set up logging
    #
    log = logging.getLogger(SCRIPTNAME)
    log.setLevel(cfg.loglevel)
    if os.isatty(sys.stdin.fileno()):
        # Executed from terminal
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter('[%(levelname)s] %(message)s')
        )
        log.addHandler(handler)
    else:
        # Executed from crontab
        handler = logging.handlers.SysLogHandler(address = '/dev/log')
        handler.setFormatter(
            logging.Formatter('%(name)s: [%(levelname)s] %(message)s')
        )
        log.addHandler(handler)
    # DB Handler
    handler = LogDBHandler(cfg.database, level = cfg.loglevel)
    log.addHandler(handler)


    # Script/execution level try-except
    try:
        with    Lockfile(cfg.lockfile), \
                psycopg.connect(f"dbname={cfg.database}").cursor() as cursor:

            pendingregs = PendingGitHubRegistrations(cursor)
            for reg in pendingregs:
                # Registration level try-except
                try: 
                    gh_session = requests.Session()
                    gh_session.auth = (reg['course_account'], reg['course_accesstoken'])

                    headers = {'Authorization': 'token ' + reg['course_accesstoken']}
                    url = 'https://api.github.com/user/repository_invitations'
                    invitations = requests.get(url, headers=headers).json()

                    reg.update(invite_matched = False)
                    utuid = reg['uid']
                    github_account = reg['student_account']
                    course_code = reg['course_code']
                    repo_url = f"https://api.github.com/repos/{reg['student_account']}/{reg['course_code']}"

                    for invite in invitations:
                        repo = invite.get('repository')
                        if repo['owner']['login'] == github_account: # and repo['name'] == course_code:
                            reg['student_repository'] = repo['name']
                            reg['invite_matched'] = True

                            # Accept invite
                            requests.patch(
                                f"{url}/{invite.get('id')}",
                                data={}, 
                                headers=headers
                            )

                            # Check that the repository is now accessible
                            if requests.get(repo_url, headers=headers).status_code == 200:
                                # Register AND send notification
                                GitRegistration.register_repository(
                                    cursor,
                                    reg['submission_id'],
                                    reg['student_repository']
                                )

                    # TODO: handle possible cases where an invitation has
                    #       already been accepted in github 
                    if not reg['invite_matched']:
                        if requests.get(repo_url, headers=headers).status_code == 200:
                            log.warning(
                                "Repository found but invite already accepted in GitHub"
                            )
                        else:
                            log.debug(
                                f"GitHub invitation matching {reg['student_account']} not found"
                            )

                except Exception as e:
                    log.exception(f"Script execution error! {str(e)}")
                    cursor.connection.rollback()
                else:
                    cursor.connection.commit()

    except Lockfile.AlreadyRunning as e:
        log.warning(
            "Exiting. Another process is still executing (lockfile exists and is locked)"
        )
    except Exception as e:
        log.exception(str(e))

    #
    # All pending registrations handled / attempted
    #
    elapsed = time.time() - script_start_time 
    log.info(f"Execution took {elapsed} seconds.")




# EOF
