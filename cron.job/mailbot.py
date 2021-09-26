#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Tuisku Polvinen <tumipo@utu.fi>
#
# mailbot.py - Email backgroundtask
#   2021-08-23  Initial version.
#   2021-08-25  (JTa) Add attachment and priority handling.
#   2021-08-26  (JTa) New config object.
#   2021-08-27  (JTa) Support for multiple recipients.
#   2021-08-27  (JTa) Refactored and tested.
#   2021-08-29  (JTa) Add lockfile.
#   2021-08-30  (JTa) Now changes CWD /before/ attempting to read 'app.conf'.
#                     Imports from shared schooner package.
#   2021-09-26  (JTa) Configure root logging instance instead of local.
#   
#
# Scans 'email.message' table for unsent messages and sends them.
#
#   Return-to header is added in hopes that non-existent email addresses
#   (delivery failures) are replies to the course-specific email address,
#   allowing the course staff to detect anomalies and try to fix them.
#
#   Sender nor recipient fields are not parsed - that is the responsibility
#   of the sender which creates the email.message row.
#
#   Priority is set in the message header, but doesn't seem to be standardized.
#   Microsoft Outlook uses THREE (3) fields:
#       X-Priority: 1 | 3 | 5                   (1 = high, 3 = normal, 5 = low)
#       X-MSMail-Priority: High | Normal | Low
#       Importance: High | Normal | Low
#   We shall try first using on the 'X-Priority' header...
#
import os
import sys

import psycopg
import logging
import logging.handlers

import smtplib
import email
from email.mime.multipart   import MIMEMultipart
from email.mime.text        import MIMEText
from email.mime.application import MIMEApplication

# Local packages, add path for crontab execution
#   But not as the zero index... as a habit.
#   This could be important since 3rd party code may rely on sys.path
#   documentation conformance:
#
#           As initialized upon program startup, the first item of this list,
#           path[0], is the directory containing the script that was used to
#           invoke the Python interpreter.
#
sys.path.insert(
    1,
    os.path.normpath(
        os.path.join(
            os.path.dirname(
                os.path.realpath(
                    os.path.join(
                        os.getcwd(),
                        os.path.expanduser(__file__)
                    )
                )
            ),
            ".." # Parent directory (relative to this script)
        )
    )
)

from schooner.util import AppConfig
from schooner.util import Lockfile
from schooner.util import Counter
from schooner.util import Timer
from schooner.util import LogDBHandler


CONFIG_FILE = "app.conf"




class MailQueue(list):

    def __init__(self, cursor):
        # Using email.sendqueue(), which automatically decrements .retry_count
        # This query must be committed, so that in case that this entire script
        # fails, the retry_count changes are not lost.
        SQL = """
            SELECT      message.*
            FROM        email.sendqueue() message
            """
        if cursor.execute(SQL).rowcount:
            super().__init__(
                [dict(zip([k[0] for k in cursor.description], r)) for r in cursor]
            )
        # Because email.sendqueue() decremented .retry_count values
        cursor.connection.commit()



