#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Tuisku Polvinen <tumipo@utu.fi>, Jani Tammi <jasata@utu.fi>
#
# gitbot.py - Git exercise retriever
#   2021-08-13  Initial version (HubBot).
#   2021-09-12  Forked as GitBot and modified.
#
#
# GitBot is a modified copy of HubBot, which is intended to support multiple
# Git Repositories (GitHub and UTU GitLab at first). This work will not be
# completed or taken into use until early 2022, due to limited work time being
# available.
#
# 
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




# Add parent directory to the python search path
#
#   This is necessary for the directory location of cron jobs (such as this)
#   in relation to the application package "schooner".
#
#   NOTE:   The search path addition (sys.path.insert()) should not go into
#           the zero index because it could be important for 3rd party code.
#           Some rely on sys.path documentation conformance:
#
#           "As initialized upon program startup, the first item of this list,
#           path[0], is the directory containing the script that was used to
#           invoke the Python interpreter.""
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
import logging
import psycopg
import argparse
import datetime
from schooner.util      import AppConfig
from schooner.util      import Lockfile
from schooner.util      import Timer
from schooner.util      import LogDBHandler
from schooner.util      import SubProcess

# For config
class DefaultDotDict(dict):
    """Dot-notation access dict with default key '*'. Returns value for key '*' for missing missing keys, or None if '*' value has not been set."""
    def __custom_get__(self, key):
        """For all DotDict.key access, missing or otherwise."""
        return self.get(key, self.get('*', None))
    __getattr__ = __custom_get__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    def __missing__(self, key):
        """For DefaultDotDict[key] access, missing keys."""
        return self.get('*', None)


###############################################################################
#
# DEFAULT CONFIGURATION  (Hardcoded / fallback defaults)
#
#   For instance specific configuration, please use the .conf file.
#   IMPORTANT! This script will reject any keys from .conf file which
#   do not appear in the config dictionary below!!
#
config = DefaultDotDict(
    appname     = "gitbot",
    dateformat  = "%Y-%m-%d",
    timeformat  = "%H:%M:%S",
    loglevel    = "INFO",
    lockfile    = f"{os.path.splitext(os.path.basename(__file__))[0]}.lock",
    # Explicitly, config file is in the same directory as this script
    cfgfile     = f"{os.path.dirname(os.path.realpath(__file__))}/app.conf",
    database    = "schooner",
    store       = "/srv/schooner/submissions"
)

# PEP 396 -- Module Version Numbers https://www.python.org/dev/peps/pep-0396/
__version__     = "0.5.0 (2021-09-12)"
__authors__     = "Tuisku Polvinen <tumipo@utu.fi>, Jani Tammi <jasata@utu.fi>"
VERSION         = __version__
HEADER          = f"""
=============================================================================
University of Turku, Faculty of Technology, Department of Computing
Hubbot version {__version__} - The Git exercise retriever
(c) 2018-2021 {__authors__}
"""


def to_bool(v):
    """Utility to translated string values to bool."""
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise TypeError('Boolean value expected.')


