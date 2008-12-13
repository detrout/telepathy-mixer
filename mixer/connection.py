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
from telepathy._generated.Connection_Interface_Requests import ConnectionInterfaceRequests

import dbus

from mxit.connection import MxitConnection
from mxit.handles import Status, StatusChangeReason, BuddyType, Message
from mxit.jadreader import read_jad, parse_url

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
from mixer.coreproperties import MixerCoreProperties

__all__ = ['MixerConnection']

logger = logging.getLogger('Mixer.Connection')



        
class MixerConnection(telepathy.server.Connection,
                      MixerPresence,
                      MixerAliasing,
                      ConnectionInterfaceRequests,
                      MixerCoreProperties):
    _mandatory_parameters = {
            'account' : 's',
            'password' : 's',
            'settings-file' : 's',
            }
    _parameter_defaults = {}
    _optional_parameters = {}

    @logexceptions(logger)
    def __init__(self, manager, parameters):
        self.check_parameters(parameters)
        self._manager = manager
        account = parameters['account']
        settings_file = parameters['settings-file']
        file = open(settings_file, "r")
        settings = read_jad(file)
        file.close()
        protocol, host, port, path = parse_url(settings['sl1'])
        
        logger.info("Settings: %s" % settings_file)
        #server = parameters['server'].encode('utf-8')
        #port = parameters['port']
        
        self._account = account
        
        self._channel_manager = ChannelManager(self)
        
        # Call parent initializers
        try:
            telepathy.server.Connection.__init__(self, 'mxit', account, 'mixer')
        except TypeError: # handle old versions of tp-python
            telepathy.server.Connection.__init__(self, 'mxit', account)
        ConnectionInterfaceRequests.__init__(self)
        MixerPresence.__init__(self)
        MixerAliasing.__init__(self)
        MixerCoreProperties.__init__(self)
        
        self._register_r('org.freedesktop.Telepathy.Connection.Interface.Requests', 'RequestableChannelClasses', 'Channels')
        
        self.set_self_handle(MixerHandleFactory(self, 'self'))
        con = MxitConnection(host=host, port=port, client_id=settings['c'], country_code=int(settings['cc']), language=settings['loc'])
        con.listeners.add(MixerListener(self))
        con.id = account.split('@')[0]
        con.password = parameters['password']
        #con.client_id = parameters['client_id']
        self.mxit = con
        self.commands = CommandHandler(self)
        

        logger.info("Connection to the account %s created" % account)
        

    @property
    def RequestableChannelClasses(self):
        result = []
        for type in self._channel_manager.channel_types:
            result.append((type.fixed, type.allowed))
        return dbus.Array(result, signature='(a{sv}as)')
        #return dbus.Array(signature='(a{sv}as)')
   
    @property
    def Channels(self):
        result = []
        for channel in self._channel_manager.all_channels():
            result.append((channel._object_path, channel.identifiers()))
        return dbus.Array(result, signature='(oa{sv})')
    
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
            handle = self.get_handle(handle_type, name)
            handles.append(handle.id)
            self.add_client_handle(handle, sender)
        return handles
        
    def get_handle(self, handle_type, name):
        if handle_type == telepathy.HANDLE_TYPE_CONTACT:
            handle = MixerHandleFactory(self, 'contact', name)
        elif handle_type == telepathy.HANDLE_TYPE_LIST:
            handle = MixerHandleFactory(self, 'list', name)
        elif handle_type == telepathy.HANDLE_TYPE_GROUP:
            handle = MixerHandleFactory(self, 'group', name)
            #logger.info("handle for group: %s" % name)
        #elif handle_type == telepathy.HANDLE_TYPE_ROOM:
        #    handle = MixerHandleFactory(self, 'room', name)
            #logger.info("handle for room: %s" % name)
        elif handle_type == telepathy.HANDLE_TYPE_NONE:
            handle = MixerHandleFactory(self, 'none')
            #logger.info("handle none")
        else:
            raise telepathy.NotAvailable('Handle type unsupported %d' % handle_type)
        return handle
    
    @logexceptions(logger)
    def CreateChannel(self, request):
        logger.info('CreateChannel %r' % request)
        channel, created = self._channel_manager.create_channel(request, True)
        if not created:
            raise telepathy.NotAvailable('Channel already exists: %r' % request)
        channel.Requested = True
        
        props = channel.identifiers()
        return (channel._object_path, props)
    
    @async
    def channel_created(self, channel, suppress_handler):
        ident = channel.identifiers()
        logger.info("New Channel: %r" % ident)
        self.NewChannels([(channel._object_path, ident)])
        self.add_channel(channel, channel.handle, suppress_handler)
        
    @async
    def channel_removed(self, channel):
        self.ChannelClosed(channel._object_path)
        #channel.remove_from_connection()
        
    @logexceptions(logger)
    def EnsureChannel(self, request):
        logger.info('EnsureChannel %r' % request)
        channel, created = self._channel_manager.create_channel(request, True)
        props = channel.identifiers()
        
        #TODO: also 'Yours' if created by the connection manager
        return (created, channel._object_path, props)
    
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
                if handle.contact:
                    channel = channel_manager.channel_for_text(handle, suppress_handler)
                else:
                    raise telepathy.NotAvailable("The given contact does not exist")
            #elif handle_type == telepathy.HANDLE_TYPE_ROOM:
            #    channel = channel_manager.channel_for_room(handle, suppress_handler)
            else:
                raise telepathy.NotImplemented("Only contacts are allowed")
            
        #elif type == telepathy.CHANNEL_TYPE_ROOM_LIST:
        #    channel = channel_manager.channel_for_roomlist(handle, suppress_handler)
            #logger.info("Path: %s" % channel._object_path)
            #logger.info("Channel for roomlist with handle: %r" % handle)
            #return None
            #raise telepathy.NotImplemented("room list not implemented")
        else:
            raise telepathy.NotImplemented("unknown channel type %s" % type)
        
        channel.Requested = True
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
        #handle = MixerHandleFactory(self, 'room', room.jid)
        return self.get_buddy_channel(room)
        #return self._channel_manager.channel_for_room(handle)
    
    def get_file_channel(self, descriptor):
        info = self.mxit.roster.info_buddy
        handle = self.handle_for_buddy(info)
        return self._channel_manager.channel_for_file(handle)
        
    def get_group_channels(self):
        channels = []
        for ch in self._channel_manager.list_channels():
            if isinstance(ch, MixerGroupChannel):
                channels.append(ch)
        return channels
            
    def _advertise_disconnected(self):
        self._manager.disconnected(self)
           
    def info(self, message, channel=None):
        info = self.mxit.roster.info_buddy
        if not channel:
            channel = self.get_buddy_channel(info)
        logger.info("Channel: %s" % channel)
        msg = Message(info, message)
        if isinstance(channel, MixerRoomChannel):
            handle = self.handle_for_buddy(info)
            channel.message_received(handle, msg, type=telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NOTICE)
        else:
            channel.message_received(msg, type=telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NOTICE)
        
        
    def notify_error(self, message, channel=None): 
        self.info(message, channel)
        