#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# ExerciseArchive.py - Class to retrieve and archive exercise for download.
#   2021-09-02  Initial version.
#
import os
import tarfile
from schooner.db.core       import Submission
from schooner.db.system     import Config


class ExerciseArchive:

    class InvalidAccessToken(Exception):
        def __init__(self, message = "Accesstoken is not valid!"):
            self.message = message
            super().__init__(self.message)


    def __init__(self, cursor, token: int):
        self.directory = Config(cursor).submissions_directory
        SQL = """
            SELECT assistant.accesstoken_validate(%(token)s)
        """
        # Query always returns a row: NULL or the submission_id (if valid)
        self.submission_id = cursor.execute(SQL, locals()).fetchone()[0]
        if not self.submission_id:
            raise ExerciseArchive.InvalidAccessToken(
                f"Access token is not valid! ({self.submission_id})"
            )
        #
        # Parse path and file
        #
        submission = Submission(cursor, self.submission_id)
        self.path = os.path.join(
            self.directory,
            submission['course_id'],
            submission['uid'],
            submission['assignment_id'],
            "accepted"
        )
        self.filename = "/tmp/" + str(self.submission_id) + ".tar.gz"
        # Check that the path exists as a directory / softlink
        if not os.path.isdir(self.path):
            raise Exception(
                f"Path '{self.path}' either does not exist or is not a directory!"
            )


    def create(self) -> str:
        #https://stackoverflow.com/questions/2032403/how-to-create-full-compressed-tar-file-using-python
        with tarfile.open(self.filename, "w:gz", dereference=True) as tar:
            tar.add(self.path, arcname=os.path.basename(self.path))
        #
        # Return archive filename
        #
        return self.filename



# EOF