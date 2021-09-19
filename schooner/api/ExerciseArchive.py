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
#
# Serving large files
#
#       This is not an issue for now. However, this note is left behind,
#       should large (100MB+) exercise archives become reality.
#
#       In theory, generator function should solve the issue as follows:
#
#   def create(self) -> flask.response:
#       def generate(filename: str):
#           with open(filename) as src:
#               yield from src
#           os.remove(filename)     # Removes the archive once sent
#
#       response = app.response_class(
#           generate(),
#           mimetype="application/gzip"
#       )
#       response.headers.set(
#           'Content-Disposition',
#           'attachment',
#           filename = self.filename
#       )
#       response.headers.set(
#           'X-SubmissionID',
#           self.submission_id
#       )
#       return response
#
import os
from schooner.db.core       import Submission
from schooner.db.system     import Config


class ExerciseArchive:
    """Utility class to create downloadable archives of exercises (fetched by hubbot). Requires a valid accesstoken (assistant.accesstoken -table)."""

    class InvalidAccessToken(Exception):
        def __init__(self, message = "Accesstoken is not valid!"):
            self.message = message
            super().__init__(self.message)


    def __init__(self, cursor, token: int):
        """Validates access token and sets up attributes: .submission_id, .path (to-be archived), .filename (temporary archive for sending)."""
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
        # Get course, assignment and user IDs for HTTP header
        #
        SQL = """
            SELECT      course_id,
                        assignment_id,
                        uid
            FROM        core.submission
            WHERE       submission_id = %(submission_id)s
        """
        cursor.execute(SQL, {'submission_id' : self.submission_id})
        self.course_id, self.assignment_id, self.uid = cursor.fetchone()
        #
        # Parse path and file
        #
        submission = Submission(cursor, self.submission_id)
        self.exercise_path = os.path.join(
            Config(cursor).submissions_directory,
            submission['course_id'],
            submission['uid'],
            submission['assignment_id'],
            "accepted"
        )
        self.filename = os.path.join(
            "{}_{}_{}_#{}.tar.gz".format(
                submission['course_id'],
                submission['assignment_id'],
                submission['uid'],
                submission['submission_id']
            )
        )
        self.local_tarfile = os.path.join(
            "/tmp/",
            self.filename
        )
        # Check that the path exists as a directory / softlink
        if not os.path.isdir(self.exercise_path):
            raise Exception(
                f"Path '{self.exercise_path}' either does not exist or is not a directory!"
            )




    def send(self) -> str:
        import tarfile
        from application import app

        def generate(filename: str):
            with open(filename, 'rb') as f:
                yield from f
            os.remove(filename)

        # Create temporary tar (deleted by generate())
        with tarfile.open(self.local_tarfile, "w:gz", dereference=True) as tar:
            tar.add(self.exercise_path, arcname=os.path.basename(self.exercise_path))

        response = app.response_class(
            generate(self.local_tarfile),
            mimetype            = 'application/gzip',
            direct_passthrough  = True
        )
        response.headers.set(
            "Content-Disposition",
            "attachment",
            filename = self.filename
        )
        response.headers.set(
            "X-CourseID",
            self.course_id
        )
        response.headers.set(
            "X-AssignmentID",
            self.assignment_id
        )
        response.headers.set(
            "X-UserID",
            self.uid
        )
        response.headers.set(
            "X-SubmissionID",
            self.submission_id
        )
        response.headers.set(
            "X-Redirect",
            f"https://schooner.utu.fi/assistant_evaluation.html?sid={self.submission_id}"
        )
        return response




    def create_old(self):
        import tarfile
        #https://stackoverflow.com/questions/2032403/how-to-create-full-compressed-tar-file-using-python
        with tarfile.open(self.filename, "w:gz", dereference=True) as tar:
            tar.add(self.exercise_path, arcname=os.path.basename(self.exercise_path))
        #
        # Return archive filename
        #
        return self.filename




# EOF