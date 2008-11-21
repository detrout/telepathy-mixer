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

import telepathy

from mixer.util.decorator import async, logexceptions
from mixer.handle import MixerHandleFactory
from mixer.channel.contact_list import MixerListChannel

__all__ = ['MixerGroupChannel']

logger = logging.getLogger('Mixer.GroupChannel')


class MixerGroupChannel(MixerListChannel):

    def __init__(self, connection, handle):
        self.__pending_add = []
        self.__pending_remove = []
        MixerListChannel.__init__(self, connection, handle)
        
        self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_CAN_ADD | 
                telepathy.CHANNEL_GROUP_FLAG_CAN_REMOVE | telepathy.CHANNEL_GROUP_FLAG_ONLY_ONE_GROUP, 0)
        

    @logexceptions(logger)
    def AddMembers(self, contacts, message):
        try:
            added = set()
            for contact_handle_id in contacts:
                handle = self.con.handle(telepathy.HANDLE_TYPE_CONTACT, contact_handle_id)
                contact = handle.contact
                group = self._handle.group
                self.con.mxit.update_buddy(contact, group=group)
                
        except:
            import traceback
            logger.error(traceback.format_exc())

    @logexceptions(logger)
    def RemoveMembers(self, contacts, message):
        removed = set()
        for contact_handle_id in contacts:
            handle = self.con.handle(telepathy.HANDLE_TYPE_CONTACT, contact_handle_id)
            contact = handle.contact
            group = self._handle.group
            root_group = self.con.mxit.roster.root_group()
            if contact.group == group:
                self.con.mxit.update_buddy(contact, group=root_group)
              


    def remove_contacts(self, handles):
        self.MembersChanged('', (), handles, (), (), 0,
                        telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
        
    def add_contacts(self, handles):
        self.MembersChanged('', handles, (), (), (), 0,
                        telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
        
    def Close(self):
        # Groups in MXit are never actually deleted
        logger.debug("Deleting group %s" % self._handle.name)

    def _filter_contact(self, contact):
        if contact.group.name == self._handle.name:
            return (True, False, False)
        else:
            return (False, False, False)

    # TODO: check if similar functionality is required
    def on_addressbook_group_deleted(self, group):
        if group.name == self._handle.name:
            self.Closed()
            self._conn.remove_channel(self)

