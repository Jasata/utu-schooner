#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# IntervalTimer.py - Function calls at (fairly) steady intervals
#   2021-08-28  Initial version.
#
#
# Notes
#
#       Currently, has no support for scheduling when dictionary is appended
#       or deleted from. (TODO item, if that ever is needed).
#
#       The 'None' key (superloop interval) is "special" in a sense that it
#       does not quarantee steady intervals, but rather the longest interval
#       before the .next() returns to the superloop.
#
import time


class IntervalTimer(dict):

    def __init__(self, *args, **kwargs: dict):
        super().__init__(*args, **kwargs)
        self.__window = 0.1
        self.__schedule()


    @property
    def window(self) -> float:
        return self.__window
    @window.setter
    def window(self, value):
        if value < 0.001:
            self.__window = 0.001
        else:
            self.__window = value


    def __schedule(self):
        """(Re)Create list of events. [(time, function), (time, function), ...]"""
        # TODO: Call after dictionary is changed
        self.__now = time.time()
        self.__queue = []
        for fn, t in self.items():
            self.__queue.append((self.__now + t, fn))
        self.__queue.sort()


    def print_queue(self):
        for t, f in self.__queue:
            if f:
                print(f"{t}:\t{f.__name__}()")
            else:
                print(f"{t}:\tSuperloop interval")


    def next(self):
        """Sleep until the next event, execute it and whatever fits into the time_window, then return."""
        if not self.__queue:
            # No scheduled functions, not even None task
            return
        self.__now = time.time()
        nap = self.__queue[0][0] - self.__now
        if nap > 0:
            time.sleep(nap)
        # Run functions until time __window closes
        until = time.time() + self.__window
        task = self.__queue.pop(0)
        while True:
            # Could be None, which is just the interval to return to superloop
            if task[1]:
                task[1]()
            # Reschedule task
            #print("Adding", self[task[1]], "seconds to", task[1].__name__)
            self.__queue.append(
                (task[0] + self[task[1]], task[1])
            )
            self.__queue.sort()
            if self.__queue[0][0] > until:
                # We're done
                break
            task = self.__queue.pop(0)


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        pass



if __name__ == '__main__':

    g_str = ['.', '.', '.', '.']
    g_chr = ['\\', '|', '/', '-']

    def fn1():
        try:
            fn1.n += 1
        except AttributeError:
            fn1.n = 0
        g_str[1] = g_chr[fn1.n % len(g_chr)]
    def fn2():
        try:
            fn2.n += 1
        except AttributeError:
            fn2.n = 0
        g_str[2] = g_chr[fn2.n % len(g_chr)]
    def fn3():
        try:
            fn3.n += 1
        except AttributeError:
            fn3.n = 0
        g_str[3] = g_chr[fn3.n % len(g_chr)]

    print("\nPress CTRL-C to terminate...")
    try:
        n = 0
        tmr = IntervalTimer({None: 0.5, fn1 : 3.15, fn2 : 2.03, fn3 : 0.97})
        tmr.window = 0.01
        tmr.print_queue()
        # Superloop
        while True:
            n += 1
            tmr.next()
            g_str[0] = ['<', '^', '>'][n % 3]
            print("\r", ''.join(g_str), end='', flush=True)
    except KeyboardInterrupt:
        print("\nTerminated with CTRL-C")
        print("Entered superloop", n, "times")

# EOF