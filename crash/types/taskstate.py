#!/usr/bin/env python
# vim: sw=4 ts=4 et si:

import crash.cache
from crash.cache.syms import get_value
from crash.exceptions import CrashException
from crash.types.types import charp

class TaskStateException(CrashException):
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
        self.set_default_task_state()
        return

    count = task_stat.type.sizeof / charp.sizeof

    TASK_DEAD = 0
    TASK_TRACING_STOPPED = 0
    for i in range(0, count):
        state = task_stat[i].string()
        if '(running)' in state:
            TASK_RUNNING = 1 << i
        elif '(sleeping)' in state:
            TASK_INTERRUPTIBLE = 1 << i
        elif '(disk sleep)' in state:
            TASK_UNINTERRUPTIBLE = 1 << i
        elif '(stopped)' in state:
            TASK_STOPPED = 1 << i
        elif '(zombie)' in state:
            TASK_ZOMBIE = 1 << i
        elif '(dead)' in state:
            TASK_DEAD |= 1 << i
        elif '(swapping)' in state:
            TASK_SWAPPING = 1 << i
        elif '(tracing stop)' in state:
            TASK_TRACING_STOPPED |= 1 << i
        elif '(wakekill)' in state:
            TASK_WAKEKILL = 1 << i
        elif '(waking)' in state:
            TASK_WAKING = 1 << i

    version = crash.cache.this_kernel_version()

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
