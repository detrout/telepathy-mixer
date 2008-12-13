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
import socket

import dbus

import telepathy

from mxit.handles import *

from mixer.util.decorator import async, logexceptions
from mixer.handle import MixerHandleFactory
from mixer.coreproperties import MixerCoreProperties


__all__ = ['MixerFileChannel']

logger = logging.getLogger('Mixer.FileChannel')

CHANNEL_TYPE_FILE_TRANSFER = 'org.freedesktop.Telepathy.Channel.Type.FileTransfer.DRAFT'

FT_STATE_NONE = 0
FT_STATE_PENDING = 1
FT_STATE_ACCEPTED = 2
FT_STATE_OPEN = 3
FT_STATE_COMPLETED = 4
FT_STATE_CANCELLED = 5

class MixerFileChannel(
        telepathy.server.Channel,
        MixerCoreProperties):
    
        
    def __init__(self, connection, handle, params):
        
        self.handle = handle
        self.con = connection
        
        
        telepathy.server.Channel.__init__(self, connection, CHANNEL_TYPE_FILE_TRANSFER, handle)
        MixerCoreProperties.__init__(self)
        
        
        self._interfaces.add(CHANNEL_TYPE_FILE_TRANSFER)
        
        
        self._register_r(CHANNEL_TYPE_FILE_TRANSFER, 'ContentType', 'Filename',
                  'Size', 'ContentHashType', 'Description', 'InitialOffset', 
                  'AvailableSocketTypes')
        
        self._register_rw(CHANNEL_TYPE_FILE_TRANSFER, 'State', 'TransferredBytes')
        
        self.State = FT_STATE_PENDING
        self.ContentType = 'application/octet-stream'
        self.Filename = 'test.txt'
        self.Size = 12345
        self.ContentHashType=0
        self.Description = 'Test file'
        self.InitialOffset = 0
        self.TransferredBytes = 0
        self.AvailableSocketTypes = {2: [0, 1, 2], 0: dbus.Array([], 'u')}
        
        
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
        
        #self.InitialOffsetDefined(0)
        #self.PropertiesChanged([(1, 'my.server2.com')])
        
        #self.__add_initial_rooms()


    
    @property
    def Interfaces(self):
        return list(self._interfaces)
    
    @dbus.service.method(CHANNEL_TYPE_FILE_TRANSFER, in_signature='uuvt', out_signature='v')
    def AcceptFile(self, address_type, access_control, access_control_param, offset):
        logger.info("AcceptFile")
        return "donnie"
        
    @dbus.service.method(CHANNEL_TYPE_FILE_TRANSFER, in_signature='uuv', out_signature='v')
    def ProvideFile(self, address_type, access_control, access_control_param):
        logger.info("ProvideFile")
        self.InitialOffsetDefined(0)
        self.FileTransferStateChanged(FT_STATE_OPEN, 1)
        path, socket = self._create_socket()
        self._listen(socket)
        return path
   
    @dbus.service.signal(CHANNEL_TYPE_FILE_TRANSFER, signature='uu')
    def FileTransferStateChanged(self, state, reason):
        self.state = state
    
    @dbus.service.signal(CHANNEL_TYPE_FILE_TRANSFER, signature='t')
    def TransferredBytesChanged(self, count):
        pass
    
    @dbus.service.signal(CHANNEL_TYPE_FILE_TRANSFER, signature='t')
    def InitialOffsetDefined(self, offset):
        self.initial_offset = offset
        
    
    @logexceptions(logger)
    def Close(self):
        self.con.channel_removed(self)
        telepathy.server.Channel.Close(self)
    
    
    def _create_socket(self):
        import tempfile
        import os
        import random
        
        
        dir = tempfile.gettempdir()
        
        while True:
            i = random.randint(1, 10000000)
            path = os.path.join(dir, "tp-ft-%d" % i)
            if not os.path.exists(path):
                break
        logger.info("listening on %s" % path)
        
        #server = UnixStreamServer(path, FileSocketHandler)
        
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(path)
        server.listen(1)
        server.settimeout(5.0)
        
        return (path, server)
    
    @async
    def _listen(self, server):
        (client, address) = server.accept()
        server.close()
        descriptor = FileDescriptor(0, name=self.Filename, description=self.Description, size=self.Size, mimetype=self.ContentType)
        self.con.mxit.send_file(descriptor, self.handle.contact, client.makefile())
        

        