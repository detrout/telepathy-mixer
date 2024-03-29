# telepathy-mixer - a MXit connection manager for Telepathy
# 
# Copyright (C) 2008 Ralf Kistner <ralf.kistner@gmail.com>
# 
# Adapted from telepathy-butterfly,
#  Copyright (C) 2006-2007 Ali Sabil <ali.sabil@gmail.com>
#  Copyright (C) 2007 Johann Prieur <johann.prieur@gmail.com>
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

from mxit.handles import *

from mixer.util.decorator import async, logexceptions
from mixer.handle import MixerHandleFactory
from mixer.coreproperties import MixerCoreProperties

__all__ = ['MixerTextChannel']

logger = logging.getLogger('Mixer.TextChannel')


class MixerTextChannel(
        telepathy.server.ChannelTypeText,
        MixerCoreProperties):

    def __init__(self, connection, handle, params):
        self._recv_id = 0
        self.contact_handle = handle
        self.handle = handle
        self.con = connection

        telepathy.server.ChannelTypeText.__init__(self, connection, handle)
        MixerCoreProperties.__init__(self)
        
        self._register_r('org.freedesktop.Telepathy.Channel', 'ChannelType', 'Interfaces',
                  'TargetHandle', 'TargetID', 'TargetHandleType',
                  'Requested', 'InitiatorHandle', 'InitiatorID')
        
        
        self.ChannelType = self._type
        self.TargetHandle = self.handle.id
        self.TargetID = self.handle.jid
        self.TargetHandleType = self.handle.type
        self.Requested = False
        self.InitiatorHandle = self.handle.id
        self.InitiatorID = self.handle.jid


    @property
    def Interfaces(self):
        return list(self._interfaces)
    
    @logexceptions(logger)
    def Send(self, message_type, text):
        contact = self.contact_handle.contact
        #TODO: sending to self
        if message_type == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
            if text.startswith('/'):
                self.con.commands.handle_command(self, text)
            else:
                if contact:
                    self.con.mxit.message(self.contact_handle.contact, text)
                else:
                    raise telepathy.PermissionDenied("Contact does not exist")
        else:
            raise telepathy.NotImplemented("Unhandled message type")
        
        
    def Close(self):
        self.con.channel_removed(self)
        telepathy.server.ChannelTypeText.Close(self)
        
    def message_received(self, message, type=telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL):
        id = self._recv_id
        timestamp = int(time.time())
        contact_handle = self.con.handle_for_buddy(message.buddy)
        self.Received(id, timestamp, contact_handle, type, 0, message.message)
