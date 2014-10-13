#!/usr/bin/env python
# vim: sw=4 ts=4 et si:

import gdb
import math

import crash.exceptions
import crash.cache
from ..cache import vm
from ..cache import this_kernel_version

from crash.cache.syms import get_value
from crash.arch.x86_64 import arch
from list import hlist_for_each_entry, hlist_entry
from types import charp, atomic_long_t, unsigned_long

if 'p_pptr' in gdb.lookup_type('struct task_struct'):
    parent_member = 'p_pptr'
else:
    parent_member= 'parent'

upid_type = gdb.lookup_type('struct upid')
pid_type = gdb.lookup_type('struct pid')
task_type = gdb.lookup_type('struct task_struct')
thread_type = gdb.lookup_type('struct thread_struct')
vm = vm.cache

class TaskStateException(crash.exceptions.CrashException):
    pass

class TaskFormatException(crash.exceptions.CrashException):
    pass

TASK_RUNNING = None
TASK_INTERRUPTIBLE = None
TASK_UNINTERRUPTIBLE = None
TASK_ZOMBIE = None
TASK_STOPPED = None
TASK_SWAPPING = None
TASK_EXCLUSIVE = None
TASK_DEAD = None

TASK_SWAPPING = None
TASK_TRACING_STOPPED = None
TASK_WAKEKILL = None
TASK_WAKING = None

PF_EXITING = 0x4

MM_FILEPAGES = get_value('MM_FILEPAGES', domain=gdb.SYMBOL_VAR_DOMAIN)
MM_ANONPAGES = get_value('MM_ANONPAGES', domain=gdb.SYMBOL_VAR_DOMAIN)

mm_struct_fields = gdb.lookup_type('struct mm_struct').keys()
task_struct_fields = task_type.keys()
init_mm = get_value('init_mm')

if 'eip' in thread_type.keys():
    ip_member = 'eip'
elif 'ip' in thread_type.keys():
    ip_member = 'ip'

if 'esp' in thread_type.keys():
    sp_member = 'eip'
elif 'sp' in thread_type.keys():
    sp_member = 'ip'
elif 'ksp' in thread_type.keys():
    sp_member = 'ksp'

def set_default_task_states():
    global TASK_RUNNING
    global TASK_INTERRUPTIBLE
    global TASK_UNINTERRUPTIBLE
    global TASK_ZOMBIE
    global TASK_STOPPED
    global TASK_SWAPPING
    global TASK_EXCLUSIVE
    global TASK_DEAD

    TASK_RUNNING          = 0
    TASK_INTERRUPTIBLE    = 1
    TASK_UNINTERRUPTIBLE  = 2
    TASK_ZOMBIE           = 4
    TASK_STOPPED          = 8
    TASK_SWAPPING         = 16
    TASK_EXCLUSIVE        = 32

def initialize_task_state():
    global TASK_RUNNING
    global TASK_INTERRUPTIBLE
    global TASK_UNINTERRUPTIBLE
    global TASK_ZOMBIE
    global TASK_STOPPED
    global TASK_SWAPPING
    global TASK_EXCLUSIVE
    global TASK_DEAD
   
    task_stat = get_value('task_state_array')
    if not task_stat:
        set_default_task_states()
        return

    count = task_stat.type.sizeof / charp.sizeof

    TASK_DEAD = 0
    TASK_TRACING_STOPPED = 0
    bit = 0
    for i in range(0, count):
        state = task_stat[i].string()
        if '(running)' in state:
            TASK_RUNNING = bit
        elif '(sleeping)' in state:
            TASK_INTERRUPTIBLE = bit
        elif '(disk sleep)' in state:
            TASK_UNINTERRUPTIBLE = bit
        elif '(stopped)' in state:
            TASK_STOPPED = bit
        elif '(zombie)' in state:
            TASK_ZOMBIE = bit
        elif '(dead)' in state:
            TASK_DEAD |= bit
        elif '(swapping)' in state:
            TASK_SWAPPING = bit
        elif '(tracing stop)' in state:
            TASK_TRACING_STOPPED |= bit
        elif '(wakekill)' in state:
            TASK_WAKEKILL = bit
        elif '(waking)' in state:
            TASK_WAKING = bit

        if bit == 0:
            bit = 1
        else:
            bit <<= 1

    version = this_kernel_version()

    # NONINTERACTIVE didn't make it into task_state_array
    if version >= '2.6.16' and version < '2.6.24':
        TASK_NONINTERACTIVE = 64
    if version >= '2.6.32':
        if bin(TASK_DEAD).count('1') == 1:
            bit = math.log(TASK_DEAD, 2)
            TASK_DEAD |= 1 << (bit + 1)
            TASK_WAKEKILL |= 1 << (bit + 2)
            TASK_WAKING |= 1 << (bit + 3)

    if TASK_RUNNING is None or TASK_INTERRUPTIBLE is None or \
       TASK_UNINTERRUPTIBLE is None or TASK_ZOMBIE is None or \
       TASK_STOPPED is None:
        raise TaskStateException("Couldn't initialize valid task states")

initialize_task_state()

def maybe_dead(state):
    global TASK_INTERRUPTIBLE
    global TASK_UNINTERRUPTIBLE
    global TASK_ZOMBIE
    global TASK_STOPPED
    global TASK_SWAPPING

    known  = TASK_INTERRUPTIBLE | TASK_UNINTERRUPTIBLE
    known |= TASK_ZOMBIE | TASK_STOPPED
    if TASK_SWAPPING:
        known | TASK_SWAPPING
    return (state & known) == 0


