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

import time
import logging
import logging.handlers

import json
import requests
import git
import psycopg

import time
import errno
import datetime
import argparse
import configparser
import subprocess
import shutil

# PEP 396 -- Module Version Numbers https://www.python.org/dev/peps/pep-0396/
__version__     = "0.3.0 (2021-08-20)"
__authors__     = "Tuisku Polvinen <tumipo@utu.fi>, Jani Tammi <jasata@utu.fi>"
VERSION         = __version__
HEADER          = f"""
=============================================================================
University of Turku, Faculty of Technology, Department of Computing
Hubbot version {__version__} - The GitHub repository retriever
(c) 2018-2021 {__authors__}
"""

SCRIPTNAME  = os.path.basename(__file__)
LOGLEVEL    = logging.INFO  # logging.[DEBUG|INFO|WARNING|ERROR|CRITICAL]
CONFIG_FILE = "app.conf"

def read_config_file(cfgfile: str):
    """Reads (with ConfigParser()) '[Application]' and creates global variables. Argument 'cfgfile' has to be a filename only (not path + file) and the file must exist in the same directory as this script."""
    cfgfile = os.path.join(
        os.path.split(os.path.realpath(__file__))[0],
        cfgfile
    )
    if not os.path.exists(cfgfile):
        raise FileNotFoundError(f"Configuration file '{cfgfile}' not found!")
    import configparser
    cfg = configparser.ConfigParser()
    cfg.optionxform = lambda option: option # preserve case
    cfg.read(cfgfile)
    for k, v in cfg.items('Application'):
        globals()[k] = v

class Database():
    def __init__(self, cstring: str):
        self.cstring = cstring

    def get_passed_deadlines(self):
        sql = """
        SELECT      * 
        FROM        assignment 
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
        FROM        enrollee
        WHERE       course_id=%(course_id)s 
        AND         status='active'
        AND         github_account IS NOT NULL
        AND         uid NOT IN (
                    SELECT uid
                    FROM submission
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
        FROM    assignment 
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
        with psycopg.connect(self.cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM enrollee WHERE course_id=%s AND uid=%s", (course_id, uid)
                )
            return dict(zip([key[0] for key in cur.description], cur.fetchone()))

    def register_submission(self, student:dict, assignment:dict):
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

        with psycopg.connect(self.cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        assignment['assignment_id'],
                        assignment['course_id'],
                        student['uid'],
                        'submission content',
                        datetime.datetime.now(),
                        'draft'
                    )
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
    try:
        read_config_file(CONFIG_FILE)
    except Exception as ex:
        print(f"Error reading site configuration '{CONFIG_FILE}'")
        print(str(ex))
        os._exit(-1)

    dbname = DB_NAME
    dbuser = DB_USER
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

        clonedir = SUBMISSION_DIRECTORY
        tgt = os.path.join(
            clonedir, 
            course_id, 
            uid, 
            assignment['assignment_id']            
            )

        if not os.path.exists(tgt):
            os.makedirs(tgt)

        fetchdate = datetime.datetime.now().strftime('%Y-%m-%d')
        fetchfile = f'{tgt}/{fetchdate}.txt'

        #
        # Create a session object with the user creds in-built
        #
        token = GH_TOKEN
        user = GH_USER
        gh_session = requests.Session()
        gh_session.auth = (user, token)

        #
        # Fetch repository contents list through API call
        # Note: if repository is not found (does not exist or bot user is not collaborator), call returns only a 'Not found' message
        # log fetch in {date}.log
        try:
            src = f"https://{token}:x-oauth-basic@github.com/{student['github_account']}/{student['github_repository']}.git"
            repo_contents = json.loads(gh_session.get(f"https://api.github.com/repos/{student['github_account']}/{student['github_repository']}/contents/").text)
            if 'message' in repo_contents:
                if repo_contents['message'] == 'Not Found':
                    status = f"Student {student['uid']}: Github user ({student['github_account']}"
                    with open(fetchfile, 'a') as log_fetch:
                        log_fetch.write(status)
                    log.info(status)
                    os._exit(-1)
        except Exception as e:
            log.exception(str(e))
            os._exit(-1)
        
        #
        # Clone only if required folder is found from repo
        #
        filenames = [file['name'] for file in repo_contents]
        if assignment['assignment_id'] not in filenames:
            status = f"Required folder ({assignment['assignment_id']}) not found in student repository"
            log.info(status)
            with open(fetchfile, 'a') as log_fetch:
                log_fetch.write(status)
            os._exit(-1)

        #
        # Fetch should happen once in a day - if path  already exists, something is wrong.
        # For ease of testing, the old repo is now removed but this could be changed later.
        #
        submission_repo = os.path.join(tgt, fetchdate)
        if os.path.exists(submission_repo):
            print("Submission path already exists and will be overwritten")
            shutil.rmtree(submission_repo)

        try: 
            git.Git(tgt).clone(src, fetchdate)
            db.register_submission(student, assignment)
            # create symbolic link to evaluator home folder
            # os.symlink(f"{tgt}/{fetchdate}", dst)
            status = "fetch successful"
            with open(fetchfile, 'a') as log_fetch:
                log_fetch.write(status)
        except Exception as e:
            with open(fetchfile, 'a') as log_fetch:
                log_fetch.write(str(e))
            log.exception(str(e))

    else:
        errors = []
        try:
            log.info("Running dispatcher")

            # Using local authentication -- password is never used
            db = Database(f"dbname={dbname} user={dbuser}")
            assignments = db.get_passed_deadlines()
            filtered_students = []

            for assignment in assignments:
                if (datetime.datetime.now() - assignment['deadline']).days < 5:
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
            for row in errors:
                print(
                    f"==[{row['id']}]==========================\n{row['error']}"
                )

        except Exception as ex:
            log.exception(f"Script execution error!", exec_info = False)
            os._exit(-1)

    elapsed = time.time() - script_start_time
    log.info(f"Execution took {elapsed} seconds.")

