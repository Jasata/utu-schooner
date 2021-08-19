#!/bin/env python3
# Placeholder

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

import pwd
import time
import logging
import logging.handlers

import json
import requests
import git
import csv
import psycopg
from dotenv import load_dotenv

import time
import errno
import datetime
import argparse
import configparser
import subprocess
import shutil

# PEP 396 -- Module Version Numbers https://www.python.org/dev/peps/pep-0396/
__version__     = "0.2.2 (2021-08-17)"
__authors__     = "Jani Tammi <jasata@utu.fi>"
VERSION         = __version__
HEADER          = f"""
=============================================================================
University of Turku, Faculty of Technology, Department of Computing
Hubbot - The GitHub repository retriever
Version {__version__}, (c) 2018-2021 {__authors__}
"""

SCRIPTNAME  = os.path.basename(__file__)
LOGLEVEL    = logging.INFO  # logging.[DEBUG|INFO|WARNING|ERROR|CRITICAL]

class Database():
    def __init__(self, cstring: str):
        self.cstring = cstring

    def get_passed_deadlines(self):
        with psycopg.connect(cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM assignment WHERE handler=%s AND deadline<%s", ('HUBBOT', datetime.datetime.now())
                )
            return [dict(zip([key[0] for key in cur.description], row)) for row in cur]

    def get_course_students(self, course_id):
        with psycopg.connect(cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM enrollee WHERE course_id=%s AND status=%s", (course_id, 'active')
                )
            return [dict(zip([key[0] for key in cur.description], row)) for row in cur]

    def submission_exists(self, assignment_id, course_id, uid):
        with psycopg.connect(cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM submission WHERE assignment_id=%s AND course_id=%s AND uid=%s", (assignment_id, course_id, uid)
                )
            if cur.rowcount == 0:
                return False
            else:
                return True

    def filter_students(self, assignment):
        enrollees = self.get_course_students(assignment['course_id'])
        return [student for student in enrollees if not self.submission_exists(
            assignment['assignment_id'], assignment['course_id'], student['uid']
            ) and  not student['github_account'] == 'NULL']

    def get_assignment(self, assignment_id, course_id):
        with psycopg.connect(cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM assignment WHERE assignment_id=%s AND course_id=%s", (assignment_id, course_id)
                )
            return [dict(zip([key[0] for key in cur.description], row)) for row in cur][0]
    
    def get_enrollee(self, course_id, uid):
        with psycopg.connect(cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM enrollee WHERE course_id=%s AND uid=%s", (course_id, uid)
                )
            return [dict(zip([key[0] for key in cur.description], row)) for row in cur][0]

    def register_submission(self, student, assignment, timestamp):
        # Resolve penalty
        #
        # NOTE: Ask Jani how to handle penalty (esp. None)
        #  - should there be a default or is None logged to submission as well
        days_late = (timestamp - assignment['deadline']).days
        assignment_penalty = assignment['latepenalty']
        if assignment_penalty is None:
            assignment_penalty = 1
        penalty = days_late * assignment_penalty

        sql = """
        INSERT INTO submission (
            assignment_id, 
            course_id, 
            uid,
            content,
            created, 
            state
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        with psycopg.connect(cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        assignment['assignment_id'],
                        assignment['course_id'],
                        student['uid'],
                        student['github_account'],
                        timestamp,
                        'draft'
                    )
                )
        



                

if __name__ == '__main__':

    script_start_time = time.time()

    os.chdir(os.path.dirname(os.path.realpath(__file__)))

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
    log.setLevel(LOGLEVEL)
    handler = logging.handlers.SysLogHandler(address = '/dev/log')
    handler.setFormatter(
        logging.Formatter('%(name)s: [%(levelname)s] %(message)s')
    )
    log.addHandler(handler)

    # WORK HERE
    dbname = 'schooner'
    dbuser = 'schooner'
    dbpass = False

    args, _ = argparser.parse_known_args()

    if args.clone:
        course_id       = args.clone[0]
        assignment_id   = args.clone[1]
        uid             = args.clone[2]            
        log.info(f"Cloning {assignment_id} from repository {course_id} of student {uid}")
        cstring = f"dbname={dbname} user={dbuser}"
        if dbpass:
            cstring += f" password={dbpass}"

        db = Database(cstring)
        assignment = db.get_assignment(assignment_id, course_id)
        student = db.get_enrollee(course_id, uid)

        clonedir = os.path.join('/srv/schooner/submissions')
        tgt = os.path.join(clonedir, f"{datetime.datetime.now().strftime('%Y-%m-%d')}_{assignment['assignment_id']}")
        if not os.path.exists(tgt):
            os.makedirs(tgt)

        #
        # Create a session object with the user creds in-built
        #
        load_dotenv('.env')
        token = os.environ.get("GH_TOKEN")
        user = os.environ.get("GH_USER")
        gh_session = requests.Session()
        gh_session.auth = (user, token)

        #
        # Fetch repository contents list through API call
        # Note: if repository is not found (does not exist or bot user is not collaborator), call returns only a 'Not found' message
        #
        try:
            src = f"https://{token}:x-oauth-basic@github.com/{student['github_account']}/DTE20068.git"
            repo_contents = json.loads(gh_session.get(f"https://api.github.com/repos/{student['github_account']}/DTE20068/contents/").text)
            if 'message' in repo_contents:
                if repo_contents['message'] == 'Not Found':
                    exit(f"Github user ({student['github_account']}) or repository not found")
        except Exception as e:
            exit(str(e))
        
        #
        # Clone only if required folder is found from repo
        #
        filenames = [file['name'] for file in repo_contents]
        print(filenames)
        if assignment['assignment_id'] not in filenames:
            exit(f"Required folder ({assignment['assignment_id']}) not found in student repository")

        #
        # Fetch should happen once in a day - if path  already exists, something is wrong.
        # For ease of testing, the old repo is now removed but this should be changed later.
        #
        submission_repo = os.path.join(tgt, student['uid'])
        if os.path.exists(submission_repo):
            print("Submission path already exists and will be overwritten")
            shutil.rmtree(submission_repo)
            #exit("Submission path for student already exists")

        try: 
            git.Git(tgt).clone(src, student['uid'])
            db.register_submission(student, assignment, datetime.datetime.now())
        except Exception as e:
            exit(str(e))

    else:
        errors = []
        try:
            log.info("Testing database connection")
            cstring = f"dbname={dbname} user={dbuser}"
            if dbpass:
                cstring += f" password={dbpass}"

            db = Database(cstring)
            assignments = db.get_passed_deadlines()
            filtered_students = []

            for assignment in assignments:
                if (datetime.datetime.now() - assignment['deadline']).days < 5:
                    filtered_students = db.filter_students(assignment)

                for student in filtered_students:
                    try:
                        cloner = subprocess.Popen(
                            [
                            'python',
                            'hubbot.py', 
                            '--clone', 
                            assignment['course_id'], 
                            assignment['assignment_id'],
                            student['uid']
                            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True
                        )
                        for line in cloner.stdout:
                            errors.append({
                                'id': student['uid'],
                                'error': str(line)
                            })
                    except Exception as e:
                        errors.append({
                            'id': student['uid'],
                            'error': str(e)
                        })
            for row in errors:
                print(
                    f"==[{row['id']}]==========================\n{row['error']}"
                )

        except Exception as ex:
            log.exception(f"Script execution error!", exec_info = False)
            os._exit(-1)

    elapsed = time.time() - script_start_time
    log.info(f"Execution took {elapsed} seconds.")

