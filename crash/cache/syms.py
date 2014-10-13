#!/usr/bin/env python
# vim: sw=4 ts=4 et si:

import gdb

symbol_cache = {}


#per_cpu_start = gdb.lookup_global_symbol('__per_cpu_start')
#if not per_cpu_start:
#    per_cpu_start = gdb.lookup_minimal_symbol('__per_cpu_start')
#per_cpu_end = gdb.lookup_global_symbol('__per_cpu_end')
#if not per_cpu_end:
#    per_cpu_end = gdb.lookup_minimal_symbol('__per_cpu_end')

def is_percpu_symbol(sym):
    return sym.section is not None and 'percpu' in sym.section.name

#def get_percpu_value(name, domain=gdb.SYMBOL_VAR_DOMAIN):

def get_value(name, domain=gdb.SYMBOL_VAR_DOMAIN):
    if name in symbol_cache:
        return symbol_cache[name]

    sym = gdb.lookup_global_symbol(name, domain=domain)
    if not sym:
        try:
            sym = gdb.lookup_symbol(name, domain=domain)[0]
        except Exception, e:
            print e

    if sym:
        val = sym.value()
        if is_percpu_symbol(sym):
            val = (val.cast(charp) + per_cpu_offset).cast(val.type)
        symbol_cache[name] = val
        return val

    return sym

per_cpu_offset = get_value('__per_cpu_offset')
nr_cpus = per_cpu_offset.type.sizeof
