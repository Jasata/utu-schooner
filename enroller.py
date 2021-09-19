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
#   2021-08-28  Moved to cron.jobs (for the libraries).
#   2021-08-29  dateformat and timeformat added to config.
#   2021-08-20  With the creation of system-shared schooner package,
#               moved back to the project root.
#   2021-08-31  Supports CSV column mapping to process different exports.
#   2021-09-05  Minor fix for calling JTDTemplate.parse_and_queue().
#   2021-09-08  Updated for changed Peppi export layout... again.
#
#   IMPORTANT
# -----------------------------------------------------------------------------
#   Peppi (as of August 2021) does not export CSV files. Neither does the
#   system expose any API to automatically extract registration information.
#   Only way currently to enroll accepted Peppi course registrations is:
#   1)  Export .xlsx sheet for registrations
#   2)  Open in Excel and REMOVE THE HEADER ROW
#   3)  Ensure that all are ACCEPTED (others must not be enrolled
#   4)  Save as .csv (UTF-8) and use this script
#
#
#   Issue #1:   Template ID is hardcoded now - needs to be a column:
#     (fixed)   core.course.enrollment_message
#   Issue #2:   In -f (overwrite/update), existing records get a new
#               welcome message. Need to somehow get the info who was
#               updated and who was inserted...
#   Issue #3:   Incorrect data (course.opens) used in the welcome template.
#               Must be assignment['T01']['deadline'].
#               Vague and/or creates issues for other courses.
#               This needs additional data structures for events/lectures
#               and that is beyond the scope of this year.
#   solution => Rewrite template WITHOUT exact date information.
#   Issue #4:   Might (somehow) insert email.message rows with NULL values
#               on course_id and uid (aka. enrollee). Track down the issue.
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
import logging
import psycopg
import argparse

from schooner.util      import AppConfig
from schooner.util      import Timer
from schooner.util      import LogDBHandler
from schooner.db.core   import Course
from schooner.db.email  import Template
from schooner.jtd       import JTDCourseWelcome

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
#   For instance specific configuration, please use the .conf file.
#   IMPORTANT! This script will reject any keys from .conf file which
#   do not appear in the config dictionary below!!
#
config = DefaultDotDict(
    dateformat  = "%Y-%m-%d",
    timeformat  = "%H:%M:%S",
    loglevel    = "INFO",
    logfile     = f"{os.path.splitext(os.path.basename(__file__))[0]}.log",
    cfgfile     = "enroller.conf",
    overwrite   = False,
    database    = "schooner",
    csvmapping  = "peppi"
)
# Explicitly, config in the same directory as this script
#    cfgfile     = f"{os.path.dirname(os.path.realpath(__file__))}/app.conf",


# PEP 396 -- Module Version Numbers https://www.python.org/dev/peps/pep-0396/
__version__     = "0.4.2 (2021-09-08)"
__authors__     = "Jani Tammi <jasata@utu.fi>"
VERSION         = __version__
HEADER          = f"""
=============================================================================
Schooner - Simple Course Management System
University of Turku, Faculty of Technology, Department of Computing
Enroller v{__version__}, (c) 2018-2021 {__authors__}
Utility to enroll students to a course
"""




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


class EnrollArguments(dict):
    """Load row (a list) into an argument dictinonary for SQL execute."""

    maps = {
        'peppi' : {
            'uid' : 4, 'studentid' : 7, 'email' : 5, 'lastname' : 1, 'firstname' : 2
        },
        'nettiopsu' : {
            'uid' : 4, 'studentid' : 0, 'email' : 3, 'lastname' : 1, 'firstname' : 2
        }
    }

    def __init__(
        self,
        course_id: str,
        **kwargs
    ):
        self.mapping = kwargs.pop('map', 'peppi')
        if self.mapping not in EnrollArguments.maps:
            raise ValueError(f"Mapping '{self.mapping}' is not recognized!")
        # These keys are not sourced from rows
        self.exclude = {'course_id', 'update'}
        # Key names as required by the core.enroll() procedure call
        self.update(
            {
                'course_id' : course_id,
                'uid'       : kwargs.get('uid', None),
                'studentid' : kwargs.get('studentid', None),
                'email'     : kwargs.get('email', None),
                'lastname'  : kwargs.get('lastname', None),
                'firstname' : kwargs.get('firstname', None),
                'update'    : kwargs.get('update', False)
            }
        )

    def load(self, row: list):
        if len(row) <= max(self.maps[self.mapping].values()):
            raise ValueError(
                f"row has too few columns for the chosen mapping ('{self.mapping}')! {max(self.maps[self.mapping].values()) + 1} columns are required. Row: {str(row)}"
            )
        for k in [k for k in self.keys() if k not in self.exclude]:
            # or None replaces empty strings with NULL
            self[k] = row[self.maps[self.mapping][k]] or None
        return self




