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

from mixer.presence import MixerPresence
from mixer.aliasing import MixerAliasing
from mixer.commands import CommandHandler
from mixer.handle import MixerHandleFactory
from mixer.channel.contact_list import MixerListChannel
from mixer.channel.group import MixerGroupChannel
from mixer.channel.multitext import MixerRoomChannel
from mixer.channel_manager import ChannelManager
from mixer.util.decorator import async, logexceptions

__all__ = ['MixerListener']

logger = logging.getLogger('Mixer.Listener')

class MixerListener:
    def __init__(self, mixer_con):
        self.con = mixer_con
        
    def message_received(self, message):
        sender = message.buddy
        if sender.is_room():
            logger.info("Ignoring room message: %s" % message)
        else:
            channel = self.con.get_buddy_channel(sender)
            channel.message_received(message)
        
    def room_message_received(self, room, message):
        channel = self.con.get_room_channel(room)
        #contact_handle = self.con.handle_for_buddy(message.buddy)
        contact_handle = self.con.handle_for_buddy(room)
        msg = "<%s> %s" % (message.buddy.name, message.message)
        message.message = msg
        message.buddy = room
        channel.message_received(message)
    
    def room_buddies_joined(self, room, buddies):
        names = [buddy.name for buddy in buddies]
        logger.info("These buddies joined: %s" % names)
        channel = self.con.get_room_channel(room)
        if len(names) == 1:
            msg = "%s has joined" % (','.join(names))
        else:
            msg = "%s have joined" % (','.join(names))
        message = Message(room, msg)
        channel.message_received(message, type=telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NOTICE)
        #channel.buddies_joined(buddies)
        
    def room_buddies_left(self, room, buddies):
        names = [buddy.name for buddy in buddies]
        logger.info("These buddies left: %s" % names)
        channel = self.con.get_room_channel(room)
        if len(names) == 1:
            msg = "%s has left" % (','.join(names))
        else:
            msg = "%s have left" % (','.join(names))
        message = Message(room, msg)
        channel.message_received(message, type=telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NOTICE)
        #channel.buddies_left(buddies)
    
    def room_added(self, room, message=None):
        #channel = self.con.get_room_channel(room)
        logger.info('Room name: %s' % room.name)
        self.buddy_added(room)
        
        #channel._set(name=room.name)
        #channel.open()
        
#        if message:
#            self.con.info(message, channel)
#        else:
#            self.con.info("Room created", channel)
        
    def room_updated(self, room, **attrs):
        self.buddy_updated(room, **attrs)
#        channel = self.con.get_room_channel(room)
#        logger.info('Room name: %s' % room.name)
#        if 'name' in attrs:
#            channel._set(name=room.name)
            
    def room_removed(self, room):
        self.buddy_removed(room)
#        channel = self.con.get_room_channel(room)
#        channel.close()
    
    def room_create_error(self, name, response):
        #handle = MixerHandleFactory(self.con, 'room', name)
        #channel = self.con._channel_manager.channel_for_room(handle)
        self.con.notify_error(response.message)
    
    def message_sent(self, message):
        recipient = message.buddy
        if recipient.type == BuddyType.ROOM:
            channel = self.con.get_room_channel(recipient)
        else:
            channel = self.con.get_buddy_channel(recipient)
            #handle = self.con.handle_for_buddy(recipient)
            #handle = MixerHandleFactory(self.con, 'contact', recipient.jid)
            #channel = self.con._channel_manager.channel_for_text(handle)
            
        channel.Sent(int(time.time()), telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, message.message)
        
    
    def message_error(self, message, error="Message cannot be delivered"):        
        recipient = message.buddy
        if recipient.type == BuddyType.ROOM:
            channel = self.con.get_room_channel(recipient)
        else:
            channel = self.con.get_buddy_channel(recipient)
        
        ts = int(time.time())
        channel.SendError(ts, telepathy.CHANNEL_TEXT_SEND_ERROR_UNKNOWN, telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, message.message)
        
        
    def presence_changed(self, presence):
        self.con.presence_received(self.con.mxit.roster.self_buddy)
    
    def mood_changed(self, mood):
        self.con.presence_received(self.con.mxit.roster.self_buddy)
    
    def buddy_updated(self, buddy, **attrs):
        #logger.info("Buddy updated: %r" % (attrs))
        if 'presence' in attrs:
            self.con.presence_received(buddy)
            for channel in map(self.con.get_list_channel, ['subscribe', 'publish']):
                channel.check_buddy(buddy)
        elif 'mood' in attrs:
            self.con.presence_received(buddy)
            
        if 'name' in attrs:
            self.con._contact_alias_changed(buddy)
        if 'group' in attrs:
            self._add_to_group(buddy)
    
    def profile_updated(self, profile, **attrs):
        logger.info("Profile updated: %r" % (attrs))
        
        if 'name' in attrs:
            self.con._contact_alias_changed(profile)
            
        #if 'group' in attrs:
        #    self._add_to_group(buddy)
            
    def buddy_added(self, buddy):
        #logger.info("Buddy added|%s" % buddy)
        for channel in map(self.con.get_list_channel, ['subscribe', 'publish']):
            channel.buddy_added(buddy)
            
        self._add_to_group(buddy)
        self.con._contact_alias_changed(buddy)
    
    def room_removed(self, room):
        self.buddy_removed(room)
          
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