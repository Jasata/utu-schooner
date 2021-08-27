#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Turku University (2018) Department of Future Technologies
# Foresail-1 / PATE Monitor / Middleware (PMAPI)
# PSU controller daemon
#
# main.py - Jani Tammi <jasata@utu.fi>
#   2018-11-15  Initial version.
#   2018-11-18  Static status methods added.
#
#
# Provide a combined lock/PID file for user space daemon.
#
import os
import sys
import time
import fcntl
import errno

class Lockfile:
    class AlreadyRunning(Exception):
        def __init__(self, pid = None, message = "Already running!"):
            super().__init__(message)
            self.message    = message
            self.pid        = pid
        def __str__(self):
            return f"PID: {self.pid or 'unknown'}: {self.message}"

    def __init__(self, name: str):
        """Create a lock file and write current PID into it."""
        self.name = name
        if os.path.isfile(name):
            print(f"Lockfile '{name}' exists...")
        else:
            open(name, os.O_APPEND | os.O_EXCL | os.O_RDWR)
        try:
            try:
                self.fd = open(self.name, 'r+') # Open existing, do not tuncate
            except FileNotFoundError:
                self.fd = open(self.name, 'w+') # Create and truncate
            # Get an exclusive lock. Fails if another process has the files locked.
            fcntl.lockf(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Record the process id to pid and lock files.
            self.fd.write(f"{os.getpid()}")
            self.fd.flush()
        except BlockingIOError as e:
            if e.errno == errno.EAGAIN:
                # Action failed due to locking
                pid = self.fd.readline()
                raise Lockfile.AlreadyRunning(
                    pid or "unknown",
                    "Another process already running!"
                ) from None
            else:
                raise
        except Exception as e:
            raise

    def touch(self):
        """Update access and modified times of the lockfile."""
        os.utime(self.name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        except:
            pass
        # raise if other than "no such file or directory" exception
        try:
            os.remove(self.name)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    @staticmethod
    def file_status(filename: str) -> tuple:
        """Returns (exists: bool, locked: bool). Checks if lock file exists and if the file is locked. NOTE: Can also raise PermissionError (13), if the daemon has been started as another user (or super user). This condition is to be handled by the caller."""
        if not os.path.isfile(filename):
            return (False, False)
        # Exists - test for a lock
        try:
            fd = open(filename, 'a')
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            if e.errno == errno.EAGAIN:
                return (True, True)
        finally:
            try:
                fd.close()
            except:
                pass
        return (True, False)

    @staticmethod
    def status_report(filename: str) -> str:
        t = Lockfile.file_status(filename)
        if not t[0]:
            return f"Lockfile '{filename}' does not exist!"
        if not t[1]:
            return f"Lockfile '{filename}' is not locked!"
        return "OK"

if __name__ == '__main__':
    filename = "/tmp/locktest.lock"
    def print_status(f):
        print(
            "{s:.<60} {p}".format(
                s=filename,
                p=Lockfile.status_report(filename)
            )
        )
    print("This WILL report 'Not locked!' because it is this same process that created the lock file and thus, for us, there will be no issues (re-)acquiring the same lock. Another process would report the lock correctly.")
    print_status(filename)
    try:
        with Lockfile(filename):
            print_status(filename)
            time.sleep(3)
    except Lockfile.AlreadyRunning as e:
        print(str(e))
    print_status(filename)

# EOF