#
# This class has no uses beyond this script and is thus not included in the
# schooner library. Database has almost the same as a view:
#   core.assignments_open_for_submissions
# (The view does not include assignments that closed yesteday).
#
class GitAssignments(list):
    """List of Git assignments that are open for submissions, or have closed for submission yesterday. Because the deadline always ends are midnight, the policy of Git submissions is to fetch them right after midnight, making them "yesterdays", but still in-time as far as they are considered submissions. Soft deadlines are calculated into the closing dates."""
    # Assignments that are open or closed yesterday
    SQL = """
    SELECT      assignment.course_id,
                assignment.assignment_id,
                assignment.name,
                assignment.handler AS type,
                assignment.directives,
                COALESCE(assignment.opens, course.opens) AS opens,
                assignment.retries,
                assignment.deadline,
                assignment.latepenalty,
                CASE
                    WHEN assignment.deadline IS NULL THEN
                        course.closes
                    ELSE
                        assignment.deadline + COALESCE(
                            CEIL(1 / assignment.latepenalty) - 1,
                            0
                        )::INTEGER
                END::DATE AS last_submission_date
    FROM        core.assignment
                INNER JOIN core.course
                ON (assignment.course_id = course.course_id)
    WHERE       assignment.handler = 'HUBBOT'
                AND
                -- Assignment is open (note: course.opens is NOT NULL)
                COALESCE(assignment.opens, course.opens) < CURRENT_TIMESTAMP
                AND
                -- ...and has not yet been closed, past its deadline or softdeadline
                -- NULL here signifies that the assignment is open indefinitely
                    (
                        (
                            assignment.deadline IS NULL
                            AND
                            (
                                course.closes IS NULL
                                OR
                                course.closes > CURRENT_TIMESTAMP
                            )
                        )
                        OR
                        -- +2 because submissions are open UNTIL the END of the date (+1)
                        -- AND because HUBBOT wants to retriee submissions also for
                        -- assignments that closed at this midnight.
                        assignment.deadline + COALESCE(
                            CEIL(1 / assignment.latepenalty) - 1,
                            0
                        )::INTEGER + 2 > CURRENT_TIMESTAMP
                    )
    """


    def __init__(self, cursor):
        self.cursor = cursor
        cursor.execute(GitAssignments.SQL)
        super().__init__(
            [dict(zip([k[0] for k in cursor.description], row)) for row in cursor]
        )




class GitAssignment(dict):
    """Git Assignment dictionary with .directive attribute, which is a separate dictionary that loads JSON data from column 'directives' over default directive values."""

    SQL = """
    SELECT      *
    FROM        core.assignment
    WHERE       course_id = %(course_id)s
                AND
                assignment_id = %(assignment_id)s
    """

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
        self.cursor = cursor
        if self.cursor.execute(GitAssignment.SQL, locals()).rowcount:
            self.update(
                dict(
                    zip(
                        [key[0] for key in cursor.description],
                        cursor.fetchone()
                    )
                )
            )
        else:
            raise ValueError(
                f"Assignment ('{course_id}', '{assignment_id}') not found!"
            )
        # Create directives attribute-dictionary
        import copy
        import json
        self.directive = copy.deepcopy(GitAssignment.default_directives)
        jsonstring = self.pop("directives", None)
        if jsonstring:
            self.directive.update(json.loads(jsonstring))


    def triggers(self, contents: list) -> bool:
        """Returns list of files/directories specified by directives.fetch.trigger. Normal outcome is that there is either none, or one. Multiple is considered as a logical error - one of them has to be identified as the intended submission. These are details that the caller must deal with."""
        # NOTE: This does NOT have the capability to traverse Git repository tree.
        #       All triggers must, for now, exist in the repository root.
        import fnmatch
        trigs = []
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




# Package 'requests' should be dropped in favor of urllib3 (part of standard python)
import requests
import json
class GitRepo(requests.Session):

    def __init__(self, token: str, account: str):
        self.token      = token
        self.account    = account
        super().__init__()
        # requests.Session attribute(s)
        self.auth    = self.account, self.token


    def exists(self, account: str, repository: str) -> bool:
        URL = f"https://api.github.com/repos/{account}/{repository}/contents/"
        return self.get(URL).status_code != 404


    def filenames(self, account: str, repository: str) -> list:
        URL = f"https://api.github.com/repos/{account}/{repository}/contents/"
        return [f['name'] for f in json.loads(self.get(URL).text)]

    def contents(self, account: str, repository: str) -> list:
        URL = f"https://api.github.com/repos/{account}/{repository}/contents/"
        return json.loads(self.get(URL).text)




#
# Custom exception for the dispatcher decision making
#
class GitSkipFetch(Exception):
    pass


#
# Custom exceptions for fetcher
#
class GitRepositoryNotFound(Exception):
    pass

class GitCloneNotTriggered(Exception):
    pass


##############################################################################
#
# MAIN
#
###############################################################################
if __name__ != "__main__":
    raise Exception("This script must not be imported by other scripts!")


#
# Basic execution timer
#
runtime = Timer()

#
# Cron job speciality - change to script's directory
#
os.chdir(os.path.dirname(os.path.realpath(__file__)))


