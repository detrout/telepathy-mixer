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
import time
import exceptions

import telepathy

from mxit.handles import Presence, Mood

from mixer.handle import MixerHandleFactory
from mixer.util.decorator import async, logexceptions

__all__ = ['MixerPresence']

logger = logging.getLogger('Mixer.Presence')

class MixerPresenceMapping(object):
    AVAILABLE = 'available'
    AWAY = 'away'
    BRB = 'brb'
    BUSY = 'busy'
    DND = 'dnd'
    XA = 'xa'
    HIDDEN = 'hidden'
    OFFLINE = 'offline'
    UNKNOWN = 'unknown'
    ERROR = 'error'
#    * available (corresponding to Connection_Presence_Type_Available)
#    * away (corresponding to Connection_Presence_Type_Away)
#    * brb (Be Right Back) (corresponding to Connection_Presence_Type_Away, but more specific)
#    * busy (corresponding to Connection_Presence_Type_Busy)
#    * dnd (Do Not Disturb) (corresponding to Connection_Presence_Type_Busy, but more specific)
#    * xa (Extended Away) (corresponding to Connection_Presence_Type_Extended_Away)
#    * hidden (aka Invisible) (corresponding to Connection_Presence_Type_Hidden)
#    * offline (corresponding to Connection_Presence_Type_Offline)
#    * unknown (corresponding to Connection_Presence_Type_Unknown)
#    * error (corresponding to Connection_Presence_Type_Error)


    to_mxit = {
            AVAILABLE: Presence.AVAILABLE,
            AWAY: Presence.AWAY,
            BUSY: Presence.BUSY,
            XA: Presence.XA,
            OFFLINE: Presence.OFFLINE,
            UNKNOWN: Presence.PENDING,
            }

    to_telepathy = {
            Presence.AVAILABLE: AVAILABLE,
            Presence.AWAY: AWAY,
            Presence.BUSY:BUSY,
            Presence.XA: XA,
            Presence.CHAT: AVAILABLE,
            Presence.OFFLINE: OFFLINE,
            #Presence.NONE: UNKNOWN,
            Presence.PENDING: UNKNOWN,
            }


class MixerPresence(telepathy.server.ConnectionInterfacePresence):

    def __init__(self):
        telepathy.server.ConnectionInterfacePresence.__init__(self)
        

    @logexceptions(logger)
    def GetStatuses(self):
        # the arguments are in common to all on-line presences
        #arguments = {'message' : 's'}
        arguments = {}

        # you get one of these for each status
        # {name:(type, self, exclusive, {argument:types}}
        return {
            MixerPresenceMapping.AVAILABLE:(
                telepathy.CONNECTION_PRESENCE_TYPE_AVAILABLE,
                True, True, arguments),
            MixerPresenceMapping.AWAY:(
                telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
                True, True, arguments),
            MixerPresenceMapping.BUSY:(
                telepathy.CONNECTION_PRESENCE_TYPE_BUSY,
                True, True, arguments),
            MixerPresenceMapping.XA:(
                telepathy.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
                True, True, arguments),
            MixerPresenceMapping.OFFLINE:(
                telepathy.CONNECTION_PRESENCE_TYPE_OFFLINE,
                True, True, arguments),            
            MixerPresenceMapping.UNKNOWN:(
                7,                        #telepathy.CONNECTION_PRESENCE_TYPE_UNKNOWN
                True, True, arguments),
        }

    @logexceptions(logger)
    def RequestPresence(self, contacts):
        presences = self.get_presences(contacts)
        self.PresenceUpdate(presences)

    @logexceptions(logger)
    def GetPresence(self, contacts):
        return self.get_presences(contacts)

    @logexceptions(logger)
    def SetStatus(self, statuses):
        status, arguments = statuses.items()[0]
        if status == MixerPresenceMapping.OFFLINE:
            self.Disconnect()

        presence = MixerPresenceMapping.to_mxit[status]
        #message = arguments.get('message', u'').encode("utf-8")

        logger.info("Setting Presence to '%s'" % presence)
       
        
        self.mxit.set_presence(presence)

    def get_presences(self, contacts):
        presences = {}
        for handle_id in contacts:
            handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
            
            contact = handle.contact
            presences[handle] = (0, self._get_presence(contact))
                
        return presences

    def presence_received(self, buddy):
        handle = self.handle_for_buddy(buddy)
        self._presence_changed(handle)
        
    def _get_presence(self, buddy):
        if buddy:
            mood = buddy.mood
            presence = MixerPresenceMapping.to_telepathy[buddy.presence]
            
            arguments = {}
            if buddy.is_room():
                arguments = {'message' : 'MultiMX'}
            else:
                if mood != Mood.NONE:
                    arguments = {'message' : mood.text}
            
            return {presence : arguments}
        else:
            return {MixerPresenceMapping.OFFLINE : {}}
        
    @async
    def _presence_changed(self, handle):
        buddy = handle.contact
        
        self.PresenceUpdate({handle: (int(time.time()), self._get_presence(buddy))})
