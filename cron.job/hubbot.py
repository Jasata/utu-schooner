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

from util import AppConfig
from util import Lockfile
from util import LogDBHandler
from util import Timer

from schooner.core import Course
from schooner.core import Enrollee
from schooner.email import Template

# PEP 396 -- Module Version Numbers https://www.python.org/dev/peps/pep-0396/
__version__     = "0.4.0 (2021-08-29)"
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


class Database():
    def __init__(self, cstring: str):
        self.cstring = cstring

    def get_passed_deadlines(self):
        sql = """
        SELECT      * 
        FROM        core.assignment 
        WHERE       handler = %s
        AND         deadline < NOW()
        """
        with psycopg.connect(self.cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    ('HUBBOT',)
                )
            return [dict(zip([key[0] for key in cur.description], row)) for row in cur]

    def get_submissionless_students(self, assignment:dict) -> list:
        sql = """
        SELECT      * 
        FROM        core.enrollee
        WHERE       course_id=%(course_id)s 
        AND         status='active'
        AND         github_account IS NOT NULL
        AND         uid NOT IN (
                    SELECT uid
                    FROM core.submission
                    WHERE assignment_id=%(assignment_id)s
                    AND course_id=%(course_id)s
                    )
        """

        with psycopg.connect(self.cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql, 
                    assignment
                )
            return [dict(zip([key[0] for key in cur.description], row)) for row in cur]

    def get_assignment(self, assignment_id, course_id):
        sql = """
        SELECT  * 
        FROM    core.assignment 
        WHERE   assignment_id=%s 
        AND     course_id=%s
        """
        with psycopg.connect(self.cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (assignment_id, course_id)
                )
            return dict(zip([key[0] for key in cur.description], cur.fetchone()))
    
    def get_enrollee(self, course_id, uid):
        sql = """
        SELECT  * 
        FROM    core.enrollee 
        WHERE   course_id=%s 
        AND     uid=%s
        """
        with psycopg.connect(self.cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql, (course_id, uid)
                )
            return dict(zip([key[0] for key in cur.description], cur.fetchone()))

    def register_submission(self, student:dict, assignment:dict):
        sql = """
        INSERT INTO core.submission (
            assignment_id, 
            course_id, 
            uid,
            content,
            submitted, 
            state
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        submission_date = datetime.combine(date.today() - timedelta(1), datetime.max.time())
        with psycopg.connect(self.cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        assignment['assignment_id'],
                        assignment['course_id'],
                        student['uid'],
                        'submission content',
                        submission_date,
                        'draft'
                    )
                )

    def mail_submission_status(self, submission:dict):
        with psycopg.connect(self.cstring).cursor() as cursor:
            course = Course(cursor, submission['course_id'])
            enrollee = Enrollee(cursor, submission['course_id'], submission['uid'])
            if enrollee['notifications'] == 'enabled':
                print(course, enrollee)
                template = Template(cursor, 'HUBREG')
                template.parse_and_queue(
                    submission['course_id'],
                    submission['uid'],
                    { 'course' : course, 'enrollee' : enrollee }
                )

def processer(
        cmd: str,
        shell: bool = False,
        stdout = subprocess.DEVNULL,
        stderr = subprocess.DEVNULL    
        ):
        """Call .subprocess("ls", stdout = subprocess.PIPE), if you want output. Otherwise the output is sent to /dev/null."""        
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
        # Non-zero return code indicates an error        
        if prc.returncode:
            raise ValueError(
                f"code: {prc.returncode}, command: '{cmd}'"            )
        # Return output (stdout, stderr)
        return (
            prc.stdout.decode("utf-8") if stdout == subprocess.PIPE else None,
            prc.stderr.decode("utf-8") if stderr == subprocess.PIPE else None        )

def log_fetch(fetchfile, message):
    with open(fetchfile, 'a') as log_fetch:
        log_fetch.write(f"{message}\n")



###############################################################################
#
# MAIN
#
###############################################################################
if __name__ == '__main__':

    runtime = Timer()
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
        help    = "Clone repository from a student",
        dest    = "clone",
        metavar = ("COURSE ID", "ASSIGNMENT ID", "STUDENT NUMBER"),
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
        cstring = f"dbname={cfg.dbname} user={cfg.dbuser}"

        db = Database(cstring)
        assignment = db.get_assignment(assignment_id, course_id)
        student = db.get_enrollee(course_id, uid)

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
        with psycopg.connect(cstring).cursor() as cursor:
            course = Course(cursor, course_id)
        gh_session = requests.Session()
        gh_session.auth = (course.github_account, course.github_accesstoken)
        
        student_repository = f"{student['github_account']}/{student['github_repository']}"
        src = f"https://{course.github_accesstoken}:x-oauth-basic@github.com/{student_repository}.git"

        log_fetch(fetchfile, f"{datetime.now()}\n Trying to fetch from: https://github.com/{student_repository}.git")

        #
        # Fetch repository contents list through API call
        # Note: if repository is not found (does not exist or bot user is not collaborator), call returns only a 'Not found' message
        # log fetch in {date}.txt

        repository_content_url = f"https://api.github.com/repos/{student_repository}/contents/"

        if gh_session.get(repository_content_url).status_code == 404:
            status = f"Student {student['uid']}: Github repository ({student_repository} not found"
            log_fetch(fetchfile, status)
            log.info(status)
            os._exit(-1)

        repo_contents = json.loads(gh_session.get(repository_content_url).text)
        
        #
        # Clone only if required folder is found from repo
        #
        filenames = [file['name'] for file in repo_contents]
        if assignment['assignment_id'] not in filenames:
            status = f"Required folder ({assignment['assignment_id']}) not found in student repository"
            log.info(status)
            log_fetch(fetchfile, status)
            os._exit(0)

        #
        # Fetch should happen once in a day - if path  already exists, something is wrong.
        # For ease of testing, the old repo is now removed but this could be changed later.
        #
        submission_repo = os.path.join(tgt, fetchdate)
        if os.path.exists(submission_repo):
            log_fetch(fetchfile, "Submission path already exists and will be overwritten")
            shutil.rmtree(submission_repo)

        try: 
            git.Git(tgt).clone(src, fetchdate)
            db.register_submission(student, assignment)
            if not os.path.exists(f"{tgt}/accepted"):
                os.symlink(f"{tgt}/{fetchdate}", f"{tgt}/accepted")
            log_fetch(fetchfile, "Fetch successful")
        except Exception as e:
            log_fetch(fetchfile, str(e))
            log.exception(str(e))


    #
    # Start discrete fetches
    #
    else:
        errors = []
        try:
            with Lockfile(cfg.lockfile):
                log.info("Running dispatcher")

                # Using local authentication -- password is never used
                db = Database(f"dbname={cfg.dbname} user={cfg.dbuser}")
                assignments = db.get_passed_deadlines()
                filtered_students = []

                # TODO: use deadline check from database instead of < 5 stuff
                for assignment in assignments:
                    if (date.today() - assignment['deadline']).days < 5:
                        filtered_students = db.get_submissionless_students(assignment)

                    for student in filtered_students:
                        try:
                            clone = processer(f"python hubbot.py --clone {assignment['course_id']} {assignment['assignment_id']} {student['uid']}")
                            if not clone[1] == None:
                                errors.append({
                                    'id': student['uid'],
                                    'error': str(clone[1] )
                                })
                        except Exception as e:
                            errors.append({
                                'id': student['uid'],
                                'error': str(e)
                            })

                # For manual testing
                # for row in errors:
                #    print(
                #        f"==[{row['id']}]==========================\n{row['error']}"
                #    )
        except Lockfile.AlreadyRunning as e:
            log.error("Execution cancelled! Lockfile found (another process still running).")
        except Exception as ex:
            log.exception(f"Script execution error!", exec_info = False)
            os._exit(-1)

    # TODO, report success and error counts
    log.info(f"N successful registrations, E errors in {runtime.report()}.")


# EOF
