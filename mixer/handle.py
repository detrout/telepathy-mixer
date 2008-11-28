# telepathy-mixer - a MXit connection manager for Telepathy
#
# Copyright (C) 2008 Ralf Kistner <ralf.kistner@gmail.com>
#
# Adapted from telepathy-butterfly,
#  Copyright (C) 2007 Ali Sabil <ali.sabil@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import logging
import weakref
import exceptions

import telepathy

__all__ = ['MixerHandleFactory']

logger = logging.getLogger('Mixer.Handle')


def MixerHandleFactory(connection, type, *args):
    mapping = {'none': MixerNoneHandle,
               'self': MixerSelfHandle,
               'contact': MixerContactHandle,
               'list': MixerListHandle,
               'group': MixerGroupHandle,
               'room': MixerRoomHandle}
    handle = mapping[type](connection, *args)
    connection._handles[handle.get_type(), handle.get_id()] = handle
    return handle


class MixerHandleMeta(type):
    def __call__(cls, connection, *args):
        obj, newly_created = cls.__new__(cls, connection, *args)
        if newly_created:
            obj.__init__(connection, connection.get_handle_id(), *args)
            #logger.info("New Handle %r" % obj)
        return obj 


class MixerHandle(telepathy.server.Handle):
    __metaclass__ = MixerHandleMeta

    instances = weakref.WeakValueDictionary()
    def __new__(cls, connection, *args):
        key = (cls, connection._account[0], args)
        if key not in cls.instances.keys():
            instance = object.__new__(cls, connection, *args)
            cls.instances[key] = instance # TRICKY: instances is a weakdict
            return instance, True
        return cls.instances[key], False

    def __init__(self, connection, id, handle_type, name):
        #HACK
        if handle_type == 0:
            id = 0
        telepathy.server.Handle.__init__(self, id, handle_type, name)
        self._conn = weakref.proxy(connection)

    def __repr__(self):
        type_mapping = {telepathy.HANDLE_TYPE_CONTACT : 'Contact',
                telepathy.HANDLE_TYPE_ROOM : 'Room',
                telepathy.HANDLE_TYPE_LIST : 'List',
                telepathy.HANDLE_TYPE_GROUP : 'Group'}
        type_str = type_mapping.get(self.type, '')
        return "<Mixer%sHandle id=%u name='%s'>" % \
            (type_str, self.id, self.name)

    id = property(telepathy.server.Handle.get_id)
    type = property(telepathy.server.Handle.get_type)
    name = property(telepathy.server.Handle.get_name)


class MixerSelfHandle(MixerHandle):
    instance = None

    def __init__(self, connection, id):
        handle_type = telepathy.HANDLE_TYPE_CONTACT
        handle_name = connection._account
        self._connection = connection
        MixerHandle.__init__(self, connection, id, handle_type, handle_name)

    @property
    def jid(self):
        return self.contact.jid
    
    @property
    def contact(self):
        return self._conn.mxit.roster.self_buddy
    

class MixerNoneHandle(MixerHandle):
    def __init__(self, connection, id):
        handle_type = telepathy.HANDLE_TYPE_NONE
        handle_name = "none"
        id = 0    #HACK
        self._connection = connection
        MixerHandle.__init__(self, connection, id, handle_type, handle_name)

    
class MixerContactHandle(MixerHandle):
    def __init__(self, connection, id, jid):
        if jid == '':
            raise exceptions.Exception('No jid for contact')
        handle_type = telepathy.HANDLE_TYPE_CONTACT
        handle_name = jid
        self.jid = jid
        self.pending_groups = set()
        self.pending_alias = None
        MixerHandle.__init__(self, connection, id, handle_type, handle_name)

    @property
    def contact(self):
        return self._conn.mxit.roster.get_buddy(self.jid)
    
class MixerRoomHandle(MixerHandle):
    def __init__(self, connection, id, jid):
        
        handle_type = telepathy.HANDLE_TYPE_ROOM
        #if jid.startswith('ROOM'):
        #    jid = jid[4:]
        #handle_name = "ROOM" + jid
        
        self.jid = jid
        MixerHandle.__init__(self, connection, id, handle_type, jid)

    @property
    def room(self):
        return self._conn.mxit.roster.get_room(self.jid)

class MixerListHandle(MixerHandle):
    def __init__(self, connection, id, list_name):
        handle_type = telepathy.HANDLE_TYPE_LIST
        handle_name = list_name
        MixerHandle.__init__(self, connection, id, handle_type, handle_name)


class MixerGroupHandle(MixerHandle):
    def __init__(self, connection, id, group_name):
        handle_type = telepathy.HANDLE_TYPE_GROUP
        handle_name = group_name
        self.group_name = group_name
        MixerHandle.__init__(self, connection, id, handle_type, handle_name)

    @property
    def group(self):
        return self._conn.mxit.roster.get_group(self.group_name)

