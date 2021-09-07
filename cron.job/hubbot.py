#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Tuisku Polvinen <tumipo@utu.fi>
#
# hubbot.py - GitHub exercise retriever
#   2021-08-13  Initial version.
#   2021-08-29  (JTa) Refactoring.
#   2021-08-30  (JTa) Now uses schooner package.
#  
import os
import sys
import platform


#
# REQUIRE Python 3.7 or newer
#
pyreq = (3,7)
if sys.version_info < pyreq:
    print(
        "You need Python {} or newer! ".format(".".join(map(str, pyreq))),
        end = ""
    )
    print(
        "You have Python ver.{} on {} {}".format(
            platform.python_version(),
            platform.system(),
            platform.release()
        )
    )
    os._exit(1)

import logging
import logging.handlers

import json
import requests
import git
import psycopg

from datetime import timedelta
from datetime import datetime
from datetime import date
import argparse
import subprocess
import shutil


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

from schooner.util          import AppConfig
from schooner.util          import Lockfile
from schooner.util          import LogDBHandler
from schooner.util          import Timer
from schooner.db.core       import Course
from schooner.db.core       import Enrollee
from schooner.db.core       import Assignment
from schooner.api           import GitAssignments
from schooner.db.email      import Template
from schooner.jtd           import JTDAssignment

# PEP 396 -- Module Version Numbers https://www.python.org/dev/peps/pep-0396/
__version__     = "0.5.0 (2021-09-07)"
__authors__     = "Tuisku Polvinen <tumipo@utu.fi>, Jani Tammi <jasata@utu.fi>"
VERSION         = __version__
HEADER          = f"""
=============================================================================
University of Turku, Faculty of Technology, Department of Computing
Hubbot version {__version__} - The GitHub repository retriever
(c) 2018-2021 {__authors__}
"""

SCRIPTNAME  = os.path.basename(__file__)
CONFIG_FILE = "app.conf"

def processer(
        cmd: str,
        shell: bool = False,
        stdout = subprocess.PIPE,
        stderr = subprocess.DEVNULL    
        ):
        """Call .subprocess("ls", stdout = subprocess.PIPE), if you want output. Otherwise the output is sent to /dev/null."""
        try:
            if not shell:
                # Set empty double-quotes as empty list item            
                # Required for commands like; ssh-keygen ... -N ""           
                cmd = ['' if i == '""' or i == "''" else i for i in cmd.split(" ")]
            prc = subprocess.run(
                cmd,
                shell  = shell,
                stdout = stdout,
                stderr = stderr        
            )
            # Return output (return code, stdout, stderr)
            return (
                prc.returncode,
                prc.stdout.decode("utf-8") if stdout == subprocess.PIPE else None,
                prc.stderr.decode("utf-8") if stderr == subprocess.PIPE else None
            )
        except Exception as e:
            return (
                -1,
                str(e),
                ""
            )

def log_fetch(fetchfile, message):
    with open(fetchfile, 'a') as log_fetch:
        log_fetch.write(f"{message}\n")



class GitRepositoryNotFound(Exception):
    pass

class GitFolderNotFound(Exception):
    pass


