# telepathy-mixer - a MXit connection manager for Telepathy
#
# Copyright (C) 2008 Ralf Kistner <ralf.kistner@gmail.com>
# 
# Adapted from telepathy-butterfly,
#  Copyright (C) 2006-2007 Ali Sabil <ali.sabil@gmail.com>
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

import telepathy

from mixer.channel.contact_list import MixerContactListChannelFactory
from mixer.channel.group import MixerGroupChannel
from mixer.channel.text import MixerTextChannel
from mixer.channel.multitext import MixerRoomChannel
from mixer.channel.roomlist import MixerRoomListChannel
from mixer.handle import MixerHandleFactory

from mxit.handles import BuddyType

__all__ = ['ChannelManager']

logger = logging.getLogger('Mixer.ChannelManager')

def create_weakref(handle):
    
    ref = weakref.ref(handle)
    def get_value():
        return ref()
    return property(get_value)
    
class ChannelManager(object):
    def __init__(self, connection):
        self.con = connection
        self._list_channels = weakref.WeakValueDictionary()
        self._text_channels = weakref.WeakValueDictionary()
        self._room_channels = weakref.WeakValueDictionary()
        self._room_list_channels = weakref.WeakValueDictionary()

    def close(self):
        for channel in self._list_channels.values():
            channel.remove_from_connection()        # so that dbus lets it die.
        for channel in self._text_channels.values():
            channel.Close()
        for channel in self._room_channels.values():
            channel.Close()
        for channel in self._room_list_channels.values():
            channel.Close()

    def channel_for_list(self, handle, suppress_handler=False):
        if handle in self._list_channels:
            channel = self._list_channels[handle]
        else:
            if handle.get_type() == telepathy.HANDLE_TYPE_GROUP:
                channel = MixerGroupChannel(self.con, handle)
            else:
                channel = MixerContactListChannelFactory(self.con, handle)
            self._list_channels[handle] = channel
            self.con.add_channel(channel, handle, suppress_handler)
        
        return channel

    def channel_for_text(self, handle, suppress_handler=False):
        #if handle.contact.type == BuddyType.ROOM:
        #    return self.channel_for_room(handle)
        if handle in self._text_channels:
            channel = self._text_channels[handle]
        else:
            contact = handle.contact
            
            channel = MixerTextChannel(self.con, handle)
            self._text_channels[handle] = channel
            self.con.add_channel(channel, handle, suppress_handler)
        return channel
    
    def channel_for_room(self, handle, suppress_handler=False):
        if handle in self._room_channels:
            channel = self._room_channels[handle]
        else:            
            channel = MixerRoomChannel(self.con, handle)
            self._room_channels[handle] = channel
            self.con.add_channel(channel, handle, suppress_handler)
        return channel
    
    def channel_for_roomlist(self, handle, suppress_handler=False):
        if handle in self._room_list_channels:
            channel = self._room_list_channels[handle]
        else:
            channel = MixerRoomListChannel(self.con, handle)
            self._room_list_channels[handle] = channel
            self.con.add_channel(channel, handle, suppress_handler)
        return channel