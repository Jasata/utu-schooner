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


class Counter(dict):
    ERR = False
    OK  = True
    def __init__(self):
        self.__n = 0
        self.__e = 0
    def add(self, x: bool = True):
        self.__n += 1
        self.__e += int(not x)
    @property
    def total(self):
        return self.__n
    @property
    def errors(self):
        return self.__e
    @property
    def successes(self):
        return self.__n - self.__e
    def __repr__(self):
        return f"{self.__e} errors out of {self.__n} total"

if __name__ == '__main__':


    cnt = Counter()
    cnt.add(Counter.ERR)
    cnt.add()
    print(cnt)
