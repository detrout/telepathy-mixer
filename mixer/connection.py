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
from mxit.handles import Status, StatusChangeReason

from mixer.presence import MixerPresence
from mixer.aliasing import MixerAliasing
from mixer.handle import MixerHandleFactory
from mixer.channel.contact_list import MixerListChannel
from mixer.channel.group import MixerGroupChannel
from mixer.channel_manager import ChannelManager
from mixer.util.decorator import async, logexceptions

__all__ = ['MixerConnection']

logger = logging.getLogger('Mixer.Connection')



class MixerListener:
    def __init__(self, mixer_con):
        self.con = mixer_con
        
    def message_received(self, message):
        sender = message.buddy
        handle = MixerHandleFactory(self.con, 'contact', sender.jid)
        channel = self.con._channel_manager.channel_for_text(handle)
        channel.message_received(message)
        
    def message_sent(self, message):
        recipient = message.buddy
        handle = MixerHandleFactory(self.con, 'contact', recipient.jid)
        channel = self.con._channel_manager.channel_for_text(handle)
        channel.Sent(int(time.time()), telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, message.message)
        
    def message_error(self, message, error="Message cannot be delivered"):        
        recipient = message.buddy
        handle = MixerHandleFactory(self.con, 'contact', recipient.jid)
        channel = self.con._channel_manager.channel_for_text(handle)
        
        ts = int(time.time())
        channel.SendError(ts, telepathy.CHANNEL_TEXT_SEND_ERROR_UNKNOWN, telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, message.message)
        
        
    def presence_changed(self, presence):
        pass
    
    def mood_changed(self, mood):
        pass
    
    def buddy_updated(self, buddy, **attrs):
        logger.info("Buddy updated: %r" % (attrs))
        if 'presence' in attrs:
            self.con.presence_received(buddy)
            for channel in map(self.con.get_list_channel, ['subscribe', 'publish']):
                channel.check_buddy(buddy)
                
        if 'name' in attrs:
            self.con._contact_alias_changed(buddy)
        if 'group' in attrs:
            self._add_to_group(buddy)
    
    def buddy_added(self, buddy):
        #logger.info("Buddy added|%s" % buddy)
        for channel in map(self.con.get_list_channel, ['subscribe', 'publish']):
            channel.buddy_added(buddy)
            
        self._add_to_group(buddy)
        #self.con._contact_alias_changed(buddy)
                    
    def buddy_removed(self, buddy):
        for handle, channel in self.con._channel_manager._list_channels.items():
            if isinstance(channel, MixerListChannel):
                channel.buddy_removed(buddy)
        
        
    def status_changed(self, status, reason):
        reason_map = {
            StatusChangeReason.UNKNOWN : telepathy.CONNECTION_STATUS_REASON_NONE_SPECIFIED,
            StatusChangeReason.REQUESTED : telepathy.CONNECTION_STATUS_REASON_REQUESTED,
            StatusChangeReason.NETWORK_ERROR : telepathy.CONNECTION_STATUS_REASON_NETWORK_ERROR,
            StatusChangeReason.TIMEOUT : telepathy.CONNECTION_STATUS_REASON_NETWORK_ERROR,
            StatusChangeReason.AUTH_FAILED : telepathy.CONNECTION_STATUS_REASON_AUTHENTICATION_FAILED,
            StatusChangeReason.ERROR : telepathy.CONNECTION_STATUS_REASON_NETWORK_ERROR,
        }
        tel_reason = reason_map[reason]
        if status == Status.CONNECTING:
            self.con.StatusChanged(telepathy.CONNECTION_STATUS_CONNECTING, tel_reason)
        elif status == Status.AUTHENTICATING:
            pass
        elif status == Status.ACTIVE:
            self.con.StatusChanged(telepathy.CONNECTION_STATUS_CONNECTED, tel_reason)
            self.con.init_channels()
        elif status == Status.DISCONNECTED:
            self.con.StatusChanged(telepathy.CONNECTION_STATUS_DISCONNECTED, tel_reason)
            self.con._channel_manager.close()
            self.con._advertise_disconnected()
                
        
    def error(self, message, exception):
        import traceback
        logger.error("Random exception occured: %s | %s" % (message, traceback.format_exc()))
        
    def _add_to_group(self, buddy):
        channel = self.con.group_for_buddy(buddy)
        buddy_handle = self.con.handle_for_buddy(buddy)
        
        for ch in self.con.get_group_channels():
            if ch != channel:
                ch.buddy_removed(buddy)
                
        if channel is not None:
            #channel.add_contacts([buddy_handle])
            channel.buddy_added(buddy)
        
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
        
        self.__disconnect_reason = telepathy.CONNECTION_STATUS_REASON_NONE_SPECIFIED
        self._initial_presence = None
        self._initial_personal_message = None

        logger.info("Connection to the account %s created" % account)
        

    
   
    def handle(self, handle_type, handle_id):
        self.check_handle(handle_type, handle_id)
        return self._handles[handle_type, handle_id]

    @logexceptions(logger)
    def Connect(self):
        logger.info("Connecting")       
        #print self._account

        self.mxit.connect()
        logger.info("done")
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
                logger.info("handle for group: %s" % handle)
            else:
                raise telepathy.NotAvailable('Handle type unsupported %d' % handle_type)
            handles.append(handle.id)
            self.add_client_handle(handle, sender)
        return handles
        
    @logexceptions(logger)
    def RequestChannel(self, type, handle_type, handle_id, suppress_handler):    
        self.check_connected()

        channel = None
        channel_manager = self._channel_manager
        handle = self.handle(handle_type, handle_id)
        if type == telepathy.CHANNEL_TYPE_CONTACT_LIST:
            channel = channel_manager.channel_for_list(handle, suppress_handler)
        elif type == telepathy.CHANNEL_TYPE_TEXT:
            if handle_type != telepathy.HANDLE_TYPE_CONTACT:
                raise telepathy.NotImplemented("Only Contacts are allowed")
            
            channel = channel_manager.channel_for_text(handle, None, suppress_handler)
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
        return MixerHandleFactory(self, 'contact', buddy.jid)
    
    def init_channels(self):
        #for name in ['subscribe', 'publish', 'hide', 'allow', 'deny']:
        for name in ['subscribe', 'publish']:
            self.get_list_channel(name)
        
    def get_list_channel(self, name):
        handle = MixerHandleFactory(self, 'list', name)
        return self._channel_manager.channel_for_list(handle)
        
    def get_group_channels(self):
        channels = []
        for handle, ch in self._channel_manager._list_channels.items():
            if isinstance(ch, MixerGroupChannel):
                channels.append(ch)
        return channels
            
    def _advertise_disconnected(self):
        self._manager.disconnected(self)
            