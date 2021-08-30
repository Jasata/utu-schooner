#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# LogDBHandler.py - List of pending GitHub registrations
#   2021-08-29  Initial version.
#
import os
import psycopg
import logging


class LogDBHandler(logging.Handler):
    """Writes messages with their own connection since PostgreSQL does not feature autonomous transactions."""

    def __init__(self, database: str, level = logging.INFO):
        super().__init__(level)
        self.__db = psycopg.connect(f"dbname={database}")


    def emit(self, record: logging.LogRecord):
        def truncate(s: str, n: int) -> str:
            return (s[:(n - 3)] + "...") if len(s) > n else s
        try:
            with self.__db.cursor() as cursor:
                cursor.execute(
                    """
                        INSERT INTO system.log (name, level, message, source)
                        VALUES (%(name)s, %(level)s, %(message)s, %(source)s)
                    """,
                    {
                        'name'      : truncate(record.name, 32),
                        'level'     : truncate(record.levelname, 10),
                        'message'   : truncate(record.getMessage(), 1000),
                        'source'    : truncate(
                            f"({os.getpid()}) {record.filename}:{record.lineno} {record.funcName}",
                            100
                        )
                    }
                )
                self.__db.commit()
        except Exception as e:
            raise




# EOF
