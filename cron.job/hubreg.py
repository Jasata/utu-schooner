#!/bin/env python3
# Placeholder
#
# PROCESS
#
#   1)  Student creates GitHub account, preferrably named as UTU ID.
#   2)  Student creates a repository 'DTE20068-3002' and makes it private.
#   3)  Student invites 'dte20068@github.com' to be a collaborator.
#   4)  Student registers the GitHub account at
#       https://dte20068.utu.fi/register-github-account
#       Page creates submission in 'draft' state (content = account name).
#   5)  Background task 'hubreg.py' runs every minute and looks for 'draft'
#       submissions for 'handler' = 'HUBREG' (and for which the assignment
#       deadline has not passed). Content 
#       Once found, it looks for a pending invitation from recorded GitHub
#       account name. If found, accepts invite, updates enrollee.github and
#       sets submission.state = 'accepted'.
#   6)  An email is sent to confirm successful assignment completion.
#   7)  [OPTIONAL] An issue is created to student's repository, with content
#       that explains how exercises are handled.

import os
import pwd
import time
import logging
import logging.handlers

SCRIPTNAME  = os.path.basename(__file__)
LOGLEVEL    = logging.INFO  # logging.[DEBUG|INFO|WARNING|ERROR|CRITICAL]


if __name__ == '__main__':

    script_start_time = time.time()
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

    # WORK HERE
    try:
        log.info("NOT YET IMPLEMENTED!")
    except Exception as ex:
        log.exception(f"Script execution error!", exec_info = False)
        os._exit(-1)
    else:
        elapsed = time.time() - script_start_time
        log.info(f"Execution took {elapsed} seconds.")