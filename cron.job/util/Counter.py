#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Counter.py - Simple success/error counting class
#   2021-08-27  Initial version.
#
# USAGE
#
#   from schooner import Counter
#
#   cntr = Counter()
#   cntr.add()                  # Success
#   cntr.add(Counter.ERR)       # Failure
#   cntr.add(Counter.OK)        # Success
#
#   print("Succeeded", cntr.succeeded)
#   print(cntr)
#
class Counter:
    ERR = False
    OK  = True
    def __init__(self):
        self.__n = 0
        self.__e = 0
    def add(self, x: bool = True):
        self.__n += 1
        self.__e += int(not x)
    @property
    def total(self):
        return self.__n
    @property
    def errors(self):
        return self.__e
    @property
    def successes(self):
        return self.__n - self.__e
    def __repr__(self):
        return f"{self.__e} errors out of {self.__n} total"


if __name__ == '__main__':
    # Demo
    cntr = Counter()
    cntr.add(Counter.ERR)
    cntr.add()
    print(cntr)

# EOF