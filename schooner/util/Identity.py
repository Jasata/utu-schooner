#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Identity.py - Assume unprivileged user credentials
#   2021-08-30  Initial version.
#
#
# This class us useful for writing a system installation/setup scripts,
# in which root temporarily needs to assume a lesser privileged identity.
#
# Example use:
#   with Identity("pi"):
#       do_or_die(
#           'ssh-keygen -b 4096 -t rsa -f /home/pi/.ssh/id_rsa -q -N ""'
#       )
#
import os
import pwd
import grp


class Identity():
    def __init__(self, user: str, group: str = None):
        """Group will be user's primary group, unless specified. Use requires superuser privileges."""
        self.uid = pwd.getpwnam(user).pw_uid
        if not group:
            self.gid = pwd.getpwnam(user).pw_gid
        else:
            self.gid = grp.getgrnam(group).gr_gid
    def __enter__(self):
        self.original_uid = os.getuid()
        self.original_gid = os.getgid()
        os.setegid(self.uid)
        os.seteuid(self.gid)
    def __exit__(self, type, value, traceback):
        os.seteuid(self.original_uid)
        os.setegid(self.original_gid)


# EOF