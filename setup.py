#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2020-2021, Jani Tammi <jasata@utu.fi>
# setup.py - Flask Application setup
#
#
#   2020-01-01  Initial version.
#   2020-01-02  Import do_or_die() from old scripts.
#   2020-01-02  Add database creation.
#   2020-01-02  Add overwrite/force parameter.
#   2020-01-02  Add cron job create.
#   2020-01-02  Add cron job detection and removal.
#   2020-01-02  Fix do_or_die() to handle script input.
#   2020-01-02  Add stdout and stderr output to do_or_die().
#   2020-01-08  Add download config items into flask app instance file.
#   2020-01-29  Drop Python requirement to v.3.6 (due to vm.utu.fi).
#   2020-01-30  GITUSER (owner of this file) resolved. Theory is that owner is
#               the same account that pulled/cloned this repo. This same
#               account is assumed to be the "maintainer" and is used as the
#               owner for files created by this script.
#   2020-09-11  Modified cron job creation code, added ability to configure
#               crontab scheduling (in the cronjobs dictionary) and option
#               to install cron jobs to specified user (see 'cronjobs' dict).
#   2020-09-13  Creates 'cron.job/site.config' - Always overwritten!'
#   2020-09-18  Added .ISO to default allowed upload file extensions.
#               Rename 'cron.jobs/site.config' -> 'cron.jobs/site.conf' to be
#               inline with other config file naming.
#   2020-09-18  Add ALLOWED_EXT to 'cron.jobs/site.conf'.
#   2020-09-27  Change database script location to 'sql/'.
#   2021-08-07  Modified for Schooner application.
#
#
#   ==> REQUIRES ROOT PRIVILEGES TO RUN! <==
#
#
#   1. Creates instance/application.conf
#   2. Creates application.sqlite3
#   3. If DEV, inserts test data into application.sqlite3
#   4. Creates cron jobs
#
#
#   IMPORTANT NOTE!
#           While the execution of this script requires root privileges,
#           another, equally important local user is the "maintainer".
#           It is assumed that it will be the same local user who pulled/cloned
#           this repository and thus, the same user who is the owner of this
#           script file.
#
#           This local user will be awarded with the ownership of the new files
#           created by this script (which should mean that the new files have
#           the same owner as the files pulled from the repository).
#           Maintainer (local user) will also run the cron jobs...
#  NOTE !!! UNLESS the local user is root, in which case, 'www-data' user will
#           run the cron jobs.
#
#           Root user is expected to be the maintainer for production instance.
#           This way, root user's RSA ID can be used as a Deploy Key in GitHub
#           while DEV / UAT instance user(s) can have keys that enable pushes.
#
# .config for this script
#       You *must* have "[System]" section at the beginning of the file.
#       You make write any or all the key = value properties you find in the
#       'details' dictionary's sub-dictionaries.
#       NOTE: Boolean values are problematic. I haven't decided how to handle
#             them yet... For parameters that get written out to the instance
#             configuration file, they are fine - because they will be written
#             as strings anyway.
#             BUT(!!) for 'overwrite' this is an unsolved issue.
#

# Requires Python 3.6+ (f-strings, ordered dictionaries, {**dict_a, **dict_b})
# IMPORTANT! CANNOT be pre-3.6 due to reliance on ordered dicts!!
REQUIRE_PYTHON_VER = (3, 6)


import os
import sys

if sys.version_info < REQUIRE_PYTHON_VER:
    import platform
    print(
        "You need Python {}.{} or newer! ".format(
            REQUIRE_PYTHON_VER[0],
            REQUIRE_PYTHON_VER[1]
        )
    )
    print(
        "You have Python ver.{} on {} {}".format(
            platform.python_version(),
            platform.system(),
            platform.release()
        )
    )
    print(
        "Are you sure you did not run 'python {}' instead of".format(
            os.path.basename(__file__)
        ),
        end = ""
    )
    print(
        "'python3 {}' or './{}'?".format(
            os.path.basename(__file__),
            os.path.basename(__file__)
        )
    )
    os._exit(1)


# PEP 396 -- Module Version Numbers https://www.python.org/dev/peps/pep-0396/
__version__ = "1.0.1 (2021-08-07)"
__author__  = "Jani Tammi <jasata@utu.fi>"
VERSION = __version__
HEADER  = f"""
=============================================================================
Schooner - Course Management System / Site Setup Script
University of Turku / Faculty of Technilogy / Department of Computing
Version {__version__}, 2020-2021 {__author__}
"""


