#!/usr/bin/env python
# vim: sw=4 ts=4 et si:

import gdb
import argparse

class CrashCommand(gdb.Command):
    def __init__(self, name, parser):
        gdb.Command.__init__(self, "py" + name, gdb.COMMAND_USER)
        parser.format_help = lambda: self.__doc__
        self.parser = parser

    def invoke(self, argstr, from_tty):
        argv = gdb.string_to_argv(argstr)
        try:
            args = self.parser.parse_args(argv)
            self.execute(args)
        except SystemExit:
            return
