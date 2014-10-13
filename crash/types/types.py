#!/usr/bin/env python
# vim: sw=4 ts=4 et si:

import gdb
import struct

char = gdb.lookup_type('char')
charp = gdb.lookup_type('char').pointer()
unsigned_long = gdb.lookup_type('unsigned long')
atomic_t = gdb.lookup_type('atomic_t')
atomic_long_t = gdb.lookup_type('atomic_long_t')

bitwidth = unsigned_long.sizeof << 3

def pointer_address(address):
    if type(address) == gdb.Value:
        address = long(address)
    if address < 0:
        address += 2 ** bitwidth
    return address