#
# First argparse to see if an alternative configuration file has been given
#
cfparser = argparse.ArgumentParser(
    # Turn off help; do not react to '-h' with this parser
    add_help        = False,
    description     = __doc__,
    formatter_class = argparse.RawDescriptionHelpFormatter
)
cfparser.add_argument(
    #"-c",
    "--config",
    help    = f"Specify config file Default: '{config.cfgfile}'",
    dest    = "cfgfile",
    metavar = "FILE"
)
args, _ = cfparser.parse_known_args()
if args.cfgfile:
    config.cfgfile = args.cfgfile


#
# Read .conf file and update config:dict
#
try:
    fcfg = AppConfig(config.cfgfile, config.appname)
    # IMPORTANT: This will leave out any keys not present in the config!!!
    config.update((k, fcfg[k]) for k in set(fcfg).intersection(config))
except FileNotFoundError as ex:
    # If the config file was specified, complain about missing it
    if args.cfgfile:
        # Print it to avoid traceback
        print(ex)
        os._exit(-1)
    # else, silently accept missing config file
    print(f"Notice: Configuration file '{config.cfgfile}' was not found.")
except:
    print(f"Error reading '{config.cfgfile}'")
    os._exit(-1)


#
# Commandline arguments
#
#   NOTE:   Defaults are updated by the above config file reader.
#           This is how it is supposed to work from the user's PoV.
#           It does not matter where the value comes from - it is
#           a default unless user gives commandline argument(s)
#           to change them.
#
argparser = argparse.ArgumentParser(
    prog            = config.appname,
    description     = HEADER,
    formatter_class = lambda prog: argparse.RawTextHelpFormatter(
        prog,
        max_help_position = 34,
        width = 80
    )
)
# EXCEPTIONS!!
# Do not define a default for 'csv' or 'schemasql'
# This way 'arg.csv' and 'arg.schemasql' are left as 'None'
# and that tells us if the corresponding option was specified or not.
argparser.set_defaults(
    **{k:v for k,v in config.items() if k not in ("csv", "schemasql")}
)
argparser.add_argument(
    "--clone",
    help    = "Clone specified repository (3 arguments!)",
    dest    = "clone",
    metavar = ("CID", "AID", "UID"),
    nargs   = 3,
    type    = str
)
argparser.add_argument(
    #"-c",
    "--config",
    help    = f"Specify config file Default: '{config.cfgfile}'",
    dest    = "cfgfile",
    metavar = "FILE",
    type    = str
)
argparser.add_argument(
    #'-d',
    '--database',
    help    = f"Name of the database. Default: '{config.database}'",
    dest    = "database",
    metavar = "NAME",
    type    = str
)
argparser.add_argument(
    #"-l",
    "--loglevel",
    help    = f"Set logging level. Default: '{config.loglevel}'",
    choices = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    nargs   = "?", # optional argument, defaults to 'const' value
    dest    = "loglevel",
    const   = "INFO",
    type    = str.upper,
    metavar = "LEVEL"
)
args, _ = argparser.parse_known_args()
# Update only the existing keys
config.update(
    (k, vars(args)[k]) for k in set(vars(args)).intersection(config)
)


#
# Disable traceback for non-DEBUG runs
#
if config.loglevel != "DEBUG":
    sys.tracebacklimit = 0


#
# Set up logging
#
log = logging.getLogger(config.appname)
log.setLevel(config.loglevel)
if os.isatty(sys.stdin.fileno()):
    # Executed from terminal, add STDOUT handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter('[%(levelname)s] %(message)s')
    )
    log.addHandler(handler)
else:
    # Executed from crontab, add SYSLOG handler
    handler = logging.handlers.SysLogHandler(address = '/dev/log')
    handler.setFormatter(
        logging.Formatter('%(name)s: [%(levelname)s] %(message)s')
    )
    log.addHandler(handler)
# DB log Handler
handler = LogDBHandler(config.database, level = config.loglevel)
log.addHandler(handler)


#
# Debug, dump config, if running in a terminal
#
if os.isatty(sys.stdin.fileno()):
    print(HEADER)
    log.debug(f"commandline: {' '.join(sys.argv)}")
    log.debug(f"config: {str(config)}")




