#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# AccessToken.py - Class to verify/validate access token (assistant.accesstoken)
#   2021-09-02  Initial version.
#
#
#   Raises AccessToken.InvalidAccessToken if the token is not valid.
#   Has only one attribute: .submission_id
#
#   Possibly later: also create access tokens?
#


class AccessToken:

    class InvalidAccessToken(Exception):
        def __init__(self, message = "Accesstoken is not valid!"):
            self.message = message
            super().__init__(self.message)

    def __init__(self, cursor, token):
        # Function returns the submission_id, if the token is valid
        self.submission_id = None
        SQL = """
            SELECT      assistant.accesstoken_validate(token)
            FROM        assistant.accesstoken
            WHERE       token = %(token)s
        """
        if cursor.execute(SQL, locals()).rowcount:
            self.submission_id = cursor.fetchone()[0]
        if not self.submission_id:
            raise AccessToken.InvalidAccessToken(
                f"Access token '{token}' is not valid!"
            )



# EOF