def state_string(state):
    global TASK_RUNNING
    global TASK_INTERRUPTIBLE
    global TASK_UNINTERRUPTIBLE
    global TASK_ZOMBIE
    global TASK_STOPPED
    global TASK_SWAPPING
    global TASK_EXCLUSIVE
    global TASK_DEAD

    buf = None
    exclusive = 0

    if TASK_EXCLUSIVE:
        exclusive = state & TASK_EXCLUSIVE
        state &= ~TASK_EXCLUSIVE

    if state == TASK_RUNNING:
        buf = "RU"

    if state & TASK_INTERRUPTIBLE:
        buf = "IN"

    if state & TASK_UNINTERRUPTIBLE:
        buf = "UN"

    if state & TASK_ZOMBIE:
        buf = "ZO"

    if state & TASK_STOPPED:
        buf = "ST"

    if TASK_TRACING_STOPPED and state & TASK_TRACING_STOPPED:
        buf = "TR"

    if state == TASK_SWAPPING:
        buf = "SW"

    if state & TASK_DEAD and maybe_dead(state):
        buf = "DE"

    if buf is not None and exclusive:
        buf += "EX"

    if buf is None:
        buf = "??"

    return buf

class LinuxKernelTask:
    last_run = None
    def __init__(self, v):
        self.task_struct = v
        self.thread_info = arch.task_thread_info(v)

        self.pid = int(v['pid'])

        self.parent = v[parent_member]
        self.valid = False
        self.mem_valid = False
        self.pct_physmem = 0
        self.total_vm = 0
        self.rss = 0
        self.comm = v['comm'].string()

        if self.__class__.last_run is None:
            self.last_run = self.which_last_run()

#        self.task_addr = pointer_address(v.dereference().address)

    # Symbol values should be safe but we need to recalculate derived values
    def needs_update(self):
        return False

    def task_state(self):
        state = self.task_struct['state']
        if 'exit_state' in self.task_struct.type.fields():
            state |= self.task_struct['exit_state']
        return state

    def task_state_string(self):
        return state_string(self.task_state())

    def task_flags(self):
        return self.task_struct['flags']

    def is_exiting(self):
        return self.task_flags() & PF_EXITING

    def is_zombie(self):
        return self.task_state() & TASK_ZOMBIE

    def update_mem_usage(self):
        if self.mem_valid and not self.needs_update():
            return

        if self.is_zombie() or self.is_exiting():
            return

        mm = self.task_struct['mm']

        if not mm:
            self.mem_valid = True
            return

        self.rss = 0
        if 'rss' in mm_struct_fields:
            self.rss = long(mm['rss'].value())
        elif '_rss' in mm_struct_fields:
            self.rss = long(mm['_rss'].value())
        else:
            if 'rss_stat' in mm_struct_fields:
                rss_stat = mm['rss_stat']['count']
                self.rss += long(rss_stat[MM_FILEPAGES]['counter'])
                self.rss += long(rss_stat[MM_ANONPAGES]['counter'])
            else:
                for name in ['_anon_rss', '_file_rss']:
                    if name in mm_struct_fields:
                        if mm[name].type == atomic_long_t:
                            self.rss += long(mm[name]['counter'])
                        else:
                            self.rss += long(mm[name])

        self.total_vm = long(mm['total_vm'])
        self.pgd_addr = long(mm['pgd'])

        self.pct_physmem = float(self.rss) * 100 / float(vm.min_page_count)

        self.mem_valid = True

    def update(self):
        if self.valid and not self.needs_update():
            return

        self.update_mem_usage()

        self.valid = True

    def address(self):
        return long(self.task_struct.dereference().address)

    def get_active_set(self):
        pass

    def has_cpu(self):
        if 'has_cpu' in task_type.keys():
            return bool(self.task_struct['has_cpu'])
        elif 'cpus_runnable' in task_type.keys():
            return self.task_struct['cpus_runnable'] != ~0L
        else: 
            return True

    def stack_address(self):
        pass
        

    def cpu(self):
        return int(self.thread_info['cpu'])

    def which_last_run(self):
        if 'sched_info' in task_struct_fields and \
           'last_arrival' in self.task_struct['sched_info'].type.keys():
           return self.last_run__last_arrival

        if 'last_run' in task_struct_fields:
            return self.last_run__last_run

        if 'timestamp' in task_struct_fields:
            return self.last_run__timestamp

        raise TaskFormatException("No member for timestamp found.")

    def last_run__last_run(self):
        return long(self.task_struct['last_run'])

    def last_run__timestamp(self):
        return long(self.task_struct['timestamp'])

    def last_run__last_arrival(self):
            return long(self.task_struct['sched_info']['last_arrival'])

    def is_kernel_task(self):
        if self.task_struct['pid'] == 0:
            return True

        if self.is_zombie() or self.is_exiting():
            return False

        if self.task_struct['mm'] == 0:
            return True
        elif init_mm and self.task_struct['mm'].dereference() == init_mm:
            return True

        return False

pid_to_task_offset = gdb.Value(0).cast(task_type.pointer())['pids'][0].address
pid_to_task_offset = pid_to_task_offset.cast(gdb.lookup_type('long'))
upid_to_pid_offsets = []
for x in range(0,10):
    upid_to_pid_offsets.append(gdb.Value(0).cast(pid_type.pointer())['numbers'][x].address.cast(gdb.lookup_type('long')))

def upid_to_pid(upid):
    if upid.type != upid_type.pointer():
        raise TypeError("struct upid * required")

    level = int(upid['ns']['level'])

    offset = upid_to_pid_offsets[level]

    pid = (upid.cast(charp) - offset).cast(pid_type.pointer())
    return pid

def pid_to_task(pid):
    if pid.type != pid_type.pointer():
        raise TypeError("struct pid * required")

    if pid['tasks'][0]['first']:
        return hlist_entry(pid['tasks'][0]['first'], task_type,
                           pid_to_task_offset)

    return None
