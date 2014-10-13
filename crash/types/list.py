#!/usr/bin/env python
# vim: sw=4 ts=4 et si:

import gdb

from crash.types.types import charp

hlist_head_type = gdb.lookup_type('struct hlist_head')
hlist_node_type = gdb.lookup_type('struct hlist_node')
list_head_type = gdb.lookup_type('struct list_head')

def hlist_for_each(head):
    if type(head) == str:
        head = gdb.parse_and_eval(head)

    if head.type == hlist_node_type.pointer():
        head = head['first']

    if head.type == hlist_head_type:
        head = head.address

    if head.type != hlist_head_type.pointer():
        raise TypeError("hlist_for_each requires struct hlist_head")

    node = head['first']

    while node != 0x0:
#        print "HLFE  %s" % node
        yield node
        node = node['next']

def hlist_entry(node, container, offset):
    if type(node) == hlist_node_type:
        node = node.address

#    print "HLIST_ENTRY %s" % type(offset)
    return (node.cast(charp) - offset).cast(container.pointer())

def hlist_for_each_entry(head, container, field):
    offset = container[field].bitpos / 8
    for node in hlist_for_each(head):
#        print "HLFEE %s %s" % (node, offset.type)
        yield hlist_entry(node, container, offset)

def list_for_each(head):
    if type(head) == str:
        head = gdb.parse_and_eval(head)

    if head.type == list_head_type:
        head = head.address

    if head.type != list_head_type.pointer():
        raise TypeError("list_for_each requires struct list_head")

    node = head['next']
    while node != head:
        yield node
        node = node['next']

def list_entry(head, container, offset):
    return (node - offset).cast(container.pointer())

def list_for_each_entry(head, container, field):
    offset = container[field].bitpos / 8
    for node in list_for_each(head):
        yield list_entry(node, container, offset)

def offsetof(base_pointer, value):
    if type(container) == str:
        container = gdb.lookup_type(container)
    return gdb.Value(0).cast(container.pointer())[field].address