class Message(MIMEMultipart):

    class Attachments(list):
        def __init__(self, cursor, message_id: int):
            SQL = """
                SELECT      attachment.*
                FROM        email.attached
                            INNER JOIN email.attachment
                            ON (attached.attachment_id = attachment.attachment_id)
                WHERE       attached.message_id = %(message_id)s
            """
            if cursor.execute(SQL, locals()).rowcount:
                super().__init__(
                    [
                        dict(
                            zip(
                                [key[0] for key in cursor.description],
                                row
                            )
                        ) for row in cursor
                    ]
                )


    def __init__(self, cursor, item: dict):
        super().__init__()
        self.cursor = cursor
        try:
            #
            # Create a multipart message and set headers
            #
            self['From']         = item['sent_from']
            self['To']           = item['sent_to']
            self['Reply-to']     = item['sent_from']
            self['Date']         = email.utils.formatdate(localtime=True)
            self['Subject']      = item['subject']
            self['X-Priority']   = {
                                    'low':      '5',
                                    'normal':   '3',
                                    'high':     '1'
                                }[item['priority']]
            # "plain" or "html" (strip the "text/" part from the beginning)
            self.attach(MIMEText(item['body'], item['mimetype'].split('/')[1]))
            #
            # Attachments
            #
            for file in Message.Attachments(self.cursor, item['message_id']):
                attachment = MIMEApplication(
                    file['content'],
                    Name = file['name']
                )
                attachment.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename = file['name']
                )
                self.attach(attachment)

        except Exception as e:
            raise ValueError(
                f"Parsing message_id ({item['message_id']}) failed! {str(e)}"
            ) from None


    def send(self):
        try:
            smtpObj = smtplib.SMTP('localhost')
            smtpObj.sendmail(
                self['From'],
                self['To'].split(','),
                self.as_string()
            )
        except Exception as e:
            # Let caller manages transactions
            raise ValueError(
                f"Sending message_id ({item['message_id']}) failed {str(e)}"
            ) from None
        else:
            Message.set_as_sent(self.cursor, item['message_id'])


    @staticmethod
    def set_as_sent(cursor, message_id: int) -> None:
        cursor.execute(
            """
            UPDATE  email.message
            SET     state = 'sent'
            WHERE   message_id = %(message_id)s
            """,
            locals()
        )



###############################################################################
#
# MAIN (this file must not be included in other scripts)
#
if __name__ != "__main__":
    raise ValueError("This script must not be imported by other scripts!")

# Basic execution timer
timer = Timer()


#
# Cron job speciality - change to script's directory
#
os.chdir(os.path.dirname(os.path.realpath(__file__)))


#
# Read app.conf
#
cfg = AppConfig(CONFIG_FILE, "mailbot")


#
# Set up logging
#
root = logging.getLogger()
root.setLevel(cfg.loglevel)
if os.isatty(sys.stdin.fileno()):
    # Executed from console
    # (sys.stdin will be a TTY when executed from console)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter('[%(levelname)s] %(message)s')
    )
    root.addHandler(handler)
else:
    # Executed from crontab
    handler = logging.handlers.SysLogHandler(address = '/dev/log')
    handler.setFormatter(
        logging.Formatter('%(name)s: [%(levelname)s] %(message)s')
    )
    root.addHandler(handler)
# DB Handler
handler = LogDBHandler(cfg.database, level = cfg.loglevel)
root.addHandler(handler)
# Logger with a useful name
log = logging.getLogger(os.path.basename(__file__))



#
# No concurrent executions
#
try:
    log.debug(f"Config: {cfg}")
    log.debug(f"CWD: '{os.getcwd()}'")
    with    Lockfile(cfg.lockfile) as lock, \
            psycopg.connect(f"dbname={cfg.database}").cursor() as cursor:

        #
        # Get queue of unsent mails
        #
        cntr = Counter()

        queue = MailQueue(cursor)
        log.debug(f"{len(queue)} items in MailQueue")
        for item in queue:

            log.debug(
                f"#{item['message_id']}: '{item['sent_from']}' -> '{item['sent_to']}'"
            )
            # message-level try-except, must not terminate the loop
            try:
                #
                # Parse the message object
                #
                message = Message(cursor, item)

                message.send()
                log.debug(
                    f"Sent #{item['message_id']}: '{message['From']}' -> '{message['To']}'"
                )

            # message-level try-except
            except Exception as e:
                cursor.connection.rollback()
                cntr.add(Counter.ERR)
                log.exception(
                    f"Message #{item['message_id']} failed! {str(e)}"
                )
                # Do not escalate, let the outer loop send others
            else:
                cursor.connection.commit()
                cntr.add(Counter.OK)
            finally:
                pass

        # for loop ends
        if cntr.total or log.isEnabledFor(logging.DEBUG):
            log.info(
                f"{cntr.total} messages handled in {timer.report()}. {cntr.errors} errors and {cntr.successes} successes."
            )

except Lockfile.AlreadyRunning as e:
    log.exception(
        f"Execution cancelled! {str(e)}"
    )
except Exception as e:
    # possibly psycopg connect error
    log.exception(
        f"EXECUTION FAILURE! {str(e)}"
    )


# EOF
