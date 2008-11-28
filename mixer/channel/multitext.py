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

import telepathy
import dbus.service

from mxit.handles import *

from mixer.util.decorator import async, logexceptions
from mixer.handle import MixerHandleFactory
from mixer.properties import MixerProperties

__all__ = ['MixerRoomChannel']

logger = logging.getLogger('Mixer.RoomChannel')


class MixerRoomChannel(
        telepathy.server.ChannelTypeText,
        telepathy.server.ChannelInterfaceGroup,
        MixerProperties):

    def __init__(self, connection, handle):
        self._recv_id = 0
        self.handle = handle
        self.con = connection

        telepathy.server.ChannelTypeText.__init__(self, connection, handle)
        telepathy.server.ChannelInterfaceGroup.__init__(self)
        # ('description', 's', 1), ('subject', 's', 1)
        MixerProperties.__init__(self, [('invite-only', 'b', 1), ('name', 's', 1), ('private', 'b', 1)])
        #self._set_property('subject', "Room name: %s" % handle.room.name) 'name': handle.room.name, 
        self._set(**{'name': handle.name, 'invite-only': True, 'private': True })
        
        #2048 = telepathy.CHANNEL_GROUP_FLAG_PROPERTIES
        self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_CAN_ADD | 2048, 0)
        
        
        self.__add_initial_participants()
        

    
    @logexceptions(logger)
    def AddMembers(self, contacts, message):
        added = set()
        for contact_handle_id in contacts:
            handle = self.con.handle(telepathy.HANDLE_TYPE_CONTACT, contact_handle_id)
            contact = handle.contact
            
            logger.info("Inviting %s" % contact.name)
                
    
    
    @logexceptions(logger)
    def Send(self, message_type, text):
        if self.handle.room:
            if message_type == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
                if text.startswith('/'):
                    self.con.commands.handle_command(self, text)
                else:
                    self.con.mxit.message(self.handle.room, text)
            else:
                raise telepathy.NotImplemented("Unhandled message type")
        else:
            raise telepathy.NotAvailable("Room does not exist")

        
    @logexceptions(logger)
    def Close(self):
        logger.info("Closing room")
        telepathy.server.ChannelTypeText.Close(self)
        self.remove_from_connection()


    @logexceptions(logger)
    def GetSelfHandle(self):
        return self.con.handle_for_buddy(self.con.mxit.roster.self_buddy)
    
    @async
    def __add_initial_participants(self):
        if self.handle.room:
            self.buddies_joined([self.con.mxit.roster.self_buddy] + list(self.handle.room.buddies))
        else:
            pass
            # Is this the best place to create the room?
            #self.con.mxit.create_room(self.handle.name)
        
        
    def message_received(self, contact_handle, message, type=telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL):
        id = self._recv_id
        timestamp = int(time.time())
        
        self.Received(id, timestamp, contact_handle, type, 0, message.message)

    def buddies_joined(self, buddies):
        handles = map(self.con.handle_for_buddy, buddies)
                
        self.MembersChanged('', handles, [], [], [],
                0, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
        
    def buddies_left(self, buddies):
        handles = map(self.con.handle_for_buddy, buddies)
                
        self.MembersChanged('', [], handles, [], [],
                0, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
        