#!/bin/env python3

import os
import pwd
import grp
import subprocess
import datetime
import psycopg


ROOTPATH = os.path.split(os.path.realpath(__file__))[0]

cfg = {
    'dbname': 'postgres',
    'dbuser': 'postgres',
    'dbpass': None
}


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

def createpath(path, uid, gid, permissions = 0o775):
    """Argument path can contain a filename. If the path has no filename, it must end with '/' character - otherwise the function assumes the last name to be a file! All directories that are created will have the specified permissions (default: 775)."""
    head, tail = os.path.split(path)
    print(head, tail)
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
        """Simple alternate version. SQLite3 only..."""
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
        """Executes .sql or .py file."""
        print("CFG", cfg)
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
        import sqlite3
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
    def execute(file: str, cfg: dict):
        """Executes .sql or .py file"""
        if os.path.splitext(file) not in ('.sql', '.py'):
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


class Enrollee(dict):


    def __custom_get__(self, key):
        """For all DotDict.key access, missing or otherwise."""
        return self.get(key, self.get('*', None))


    __getattr__ = __custom_get__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


    def __missing__(self, key):
        """For DefaultDotDict[key] access, missing keys."""
        return self.get('*', None)


    def __init__(self, course_id: str, uid: str) -> None:
        """Queries enrollee data."""
        SQL = """
            SELECT      *
            FROM        enrollee
            WHERE       course_id = %(course_id)s
                        AND
                        uid = %(uid)s
            """
        cstring = "dbname=schooner user=schooner"
        with psycopg.connect(cstring).cursor() as c:
            if c.execute(SQL, locals()).rowcount:
                self.update(dict(zip([key[0] for key in c.description], c.fetchone())))
            else:
                raise ValueError(f"Enrollee ('{course_id}', '{uid}') not found!")


    def gitcourseids(self, ongoing: bool = True) -> list:
        """Query the list of course-dictinaries in which the student has an *active* enrollment (enrollee.status = 'active'), and which have GitHub registration assignment(s). List is limited to courses that are open, unless parameter 'ongoing' is defined as False"""
        return [c['course_id'] for c in self.gitcourses(ongoing)]


    def gitcourses(self, ongoing: bool = True) -> list:
        """Query the list of course-dictionaries in which the student has an *active* enrollment (enrollee.status = 'active'), and which have GitHub registration assignment. List is limited to courses that are open, unless parameter 'ongoing' is defined as False"""
        SQL = """
            SELECT  gitcourse.*
            FROM    enrollee
                    INNER JOIN
                    (
                        SELECT      course.*
                        FROM        course
                        WHERE       course_id IN (
                                        SELECT      course_id
                                        FROM        assignment
                                        WHERE       handler = 'HUBREG'
                                    )
                    ) gitcourse
                    ON (enrollee.course_id = gitcourse.course_id)
            WHERE	enrollee.status = 'active'
                    AND
                    enrollee.uid = %(uid)s
            """
        if ongoing:
            SQL += """
                    AND
                    gitcourse.opens <= CURRENT_TIMESTAMP
                    AND
                    (
                        gitcourse.closes IS NULL
                        OR
                        gitcourse.closes >= CURRENT_TIMESTAMP
                    )
            """
        cstring = "dbname=schooner user=schooner"
        with psycopg.connect(cstring).cursor() as c:
            c.execute(SQL, { 'uid' : self.uid })
        return [dict(zip([key[0] for key in c.description], row)) for row in c]



class Course(dict):

    def __custom_get__(self, key):
        """For all DotDict.key access, missing or otherwise."""
        return self.get(key, self.get('*', None))


    __getattr__ = __custom_get__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


    def __missing__(self, key):
        """For DefaultDotDict[key] access, missing keys."""
        return self.get('*', None)


    def __init__(self, course_id: str):
        """Course implementation."""
        SQL = """
            SELECT      *
            FROM        course
            WHERE       course_id = %(course_id)s
        """
        cstring = f"dbname=schooner user=schooner"
        with psycopg.connect(cstring).cursor() as c:
            if c.execute(SQL, locals()).rowcount:
                self.update(dict(zip([key[0] for key in c.description], c.fetchone())))
            else:
                raise ValueError(f"Course ('{course_id}') not found!")


    @property
    def is_ongoing(self):
        now = datetime.datetime.now()
        if self.opens < now:
            if self.closes and self.closes > now:
                return True
        return False


    def __repr__(self) -> str:
        string = ""
        for attr, value in self.__dict__.items():
            string += f"Course.{attr} = {value}\n"
        return string




