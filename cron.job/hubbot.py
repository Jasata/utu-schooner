#!/bin/env python3
# Placeholder

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

