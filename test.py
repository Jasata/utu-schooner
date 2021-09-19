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



import json
import requests
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


class GitAssignment(dict):

    SQL = """
    SELECT      directives
    FROM        core.assignment
    WHERE       course_id = %(course_id)s
                AND
                assignment_id = %(assignment_id)s
    """

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
        self.directive = copy.deepcopy(GitAssignment.default_directives)
        jsonstring = self.pop("directives", None)
        if jsonstring:
            self.directive.update(json.loads(jsonstring))


    def triggers(self, contents: list) -> bool:
        """Returns list of files/directories specified by directives.fetch.trigger."""
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



class GitRepositoryNotFound(Exception):
    pass

class GitCloneNotTriggered(Exception):
    pass


if __name__ == '__main__':

    import fnmatch
    import datetime
    from schooner.db.core import Enrollee

    cid, aid, uid = ('DTEK0002-3002', 'E01', 'jasata')
    tgt = os.path.join(
        "/srv/schooner/submissions",
        cid,
        uid,
        aid
    )
    if not os.path.exists(tgt):
        os.makedirs(tgt)

    #
    # Replicating --clone invokation of hubbot.py
    #
    try:
        with psycopg.connect(f"dbname=schooner").cursor() as cursor:
            # Line 296
            repository = GitRepo(
                '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',
                'kaislahattu'
            )
            assignment = GitAssignment(cursor, cid, aid)
            enrollee = Enrollee(cursor, cid, uid)

            # Line 332 - Check that the student repository exists
            if not repository.exists(
                enrollee['github_account'],
                enrollee['github_repository']
            ):
                raise GitRepositoryNotFound(
                    "Student '{}' GitHub repository 'git@github.com:{}/{}.git' not found".format(
                        enrollee['uid'],
                        enrollee['github_account'],
                        enrollee['github_repository']
                    )
                )
            else:
                # log.debug()
                print(
                    "Student '{}' GitHub repository 'git@github.com:{}/{}.git'".format(
                        enrollee['uid'],
                        enrollee['github_account'],
                        enrollee['github_repository']
                    )
                )

            # Line 353 - Check if submission directory exists
            # NOTE: Now, directives trigger based
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
            repodir = os.path.join(
                tgt,
                datetime.datetime.now().strftime('%Y-%m-%d')
            )
            if os.path.exists(repodir):
                import shutil
                shutil.rmtree(repodir)


            #
            # Execute clone
            #
            import git
            git.Git(tgt).clone(repository.URL.source, fetchdate)
            with psycopg.connect(cstring) as conn:
                with conn.cursor() as cursor:
                    # This call also sends a success message.
                    assignment.register_as_submission(cursor, student, assignment)
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
        print(str(e))
        #sys.stdout.write(str(e))

    """
    entries = [
        item['name']
        for item
        in  repository.contents('jasata', 'DTE20068')
        if  item['type'] == require['type']
            and
            fnmatch.fnmatch(item['name'], require['name'])
    ]
    try:
        #l = [d for d in repository.contents if fnmatch.fnmatch(d['name'], pattern)]
        if len(entries) > 1:
            raise Exception(
                "Multiple {} matching '{}' found in repository: {}. ".format(
                    "directories" if require['type'] == 'dir' else "files",
                    require['name'],
                    entries
                ) + 
                "System is unable to determine which one is the intended submission. " +
                "Your repository has been cloned in its entirety and now you must contact your course instructors to specify which directory will be used. Do so immediately, because your submission will be rejected unless you have done so by the time submissions are evaluated!"
            )
        if len(entries) < 1:
            raise Exception(
                f"Required {require['type']} '{require['name']}' not found in repository!"
            )
    except Exception as e:
        print(str(e))

    #print(len(l))
    """

# EOF