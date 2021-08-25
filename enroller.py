#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# enroller.py - Enroll students from a CSV file
#   2021-08-25  Initial version.
#   2021-08-25  Fixed issue #1.
#
#   Issue #1:   Template ID is hardcoded now - needs to be a column:
#               core.course.enrollment_message
#   Issue #2:   In -f (overwrite/update), existing records get a new
#               welcome message. Need to somehow get the info who was
#               updated and who was inserted...
#   Issue #3:   Incorrect data (course.opens) used in the welcome template.
#               Must be assignment['T01']['deadline'].
import os
import sys
import platform

#
# REQUIRE Python 3.7 or newer
#
pyreq = (3,7)
if sys.version_info < pyreq:
    print(
        "You need Python {} or newer! ".format(".".join(map(str, pyreq))),
        end = ""
    )
    print(
        "You have Python ver.{} on {} {}".format(
            platform.python_version(),
            platform.system(),
            platform.release()
        )
    )
    os._exit(1)

# Python requirement OK, import the rest
import csv
import time
import errno
import jinja2
import getpass
import logging
import psycopg
import argparse
import datetime
import configparser
import subprocess


# For config
class DefaultDotDict(dict):
    """Dot-notation access dict with default key '*'. Returns value for key '*' for missing missing keys, or None if '*' value has not been set."""
    def __custom_get__(self, key):
        """For all DotDict.key access, missing or otherwise."""
        return self.get(key, self.get('*', None))
    __getattr__ = __custom_get__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    def __missing__(self, key):
        """For DefaultDotDict[key] access, missing keys."""
        return self.get('*', None)

###############################################################################
#
# CONFIGURATION  (Hardcoded / fallback defaults)
#
#   For instance specific configuration, please use 'enroller.conf'
#
config = DefaultDotDict(
    loglevel    = "INFO",
    logfile     = f"{ os.path.splitext(os.path.basename(__file__))[0] }.log",
    cfgfile     = f"{ os.path.splitext(os.path.basename(__file__))[0] }.conf",
    overwrite   = False,
    database    = "schooner"
)

# PEP 396 -- Module Version Numbers https://www.python.org/dev/peps/pep-0396/
__version__     = "0.2.0 (2021-08-25)"
__authors__     = "Jani Tammi <jasata@utu.fi>"
VERSION         = __version__
HEADER          = f"""
=============================================================================
University of Turku, Faculty of Technology, Department of Computing
Enroller - Add students to a course in Schooner DB
Version {__version__}, (c) 2018-2021 {__authors__}
"""