import pwd
import grp
import logging
import sqlite3
import argparse
import subprocess
import configparser


# This script must be the project root, so we get the path to this script
ROOTPATH = os.path.split(os.path.realpath(__file__))[0]
SCRIPTNAME = os.path.basename(__file__)
# Local account that pulled/clones the repository = owner of this file
GITUSER  = pwd.getpwuid(os.stat(__file__).st_uid).pw_name


#
# CONFIGURATION
#
#   Modify the values in this dictionary, if needed.
#
defaults = {
    'choices':                      ['DEV', 'UAT', 'PRD'],
    'common': {
        'mode':                     'PRD',
        'upload_folder':            ROOTPATH + '/uploads',
        'upload_allowed_ext':       ['ova', 'zip', 'img', 'iso'],
        'download_folder':          '/var/www/downloads',
        'download_urlpath':         '/x-accel-redirect/',
        'sso_cookie':               'ssoUTUauth',
        'sso_session_api':          'https://sso.utu.fi/sso/json/sessions/',
        'overwrite':                False, # Force overwrite on existing files?
        'dbuser':                   'postgres', # Installation credentials
        'dbpass':                   None,       # Local authentication
        'dbname':                   'postgres'  # Only for connecting!
    },
    'DEV': {
        'mode':                     'DEV',
        'debug':                    True,
        'explain_template_loading': True,
        'log_level':                'DEBUG',
        'session_lifetime':         1,
        'overwrite':                True
    },
    'UAT': {
        'mode':                     'UAT',
        'debug':                    False,
        'explain_template_loading': False,
        'log_level':                'INFO',
        'session_lifetime':         30
    },
    'PRD': {
        'mode':                     'PRD',
        'debug':                    False,
        'explain_template_loading': False,
        'log_level':                'ERROR',
        'session_lifetime':         30,
        'overwrite':                False
    }
}

#
# SQL/Python scripts - Order is important!
#
#   label       Only used for logging purposes.
#   filename    Path + filename of the script file. If the name ends with
#               '.py', it is executed as a Python script and if ending with
#               '.sql', it is executed as a multi-statement SQL script.
#   mode        List of installation modes ["DEV", "UAT", "PRD"] under which
#               the script will be executed.
"""SQLite version
dbscripts = [
    {
        "label":    "Core Structure",
        "filename": os.path.join(ROOTPATH, "sql/core.sql"),
        "mode":     [ "DEV", "UAT", "PRD" ]
    },
    {
        "label":    "Grading systems",
        "filename": os.path.join(ROOTPATH, "sql/insert_grade.sql"),
        "mode":     [ "DEV", "UAT", "PRD" ]
    },
    {
        "label":    "Default Teacher Roles",
        "filename": os.path.join(ROOTPATH, "sql/insert_teachers.sql"),
        "mode":     [ "DEV", "UAT", "PRD" ]
    },
    {
        "label":    "DTE20068-3002 Course Implementation",
        "filename": os.path.join(ROOTPATH, "sql/insert_DTE20068-3002.sql"),
        "mode":     [ "DEV", "UAT", "PRD" ]
    },
    {
        "label":    "Insert Development Data",
        "filename": os.path.join(ROOTPATH, "sql/insert_devdata.sql"),
        "mode":     [ "DEV" ]
    }
]
"""
# PostgreSQL scripts
dbscripts = [
    {
        "label":    "Database creation statements",
        "filename": os.path.join(ROOTPATH, "sql/database.create.sql"),
        "mode":     [ "DEV", "UAT", "PRD" ],
        "dbuser":   "postgres",
        "dbname":   "postgres"
    },
    {
        "label":    "Admin user table (for SSO authentication module)",
        "filename": os.path.join(ROOTPATH, "sql/admin.sql"),
        "mode":     [ "DEV", "UAT", "PRD" ],
        "dbuser":   "www-data",
        "dbname":   "schooner"
    },
    {
        "label":    "Add local user (maintainer) as an Admin",
        "filename": os.path.join(ROOTPATH, "sql/admin.insert.py"),
        "mode":     [ "DEV", "UAT", "PRD" ],
        "dbuser":   "www-data",
        "dbname":   "schooner"
    },
    {
        "label":    "Schooner core tables",
        "filename": os.path.join(ROOTPATH, "sql/core.module.sql"),
        "mode":     [ "DEV", "UAT", "PRD" ],
        "dbuser":   "www-data",
        "dbname":   "schooner"
    },
    {
        "label":    "Tables for assistant and work queues",
        "filename": os.path.join(ROOTPATH, "sql/assistant.module.sql"),
        "mode":     [ "DEV", "UAT", "PRD" ],
        "dbuser":   "www-data",
        "dbname":   "schooner"
    },
    {
        "label":    "Tables for rules & conditions",
        "filename": os.path.join(ROOTPATH, "sql/rules.module.sql"),
        "mode":     [ "DEV", "UAT", "PRD" ],
        "dbuser":   "www-data",
        "dbname":   "schooner"
    },
    {
        "label":    "DTE20068 implementation for P2/2021",
        "filename": os.path.join(ROOTPATH, "sql/DTE20068-3002.sql"),
        "mode":     [ "DEV", "UAT", "PRD" ],
        "dbuser":   "www-data",
        "dbname":   "schooner"
    }
]