#
# Run as Dispatcher, if --clone was not specified
#
if not args.clone:
    fetches = []
    try:
        from schooner.db.core   import EnrolleeList, SubmissionList
        with    Lockfile(config.lockfile) as lock, \
                psycopg.connect(f"dbname={config.database}").cursor() as cursor:

            assignmentlist = GitAssignments(cursor)
            log.debug(f"Processing {len(assignmentlist)} open assignments")
            for assignment in assignmentlist:
                log.debug(
                    "Assignment ({}, {}) \"{}\" is open until {}".format(
                        assignment['course_id'],
                        assignment['assignment_id'],
                        assignment['name'],
                        assignment['last_submission_date']
                    )
                )
                enrolleelist = EnrolleeList(
                    cursor,
                    has_github_account = True,
                    course_id = assignment['course_id'],
                    status = 'active'
                )
                log.debug(
                    "Course '{}' has {} active enrollees with a Git account".format(
                        assignment['course_id'],
                        len(enrolleelist)
                    )
                )
                for enrollee in enrolleelist:
                    submissionlist = SubmissionList(
                        cursor,
                        course_id = assignment['course_id'],
                        assignment_id = assignment['assignment_id'],
                        uid = enrollee['uid']
                    )
                    log.debug(
                        "\tEnrollee '{}' has {} submissions".format(
                            enrollee['uid'],
                            len(submissionlist)
                        )
                    )
                    #
                    # Check if fetch attempt should be made
                    #
                    try:
                        draft = next(
                            (item for item in submissionlist if item['state'] == "draft"),
                            None
                        )
                        if draft:
                            raise GitSkipFetch(
                                "Enrollee '{}' already has a 'draft' submission #{}".format(
                                    enrollee['uid'],
                                    draft['submission_id']
                                )
                            )
                        if assignment['retries']:
                            log.debug(
                                "Assignment ('{}', '{}') retry limit set as {}.".format(
                                    assignment['course_id'],
                                    assignment['assignment_id'],
                                    assignment['retries']
                                )
                            )
                            if len(submissionlist) > assignment['retries']:
                                raise GitSkipFetch(
                                    "Enrollee '{}' has {} submissions. Next would exceed assignment's retry limit of {}".format(
                                        enrollee['uid'],
                                        len(submissionlist),
                                        assignment['retries']
                                    )
                                )

                    except GitSkipFetch as e:
                        log.debug(f"Skipping fetch: {str(e)}")
                    except Exception as e:
                        log.exception(
                            f"Fetch attempt decision code caused an exception! {str(e)}"
                        )
                    else:
                        # Git fetch attempt can be made
                        cmd = "{} --clone {} {} {}".format(
                            sys.argv[0],
                            assignment['course_id'],
                            assignment['assignment_id'],
                            enrollee['uid']
                        )
                        log.debug(f"SubProcess('{cmd}')")
                        fetches.append(SubProcess(cmd))
                        log.debug(f"Return code: {fetches[-1].returncode}")


    except Lockfile.AlreadyRunning as e:
        # Absolutely should NOT EVER happen, if this script is executed
        # once-a-day at midnight. If the lockfile exists after 24 hours,
        # something has gone very wrong!
        log.exception(
            f"Execution cancelled! {str(e)}"
        )
        os._exit(0)
    except Exception as e:
        # possibly psycopg connect error
        msg = f"Program failure while issuing fetch subprocesses! {str(e)}"
        log.exception(msg)
        sys.stderr.write(msg)
        os._exit(-1)


    #
    # Fetches -list has been compiled with executed subprocess'es.
    # Now each fetch attempt, successful or otherwise, are sent a notification.
    #
    # TODO: fetches list should contain Attempt -objects so that all the
    #       necessary data is available for creating the notifications.
    try:
        pass
    except Exception as e:
        msg = f"Program failure while sending notifications! {str(e)}"
        log.exception(msg)
        sys.stderr.write(msg)
        os._exit(-1)


    #
    # Report execution
    #
    log.info(
       f"X/{len(fetches)} (fetches/attempts) in {runtime.report()}"
    )


