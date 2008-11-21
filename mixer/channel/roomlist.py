# telepathy-mixer - a MXit connection manager for Telepathy
# 
# Copyright (C) 2008 Ralf Kistner <ralf.kistner@gmail.com>
# 
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
import time

import dbus

import telepathy

from mxit.handles import *

from mixer.util.decorator import async, logexceptions
from mixer.handle import MixerHandleFactory

__all__ = ['MixerRoomListChannel']

logger = logging.getLogger('Mixer.RoomListChannel')


class MixerRoomListChannel(
        telepathy.server.ChannelTypeRoomList,
        dbus.service.Object):

    def __init__(self, connection, handle):
        self._recv_id = 0
        self.handle = handle
        self.con = connection
        self.listing = False
        telepathy.server.ChannelTypeRoomList.__init__(self, connection)
        
        #MixerProperties.__init__(self, [('invite-only', 'b', 1), ('name', 's', 1), ('private', 'b', 1)])
        
        #self._set(**{'name': handle.room.name, 'invite-only': True, 'private': True })
        #telepathy.server.Channel.__init__(self)
        self._interfaces.add('org.freedesktop.DBus.Properties')
        
        #self.PropertiesChanged([(1, 'my.server2.com')])
        
        #self.__add_initial_rooms()


    @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        logger.info("getall %s" % interface)
        return {'Server': 'test.server.com'}
    
    
    @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='ss', out_signature='v')
    def Get(self, interface, name):
        logger.info("Get %s" % name)
        return "my.server.com"
    
        
    @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='ssv', out_signature='')
    def Set(self, interface, name, value):
        logger.info("Set %s=%r" % (name, value))
    
    @logexceptions(logger)
    def GetListingRooms(self):
        logger.info('GetListingRooms')
        return False
    
    @logexceptions(logger)
    def ListRooms(self):
        logger.info('ListRooms')
        rooms = self.con.mxit.roster.rooms.values()
        
        self.rooms_received(rooms)
    
    @logexceptions(logger)
    def StopListing(self):
        logger.info('StopListing')
       
    def Close(self):
        telepathy.server.ChannelTypeRoomList.Close(self)
        self.remove_from_connection()
    
    @async
    @logexceptions(logger)
    def rooms_received(self, rooms):
        
        data = []
        for room in rooms:
            channel = self.con.get_room_channel(room)
            handle = channel.handle
            data.append((handle, telepathy.CHANNEL_TYPE_TEXT, {'handle_name': handle.name, 'name': room.name}))
            
        self.ListingRooms(True)
        self.GotRooms(data)
        self.ListingRooms(False)
       
        