###############################################################################
#
# MAIN
#
###############################################################################
if __name__ == '__main__':

    runtime = Timer()

    #
    # Cron job speciality - change to script's directory
    #
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    cfg = AppConfig(CONFIG_FILE, 'hubbot')
    # TEST - do we need to do this?
    #os.chdir(os.path.dirname(os.path.realpath(__file__)))

    #
    # Commandline arguments
    #
    argparser = argparse.ArgumentParser(
        description     = HEADER,
        formatter_class = argparse.RawTextHelpFormatter,
    )

    argparser.add_argument(
        '--clone',
        help    = "Clone repository from one student",
        dest    = "clone",
        metavar = ("COURSE_ID", "ASSIGNMENT_ID", "STUDENT NUMBER"),
        nargs   = 3,
        type    = str
    )

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

    # Eitherway, DB log handler is always added
    handler = LogDBHandler(cfg.database, level = cfg.loglevel)
    log.addHandler(handler)


    args, _ = argparser.parse_known_args()

    #
    # Attempt submission retrieval
    #
    if args.clone:
        course_id       = args.clone[0]
        assignment_id   = args.clone[1]
        uid             = args.clone[2]            
        log.info(f"Cloning {assignment_id} from repository {course_id} of student {uid}")

        cstring = f"dbname={cfg.database} user={cfg.database}"

        with psycopg.connect(cstring) as conn:
            with conn.cursor() as cursor:
                assignment  = Assignment(cursor, course_id, assignment_id)
                student     = Enrollee(cursor, course_id, uid)
                course      = Course(cursor, course_id)

        tgt = os.path.join(
            cfg.submissions_directory, 
            course_id, 
            uid, 
            assignment['assignment_id']            
            )

        if not os.path.exists(tgt):
            os.makedirs(tgt)

        fetchdate = datetime.now().strftime(cfg.dateformat)
        fetchfile = f'{tgt}/{fetchdate}.txt'

        #
        # Create a session object with the user creds in-built
        #
        gh_session      = requests.Session()
        gh_session.auth = (course['github_account'], course['github_accesstoken'])
        
        student_repository = f"{student['github_account']}/{student['github_repository']}"
        src = f"https://{course['github_accesstoken']}:x-oauth-basic@github.com/{student_repository}.git"

        with open(fetchfile, 'a') as log_fetch:
            message = f"{datetime.now()}\nTrying to fetch from: https://github.com/{student_repository}.git\n"
            log_fetch.write(message)


        try:
            #
            # Handle case: repository doesn't exist or cannot be found
            #
            repository_content_url = f"https://api.github.com/repos/{student_repository}/contents/"
            if gh_session.get(repository_content_url).status_code == 404:
                raise GitRepositoryNotFound(
                    f"Student {student['uid']}: Github repository ({student_repository} not found\n"
                ) 
            log.debug("REPO EXISTS")

            #
            # Clone only if required folder is found from repo
            #
            repo_contents   = json.loads(gh_session.get(repository_content_url).text)
            filenames       = [file['name'] for file in repo_contents]
            if assignment['assignment_id'] not in filenames:
                log.debug("GIT FOLDER NOT FOUND!")
                raise GitFolderNotFound(
                    f"Required folder ({assignment['assignment_id']}) not found in student repository\n"
                )
            log.debug(f"FOLDER {assignment['assignment_id']} FOUND IN {student['github_account']}/{student['github_repository']}")

            #
            # Fetch should happen once in a day - if path  already exists, something is wrong.
            # For ease of testing, the old repo is now removed but this could be changed later.
            #
            submission_repo = os.path.join(tgt, fetchdate)
            if os.path.exists(submission_repo):
                with open(fetchfile, 'a') as log_fetch:
                    log_fetch.write("Submission path already exists and will be overwritten\n")
                shutil.rmtree(submission_repo)

            #
            # Clone and send mail if successful.
            #
            git.Git(tgt).clone(src, fetchdate)
            with psycopg.connect(cstring) as conn:
                with conn.cursor() as cursor:
                    # This call also sends a success message.
                    assignment.register_as_submission(cursor, student, assignment)
            # Successfully fetched and registered - create 'accepted' symlink
            if not os.path.exists(f"{tgt}/accepted"):
                os.symlink(f"{tgt}/{fetchdate}", f"{tgt}/accepted")
            log.debug("GIT CLONE DONE")


        except (GitRepositoryNotFound, GitFolderNotFound) as e:
            log.info(f"GIT EXCEPTION {e}")
            with open(fetchfile, 'a') as log_fetch:
                log_fetch.write(f"{str(e)}\nEnd of fetch.\n")
            sys.stdout.write(str(e))
            with psycopg.connect(cstring).cursor() as cursor:
                try:
                    Assignment.send_retrieval_failure_mail(
                        cursor,
                        assignment,
                        student['uid'],
                        str(e)
                    )
                    log.debug(
                        f"Template parsed and queued for {student['uid']}"
                    )
                except Template.NotSent as e:
                    log.warning(str(e))
                except Exception as e:
                    log.exception(f"Automated message NOT sent! {str(e)}")
                finally:
                    cursor.connection.commit()
                    os._exit(1)
        except Exception as e:
            log.exception(str(e))
            with open(fetchfile, 'a') as log_fetch:
                log_fetch.write(f"{str(e)}\nEnd of fetch.\n")
            sys.stdout.write(str(e))
            try:
                Assignment.send_retrieval_failure_mail(
                    psycopg.connect(cstring).cursor(),
                    assignment,
                    student['uid'],
                    str(e)
                )
                log.debug(
                    f"Template parsed and queued for {student['uid']}"
                )
            except Template.NotSent as e:
                log.debug(f"Automated message not sent: {str(e)}")
            except Exception as e:
                log.exception(f"Automated message NOT sent! {str(e)}")
            finally:
                os._exit(-1)

        else:
            with open(fetchfile, 'a') as log_fetch:
                log_fetch.write(f"Fetch successful\nEnd of fetch.\n")
            sys.stdout.write("Fetch successful")

    #
    # Start discrete fetches
    #
    else:
        errors  = []
        fetches = []
        try:
            with Lockfile(cfg.lockfile):
                log.info("Running dispatcher")

                # Using local authentication -- password is never used
                cstring = f"dbname={cfg.database} user={cfg.database}"
   
                with psycopg.connect(cstring).cursor() as cursor:               
                    assignments    = GitAssignments(cursor)

                    for assignment in assignments:
                        for submission in assignments.submissions(**assignment):
                            draft       = submission['draft_submission_id']
                            accepted    = submission['accepted_submission_id']
                            can_retry   = not (assignment['retries'] == None) or (submission['n_submissions'] < assignment['retries'] + 1)
                            has_github  = submission['github_account']

                            if not accepted and not draft and can_retry and has_github:
                                try:
                                    fetchstring = f"{assignment['course_id']} {assignment['assignment_id']} {submission['uid']}"
                                    clone = processer(f"python hubbot.py --clone {fetchstring}")
                                    fetches.append(clone)
                                except Exception as e:
                                    fetches.append((-1, None, str(e)))
                                    log.error(str(e))
                                    
        except Lockfile.AlreadyRunning as e:
            log.error("Execution cancelled! Lockfile found (another process still running).")
        except Exception as ex:
            log.exception(f"Script execution error!", exec_info = False)
            os._exit(-1)

        # Report success and error counts
        success     = 0
        not_found   = 0
        errors      = 0
        for fetch in fetches:
            if fetch[0] == 0:
                success +=1
            elif fetch[0] == 1:
                not_found +=1
            else:
                errors += 1
        log.info(f"Of {len(fetches)} fetches: {success} successful fetches, {not_found} not found, {errors} errors in {runtime.report()}.")


# EOF
