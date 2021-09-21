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


class MessageBuffer(list):
    def __init__(self, log):
        self.log = log
    def debug(self, msg: str):
        if self.log.getEffectiveLevel() <= 10:
            self.append(msg)
    def info(self, msg: str):
        if self.log.getEffectiveLevel() <= 20:
            self.append(msg)
    def warning(self, msg: str):
        if self.log.getEffectiveLevel() <= 30:
            self.append(msg)
    def error(self, msg: str):
        if self.log.getEffectiveLevel() <= 40:
            self.append(msg)
    def exception(self, msg: str):
        if self.log.getEffectiveLevel() <= 40:
            self.append(msg)
    def __repr__(self):
        return "\n".join(self)


class GitRepositoryNotFound(Exception):
    pass

class GitFetchTriggerNotFound(Exception):
    pass


class GitRepo(requests.Session):

    class Url:
        def __init__(self, repo):
            self.repo = repo
        @property
        def source(self) -> str:
            return "https://{}:x-oauth-basic@github.com/{}/{}.git".format(
                self.repo.token,
                self.repo.account,
                self.repo.reponame
            )
        @property
        def contents(self) -> str:
            return "https://api.github.com/repos/{}/{}/contents/".format(
                self.repo.account,
                self.repo.reponame
            )
        @property
        def SSH(self) -> str:
            return "git@github.com:{}/{}.git".format(
                self.repo.account,
                self.repo.reponame
            )
        @property
        def HTTPS(self) -> str:
            return "https://github.com/{}/{}.git".format(
                self.repo.account,
                self.repo.reponame
            )

    def __init__(self, token: str, account: str, reponame: str):
        self.token      = token
        self.account    = account
        self.reponame   = reponame
        super().__init__()
        # requests.Session attribute(s)
        self.auth    = self.account, self.token
        self.URL = GitRepo.Url(self)
        # TODO: Test token by retrieving course's git account
        # https://api.github.com/users/DTEK0068
        # status_code 401 is bad credentials


    def exists(self) -> bool:
        """Raises GitRepo.NotFound if not found"""
        return self.get(self.URL.contents).status_code != 404

    @property
    def files(self):
        """Repository folder contents JSON"""
        response = self.get(self.URL.contents)
        if response.status_code != 200:
            raise ValueError(
                "Repository content retrieval failure! " +
                f"Response code: {response.status_code}, " +
                response.text
            )
        return json.loads(response.text)

    @property
    def filenames(self):
        return [f['name'] for f in self.files]

    def file_exists(self, file: str) -> bool:
        return file in self.filenames



