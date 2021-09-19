#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# SubProcess.py - Class to run a subprocess and collect output
#   2021-09-11  Initial version.
#
import subprocess


class SubProcess:

    def __init__(
        self,
        cmd: str,
        shell: bool = False,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE
    ):
        """If output is not wanted, set stdout/stderr = subprocess.DEVNULL."""
        self.command = cmd
        try:
            if not shell:
                # Set empty double-quotes as empty list item
                # Required for commands like; ssh-keygen ... -N ""
                cmd = ['' if i == '""' or i == "''" else i for i in cmd.split(" ")]
            prc = subprocess.run(
                cmd,
                shell  = shell,
                stdout = stdout,
                stderr = stderr
            )
            # Store result/output
            self.returncode = prc.returncode
            self.stdout = prc.stdout.decode("utf-8") if stdout == subprocess.PIPE else None
            self.stderr = prc.stderr.decode("utf-8") if stderr == subprocess.PIPE else None

        except Exception as e:
            self.returncode = -2
            self.stdout = ""
            self.stderr = str(e)



# EOF