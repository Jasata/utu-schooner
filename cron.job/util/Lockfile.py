#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Lockfile.py - Simple lockfile implementation to prevent concurrent execution
#   2018-11-15  Initial version.
#   2018-11-18  Static status methods added.
#   2021-08-28  Locking fixed (status reports still bug).
#
#
"""
os.O_RDONLY: opened in read-only mode
os.O_WRONLY: opened in write-only
os.O_RDWR: opened in read and write
os.O_NONBLOCK: open without blocking
os.O_APPEND: Open in additional
os.O_CREAT: Create and open a new file
os.O_TRUNC: Open a file and truncate it to zero length (must have write permission)
os.O_EXCL: If the specified file exists, an error is returned
os.O_SHLOCK: automatically acquire a shared lock
os.O_EXLOCK: lock automatically obtain independent
os.O_DIRECT: eliminate or reduce the effect of caching
os.O_FSYNC: synchronous write
os.O_NOFOLLOW: Not Track soft links
"""
import os
import sys
import time
import fcntl
import errno


class Lockfile:

    class AlreadyRunning(Exception):
        def __init__(self, message: str = "Already running!"):
            super().__init__(message)
            self.message = message


    def __init__(self, filename: str):
        """Create a lock file and write current PID into it."""
        self.name = filename
        self.fd = os.open(filename, os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        try:
            # Get an exclusive lock. Fails if another process has the files locked.
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            os.close(self.fd)
            raise Lockfile.AlreadyRunning() from None
        except BlockingIOError as e:
            os.close(self.fd)
            if e.errno == errno.EAGAIN:
                # Action failed due to locking
                raise Lockfile.AlreadyRunning() from None
            else:
                raise
        # Record the process id to pid and lock files.
        os.write(self.fd, f"{os.getpid()}".encode())
        os.fsync(self.fd)


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
            fd = os.open(filename, os.O_RDWR)
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            return (True, True)
        except BlockingIOError as e:
            if e.errno == errno.EAGAIN:
                return (True, True)
        finally:
            try:
                os.close(fd)
            except:
                pass
        return (True, False)

    @staticmethod
    def status_report(filename: str) -> str:
        t = Lockfile.file_status(filename)
        if t[1]:
            return f"Lockfile '{filename}' exists and is locked!"
        if t[0]:
            return f"Lockfile '{filename}' exists but is NOT locked!"
        return f"Lockfile '{filename}' does not exist."




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