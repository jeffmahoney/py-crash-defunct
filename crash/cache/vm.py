#!/usr/bin/env python
# vim: sw=4 ts=4 et si:

import gdb

import crash.arch.x86_64 as arch

from crash.types.types import unsigned_long

from crash.cache.syms import get_value

class LinuxVM:
    def __init__(self):
        self.high_memory = get_value('high_memory')
        print self.high_memory

        self.total_pages = arch.arch.base_to_page(arch.arch.virt_to_phys(self.high_memory.cast(unsigned_long)))
        self.min_page_count = self.total_pages

        num_physpages = get_value('num_physpages')
        if num_physpages:
            self.num_physpages = num_physpages.cast(unsigned_long)
            if num_physpages < self.total_pages:
                self.min_page_count = self.num_physpages
        else:
            self.num_physpages = None

        print "%u" % self.total_pages

cache = LinuxVM()