##############################################################################
#
# MAIN
#
##############################################################################
if __name__ == '__main__':

    timer = Timer()
    #
    # Change working directory to script's directory
    # Place for conf and log files...
    #
    os.chdir(os.path.dirname(os.path.realpath(__file__)))


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
    if args.cfgfile:
        config.cfgfile = args.cfgfile


    #
    # Read .conf file and update config:dict
    #
    try:
        fcfg = AppConfig(config.cfgfile, "enroller")
        # IMPORTANT: This will leave out any keys not present in the config!!!
        config.update((k, fcfg[k]) for k in set(fcfg).intersection(config))
    except FileNotFoundError as ex:
        # If the config file was specified, complain about missing it
        if args.cfgfile:
            # Print it to avoid traceback
            print(ex)
            os._exit(-1)
        # else, silently accept missing config file
        print(f"Notice: Configuration file '{config.cfgfile}' was not found.")
    except:
        print(f"Error reading '{config.cfgfile}'")
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
        prog            = "Enroller",
        description     = HEADER,
        formatter_class = lambda prog: argparse.RawTextHelpFormatter(
            prog,
            max_help_position = 34,
            width=80
        )
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
        "-m",
        "--map",
        help    = f"Set logging level. Default: '{config.csvmapping}'. Available: {list(EnrollArguments.maps.keys())}",
        choices = EnrollArguments.maps.keys(),
        dest    = "csvmapping",
        type    = str,
        metavar = "MAP"
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
    log = logging.getLogger(os.path.basename(__file__))
    log.setLevel(config.loglevel)
    # STDOUT handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter('[%(levelname)s] %(message)s')
    )
    log.addHandler(handler)
    # FILE handler
    try:
        handler = logging.FileHandler(config.logfile)
        handler.setFormatter(
            logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        )
        # Logfile will always get DEBUG level info...
        handler.setLevel(level=logging.DEBUG)
        log.addHandler(handler)
    except PermissionError:
        print(f"Unable to write to '{config.logfile}'!")
        os._exit(-1)
    else:
        os.chmod(config.logfile, 0o664)
    # DB log Handler
    handler = LogDBHandler(config.database, level = config.loglevel)
    log.addHandler(handler)


    #
    # Debug, dump config
    #
    print(HEADER)
    log.debug(f"commandline: {' '.join(sys.argv)}")
    log.debug(f"config: {str(config)}")


    #
    # Check that the CSV file exists
    #
    if not os.path.isfile(args.csvfile):
        e = f"CSV file '{args.csvfile}' not found!"
        log.error(e)
        os._exit(-1)


    # Local "ident" authentication (current user)
    with psycopg.connect(f"dbname={config.database}").cursor() as cursor:
        # conn.isolation_level = psycopg.extensions.ISOLATION_LEVEL_READ_COMMITTED
        # conn.set_isolation_level(1)
        try:
            course = Course(cursor, args.course_id)
            if course['enrollment_message']:
                jt_msg  = Template(cursor, course['enrollment_message'])
                jt_data = JTDCourseWelcome(cursor, args.course_id)

        except Exception as e:
            log.exception(str(e))
            os._exit(-1)


        #
        # Import CSV (enrolled students)
        #
        with open(args.csvfile, "r", newline='') as csvfile:
            csvreader = csv.reader(
                csvfile,
                dialect     = 'excel',
                delimiter   = ';',
                quotechar   = '"'
            )
            try:
                sqlargs = EnrollArguments(
                    args.course_id,
                    update = args.overwrite,
                    map = config.csvmapping
                )
                for idx, row in enumerate(csvreader):
                    # Whoops! ...better strip those whitespaces...
                    row = [col.strip() for col in row]
                    cursor.execute(
                        """
                        CALL core.enrol
                        (
                            %(course_id)s,
                            %(uid)s,
                            %(studentid)s,
                            %(email)s,
                            %(lastname)s,
                            %(firstname)s,
                            %(update)s
                        )
                        """,
                        sqlargs.load(row)
                    )
                    # If enrollment message is defined
                    if course['enrollment_message']:
                        try:
                            jt_msg.parse_and_queue(
                                args.course_id,
                                row[4],
                                **jt_data
                            )
                        except Template.NotSent as e:
                            log.warning(str(e))
            except psycopg.errors.StringDataRightTruncation as e:
                cursor.connection.rollback()
                log.error(f"sqlargs: {str(sqlargs)}")
                log.exception(f"{str(e)}")
                os._exit(-1)
            except Exception as e:
                cursor.connection.rollback()
                log.exception(f"{str(e)}")
                os._exit(-1)
            else:
                cursor.connection.commit()
                log.info(
                    f"{idx + 1} records imported from '{args.csvfile}' in {timer.report()}"
                )



# EOF