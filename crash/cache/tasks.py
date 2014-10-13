#!/usr/bin/env python
# vim: sw=4 ts=4 et si:

import gdb

from crash.types.task import LinuxKernelTask, upid_type, upid_to_pid
from crash.types.task import pid_to_task, task_type
from crash.types.list import hlist_for_each_entry
from crash.types.types import pointer_address

from syms import get_value

pid_hash = get_value("pid_hash")
pidhash_shift = get_value('pidhash_shift')
pidhash_size = 1 << pidhash_shift
init_task = LinuxKernelTask(get_value("init_task"))


def upids_from_bucket(bucket):
    hlist = pid_hash[bucket]
    for pid in hlist_for_each_entry(hlist, upid_type, 'pid_chain'):
        yield pid

def upids():
    for bucket in range(0, pidhash_size):
        for upid in upids_from_bucket(bucket):
            yield upid

def pids():
    for upid in upids():
        yield upid_to_pid(upid)

def running_tasks():
    for pid in pids():
        task_struct = pid_to_task(pid)
        if task_struct:
            task = LinuxKernelTask(task_struct)
            yield task

class LinuxTaskCache:
    def __init__(self, load=True):
        self.valid = False
        self.task_lookup = None
        self.tasklist = None

        if load:
            self.update_cache()

    def needs_update(self):
        return False

    def update_cache(self):
        if not self.task_lookup or self.needs_update():
            if self.task_lookup:
                del self.task_lookup['pid']
                del self.task_lookup['task_struct']
            del self.tasklist
            self.tasklist = []
            self.task_lookup = {}
            self.task_lookup['pid'] = {}
            self.task_lookup['task_struct'] = {
                long(init_task.task_struct.address) : init_task
                }

            for task in running_tasks():
                self.tasklist.append(task)
                self.task_lookup['pid'][int(task.pid)] = task
                addr = long(task.task_struct.dereference().address)
                self.task_lookup['task_struct'][addr] = task

    def task_by_pid(self, pid):
        if not self.valid:
            self.update_cache();
        return self.task_lookup['pid'][pid]

    def task_by_addr(self, addr):
        if type(addr) == gdb.Value:
            if addr.type == task_type.pointer():
                addr = addr.dereference()
            if addr.type == task_type:
                addr = long(addr.address)
        elif type(addr) != long:
            raise TypeError("task_by_addr takes task_struct, task_struct *, or long")

        return self.task_lookup['task_struct'][addr]

    def tasks(self, sort_key=None):
        if not sort_key:
            return self.tasklist

        return sorted(self.tasklist, key=sort_key)

cache = LinuxTaskCache(True)