# If in doubt, use: https://crontab.guru/#0_3/3_*_*_*
# See also class CronJob
# NOTE: 'script' cannot start with '/' character - it has to be
#       a path relative to the execution directory of this script.
# script:       path/filename for the script.
# schedule:     Crontab schedule string.
# user:         (optional) If not GITUSER, the user who's crontab
#               will run the script.
cronjobs = {
    'HubReg - GitHub account registering service':
    {
        'script':   'cron.job/hubreg.py',
        'schedule': '*/1 * * * *'       # Every minute
    },
    'HubBot - GitHub exercise submission retriever':
    {
        'script':   'cron.job/hubbot.py',
        'schedule': '0 0 * * *'         # At midnight every day
    },
    'Task and deadline reminder':
    {
        'script':   'cron.job/nagger.py',
        'schedule': '0 5 * * *'         # At 05:00 every day
    }
}

class CronJob():

    def __init__(self, script: str, schedule: str, user: str = None):
        """."""
        self.script = os.path.join(
            # NOT working directory, but directory for this script!
            os.path.dirname(os.path.realpath(__file__)),
            script
        )
        self.schedule = schedule
        self.user = user


    def remove(self):
        usr = "-u " + self.user if self.user else ""
        cmd =  f"crontab {usr} -l 2>/dev/null | "
        cmd += f"grep -v '{self.script}' | crontab {usr} -"
        CronJob.subprocess(cmd, shell = True)


    def create(self, force: bool = False):
        if self.exists:
            if force:
                self.remove()
            else:
                raise ValueError(
                    f"Job '{self.script}' already exists!"
                )
        #self.script += " -with args"
        usr = "-u " + self.user if self.user else ""
        cmd = f'(crontab {usr} -l 2>/dev/null; echo "{self.schedule} '
        cmd += f'{self.script} >/dev/null 2>&1") | crontab {usr} -'
        CronJob.subprocess(cmd, shell = True)


    @property
    def exists(self) -> bool:
        """Argument is script name."""
        usr = "-u " + self.user if self.user else ""
        pipe = subprocess.Popen(
            f'crontab {usr} -l 2> /dev/null',
            shell = True,
            stdout = subprocess.PIPE
        )
        for line in pipe.stdout:
            if self.script in line.decode('utf-8'):
                return True
        return False


    @staticmethod
    def subprocess(
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
                f"code: {prc.returncode}, command: '{cmd}'"
            )
        # Return output (stdout, stderr)
        return (
            prc.stdout.decode("utf-8") if stdout == subprocess.PIPE else None,
            prc.stderr.decode("utf-8") if stderr == subprocess.PIPE else None
        )



