
#!/bin/env python3

import os
import time
import smtplib
import psycopg
import logging
import logging.handlers

SCRIPTNAME  = os.path.basename(__file__)
LOGLEVEL    = logging.INFO  # logging.[DEBUG|INFO|WARNING|ERROR|CRITICAL]
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
        
class Database():
    def __init__(self, cstring: str):
        self.cstring = cstring

    def get_email_queue(self):
        sql = """
        SELECT      * 
        FROM        email 
        WHERE       state = 'queued'
        """
        with psycopg.connect(self.cstring) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                )
            return [dict(zip([key[0] for key in cur.description], row)) for row in cur]


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

    try:
        read_config_file(CONFIG_FILE)
    except Exception as ex:
        print(f"Error reading site configuration '{CONFIG_FILE}'")
        print(str(ex))
        os._exit(-1)
    
    db = Database(f"dbname={DB_NAME} user={DB_USER}")
    print(db.get_email_queue())

    sender = 'tumipo@utu.fi'
    receivers = ['tumipo@utu.fi']

    message = """From: Tuisku
    To: To Tuisku
    Subject: SMTP test

    This is a test message.
    """

    try:
        smtpObj = smtplib.SMTP('localhost')
        smtpObj.sendmail(sender, receivers, message)         
        print("email sent")
    except SMTPException:
        print("failed to send")
