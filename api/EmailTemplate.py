#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# EmailTemplate.py - GitHub account registration data
#   2021-08-24  Initial version.
#   
#
# Parses Jinja message templates.
#

import jinja2
import datetime
from flask import g


class EmailTemplate(dict):
    """Retrieve email template and parse it (as Jinja)."""


    def __custom_get__(self, key):
        """For all DotDict.key access, missing or otherwise."""
        return self.get(key, self.get('*', None))


    __getattr__ = __custom_get__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


    def __missing__(self, key):
        """For DefaultDotDict[key] access, missing keys."""
        return self.get('*', None)


    def __init__(self, template_id: str) -> None:
        SQL = """
            SELECT      *
            FROM        email.template
            WHERE       template_id = %(template_id)s
        """
        with g.db.cursor() as c:
            if c.execute(SQL, locals()).rowcount:
                self.update(dict(zip([key[0] for key in c.description], c.fetchone())))
            else:
                raise ValueError(f"Email template '{template_id}' not found!")


    def parse_and_send(
        self,
        course_id: str,
        uid: str,
        params: dict
    ) -> int:
        """Apply provided arguments into the message template and queue message for sending. Returns message_id."""
        SQL = """
            SELECT      course.course_id,
                        course.code AS course_code,
                        enrollee.uid,
                        COALESCE(course.email, 'do-not-reply@utu.fi') AS sent_from,
                        enrollee.email AS sent_to,
                        NULL AS subject,
                        NULL AS body
            FROM        core.course INNER JOIN
                        core.enrollee ON (course.course_id = enrollee.course_id)
            WHERE       enrollee.email IS NOT NULL
                        AND
                        course.course_id = %(course_id)s
                        AND
                        enrollee.uid = %(uid)s
        """
        with g.db.cursor() as c:
            if not c.execute(SQL, locals()).rowcount:
                raise ValueError(
                    f"Unable to find enrollee ('{course_id}', '{uid}')!"
                )
            message = dict(zip([key[0] for key in c.description], c.fetchone()))

            # Parse subject and body, and add/change few others
            message['subject'] = jinja2.Environment(
                loader=jinja2.BaseLoader
            ).from_string(self.subject).render(**params)
            message['body'] = jinja2.Environment(
                loader=jinja2.BaseLoader
            ).from_string(self.body).render(**params)
            message['mimetype'] = self.mimetype
            message['priority'] = self.priority
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
            if not c.execute(SQL, message).rowcount:
                raise ValueError(
                    f"Email message queueing failed! (template: '{self.code}', course_id: '{course_id}', recipient uid: '{uid}')"
                )
            self.message_id = int(c.fetchone()[0])

            #
            # Copy attachments
            #
            c.execute(
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
                self
            )

            g.db.commit()

        return self.message_id


    def get_keys(self) -> list:
        """Retrieves all the needed keys to parse this template."""
        # This function would be useful to check if keys are available...
        #https://stackoverflow.com/questions/8260490/how-to-get-list-of-all-variables-in-jinja-2-templates
        env = jinja2.Environment(loader=jinja2.BaseLoader)
        template = env.from_string(self.body)
        parsed = env.parse(template)
        return jinja2.meta.find_undeclared_variable(parsed) # HAS NO .meta !!!



if __name__ == '__main__':

    # MUST execute as local user 'schooner'
    import psycopg
    from flask import Flask
    app = Flask(__name__)
    with app.app_context():
        if not hasattr(g, 'db'):
            g.db = psycopg.connect("dbname=schooner user=schooner")
        t = EmailTemplate('DTEK0068-3002_WELCOME')
        SQL = """
            SELECT      *
            FROM        core.course
            WHERE       course_id = 'DTE20068-3002'
        """
        with g.db.cursor() as c:
            if c.execute(SQL).rowcount:
                course = dict(zip([key[0] for key in c.description], c.fetchone()))
            else:
                raise ValueError(f"Course DTE20068-3002 not found!")

        s = t.parse_and_send('DTE20068-3002', 'jasata', { 'course' : course })
        print(s)
        #print(t.get_keys())


# EOF