class ConfigFile:
    """As everything in this script, assumes superuser privileges. Only filename and content are required. User and group will default to effective user and group values on creation time and permissions default to common text file permissions wrxwr-wr- (0o644).
    Object Properties:
    name            str     Full path and name
    owner           str     Username ('pi', 'www-data', etc)
    group           str     Group ('pi', ...)
    uid             int     User ID
    gid             int     Group ID
    permissions     int     File permissions. Use octal; 0o644
    content         str     What goes into the file.

    Once properties and content are satisfactory, write the file to disk:
    myFile = File(...)
    myFile.create(overwrite = True)
    If you wish the write to fail when the target file already exists, just leave out the 'overwrite'.
    """
    def __init__(
        self,
        name: str,
        content: str,
        owner: str = None,          # None defaults to EUID
        group: str = None,          # None defaults to EGID
        permissions: int = 0o644
    ):
        # Default to effective UID/GID
        owner = pwd.getpwuid(os.geteuid()).pw_name if not owner else owner
        group = grp.getgrgid(os.getegid()).gr_name if not group else group
        self.name           = name
        self._owner         = owner
        self._group         = group
        self._uid           = pwd.getpwnam(owner).pw_uid
        self._gid           = grp.getgrnam(group).gr_gid
        self.permissions    = permissions
        self.content        = content


    def create(self, overwrite = False, createdirs = True):
        def createpath(path: str, uid: int, gid: int, permissions: int = 0o775):
            """Argument path CANNOT contain a filename. The function cannot determine if the last name in path is a file or folder. All directories that are created will have the specified permissions (default: 775)."""
            head, tail = os.path.split(path)
            if not tail:
                head, tail = os.path.split(head)
            if head and tail and not os.path.exists(head):
                try:
                    createpath(head, uid, gid)
                except FileExistsError:
                    pass
                cdir = os.curdir
                if isinstance(tail, bytes):
                    cdir = bytes(os.curdir, 'ASCII')
                if tail == cdir:
                    return
            try:
                os.mkdir(path, permissions)
                # This is added - ownership equal to file ownership
                os.chown(path, uid, gid)
            except OSError:
                if not os.path.isdir(path):
                    raise
        # Begin create()
        if createdirs:
            path = os.path.split(self.name)[0]
            if path:
                createpath(path, self._uid, self._gid)
        mode = "x" if not overwrite else "w+"
        with open(self.name, mode) as file:
            file.write(self.content)
        os.chmod(self.name, self.permissions)
        os.chown(self.name, self._uid, self._gid)


    def replace(self, key: str, value: str):
        """For replacing placeholders/keys. Example: instanceconfig.replace("{{secret_key}}", os.urandom(24))"""
        self.content = self.content.replace(key, value)


    @property
    def owner(self) -> str:
        return self._owner
    @owner.setter
    def owner(self, name: str):
        self._uid           = pwd.getpwnam(name).pw_uid
        self._owner         = name


    @property
    def group(self) -> str:
        return self._group
    @group.setter
    def group(self, name: str):
        self._gid           = grp.getgrnam(name).gr_gid
        self._group         = name


    @property
    def uid(self) -> int:
        return self._uid
    @uid.setter
    def uid(self, uid: int):
        self._uid           = uid
        self._owner         = pwd.getpwuid(uid).pw_name


    @property
    def gid(self) -> int:
        return self._gid
    @gid.setter
    def gid(self, gid: int):
        self._gid           = gid
        self._group         = grp.getgrgid(gid).gr_name


    def __str__(self):
        return "{} {}({}).{}({}) {} '{}'". format(
            oct(self.permissions),
            self._owner, self._uid,
            self._group, self._gid,
            self.name,
            (self.content[:20] + '..') if len(self.content) > 20 else self.content
        )


files = {}

files['application.conf'] = ConfigFile(
    ROOTPATH + '/instance/application.conf',
    """
# -*- coding: utf-8 -*-
#
# Schooner - Simple Course Management System
# Flask application instance configuration
# University of Turku / Faculty of Technology / Department of Computing
#
# application.conf - Jani Tammi <jasata@utu.fi>
#
#   2021-08-14  Initial version.
#
#
# See https://flask.palletsprojects.com/en/1.1.x/config/ for details.
#
#
import os

DEBUG                    = {{debug}}
EXPLAIN_TEMPLATE_LOADING = {{explain_template_loading}}

TOP_LEVEL_DIR            = os.path.abspath(os.curdir)
BASEDIR                  = os.path.abspath(os.path.dirname(__file__))

SESSION_COOKIE_NAME      = 'FLASKSESSION'
SESSION_LIFETIME         = {{session_lifetime}}
SECRET_KEY               = {{secret_key}}


#
# Single Sign-On session validation settings
#
SSO_COOKIE              = '{{sso_cookie}}'
SSO_SESSION_API         = '{{sso_session_api}}'


#
# Flask app logging
#
LOG_FILENAME             = 'application.log'
LOG_LEVEL                = '{{log_level}}'


#
# SQLite3 configuration
#
SQLITE3_DATABASE_FILE   = 'application.sqlite3'


#
# PostgresQL configuration
#
PGSQL_USERNAME          = 'postgres'
PGSQL_PASSWORD          = 'postgres'
PGSQL_DATABASE          = 'schooner'


#
# File upload and download
#
UPLOAD_FOLDER           = '{{upload_folder}}'
UPLOAD_ALLOWED_EXT      = {{upload_allowed_ext}}
DOWNLOAD_FOLDER         = '{{download_folder}}'
DOWNLOAD_URLPATH        = '{{download_urlpath}}'

# EOF

""",
    GITUSER, 'www-data'
)


