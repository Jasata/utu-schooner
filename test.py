#!/bin/env python3

import os
import psycopg
import subprocess



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




    def sort(self, key):
        super().sort(key=lambda k : k[key])



from schooner.db.core   import EnrolleeList
from schooner.db.core   import AssignmentList
from schooner.db.core   import CourseList

import datetime


if __name__ == '__main__':

    with psycopg.connect(f"dbname=schooner").cursor() as cursor:
        """
        course_list = CourseList(
            cursor,
#            handlers = ['HUBBOT', 'HUBREG', 'BOGUS'],
#            opens = '2021-08-25 00:00:00'
            opens = datetime.datetime(2021, 8, 25, 0, 0, 0, 0)
#            github_account = 'DTEK0068'
        )
        
        print("Found", len(course_list), "matching courses:")
        course_list.sort('course_id')
        for c in course_list:
            print(c['course_id'], c['opens'])


        my_courses = EnrolleeList(
            cursor, course_id = 'DTEK0000-3002'
        )
        my_courses.sort('uid')
        print("Total of", len(my_courses), "enrollments:")
        for row in my_courses:
            print(row['course_id'], row['uid'])


        al = AssignmentList(cursor, course_id = 'DTEK0068-3002')
        al.sort("deadline")
        for a in al:
            print(a['assignment_id'], a['name'], a['deadline'])

        cl = CourseList(cursor, uid = 'jasata')
        for c in cl:
            print(c['code'], c['name'])
        """

        from schooner.db.assistant import Assistant
        from schooner.db.assistant import AssistantList

        print("=== Assistants for course DTEK0068-3002")
        al = AssistantList(cursor, course_id = 'DTEK0068-3002')
        al.sort('assistant_uid', desc=True)
        for a in al:
            for k, v in a.items():
                print(k, "=", v)
        print("and again.....")
        al.sort('assistant_uid', desc=False)
        for a in al:
            for k, v in a.items():
                print(k, "=", v)

        a = Assistant(cursor, 'DTEK0000-3002', 'jasata')
        if a.currently_evaluating():
            print("Currently evaluating")
        else:
            print("Currently slacking off")

        """
        print("=== Courses for assistant jasata")
        cl = AssistantList(cursor, uid = 'jasata')
        for c in cl:
            for k, v in c.items():
                print(k, "=", v)

        from schooner.api       import AssistantWorkqueue
        q = AssistantWorkqueue(cursor, 'jasata', course_id = 'DTEK0068-3002')
        for s in q:
            for k, v in s.items():
                print(k, "=", v)
        """

    """
    # Why does this print root keys twice?
    from schooner.util import AppConfig
    allCfg = AppConfig("cron.job/app.conf")
    for k, v in allCfg.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                print(f"{k}.{k2} = {v2}")
        else:
            print(f"{k} = {v}")
        for k, v in cfg.items():
            print(k, "=", v)

    for k in allCfg.keys():
        print("KEY", k)
    """



# EOF