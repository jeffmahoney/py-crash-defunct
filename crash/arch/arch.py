#!/usr/bin/env python
# vim: sw=4 ts=4 et si:

import crash.exceptions
import gdb

class CrashArchitectureNotImplementedException(crash.exceptions.CrashException):
    pass

class CrashArchitecture:
    def __init__(self):
        pass

    @staticmethod
    def virt_to_phys(vaddr):
        raise CrashArchitectureNotImplementedException("NI")

    @staticmethod
    def phys_to_virt(paddr):
        raise CrashArchitectureNotImplementedException("NI")

    @staticmethod
    def task_thread_info(task):
        t = gdb.lookup_type('struct thread_info').pointer()
        return task['stack'].cast(t)