###############################################################################
#
# Database Scripts
#
class File:

    @staticmethod
    def exists(file: str) -> bool:
        """Tests if file exists (and is an actual file)."""
        if os.path.exists(file):
            if os.path.isfile(file):
                return True
        return False


    @staticmethod
    def _exec_py(
        cmd: str,
        shell: bool = False,
        stdout      = subprocess.DEVNULL,
        stderr      = subprocess.DEVNULL
    ):
        """Executes Python script in a subprocess. Call _exec_py("ls", stdout = subprocess.PIPE), if output is needed."""
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
        if prc.returncode:
            raise ValueError(
                f"Non-zero return code for command '{cmd}'! ({prc.returncode})"
            )
        # Return output (stdout, stderr)
        return (
            prc.stdout.decode("utf-8") if stdout == subprocess.PIPE else None,
            prc.stderr.decode("utf-8") if stderr == subprocess.PIPE else None
        )


    def _exec_py2(
        scriptfilepath: str,
        dbfilepath: str = ''
    ):
        """Simple alternate version."""
        # No clear way to execute with arguments, changed to subprocess
        #exec(open(scriptfilepath).read())
        subprocess.call([scriptfilepath, dbfilepath])
        # TODO: Check outcome!




class pgSQLScript(File):

    @staticmethod
    def _exec_sql(
        script: str,
        dbname: str,
        dbuser: str,
        dbpass: str = None
    ):
        """Indent authentication does not use a password."""
        import psycopg
        cstring = f"dbname={dbname} user={dbuser}"
        if dbpass:
            cstring += f" password={dbpass}"
        with psycopg.connect(cstring) as conn:
            with conn.cursor() as cur:
                # TODO: if cfg['overwrite']: drop database
                cur.execute(open(script, 'r').read())


    @staticmethod
    def execute(file: str, cfg: dict):
        """Executes .sql or .py file"""
        if os.path.splitext(file)[1] not in ('.sql', '.py'):
            raise ValueError(
                f"Unsupported script type '{file}'! (.sql and .py accepted)")
        if file.endswith(".py"):
            return pgSQLScript._exec_py(file, **cfg)
        elif file.endswith(".sql"):
            return pgSQLScript._exec_sql(file, **cfg)
        else:
            raise ValueError(
                f"Unsupported script type! ('{file}')"
            )




class SQLiteScript(File):

    @staticmethod
    def _exec_sql(
        scriptfilepath: str,
        dbfilepath: str
    ):
        """Run multi-command scripts using sqlite3.executescript(). This function has a problem in that it issues commits automatically and does not support clean rollbacks."""
        # Isolation levels:
        # https://docs.python.org/3.8/library/sqlite3.html#sqlite3-controlling-transactions
        with    sqlite3.connect(dbfilepath) as db, \
                open(scriptfilepath, "r") as scriptfile:
            script = scriptfile.read()
            cursor = db.cursor()
            try:
                cursor.executescript(script)
            except:
                db.rollback()
                raise
            else:
                db.commit()
            finally:
                cursor.close()


    @staticmethod
    def execute(file: str):
        """Executes .sql or .py file"""
        if os.path.splitext(file) not in ('.sql', '.py'):
            raise ValueError(
                f"Unsupported script type '{file}'! (.sql and .py accepted)")
        if file.endswith(".py"):
            return pgSQLScript._exec_py(file)
        elif file.endswith(".sql"):
            return pgSQLScript._exec_sql(file)
        else:
            raise ValueError(
                f"Unsupported script type! ('{file}')"
            )





class Identity():
    def __init__(self, user: str, group: str = None):
        """Group will be user's primary group, unless specified. Use requires superuser privileges."""
        self.uid = pwd.getpwnam(user).pw_uid
        if not group:
            self.gid = pwd.getpwnam(user).pw_gid
        else:
            self.gid = grp.getgrnam(group).gr_gid
    def __enter__(self):
        self.original_uid = os.getuid()
        self.original_gid = os.getgid()
        os.setegid(self.uid)
        os.seteuid(self.gid)
    def __exit__(self, type, value, traceback):
        os.seteuid(self.original_uid)
        os.setegid(self.original_gid)

