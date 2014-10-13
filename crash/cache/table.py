#!/usr/bin/env python
# vim: sw=4 ts=4 et si:

import crash.exceptions
import syms

class CrashTableException(crash.exceptions.CrashException):
    pass

class LinuxKernelVersion:
    def __init__(self, vstr):
        self.values = vstr.split('-')[0].split('.')
        self.string = vstr
        for i in range(0, 4 - len(self.values)):
            self.values.append(0)

    def __cmp__(self, other):
        if type(other) == str:
            return self.__cmp__(LinuxKernelVersion(other))
        return cmp(self.values,other.values)

    def __str__(self):
        return self.string

def this_kernel_version():
    uts = syms.get_value("system_utsname")
    if not uts:
        uts = syms.get_value("init_uts_ns")
        if uts:
            uts = uts['name']
    if not uts:
        raise CrashTableException("Can't locate utsname")

    return LinuxKernelVersion(uts['release'].string())