class GitAssignment(Assignment):
    """Git Assignment dictionary with .directive attribute, which is a separate dictionary that loads JSON data from column 'directives' over default directive values."""


    class Course(dict):
        def __init__(self, cursor, course_id: str):
            self.cursor = cursor
            SQL = """
            SELECT      *
            FROM        core.course
            WHERE       course_id = %(course_id)s
            """
            cursor.execute(SQL, locals())
            self.update(
                dict(
                    zip(
                        [key[0] for key in cursor.description],
                        cursor.fetchone()
                    )
                )
            )


    # Default/seed key: values that get updated after being copied for an object instance
    default_directives = {
        "fetch" : {
            "trigger"   : {
                "type"      : "file",
                "path"      : "/",
                "pattern"   : "READY*"
            },
            "notify-on-failure" : True,
            "notify-on-success" : True
        },
        # Because git does not retrieve partial repositories, additional step is provided
        # which removes unwanted content. List of patterns, white- or blacklist.
        # Operation will be applied to the local cloned repository
        "prune" : {
            "type"  : "whitelist",
            "list"  : [ "*" ]
        },
        # Test -phase contains yet-to-be-determined automated testing sequences.
        # The may include such as: coding standard compliance scanning, compile tests,
        # container-based execution with input/output criteria.
        # THIS PART WILL NOT BE PART OF SCHOONER, but as an external service
        # API and implementation are left for future
        "test" : {
            "TBA" : "TBA"
        },
        # Evaluate -phase is inteded for course assistants to review things that
        # cannot reasobably be automated. This should be a list of evaluation
        # criteria that can be parsed into a check-list into the evaluation page.
        "evaluate" : [
            {
                "TBA" : "TBA"
            }
        ]
    }

    def __init__(self, cursor, course_id: str, assignment_id: str):
        super().__init__(cursor, course_id, assignment_id)
        # Create directives attribute-dictionary
        import copy
        import json
        self.directive = copy.deepcopy(GitAssignment.default_directives)
        jsonstring = self.get("directives", None)
        if jsonstring:
            self.directive.update(json.loads(jsonstring))
        # Create Course sub-object
        self.course = GitAssignment.Course(cursor, self['course_id'])


    def triggers(self, contents: list) -> bool:
        """Returns list of files/directories specified by directives.fetch.trigger. Normal outcome is that there is either none, or one. Multiple is considered as a logical error - one of them has to be identified as the intended submission. These are details that the caller must deal with."""
        # NOTE: This does NOT have the capability to traverse Git repository tree.
        #       All triggers must, for now, exist in the repository root.
        import fnmatch
        trigs = []
        #print("WILL TRIGGER FOR", self.directive['fetch']['trigger'])
        if not self.directive:
            return trigs
        for item in list(contents):
            if (self.directive['fetch']['trigger']['type'] == "any" or
                self.directive['fetch']['trigger']['type'] == item['type']):
                # print(
                #     "Type match! Matching ",
                #     item['path'],
                #     self.directive['fetch']['trigger']['pattern']
                # )
                if fnmatch.fnmatch(
                    item['path'],
                    self.directive['fetch']['trigger']['pattern']
                ):
                    # print("Pattern match!", self.directive['fetch']['trigger']['pattern'], item['path'])
                    # Add to the list of triggering items
                    trigs.append(
                        {
                            k : item[k]
                            for k
                            in set(item).intersection(
                                ('name', 'path', 'type', 'size')
                            )
                        }
                    )
        return trigs


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

    #
    # Read application configuration
    #
    cfg = AppConfig(CONFIG_FILE, 'hubbot')

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


    args, _ = argparser.parse_known_args()

    #
    # Attempt submission retrieval
    #
    if args.clone:
        course_id       = args.clone[0]
        assignment_id   = args.clone[1]
        uid             = args.clone[2]
        log.info(
            f"Cloning assignment ('{course_id}', '{assignment_id}') from student '{uid}'"
        )

        #
        # Collect/generate data for execution
        #
        cstring = f"dbname={cfg.database}"
        try:
            with psycopg.connect(cstring).cursor() as cursor:
                assignment  = GitAssignment(cursor, course_id, assignment_id)
                student     = Enrollee(cursor, course_id, uid)

            #
            # Terminate fetch if student is not active
            #
            if student['status'] != 'active':
                log.info(
                    f"Student '{uid}' status is not 'active'! Skipping fetch..."
                )
                os._exit(1)

            tgt = os.path.join(
                cfg.submissions_directory,
                course_id,
                uid,
                assignment_id
                )
            if not os.path.exists(tgt):
                os.makedirs(tgt)
            fetchdate = datetime.now().strftime(cfg.dateformat)
            fetchfile = f'{tgt}/{fetchdate}.txt'

            #
            # Create a session object with the user creds in-built
            #
            repository = GitRepo(
                assignment.course['github_accesstoken'],
                student['github_account'],
                student['github_repository']
            )

        except Exception as e:
            msg = "Execution data generation phase error!"
            log.exception(msg)
            sys.stdout.write(msg + "\n" + str(e))
            os._exit(-1)


        #
        # Write fetch log with attempt 
        #
        with open(fetchfile, 'a') as log_fetch:
            log_fetch.write(
                "{}\nTrying to fetch from: https://github.com/{}/{}.git\n".format(
                    datetime.now(),
                    student['github_account'],
                    student['github_repository']
                )
            )
        log.debug(
            "Fetching from: https://github.com/{}/{}.git".format(
                student['github_account'],
                student['github_repository']
            )
        )


        try:
            #
            # Handle case: repository doesn't exist or cannot be found
            #
            if not repository.exists():
                raise GitRepositoryNotFound(
                    "Student {}: Github repository ({}) not found".format(
                        uid,
                        repository.URL.HTTPS
                    )
                ) 
            log.debug(
                "Student '{}' repository {} exists".format(
                    uid,
                    repository.URL.HTTPS
                )
            )

            #
            # Clone only if triggering condition is met
            #
            triggers = assignment.triggers(repository.files)
            if len(triggers) < 1:
                raise GitFetchTriggerNotFound(
                    f"'{course_id}', '{assignment_id}', '{uid}': " +
                    "Content trigger {} not found in repository {}".format(
                        assignment.directive['fetch']['trigger'],
                        repository.URL.HTTPS
                    )
                )
            log.debug(f"Positive trigger(s) for fetch: {triggers}")


            #
            # Fetch should happen once in a day - if path already exists, something is wrong.
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
            git.Git(tgt).clone(repository.URL.source, fetchdate)
            with psycopg.connect(cstring).cursor() as cursor:
                    # This call also sends a success message.
                    assignment.register_as_submission(cursor, student, assignment)
                    cursor.connection.commit()
            # Successfully fetched and registered - create 'accepted' symlink
            if not os.path.exists(f"{tgt}/accepted"):
                if len(triggers) > 1:
                    log.error(
                        "More than one qualifying (triggering) items! " +
                        str(triggers)
                    )
                else:
                    os.symlink(
                        os.path.join(tgt, fetchdate, triggers[0]['path']),
                        os.path.join(tgt, "accepted")
                    )
            log.debug(
                "GitHub clone successful for user '{}', repository '{}' assignment ({}, {})".format(
                    uid,
                    repository.URL.HTTPS,
                    course_id,
                    assignment_id
                )
            )

        except (GitRepositoryNotFound, GitFetchTriggerNotFound) as e:
            log.info(f"Git clone not successful: {e}")
            with open(fetchfile, 'a') as log_fetch:
                log_fetch.write(f"{str(e)}\nEnd of fetch.\n")
            # Already in the log.info call above
            #sys.stdout.write(str(e))
            with psycopg.connect(cstring).cursor() as cursor:
                try:
                    Assignment.send_retrieval_failure_mail(
                        cursor,
                        assignment,
                        uid,
                        str(e)
                    )
                    log.debug(
                        f"Template parsed and queued for {uid}"
                    )
                except Template.NotSent as e:
                    log.info(f"Automated message not sent: {str(e)}")
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
                    uid,
                    str(e)
                )
                log.debug(
                    f"Template parsed and queued for {uid}"
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



    ###########################################################################
    #
    # Dispatcher
    #
    else:
        # Dispatcher logs to the DB
        handler = LogDBHandler(cfg.database, level = cfg.loglevel)
        log.addHandler(handler)
        log.name = "HubBot Dispatcher"
        logbuffer = MessageBuffer(log)
        errors  = []
        fetches = []
        # Using local authentication -- password is never used
        cstring = f"dbname={cfg.database}"
        try:
            with Lockfile(cfg.lockfile), \
                 psycopg.connect(cstring).cursor() as cursor:
   
                assignments = GitAssignments(cursor)
                logbuffer.info(f"Dispatcher processing {len(assignments)} assignments")
                for assignment in assignments:
                    logbuffer.info(
                        "\n{}, {} (last retrieval {})".format(
                            assignment['course_id'],
                            assignment['assignment_id'],
                            assignment['last_retrieval_date']
                        )
                    )
                    for submission in assignments.submissions(**assignment):
                        can_retry   = not   (assignment['retries'] == None) or \
                                            (
                                                submission['n_submissions'] < \
                                                assignment['retries'] + 1
                                            )
                        uid = submission['uid']

                        #
                        # Reasons to skip a fetch
                        #
                        if submission['status'] != 'active':
                            logbuffer.debug(
                                f"'{uid}' : Skipping - not active in course!"
                            )
                            continue
                        if submission['github_account'] is None:
                            logbuffer.debug(
                                f"'{uid}' : Skipping - no GitHub account registered!"
                            )
                            continue
                        if submission['draft_submission_id'] is not None:
                            logbuffer.debug(
                                f"'{uid}' : Skipping - has an open draft submission!"
                            )
                            continue
                        if submission['accepted_submission_id'] is not None:
                            if not can_retry:
                                logbuffer.debug(
                                    f"'{uid}' : Skipping - has already accepted submission!"
                                )
                                continue
                        #
                        # No reason found to skip, make a fetch attempt
                        #
                        try:
                            # Sub process returns tuple (return_code, stdout, stderr)
                            clone = processer(
                                "python hubbot.py --clone {} {} {}".format(
                                    assignment['course_id'],
                                    assignment['assignment_id'],
                                    submission['uid']
                                )
                            )
                            fetches.append(clone)
                        except Exception as e:
                            logbuffer.debug(
                                "'{}' : Fetch FAILURE!\n{}".format(uid, str(e))
                            )
                            fetches.append((-1, None, str(e)))
                            log.error(str(e))
                        else:
                            logbuffer.debug(
                                "'{}' : Fetch completed without errors\n".format(uid) +
                                "Return code: {}\nSTDOUT : \n{}STDERR : \n{}".format(
                                    str(fetches[-1][0]),
                                    "\n    ".join(fetches[-1][1].split("\\n")) if fetches[-1][1] else "(None)",
                                    "\n    ".join(fetches[-1][2].split("\\n")) if fetches[-1][2] else "(None)"
                                )
                            )


        except Lockfile.AlreadyRunning as e:
            log.error("Execution cancelled! Lockfile found (another process still running).")
            os._exit(1)
        except Exception as ex:
            # Dump out whatever has been accumulated into the logbuffer
            log.info(logbuffer)
            log.exception(f"Script execution error!") #, exec_info = False)
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
        logbuffer.info(
            "\nTotal of {} fetch attempts ({} successes, {} not found, {} errors) in {}.".format(
                len(fetches),
                success,
                not_found,
                errors,
                runtime.report()
            )
        )
        log.info(logbuffer)


# EOF
