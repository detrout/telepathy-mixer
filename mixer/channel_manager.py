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

from mixer.channel.contact_list import MixerContactListChannelFactory, MixerListChannel
from mixer.channel.group import MixerGroupChannel
from mixer.channel.text import MixerTextChannel
from mixer.channel.multitext import MixerRoomChannel
from mixer.channel.roomlist import MixerRoomListChannel
from mixer.channel.filetransfer import MixerFileChannel
from mixer.handle import MixerHandleFactory
from mixer.util.helpers import prefix

from mxit.handles import BuddyType

__all__ = ['ChannelManager']

logger = logging.getLogger('Mixer.ChannelManager')
        
        
class ChannelType:
    def __init__(self, channel_class, identifiers, fixed, allowed):
        self.channel_class = channel_class
        self.identifiers = identifiers
        self.fixed = fixed
        self.allowed = allowed
        
    def create(self, connection, handle, params):
        logger.info("Creating new instance of %r" % self.channel_class)
        return self.channel_class(connection, handle, params)
        
    def filter_identifiers(self, params):
        result = {}
        for key, value in params.items():
            if key in self.identifiers:
                result[key] = value
        return result
    
    def matches(self, params):
        for key, value in params.items():
            if (key in self.fixed and self.fixed[key] == value) or key in self.allowed:
                continue
            return False
        return True
    
class ChannelManager:
    def __init__(self, connection):
        self.con = connection
        basic = prefix('org.freedesktop.Telepathy.Channel.', 'ChannelType', 'TargetHandleType', 'TargetHandle')
        ch_allowed = prefix('org.freedesktop.Telepathy.Channel.', 'TargetHandle', 'TargetHandleID')
        ft_allowed = prefix('org.freedesktop.Telepathy.Channel.Type.FileTransfer.DRAFT.', 'Filename', 'ContentType', 'Size', 'Description', 'InitialOffset')
        
        CHANNEL_TYPE = 'org.freedesktop.Telepathy.Channel.ChannelType'
        HANDLE_TYPE = 'org.freedesktop.Telepathy.Channel.TargetHandleType'
        
        ft_fixed = {CHANNEL_TYPE: 'org.freedesktop.Telepathy.Channel.Type.FileTransfer.DRAFT', HANDLE_TYPE: telepathy.HANDLE_TYPE_CONTACT}
        text_fixed = {CHANNEL_TYPE: 'org.freedesktop.Telepathy.Channel.Type.Text', HANDLE_TYPE: telepathy.HANDLE_TYPE_CONTACT}
        group_fixed = {CHANNEL_TYPE: 'org.freedesktop.Telepathy.Channel.Type.ContactList',  HANDLE_TYPE: telepathy.HANDLE_TYPE_GROUP}
        list_fixed = {CHANNEL_TYPE: 'org.freedesktop.Telepathy.Channel.Type.ContactList',  HANDLE_TYPE: telepathy.HANDLE_TYPE_LIST}
        
        filetype = ChannelType(MixerFileChannel, basic, ft_fixed, ch_allowed + ft_allowed)
        texttype = ChannelType(MixerTextChannel, basic, text_fixed, ch_allowed)
        grouptype = ChannelType(MixerGroupChannel, basic, group_fixed, ch_allowed)
        listtype = ChannelType(MixerContactListChannelFactory, basic, list_fixed, ch_allowed)
        
        self.channel_types = [filetype, texttype, grouptype, listtype]
        
        self._channels = {}
     
        
    def check_handle(self, params, suppress_handler=False):
        type = params.get('org.freedesktop.Telepathy.Channel.TargetHandleType')
        id = params.get('org.freedesktop.Telepathy.Channel.TargetHandle')
        name = params.get('org.freedesktop.Telepathy.Channel.TargetHandleID')
        if id:
            handle = self.con.handle(type, id)
            params['org.freedesktop.Telepathy.Channel.TargetHandleID'] = handle.name
        else:
            handle = self.con.get_handle(type, name)
            params['org.freedesktop.Telepathy.Channel.TargetHandle'] = handle.id
        return handle
        
    def create_channel(self, params, suppress_handler=False):
        handle = self.check_handle(params)
        
        type = None
        for t in self.channel_types:
            if t.matches(params):
                type = t
                
        if not type:
            logger.error("No matching channel type found for %r" % (params))
            return (None, False)
        
        key = self._build_key(type, params)
        
        if key in self._channels:
            return self._channels[key], False
        else:
            ch = type.create(self.con, handle, params)
            self._channels[key] = ch
            self.con.channel_created(ch, suppress_handler)
            return ch, True
    
    
    def _build_key(self, type, params):
        ident = type.filter_identifiers(params)
        vals = ident.values()
        vals.sort()
        return tuple(vals)
            
    def get_channel(self, params, suppress_handler=False):
        channel, created = self.create_channel(params, suppress_handler)
        return channel
        
    def channel_for(self, type, handle, suppress_handler=False):
        params = {'org.freedesktop.Telepathy.Channel.TargetHandleType': handle.type,
                  'org.freedesktop.Telepathy.Channel.TargetHandle': handle.id,
                  'org.freedesktop.Telepathy.Channel.TargetHandleID': handle.name,
                  'org.freedesktop.Telepathy.Channel.ChannelType': type
                  }
        return self.get_channel(params, suppress_handler)
        
    def channel_for_text(self, handle, suppress_handler=False):
        return self.channel_for('org.freedesktop.Telepathy.Channel.Type.Text', handle, suppress_handler)
    
    def channel_for_room(self, handle, suppress_handler=False):
        return self.channel_for('org.freedesktop.Telepathy.Channel.Type.Text', handle, suppress_handler)
        
    def channel_for_list(self, handle, suppress_handler=False):
        return self.channel_for('org.freedesktop.Telepathy.Channel.Type.ContactList', handle, suppress_handler)
    
    def channel_for_file(self, handle, suppress_handler=False):
        return self.channel_for('org.freedesktop.Telepathy.Channel.Type.FileTransfer.DRAFT', handle, suppress_handler)
    
    
    def list_channels(self):
        channels = []
        for ch in self._channels.values():
            if isinstance(ch, MixerListChannel):
                channels.append(ch)
        return channels
    
    def close(self):
        for channel in self._channels.values():
            channel.Close()
    
    def all_channels(self):
        return self._channels.values()