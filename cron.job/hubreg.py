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
#   2021-09-18  (JTa) Increased the indent of a block at line 166.
#   2021-09-21  (JTa) No log output @INFO, unless performs task(s).
#
# 
# PROCESS 
# 
#   1)  Student creates GitHub account, preferrably named as UTU ID. 
#   2)  Student creates a repository 'DTEK0068' and makes it private. 
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
from schooner.util      import Timer
from schooner.util      import Counter
from schooner.api       import GitRegistration
from schooner.api       import PendingGitHubRegistrations
 
SCRIPTNAME  = os.path.basename(__file__) 
CONFIG_FILE = "app.conf"


if __name__ == '__main__': 
 
    runtime = Timer()

    #
    # Cron job speciality - change to script's directory
    #
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    cfg = AppConfig(CONFIG_FILE, "hubreg")

    #
    # Set up logging
    #
    root = logging.getLogger()
    root.setLevel(cfg.loglevel)
    if os.isatty(sys.stdin.fileno()):
        # Executed from terminal
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter('[%(levelname)s] %(message)s')
        )
        root.addHandler(handler)
    else:
        # Executed from crontab
        handler = logging.handlers.SysLogHandler(address = '/dev/log')
        handler.setFormatter(
            logging.Formatter('%(name)s: [%(levelname)s] %(message)s')
        )
        root.addHandler(handler)
    # DB Handler
    handler = LogDBHandler(cfg.database, level = cfg.loglevel)
    root.addHandler(handler)
    # Log instance with useful name
    log = logging.getLogger(SCRIPTNAME)


    # Script/execution level try-except
    try:
        with    Lockfile(cfg.lockfile), \
                psycopg.connect(f"dbname={cfg.database}").cursor() as cursor:

            #
            # Count successes / failures
            #
            cntr = Counter()

            pendingregs = PendingGitHubRegistrations(cursor)
            for reg in pendingregs:
                # Registration level try-except
                try: 
                    if not reg['course_accesstoken']:
                        raise Exception("GitHub access token is missing.")
                    gh_session = requests.Session()
                    gh_session.auth = (reg['course_account'], reg['course_accesstoken'])

                    headers = {'Authorization': 'token ' + reg['course_accesstoken']}
                    url = 'https://api.github.com/user/repository_invitations'
                    invitations = requests.get(url, headers=headers).json()

                    reg.update(invite_matched = False)
                    utuid = reg['uid']
                    github_account = reg['student_account']
                    course_code = reg['course_code']
                    repo_url = ''

                    for invite in invitations:

                        log.debug(f"Invite from: {invite['repository']['owner']['login']}")
                        repo = invite.get('repository')
                        repo_url = f"https://api.github.com/repos/{reg['student_account']}/{repo['name']}"
                        if repo['owner']['login'] == github_account:
                            reg['student_repository'] = repo['name']
                            reg['invite_matched'] = True

                            # Accept invite
                            log.debug("ACCEPTING INVITE")
                            requests.patch(
                                f"{url}/{invite.get('id')}",
                                data={}, 
                                headers=headers
                            )

                            # Check that the repository is now accessible
                            status_code = requests.get(
                                repo_url,
                                headers = headers
                            ).status_code
                            if status_code == 200:
                                # Register AND send notification
                                log.debug(
                                    "Registering '{}' for enrollee ('{}', '{}')".format(
                                        reg['student_repository'],
                                        reg['course_id'],
                                        reg['uid']
                                    )
                                )
                                GitRegistration.register_repository(
                                    cursor,
                                    reg['submission_id'],
                                    reg['student_repository']
                                )
                                cntr.add(Counter.OK)
                            else:
                                # status code not 200
                                log.debug(
                                    "Repository query '{}' for enrollee ('{}', '{}') returned {}".format(
                                        reg['student_repository'],
                                        reg['course_id'],
                                        reg['uid'],
                                        status_code
                                    )
                                )

                        # TODO: handle possible cases where an invitation has
                        #       already been accepted in github 
                        if not reg['invite_matched']:
                            if requests.get(repo_url, headers=headers).status_code == 200:
                                log.warning(
                                    "Repository found but invite already accepted in GitHub"
                                )
                                cntr.add(Counter.OK)
                            else:
                                log.debug(
                                    f"GitHub invitation matching {reg['student_account']} not found"
                                )
                                cntr.add(Counter.ERR)

                except Exception as e:
                    log.exception(f"Script execution error! {str(e)}")
                    cursor.connection.rollback()
                    cntr.add(Counter.ERR)
                else:
                    cursor.connection.commit()

    except Lockfile.AlreadyRunning as e:
        log.warning(
            "Exiting. Another process is still executing (lockfile exists and is locked)"
        )
        os._exit(1)
    except Exception as e:
        log.exception(str(e))
        os._exit(-1)

    #
    # All pending registrations handled / attempted
    #
    if cntr.total or log.isEnabledFor(logging.DEBUG):
        log.info(
            "{} successful registrations, {} still pending. Execution took {}.".format(
                cntr.successes,
                cntr.errors,
                runtime.report()
            )
        )




# EOF
