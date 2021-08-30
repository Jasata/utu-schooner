#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Timer.py - Ultra-simple timer class
#   2021-08-28  Initial version.
#
import time

class Timer:

    def __init__(self) -> None:
        self.__started = time.time()

    @property
    def elapsed(self) -> float:
        """Elapsed time in seconds."""
        return time.time() - self.__started

    def report(self) -> str:
        t = time.time() - self.__started
        return "{:02d}:{:02d}:{:02d}.{:03d}".format(
            int(t / 3600),
            int((t % 3600) / 60),
            int(t % 60),
            int((t % 1) * 1000)
        )


if __name__ == '__main__':

    timer = Timer()
    time.sleep(1.4)
    print(timer.report())

# EOF