###############################################################################
#
# Run as Git fetch attempt (--clone was specified)
#
###############################################################################
else:

    #
    # Run fetching under a different name (shows in the database system.log)
    #
    config.appname = "gitfetcher"
    log.name = config.appname


    #
    # --clone command line arguments
    #
    cid, aid, uid = args.clone


    #
    # Save-to directory (rename variable?)
    #
    tgt = os.path.join(
        config.submissions_directory,
        cid,
        uid,
        aid
    )
    if not os.path.exists(tgt):
        log.debug(f"Fetching for '{tgt}' (directory will be created).")
        os.makedirs(tgt)
    else:
        log.debug(f"Fetching for '{tgt}'.")


    try:
        from schooner.db.core import Enrollee
        with psycopg.connect(f"dbname={config.database}").cursor() as cursor:
            repository = GitRepo(
                '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',
                'kaislahattu'
            )
            # TODO: Modify GitAssignment to include all necessary data from
            #       Enrollee AND collect course data (esp. github credentials)
            assignment = GitAssignment(cursor, cid, aid)
            enrollee = Enrollee(cursor, cid, uid)


            #
            # Check that student's repository exists
            #
            if not repository.exists(
                enrollee['github_account'],
                enrollee['github_repository']
            ):
                raise GitRepositoryNotFound(
                    "Student '{}' GitHub repository 'git@github.com:{}/{}.git' not found!".format(
                        enrollee['uid'],
                        enrollee['github_account'],
                        enrollee['github_repository']
                    )
                )
            else:
                log.debug(
                    "Student '{}' GitHub repository 'git@github.com:{}/{}.git' exists".format(
                        enrollee['uid'],
                        enrollee['github_account'],
                        enrollee['github_repository']
                    )
                )


            #
            # Check if required file/folder exists
            #
            triggers = assignment.triggers(
                repository.contents(
                    enrollee['github_account'],
                    enrollee['github_repository']
                )
            )
            # TODO: clone regardless when the deadline is reached, and while on soft deadline
            if not triggers:
                raise GitCloneNotTriggered(
                    "Cloning condition not met! " +
                    "GitHub repository 'git@github.com:{}/{}.git' ".format(
                        enrollee['github_account'],
                        enrollee['github_repository']
                    ) +
                    "(registered to student '{}') ".format(
                        enrollee['uid']
                    ) +
                    "does not contain an entry to match the submission-triggering pattern " +
                    "'{}' for assignment ('{}', '{}').".format(
                        assignment.directive['fetch']['trigger'],
                        cid,
                        aid
                    )
                )


            #
            # If the save-to directory already exists (should not), remove it
            #
            try:
                repodir = os.path.join(
                    tgt,
                    datetime.datetime.now().strftime(config.dateformat)
                )
                if os.path.exists(repodir):
                    log.warning(
                        f"target clone directory '{repodir}' already exists! " +
                        "Removing directory."
                    )
                    import shutil
                    shutil.rmtree(repodir)
            except Exception as e:
                raise Exception(
                    f"Unable to prepare target directory for cloning! " +
                    str(e)
                ) from None


            ###############################################################
            #
            # TODO HERE! THE CODE BELOW HAS NOT BEEN MODIFIED YET
            #
            # Execute clone
            import git
            #
            # Clone and send mail if successful.
            #
            URL = "https://{}:x-oauth-basic@github.com/{}/{}.git".format(
                repository.token,
                enrollee['github_account'],
                enrollee['github_reponame']
            )
            git.Git(tgt).clone(URL, repodir)
            # This call also sends a success message.
            assignment.register_as_submission(cursor, uid, aid)
            # Successfully fetched and registered - create 'accepted' symlink
            if not os.path.exists(f"{tgt}/accepted"):
                os.symlink(
                    f"{tgt}/{fetchdate}/{assignment['assignment_id']}",
                    f"{tgt}/accepted"
                )
            log.debug(
                "GitHub clone successful for user '{}', repository '{}' assignment ({}, {})".format(
                    student['uid'],
                    repository.URL.HTTPS,
                    course_id,
                    assignment_id
                )
            )


    except (GitRepositoryNotFound, GitCloneNotTriggered) as e:
        sys.stdout.write(str(e))
        # Return with positive return code to indicate logical error
        os._exit(1)
    except Exception as e:
        # Negative return code indicates program code error
        sys.stderr.write(str(e))
        os._exit(-1)
    else:
        # Return with all-clear zero-value
        sys.stdout.write("SOME USEFUL DATA?")
        os._exit(0)




# EOF