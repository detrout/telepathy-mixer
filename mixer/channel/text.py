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

__all__ = ['MixerTextChannel']

logger = logging.getLogger('Mixer.TextChannel')


class MixerTextChannel(
        telepathy.server.ChannelTypeText):

    def __init__(self, connection, handle):
        self._recv_id = 0
        self.contact_handle = handle
        self.con = connection

        telepathy.server.ChannelTypeText.__init__(self, connection, handle)
        


    @logexceptions(logger)
    def Send(self, message_type, text):
        logger.info("Sending %s to %s, %s" % (text, self.contact_handle.jid, message_type))
        if message_type == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
            self.con.mxit.message(self.contact_handle.contact, text)
        else:
            raise telepathy.NotImplemented("Unhandled message type")

    def Close(self):
        telepathy.server.ChannelTypeText.Close(self)
        self.remove_from_connection()
        
    def message_received(self, message):
        id = self._recv_id
        timestamp = int(time.time())
        type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
        
        self.Received(id, timestamp, self.contact_handle, type, 0, message.message)
