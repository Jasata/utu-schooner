#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Template.py - Data dictionary class for email.template
#   2021-08-27  Initial version.
#
import jinja2


class Template(dict):

    class NotSent(Exception):
        def __init__(self, message: str):
            super().__init__(message)

    def __init__(self, cursor, template_id: str = None):
        self.cursor = cursor
        SQL = """
            SELECT      *
            FROM        email.template
            WHERE       template_id = %(template_id)s
        """
        if cursor.execute(SQL, locals()).rowcount:
            self.update(
                dict(
                    zip(
                        [key[0] for key in cursor.description],
                        cursor.fetchone()
                    )
                )
            )
        elif template_id is None:
            # Create empty dict
            self.update(
                dict(
                    zip(
                        [key[0] for key in cursor.description],
                        [None] * len(cursor.description)
                    )
                )
            )
        else:
            raise ValueError(f"Template '{template_id}' not found!")


    def parse_and_send(
        self,
        course_id: str,
        uid: str,
        kwargs: dict
    ) -> int:
        """Recipient identified as an enrollee (course_id, uid) because emails are only ever sent for enrolled course. Caller must source (email.jtd_* functions) or prepare correctly populated dictionary for th Jinja parser. Function returns the message_id for the created message."""
        SQL = """
            SELECT      course.course_id,
                        course.code AS course_code,
                        enrollee.uid,
                        COALESCE(course.email, 'do-not-reply@utu.fi') AS sent_from,
                        enrollee.email AS sent_to,
                        NULL AS subject,
                        NULL AS body,
                        enrollee.notifications
            FROM        core.course INNER JOIN
                        core.enrollee ON (course.course_id = enrollee.course_id)
            WHERE       course.course_id = %(course_id)s
                        AND
                        enrollee.uid = %(uid)s
        """
        if not self.cursor.execute(SQL, locals()).rowcount:
            raise ValueError(
                f"Unable to find enrollee ('{course_id}', '{uid}')!"
            )
        message = dict(
            zip(
                [key[0] for key in self.cursor.description],
                self.cursor.fetchone()
            )
        )
        #
        # Enrollee may have opted NOT to receive notifications
        #
        if message['notifications'] == 'disabled':
            raise Template.NotSent(
                f"Enrollee ('{course_id}', '{uid}') has set notifications OFF."
            )
        elif not message['sent_to']:
            raise Template.NotSent(
                f"Enrollee ('{course_id}', '{uid}') has no email address."
            )

        # Parse subject and body, and add/change few others
        message['subject'] = jinja2.Environment(
            loader=jinja2.BaseLoader
        ).from_string(
            self['subject']
        ).render(
            **kwargs
        )
        message['body'] = jinja2.Environment(
            loader=jinja2.BaseLoader
        ).from_string(
            self['body']
        ).render(
            **kwargs
        )
        message['mimetype'] = self['mimetype']
        message['priority'] = self['priority']
        # "Namify" sender with course code
        if message['course_code']:
            message['sent_from'] = f"{message['course_code']} <{message['sent_from']}>"

        SQL = """
            INSERT INTO email.message
            (
                course_id,
                uid,
                mimetype,
                priority,
                sent_from,
                sent_to,
                subject,
                body
            )
            VALUES
            (
                %(course_id)s,
                %(uid)s,
                %(mimetype)s,
                %(priority)s,
                %(sent_from)s,
                %(sent_to)s,
                %(subject)s,
                %(body)s
            )
            RETURNING message_id
        """
        if not self.cursor.execute(SQL, message).rowcount:
            raise ValueError(
                f"Email message queueing failed! (template: '{self['template_id']}', course_id: '{course_id}', recipient uid: '{uid}')"
            )
        message_id = int(self.cursor.fetchone()[0])

        #
        # Copy attachments
        #
        self.cursor.execute(
            """
            INSERT INTO email.attached
            (
                attachment_id,
                message_id
            )
            SELECT      attachment_id,
                        %(message_id)s
            FROM        email.attached
            WHERE       template_id = %(template_id)s
            """,
            { 'message_id': message_id, 'template_id': self['template_id'] }
        )
        return message_id



# EOF