class Course(dict):

    def __init__(self, cur, course_id: str):
        SQL = """
            SELECT      *
            FROM        core.course
            WHERE       course_id = %(course_id)s
            """
        if cur.execute(SQL, locals()).rowcount:
            self.update(
                dict(zip([key[0] for key in cur.description], cur.fetchone()))
            )
        else:
            raise ValueError(f"Course '{course_id}' not found!")



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


    def __init__(self, cur, template_id: str) -> None:
        SQL = """
            SELECT      *
            FROM        email.template
            WHERE       template_id = %(template_id)s
        """
        if cur.execute(SQL, locals()).rowcount:
            self.update(dict(zip([key[0] for key in cur.description], cur.fetchone())))
        else:
            raise ValueError(f"Email template '{template_id}' not found!")


    def parse_and_send(
        self,
        cur,
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
        if not cur.execute(SQL, locals()).rowcount:
            raise ValueError(
                f"Unable to find enrollee ('{course_id}', '{uid}')!"
            )
        message = dict(zip([key[0] for key in cur.description], cur.fetchone()))

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
        if not cur.execute(SQL, message).rowcount:
            raise ValueError(
                f"Email message queueing failed! (template: '{self.code}', course_id: '{course_id}', recipient uid: '{uid}')"
            )
        self.message_id = int(cur.fetchone()[0])

        #
        # Copy attachments
        #
        cur.execute(
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
        return self.message_id


def to_bool(v):
    """Utility to translated string values to bool."""
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise TypeError('Boolean value expected.')




##############################################################################
#
# MAIN
#
##############################################################################
if __name__ == '__main__':

    #
    # Change working directory to script's directory
    #
    #os.chdir(os.path.dirname(os.path.realpath(__file__)))


    #
    # First argparse to see if an alternative configuration file has been given
    #
    cfparser = argparse.ArgumentParser(
        # Turn off help; do not react to '-h' with this parser
        add_help        = False,
        description     = __doc__,
        formatter_class = argparse.RawDescriptionHelpFormatter
    )
    cfparser.add_argument(
        #"-c",
        "--config",
        help    = f"Specify config file Default: '{config.cfgfile}'",
        dest    = "cfgfile",
        metavar = "FILE"
    )
    args, _ = cfparser.parse_known_args()


    #
    # Read config file
    #
    try:
        with open(args.cfgfile or config.cfgfile, "r") as cfgfile:
            cfgparser = configparser.ConfigParser()
            cfgparser.read_file(cfgfile)
            # Use only [Configuration] section
            fcfg = dict(cfgparser.items("Configuration"))
            # Update only existing keys
            config.update((k, fcfg[k]) for k in set(fcfg).intersection(config))
    except FileNotFoundError as ex:
        # If the config file was specified, complain about missing it
        if args.cfgfile:
            # Print it to avoid traceback
            print(ex)
            os._exit(-1)
        # else, silently accept missing config file
    except:
        print(f"Error reading '{args.cfgfile or config.cfgfile}'")
        os._exit(-1)


    #
    # Commandline arguments
    #
    #   NOTE:   Defaults are updated by the above config file reader.
    #           This is how it is supposed to work from the user's PoV.
    #           It does not matter where the value comes from - it is
    #           a default unless user gives commandline argument(s)
    #           to change them.
    #
    argparser = argparse.ArgumentParser(
        description     = HEADER,
        formatter_class = argparse.RawTextHelpFormatter,
    )
    # EXCEPTIONS!!
    # Do not define a default for 'csv' or 'schemasql'
    # This way 'arg.csv' and 'arg.schemasql' are left as 'None'
    # and that tells us if the corresponding option was specified or not.
    argparser.set_defaults(
        **{k:v for k,v in config.items() if k not in ("csv", "schemasql")}
    )
    argparser.add_argument(
        "-f",
        "--force",
        help    = "Overwrite/update existing.",
        action  = "store_true",
        dest    = "overwrite",
        default = config.overwrite
    )
    argparser.add_argument(
        #"-c",
        "--config",
        help    = f"Specify config file Default: '{config.cfgfile}'",
        dest    = "cfgfile",
        metavar = "FILE",
        type    = str
    )
    argparser.add_argument(
        #'-d',
        '--database',
        help    = f"Name of the database. Default: '{config.database}'",
        dest    = "database",
        metavar = "NAME",
        type    = str
    )
    argparser.add_argument(
        #"-l",
        "--loglevel",
        help    = f"Set logging level. Default: '{config.loglevel}'",
        choices = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        nargs   = "?", # optional argument, defaults to 'const' value
        dest    = "loglevel",
        const   = "INFO",
        type    = str.upper,
        metavar = "LEVEL"
    )
    argparser.add_argument(
        '--logfile',
        help    = f"Specify logfile. Default: '{config.logfile}'",
        dest    = "logfile",
        metavar = "FILE",
        type    = str
    )
    argparser.add_argument(
        'course_id',
        help    = "Instance code (course_id) for the course.",
        metavar = "course-instance",
        type    = str
    )
    argparser.add_argument(
        'csvfile',
        help    = "CSV file of students to be enrolled",
        metavar = "students.csv",
        type    = str
    )
    args, _ = argparser.parse_known_args()
    # Update only the existing keys
    config.update(
        (k, vars(args)[k]) for k in set(vars(args)).intersection(config)
    )
    # Fix booleans (cannot be handled as "cleanly" by argparse as I'd like)
    config.overwrite = to_bool(config.overwrite)

    #
    # Disable traceback for non-DEBUG runs
    #
    if config.loglevel != "DEBUG":
        sys.tracebacklimit = 0


    #
    # Set up logging
    #
    logging.basicConfig(
        level       = config.loglevel,
        filename    = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            config.logfile
        ),
        format      = "%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
        datefmt     = "%H:%M:%S"
    )
    log = logging.getLogger()
    # Leave a single INFO level line for the start of the script
    log.info(
        f"{time.strftime('%Y-%m-%d')} {' '.join(sys.argv)}"
    )


    #
    # Debug, dump config
    #
    log.debug(f"config: {str(config)}")


    #
    # Check that the file exists
    #
    if not os.path.isfile(args.csvfile):
        e = f"CSV file '{args.csvfile}' not found!"
        log.error(e)
        print(e)
        os._exit(-1)


    #
    # Test database connection and check that the course_id exists
    #
    cstr = f"dbname={args.database} user={getpass.getuser()}"
    log.debug(f"Connection string: '{cstr}'")

    with psycopg.connect(cstr) as conn:
        # conn.isolation_level = psycopg.extensions.ISOLATION_LEVEL_READ_COMMITTED
        # conn.set_isolation_level(1)
        cur = conn.cursor()
        try:
            course = Course(cur, args.course_id)
            if course['enrollment_message']:
                msg = EmailTemplate(cur, course['enrollment_message'])
        except Exception as e:
            log.exception(str(e))
            print(str(e))
            os._exit(-1)


        #
        # Import CSV (enrolled students)
        #
        print(f"Importing students from '{args.csvfile}'... ", end='')
        log.info(f"Importing students from '{args.csvfile}'")
        with open(args.csvfile, "r", newline='') as csvfile:
            csvreader = csv.reader(
                csvfile,
                dialect     = 'excel',
                delimiter   = ';',
                quotechar   = '"'
            )
            try:
                for idx, row in enumerate(csvreader):
                    # Whoops! ...better strip those whitespaces...
                    row = [col.strip() for col in row]
                    cur.execute(
                        """
                        CALL core.enrol
                        (
                            %(course_id)s,
                            %(uid)s,
                            %(studentid)s,
                            %(email)s,
                            %(lastname)s,
                            %(firstname)s,
                            %(update_existing)s
                        )
                        """,
                        {
                            'course_id':        args.course_id,
                            'uid':              row[4],
                            'studentid':        row[0],
                            'email':            row[3],
                            'lastname':         row[1],
                            'firstname':        row[2],
                            'update_existing':  args.overwrite
                        }
                    )
                    # If enrollment message is defined
                    if course['enrollment_message']:
                        msg.parse_and_send(
                            cur,
                            args.course_id,
                            row[4],
                            { 'course' : course }
                        )
            except Exception as ex:
                conn.rollback()
                print(f"ERROR: {str(ex)}")
                os._exit(-1)
            else:
                conn.commit()
                log.info(f"{idx + 1} records imported OK!")
                print(f"{idx + 1} records imported OK!")



# EOF