# Example use:
#   with Identity("pi"):
#       do_or_die(
#           'ssh-keygen -b 4096 -t rsa -f /home/pi/.ssh/id_rsa -q -N ""'
#       )


##############################################################################
#
# MAIN
#
##############################################################################

if __name__ == '__main__':

    #
    # Commandline arguments
    #
    parser = argparse.ArgumentParser(
        description     = HEADER,
        formatter_class = argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '-m',
        '--mode',
        help    = "Instance mode. Default: '{}'".format(
            defaults['common']['mode']
        ),
        choices = defaults['choices'],
        dest    = "mode",
        default = defaults['common']['mode'],
        type    = str.upper,
        metavar = "MODE"
    )
    parser.add_argument(
        '--config',
        help    = "Configuration file.",
        dest    = "config_file",
        metavar = "CONFIG_FILE"
    )
    parser.add_argument(
        '-q',
        '--quiet',
        help    = 'Do not display messages.',
        action  = 'store_true',
        dest    = 'quiet'
    )
    parser.add_argument(
        '-f',
        '--force',
        help    = 'Overwrite existing files.',
        action  = 'store_true',
        dest    = 'force'
    )
    args = parser.parse_args()



    #
    # Require root user
    # Checked here so that non-root user can still get help displayed
    #
    if os.getuid() != 0:
        parser.print_help(sys.stderr)
        print("ERROR: root privileges required!")
        print(f"Use: 'sudo {SCRIPTNAME}' (or 'sudo su -' or 'su -')")
        os._exit(1)


    #
    # Read config file, if specified
    #
    if args.config_file:
        cfgfile = configparser.ConfigParser()
        if File.exists(args.config_file):
            try:
                cfgfile.read(args.config_file)
            except Exception as e:
                print("ERROR: Config file read failed! ", e)
                os._exit(-1)
        else:
            print(f"ERROR: Config file '{args.config_file}' does not exist!")
            os._exit(-1)
    else:
        # Use empty dummy, if not specified
        cfgfile = {'System': {}}


    #
    # Combine configuration values
    #
    cfg = {**defaults['common'], **defaults[args.mode], **cfgfile['System']}
    # Add special value; generated SECRET_KEY
    cfg['secret_key'] = os.urandom(24)
    # Unfortunately, argparse object cannot be merged (it's not a dictionary)
    if args.force:
        # Could not test against None, as the 'action=store_true' means that
        # this option value is ALWAYS either True or False
        cfg['overwrite'] = args.force


    # TODO: REMOVE THIS DEV TIME PRINT
    #from pprint import pprint
    #pprint(cfg)


    #
    # Set up logging
    #
    logging.basicConfig(
        level       = logging.INFO,
        filename    = "setup.log",
        format      = "%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
        datefmt     = "%H:%M:%S"
    )
    log = logging.getLogger()
    if not args.quiet:
        log.addHandler(logging.StreamHandler(sys.stdout))



    ###########################################################################
    #
    # Check for application prerequisites
    #
    ###########################################################################
    issues = []
    # Check if PostgreSQL is installed
    # Option #1 - Does 'psql' exist?
    #       'which' return 0 if specified command(s) are found
    # Option #2 - Check service status
    #       'systemctl status postgresql.service' (echo $? to see return code)
    #       'systemctl' return codes:
    #       0 program is running or service is OK
    #       1 program is dead and /var/run pid file exists
    #       2 program is dead and /var/lock lock file exists
    #       3 program is not running
    #       4 program or service status is unknown
    # http://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic.html#INISCRPTACT
    prc = subprocess.run(
        ['systemctl', 'status', 'postgresql.service'],
        shell   = False,
        stdout  = subprocess.DEVNULL,
        stderr  = subprocess.DEVNULL
    )
    if prc.returncode:
        issues.append(
            "PostgreSQL {}".format(
                (
                    "service running OK",
                    "service is dead and /var/run pid file exists",
                    "service is dead and /var/lock lock file exists",
                    "service is not running",
                    "service not found",
                    ": Unknown return code for status!"
                )[5 if prc.returncode > 5 else prc.returncode]
            )
        )
    # Check Python module dependencies
    pymodules = ['psycopg']
    for pymod in pymodules:
        try:
            _ = __import__(pymod)
        except ImportError as e:
            issues.append(f"Python module '{pymod}' not found!")
    if issues:
        print("ERROR: All prerequisites are not met!")
        log.error("Prerequisites not met!")
        for issue in issues:
            print("\t-", issue)
        os._exit(1)
    else:
        log.info("Requirements OK")



    ###########################################################################
    #
    # Application installation
    #
    ###########################################################################
    try:
        #
        # 1. Create 'instance/application.conf'
        #
        log.info("Creating configuration file for Flask application instance")
        log.info(files['application.conf'].name)
        # Replace content {{keys}} with "values"
        for key, value in cfg.items():
            files['application.conf'].replace(
                '{{' + key + '}}',
                str(value)
            )
        # Write out the file
        files['application.conf'].create(overwrite = cfg['overwrite'])



        """ Obsoleted (moved to PostgreSQL)
        #
        # 2. Create application.sqlite3
        #
        dbfile = os.path.join(ROOTPATH, "application.sqlite3")
        log.info("Creating application database")
        # Because sqlite3.connect() has no open mode parameters
        if cfg['overwrite']:
            try:
                os.remove(dbfile)
            except:
                pass
        for script in [f for f in dbscripts if cfg['mode'] in f['mode']]:
            log.debug(f"processing DB script '{script}'")
            if script['filename'].endswith(".sql"):
                execute_sql(script['filename'], dbfile)
            elif script['filename'].endswith(".py"):
                execute_python(script['filename'], dbfile)
            else:
                raise ValueError(
                    f"Unsupported script type! ('{script['filename']}')"
                )
        #
        # Set owner and permissions for the database file
        #
        do_or_die(f"chown {GITUSER}.www-data {dbfile}")
        do_or_die(f"chmod 664 {dbfile}")
        """
        #
        # 2. Create PostgreSQL database
        #
        log.info("Creating application database")
        for script in [f for f in dbscripts if cfg['mode'] in f['mode']]:
            log.debug(f"\t{script['label']}'{script['filename']}'")
            # NOTE: Don't add extra args to cfg dict, add them to a new
            #       new dictionary. E.g., ..., {**cfg, 'shell' : True})
            with Identity(script['dbuser']):
                pgSQLScript.execute(script['filename'], { **cfg, **script })



        #
        # 3. Create 'cron.jobs/system.conf' and schedule the cron jobs
        #
        import configparser
        sitecfg = configparser.ConfigParser(
            {"# Automatically generated by setup.py": None},
            allow_no_value = True
        )
        sitecfg.optionxform = lambda option: option # Preserve case
        sitecfg.add_section("System")
        sitecfg.set('System', 'UPLOAD_DIR',   cfg['upload_folder'])
        sitecfg.set('System', 'DOWNLOAD_DIR', cfg['download_folder'])
        sitecfg.set('System', 'DATABASE',     os.path.join(ROOTPATH, 'application.sqlite3'))
        sitecfg.set('Site', 'ALLOWED_EXT',  ', '.join(cfg['upload_allowed_ext']))
        with open("cron.job/system.conf", "w") as sitecfgfile:
            sitecfg.write(sitecfgfile)

        # Install cron jobs
        #   Required cronjobs dictionary keys are ('script', 'schedule'):
        #   { 'titlestring':
        #       {'script': str, 'schedule': str[,'user': str]},
        #       ... 
        #   }
        # 'script'      filepath relative to the path of this script
        # 'schedule'    crontab "* * * * *" format
        # 'user'        (optional) to run cron job as user (other than root)
        for title, jobDict in cronjobs.items():
            cronjob = CronJob(**jobDict)
            if cronjob.exists:
                if cfg['overwrite']:
                    cronjob.remove()
                    log.info(f"Pre-existing job '{title}' removed")
                else:
                    log.error(f"Job '{title}' already exists")
                    raise ValueError(
                        f"Job '{title}' already exists!"
                    )
            log.info(f"Creating cron job to {title}")
            cronjob.create()


    except Exception as e:
        msg = "SETUP DID NOT COMPLETE SUCCESSFULLY!"
        if args.quiet:
            print(msg)
            print(str(e))
        else:
            log.exception(msg)


    else:
        log.info("Setup completed successfully!")


# EOF
