#!/bin/env python3 
# Placeholder 
# 
# PROCESS 
# 
#   1)  Student creates GitHub account, preferrably named as UTU ID. 
#   2)  Student creates a repository 'DTE20068-3002' and makes it private. 
#   3)  Student invites 'dte20068@github.com' to be a collaborator. 
#   4)  Student registers the GitHub account at 
#       https://dte20068.utu.fi/register-github-account 
#       Page creates submission in 'draft' state (content = account name). 
#   5)  Background task 'hubreg.py' runs every minute and looks for 'draft' 
#       submissions for 'handler' = 'HUBREG' (and for which the assignment 
#       deadline has not passed). Content  
#       Once found, it looks for a pending invitation from recorded GitHub 
#       account name. If found, accepts invite, updates enrollee.github and 
#       sets submission.state = 'accepted'. 
#   6)  An email is sent to confirm successful assignment completion. 
#   7)  [OPTIONAL] An issue is created to student's repository, with content 
#       that explains how exercises are handled. 
 
from operator import sub
import os 
import time
import datetime
import logging 
import logging.handlers 
 
import psycopg
import requests 
import json 

 
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
    """Each operation opens and closes the database for maximum concurrency support."""
    def __init__(self, cstring: str):
        self.cstring = cstring
    
    def get_pending_github_info(self):
        sql = """
        SELECT      assignment.assignment_id, 
                    assignment.course_id,
                    assignment.points,
                    assignment.code,
                    submission.uid,
                    submission.content
        FROM        core.submission
                    INNER JOIN 
                    (
                            SELECT      assignment.assignment_id, 
                                        assignment.course_id,
                                        assignment.points,
                                        course.code
                            FROM        core.course
                            INNER JOIN  core.assignment
                            ON          assignment.course_id = course.course_id
                            WHERE       handler = 'HUBREG'
                            AND         deadline > NOW()
                    ) assignment
                    ON submission.course_id = assignment.course_id
        WHERE       state = 'draft'
        """
        with psycopg.connect(self.cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql
                )
            return [dict(zip([key[0] for key in cur.description], row)) for row in cur]
        
    def set_enrollee_account(self, submission:dict):

        sql_update_enrollee = """
        UPDATE      core.enrollee
        SET         github_account  = %(content)s,
                    github_repository =%(github_repository)s
        WHERE       uid             = %(uid)s
        AND         course_id       = %(course_id)s
        """
        sql_update_submission = """
        UPDATE      core.submission
        SET         score           = %(points)s,
                    state           = 'accepted',
                    evaluator       = 'HUBREG'
        WHERE       uid             = %(uid)s
        AND         course_id       = %(course_id)s
        AND         assignment_id   = %(assignment_id)s
        """

        with psycopg.connect(self.cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql_update_enrollee, submission
                )

                cur.execute(
                    sql_update_submission, submission
                )
 
if __name__ == '__main__': 
 
    script_start_time = time.time() 
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

    try:
        read_config_file(CONFIG_FILE)
    except Exception as ex:
        print(f"Error reading site configuration '{CONFIG_FILE}'")
        print(str(ex))
        os._exit(-1)

    cstring = f"dbname={DB_NAME} user={DB_USER}"
 
    # WORK HERE 
    try: 
        db = Database(cstring)
        github_account_submissions = db.get_pending_github_info()

        # Check for invitations 
        token = GH_TOKEN
        user = GH_USER
        gh_session = requests.Session() 
        gh_session.auth = (user, token)

        headers = {'Authorization': 'token ' + token}
        url = 'https://api.github.com/user/repository_invitations' 
        invitations = requests.get(url, headers=headers).json()

        for submission in github_account_submissions:
            submission.update(invite_matched = False)
            utuid = submission['uid']
            github_account = submission['content']
            course_code = submission['code']

            for invite in invitations: 
                repo = invite.get('repository')
                if repo['owner']['login'] == github_account and repo['name'] == course_code:
                    submission.update(github_repository = repo['name'])
                    submission['invite_matched'] = True
                    db.set_enrollee_account(submission)
                    requests.patch(
                        f"{url}/{invite.get('id')}",
                        data={}, 
                        headers=headers
                    )

        #
        # TODO: handle possible cases where an invitation has already been accepted in github (if submission cannot be matched to an invite, check against existing collaborators)

    except Exception as ex: 
        log.exception(f"Script execution error!", exec_info = False) 
        os._exit(-1) 
    else: 
        elapsed = time.time() - script_start_time 
        log.info(f"Execution took {elapsed} seconds.")