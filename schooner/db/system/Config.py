#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Config.py - Data dictionary for system.config
#   2021-09-02  Initial version.
#

class Config(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __init__(self, cursor):
        # system.config is quaranteed to have only one row
        SQL = """
            SELECT      *
            FROM        system.config
        """
        if cursor.execute(SQL).rowcount:
            self.update(
                dict(
                    zip(
                        [key[0] for key in cursor.description],
                        cursor.fetchone()
                    )
                )
            )
        else:
            raise ValueError(
                "system.config is empty! Contact administrator!"
            )


# EOF