class GitHubAccountRegistration(dict):
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


    def __init__(self, course_id: str, uid: str) -> None:
        """Load object with registration data."""
        SQL = """
            SELECT      submission.*,
                        course.opens AS course_opens,
                        course.closes AS course_closes,
                        enrollee.github_account,
                        enrollee.github_repository,
                        enrollee.studentid AS enrollee_studentid
            FROM        enrollee INNER JOIN course
                        ON (enrollee.course_id = course.course_id)
                        INNER JOIN (
                            -- Unique index guarantees that there can only be
                            -- zero or one 'HUBREG' assignments per course.
                            SELECT      assignment.*
                            FROM        assignment
                            WHERE       handler = 'HUBREG'
                        ) hubregassignment
                        ON (course.course_id = hubregassignment.course_id)
                        LEFT OUTER JOIN submission
                        ON (
                            hubregassignment.course_id = submission.course_id
                            AND
                            hubregassignment.assignment_id = submission.assignment_id
                        )
            WHERE       enrollee.course_id = %(course_id)s
                        AND
                        enrollee.uid = %(uid)s
                        AND
                        submission.uid = %(uid)s
        """
        SQL = """
            SELECT 		course.course_id,
                        course.opens AS course_opens,
                        course.closes AS course_closes,
                        enrollee.uid,
                        CASE
                            WHEN enrollee.studentid IS NULL THEN 'n'
                            ELSE 'y'
                        END AS has_enrolled,
                        CASE
                            WHEN submission.assignment_id IS NULL THEN 'n'
                            ELSE 'y'
                        END AS has_submission,
                        enrollee.github_account,
                        enrollee.github_repository,
                        assignment.assignment_id,
                        assignment.deadline,
                        submission.content,
                        submission.state,
                        submission.evaluator,
                        submission.score,
                        submission.created,
                        submission.modified
            FROM		(
                            SELECT		*
                            FROM		enrollee
                            WHERE		uid = %(uid)s
                                        AND
                                        course_id = %(course_id)s
                        ) enrollee RIGHT OUTER JOIN course
                        ON (enrollee.course_id = course.course_id)
                        LEFT OUTER JOIN (
                            -- Unique index guarantees that there can be only one (or none) 'HUBREG' assignments
                            SELECT		assignment.*
                            FROM		assignment
                            WHERE		handler = 'HUBREG'
                        ) assignment
                        ON (course.course_id = assignment.course_id)
                        LEFT OUTER JOIN (
                            SELECT		*
                            FROM		submission
                            WHERE		uid = %(uid)s
                        ) submission
                        ON (
                            assignment.course_id = submission.course_id
                            AND
                            assignment.assignment_id = submission.assignment_id
                        )
            WHERE		course.course_id = %(course_id)s
        """
        cstring = f"dbname=schooner user=schooner"
        with psycopg.connect(cstring).cursor() as c:
            if c.execute(SQL, locals()).rowcount:
                self.update(dict(zip([key[0] for key in c.description], c.fetchone())))
            else:
                raise ValueError(f"Course ('{course_id}') not found!")
                #self.update(dict(zip([key[0] for key in c.description], [None] * len(c.description))))
        # Other exceptional reasons
        if not self.assignment_id:
            raise ValueError(f"Course ('{course_id}') does not have GitHub account registration!")
        if not self.uid:
            raise ValueError(f"Student ('{uid}') is not enrolled in course ('{course_id}')!")



    @property
    def is_enrolled(self) -> bool:
        """True, if student has been enrolled to the course."""
        return True if self.has_enrolled == 'y' else False

    @property
    def has_submission(self) -> bool:
        """True, if student has HUBREG submission."""
        return True if self.has_submission else False

    @property
    def is_open(self):
        """Is registration-assignment deadline passed?"""
        return True if self.deadline > datetime.datetime.now() else False


if __name__ == '__main__':

    """
    issues = []
    # Check if PostgreSQL is installed (does 'psql' exist?)
    # 'which' return 0 if specified command(s) are found
    import subprocess
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

    pymodules = ['psycopg']
    for pymod in pymodules:
        try:
            _ = __import__(pymod)
        except ImportError as e:
            issues.append(f"Python module '{pymod}' not found!")
    if issues:
        print("ERROR: All prerequisites are not met!")
        for issue in issues:
            print("\t-", issue)
        os._exit(1)
    else:
        print("Requirements OK")



    for script in [f for f in dbscripts]:
        print(f"\t{script['label']}'{script['filename']}'")
        # NOTE: Don't add extra args to cfg dict, add them to a new
        #       new dictionary. E.g., ..., {**cfg, 'shell' : True})
        with Identity(script['dbuser']):
            pgSQLScript.execute(script['filename'], { **cfg, **script })
    """

    s = Enrollee('DTE20068-3002', 'tumipo')
    # List of courses that use GitHub
    print(s.gitcourseids())

    c = Course('DTE20068-3003')
    print(c)
    print(c.opens)
    print("Is on-going:", c.is_ongoing)


    """ OK 2021-08-19
    print(GitHubAccountRegistration('DTE20068-3002', 'tumipo'))
    print(GitHubAccountRegistration('DTE20068-3002', 'jasata'))
    print(GitHubAccountRegistration('DTE20068-3003', 'tumipo'))
    print(GitHubAccountRegistration('DTE20068-3003', 'jasata'))

    rg = GitHubAccountRegistration('DTE20068-3003', 'jasata')
    print("Registration is", "open" if rg.is_open else "closed")
    """


