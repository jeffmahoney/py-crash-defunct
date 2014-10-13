#!/usr/bin/env python
# vim: sw=4 ts=4 et si:

import arch

START_KERNEL_map = 0xffffffff80000000
PAGE_OFFSET = 0xffff880000000000
PAGE_SHIFT = 12
PAGE_SIZE = 1 << PAGE_SHIFT

class x8664Architecture(arch.CrashArchitecture):
    def __init__(self):
        arch.CrashArchitecture.__init__(self)

    @staticmethod
    def virt_to_phys(vaddr):
        if (vaddr >= START_KERNEL_map):
            return vaddr - START_KERNEL_map 
        else:
            return vaddr - PAGE_OFFSET

    @staticmethod
    def phys_to_virt(paddr):
        return paddr + PAGE_OFFSET

    @staticmethod
    def page_to_base(page):
        return page << PAGE_SHIFT

    @staticmethod
    def base_to_page(base):
        return base >> PAGE_SHIFT

arch = x8664Architecture()
