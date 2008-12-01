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

import weakref
import logging
import exceptions
import time

import telepathy

from mxit.connection import MxitConnection
from mxit.handles import Status, StatusChangeReason, BuddyType, Message

from mixer.listener import MixerListener
from mixer.presence import MixerPresence
from mixer.aliasing import MixerAliasing
from mixer.commands import CommandHandler
from mixer.handle import MixerHandleFactory, MixerSelfHandle
from mixer.channel.contact_list import MixerListChannel
from mixer.channel.group import MixerGroupChannel
from mixer.channel.multitext import MixerRoomChannel
from mixer.channel_manager import ChannelManager
from mixer.util.decorator import async, logexceptions

__all__ = ['MixerConnection']

logger = logging.getLogger('Mixer.Connection')



        
class MixerConnection(telepathy.server.Connection, MixerPresence, MixerAliasing):

    _mandatory_parameters = {
            'account' : 's',
            'password' : 's',
            'client_id' : 's',
            }
    _optional_parameters = {
            'server' : 's',
            'port' : 'q',
            }
    _parameter_defaults = {
            'server' : 'stream.mxit.co.za',
            'port' : 9119,
            }

    @logexceptions(logger)
    def __init__(self, manager, parameters):
        self.check_parameters(parameters)
        
        self._manager = manager
        account = parameters['account']
        server = parameters['server'].encode('utf-8')
        port = parameters['port']
        
        self._account = account
        
        self._channel_manager = ChannelManager(self)
        
        # Call parent initializers
        try:
            telepathy.server.Connection.__init__(self, 'mxit', account, 'mixer')
        except TypeError: # handle old versions of tp-python
            telepathy.server.Connection.__init__(self, 'mxit', account)
        MixerPresence.__init__(self)
        MixerAliasing.__init__(self)

        self.set_self_handle(MixerHandleFactory(self, 'self'))
        con = MxitConnection(host=server, port=port)
        con.listeners.add(MixerListener(self))
        con.id = parameters['account'].split('@')[0]
        con.password = parameters['password']
        con.client_id = parameters['client_id']
        self.mxit = con
        self.commands = CommandHandler(self)
        

        logger.info("Connection to the account %s created" % account)
        

    
   
    def handle(self, handle_type, handle_id):
        if handle_type == 0 and handle_id == 0:
            return MixerHandleFactory(self, 'none')    #HACK
        self.check_handle(handle_type, handle_id)
        return self._handles[handle_type, handle_id]

    @logexceptions(logger)
    def Connect(self):
        logger.info("Connecting")       
        #print self._account
        if self.mxit.status == Status.DISCONNECTED:
            self.mxit.connect()
            logger.info("done")
        else:
            logger.error("Already connected!")
        #self.mxit.start()
        #self.start()
        
        
    @logexceptions(logger)
    def Disconnect(self):
        logger.info("Disconnecting")
        self.mxit.close()

    @logexceptions(logger)
    def RequestHandles(self, handle_type, names, sender):   
        self.check_connected()
        self.check_handle_type(handle_type)

        handles = []
        for name in names:
            #name = name.encode('utf-8')
            if handle_type == telepathy.HANDLE_TYPE_CONTACT:
                handle = MixerHandleFactory(self, 'contact', name)
            elif handle_type == telepathy.HANDLE_TYPE_LIST:
                handle = MixerHandleFactory(self, 'list', name)
            elif handle_type == telepathy.HANDLE_TYPE_GROUP:
                handle = MixerHandleFactory(self, 'group', name)
                #logger.info("handle for group: %s" % name)
            elif handle_type == telepathy.HANDLE_TYPE_ROOM:
                handle = MixerHandleFactory(self, 'room', name)
                #logger.info("handle for room: %s" % name)
            elif handle_type == telepathy.HANDLE_TYPE_NONE:
                handle = MixerHandleFactory(self, 'none')
                #logger.info("handle none")
            else:
                raise telepathy.NotAvailable('Handle type unsupported %d' % handle_type)
            handles.append(handle.id)
            self.add_client_handle(handle, sender)
        return handles
        
    @logexceptions(logger)
    def RequestChannel(self, type, handle_type, handle_id, suppress_handler):    
        self.check_connected()
        
        #logger.info("requestion channel of type %s for handle %s, %s" % (type, handle_type, handle_id))
        channel = None
        channel_manager = self._channel_manager
        handle = self.handle(handle_type, handle_id)
        #logger.info("handle: %r" % handle)
        if type == telepathy.CHANNEL_TYPE_CONTACT_LIST:
            channel = channel_manager.channel_for_list(handle, suppress_handler)
        elif type == telepathy.CHANNEL_TYPE_TEXT:
            if handle_type == telepathy.HANDLE_TYPE_CONTACT:
                if isinstance(handle, MixerSelfHandle):
                    raise telepathy.NotImplemented("Cannot chat to self")
                channel = channel_manager.channel_for_text(handle, suppress_handler)
            elif handle_type == telepathy.HANDLE_TYPE_ROOM:
                channel = channel_manager.channel_for_room(handle, suppress_handler)
            else:
                raise telepathy.NotImplemented("Only Contacts and Rooms are allowed")
            
        elif type == telepathy.CHANNEL_TYPE_ROOM_LIST:
            channel = channel_manager.channel_for_roomlist(handle, suppress_handler)
            #logger.info("Path: %s" % channel._object_path)
            #logger.info("Channel for roomlist with handle: %r" % handle)
            #return None
            #raise telepathy.NotImplemented("room list not implemented")
        else:
            raise telepathy.NotImplemented("unknown channel type %s" % type)
        
        return channel._object_path
        

    def group_for_buddy(self, buddy):
        if not buddy.group.is_root():
            group_name = buddy.group.name
            group_handle = MixerHandleFactory(self, 'group', group_name)
            channel = self._channel_manager.channel_for_list(group_handle)
            return channel
        else:
            return None
        
        
    def handle_for_buddy(self, buddy):
        if buddy == self.mxit.roster.self_buddy:
            return MixerHandleFactory(self, 'self')
        return MixerHandleFactory(self, 'contact', buddy.jid)
    
    def init_channels(self):
        #for name in ['subscribe', 'publish', 'hide', 'allow', 'deny']:
        for name in ['subscribe', 'publish']:
            self.get_list_channel(name)
        
    def get_list_channel(self, name):
        handle = MixerHandleFactory(self, 'list', name)
        return self._channel_manager.channel_for_list(handle)
    
    def get_buddy_channel(self, buddy):    
        handle = self.handle_for_buddy(buddy)
        return self._channel_manager.channel_for_text(handle)
    
    def get_room_channel(self, room):
        handle = MixerHandleFactory(self, 'room', room.jid)
        return self._channel_manager.channel_for_room(handle)
    
    def get_group_channels(self):
        channels = []
        for handle, ch in self._channel_manager._list_channels.items():
            if isinstance(ch, MixerGroupChannel):
                channels.append(ch)
        return channels
            
    def _advertise_disconnected(self):
        self._manager.disconnected(self)
           
    def info(self, message, channel=None):
        info = self.mxit.roster.info_buddy
        if not channel:
            channel = self.get_buddy_channel(info)
        
        msg = Message(info, message)
        if isinstance(channel, MixerRoomChannel):
            handle = self.handle_for_buddy(info)
            channel.message_received(handle, msg, type=telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NOTICE)
        else:
            channel.message_received(msg, type=telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NOTICE)
        
        
    def notify_error(self, message, channel=None): 
        self.info(message, channel)
        