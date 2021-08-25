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
import time

import psycopg
import logging
import logging.handlers

import smtplib
import email

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

SCRIPTNAME  = os.path.basename(__file__)
LOGLEVEL    = logging.DEBUG  # logging.[DEBUG|INFO|WARNING|ERROR|CRITICAL]
CONFIG_FILE = "app.conf"

def read_config_file(cfgfile: str):
    """Reads (with ConfigParser()) '[Application]' and creates global variables. Argument 'cfgfile' has to be a filename only (not path + file) and the file must exist in the same directory as this script."""
    cfgfile = os.path.join(
        os.path.split(os.path.realpath(__file__))[0],
        cfgfile
    )
    if not os.path.exists(cfgfile):
        raise FileNotFoundError(f"Configuration file '{cfgfile}' not found!")
    import configparser
    cfg = configparser.ConfigParser()
    cfg.optionxform = lambda option: option # preserve case
    cfg.read(cfgfile)
    for k, v in cfg.items('Application'):
        globals()[k] = v



class MailQueue(list):

    def __init__(self, cstr: str):
        SQL = """
            SELECT      message.*,
                        course.code
            FROM        email.message
                        INNER JOIN core.course
                        ON (message.course_id = course.course_id)
            WHERE       state = 'queued'
                        AND
                        retry_count > 0
            """
        with psycopg.connect(cstr).cursor() as c:
            if c.execute(SQL).rowcount:
                super().__init__(
                    [dict(zip([key[0] for key in c.description], row)) for row in c]
                )

class Attachments(list):

    def __init__(self, cstr: str, message_id: int):
        SQL = """
            SELECT      attachment.*
            FROM        email.attached
                        INNER JOIN email.attachment
                        ON (attached.attachment_id = attachment.attachment_id)
            WHERE       attached.message_id = %(message_id)s
            """
        with psycopg.connect(cstr).cursor() as c:
            if c.execute(SQL, locals()).rowcount:
                super().__init__(
                    [dict(zip([key[0] for key in c.description], row)) for row in c]
                )


class Record:

    @staticmethod
    def fail(cstr: str, message_id: int) -> None:
        try:
            with psycopg.connect(cstr) as conn:
                with conn.cursor() as c:
                    c.execute(
                        """
                        UPDATE  email.message
                        SET     retry_count = retry_count - 1
                        WHERE   message_id = %(message_id)s
                        """,
                        locals()
                    )
                conn.commit()
        except:
            pass

    @staticmethod
    def success(cstr: str, message_id: int) -> None:
        try:
            with psycopg.connect(cstr) as conn:
                with conn.cursor() as c:
                    c.execute(
                        """
                        UPDATE  email.message
                        SET     state = 'sent'
                        WHERE   message_id = %(message_id)s
                        """,
                        locals()
                    )
                conn.commit()
        except:
            pass




if __name__ == '__main__':

    script_start_time = time.time()

    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    
    #
    # Set up logging
    #
    log = logging.getLogger(SCRIPTNAME)
    log.setLevel(LOGLEVEL)
    handler = logging.handlers.SysLogHandler(address = '/dev/log')
    handler.setFormatter(
        logging.Formatter('%(name)s: [%(levelname)s] %(message)s')
    )
    log.addHandler(handler)

    #
    # Read config
    #
    try:
        read_config_file(CONFIG_FILE)
    except Exception as ex:
        print(f"Error reading site configuration '{CONFIG_FILE}'")
        print(str(ex))
        os._exit(-1)
    
    #
    # Get queue of unsent mails
    #
    cstr = f"dbname={DB_NAME} user={DB_USER}"
    for item in MailQueue(cstr):

        try:
            #
            # Create a multipart message and set headers
            #
            message = MIMEMultipart()
            message['From']         = item['sent_from']
            message['To']           = item['sent_to']
            message['Reply-to']     = item['sent_from']
            message['Date']         = email.utils.formatdate(localtime=True)
            message['Subject']      = item['subject']
            message['X-Priority']   = {'low': '5', 'normal': '3', 'high': '1'}[item['priority']]
            # "plain" or "html" (strip the "text/" part from the beginning)
            message.attach(MIMEText(item['body'], item['mimetype'].split('/')[1]))

            #
            # Attachments
            #
            for file in Attachments(cstr, item['message_id']):
                attachment = MIMEApplication(
                    file['content'],
                    Name = file['name']
                )
                attachment.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename = file['name']
                )
                message.attach(attachment)
    
        except Exception as e:
            log.exception(
                f"Parsing message_id ({item['message_id']}) failed!"
            )
        else:
            #
            # Try sending
            #
            try:
                smtpObj = smtplib.SMTP('localhost')
                smtpObj.sendmail(message['From'], message['To'], message.as_string())
                log.debug(
                    f"Email '{message['From']}' -> '{message['To']}' (ID: {item['message_id']}) sent"
                )
            except Exception as e:
                log.exception(
                    f"Sending message_id ({item.message_id}) failed {str(e)}"
                )
                # Decrement message.retry_count
                Record.fail(cstr, item['message_id'])

            else:
                Record.success(cstr, item['message_id'])
                # TO BE REMOVED
                print(
                     f"Email '{message['From']}' -> '{message['To']}' (ID: {item['message_id']}) sent"
                )


# EOF
