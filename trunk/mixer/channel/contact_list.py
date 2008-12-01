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

from mixer.util.decorator import async, logexceptions
from mixer.handle import MixerHandleFactory

from mxit.handles import Presence

__all__ = ['MixerContactListChannelFactory']

logger = logging.getLogger("Mixer.ContactList")

def MixerContactListChannelFactory(connection, handle):
    
    if handle.get_name() == 'subscribe':
        channel_class = MixerSubscribeListChannel
    elif handle.get_name() == 'publish':
        channel_class = MixerPublishListChannel
    elif handle.get_name() == 'hide':
        channel_class = MixerHideListChannel
    elif handle.get_name() == 'allow':
        channel_class = MixerAllowListChannel
    elif handle.get_name() == 'deny':
        channel_class = MixerDenyListChannel
    else:
        raise TypeError("Unknown list type : " + handle.get_name())
    logger.info("Contact list channel creating: %s" % channel_class)
    return channel_class(connection, handle)


class MixerListChannel(
        telepathy.server.ChannelTypeContactList,
        telepathy.server.ChannelInterfaceGroup):
    "Abstract Contact List channels"

    def __init__(self, connection, handle):
        self.con = connection
        telepathy.server.ChannelTypeContactList.__init__(self, connection, handle)
        telepathy.server.ChannelInterfaceGroup.__init__(self)
        self._populate(connection)

    def GetLocalPendingMembersWithInfo(self):
        return []
    
    
    @logexceptions(logger)
    def GetLocalPendingMembers(self):
        result = []
        for info in self.GetLocalPendingMembersWithInfo():
            result.append(info[0])
        logger.info("Local pending membmers: %r" % (result))
        return result

    @async
    def _populate(self, connection):
        added = set()
        local_pending = set()
        remote_pending = set()
        
        buddies = list(connection.mxit.roster.all_buddies()) + list(connection.mxit.roster.all_rooms())
        for contact in buddies:
            ad, lp, rp = self._filter_contact(contact)
            if ad or lp or rp:
                #handle = MixerHandleFactory(self.con, 'contact', contact.jid)
                handle = self.con.handle_for_buddy(contact)
                if ad: added.add(handle)
                if lp: local_pending.add(handle)
                if rp: remote_pending.add(handle)
        self.MembersChanged('', added, (), local_pending, remote_pending, 0,
                telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

    def _filter_contact(self, contact):
        return (False, False, False)

    def _contains_handle(self, handle):
        members, local_pending, remote_pending = self.GetAllMembers()
        return (handle in members) or (handle in local_pending) or \
                (handle in remote_pending)
                
    def buddy_added(self, contact):
        added = set()
        local_pending = set()
        remote_pending = set()
        
        ad, lp, rp = self._filter_contact(contact)
        if ad or lp or rp:
            handle = MixerHandleFactory(self.con, 'contact',
                    contact.jid)
            if ad: added.add(handle)
            if lp: local_pending.add(handle)
            if rp: remote_pending.add(handle)
        if lp:
            reason = telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED
        else:
            reason = telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE
        self.MembersChanged('', added, (), local_pending, remote_pending, 0, reason)
        
        
    def check_buddy(self, contact):
        handle = MixerHandleFactory(self.con, 'contact', contact.jid)
        added = set()
        local_pending = set()
        remote_pending = set()
        removed = set()
        ad, lp, rp = self._filter_contact(contact)
        if ad or lp or rp:
            if ad: added.add(handle)
            if lp: local_pending.add(handle)
            if rp: remote_pending.add(handle)
        else:
            if self._contains_handle(handle):
                removed.add(handle)
        
        if lp:
            reason = telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED
        else:
            reason = telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE
            
        if added or local_pending or remote_pending or removed:
            self.MembersChanged('', added, removed, local_pending, remote_pending, 0, reason)
        
        
    def buddy_removed(self, contact):
        handle = MixerHandleFactory(self.con, 'contact', contact.jid)
        if self._contains_handle(handle):
            self.MembersChanged('', (), [handle], (), (), 0, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

class MixerSubscribeListChannel(MixerListChannel):
    """Subscribe List channel.

    This channel contains the list of contact to whom the current user is
    'subscribed', basically this list contains the contact for whom you are
    supposed to receive presence notification."""

    def __init__(self, connection, handle):
        MixerListChannel.__init__(self, connection, handle)
        self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_CAN_ADD |
                telepathy.CHANNEL_GROUP_FLAG_CAN_REMOVE, 0)

    @logexceptions(logger)
    def AddMembers(self, contacts, message):
        logger.info("TODO: subscribe add members: %s" % (contacts))
        for handle_id in contacts:
            handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
            contact = handle.contact
            
            if contact:
                logger.info("Contact: %r" % contact)
                if not contact.is_subscribed():
                    logger.info("inviting %s" % contact.jid)
                    self._conn.mxit.invite(contact.jid, contact.name, contact.group)
            else:
                self._conn.mxit.invite(handle.jid, handle.jid, self._conn.mxit.roster.root_group)
            
    
    @logexceptions(logger)
    def RemoveMembers(self, contacts, message):
        logger.info("removing members from subscribe list")
        
        for h in contacts:
            handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, h)
            contact = handle.contact
            if contact:
                logger.info("Removing %s" % contact)
                self._conn.mxit.remove_buddy(contact)
            #self.buddy_removed(contact)

    def _filter_contact(self, contact):
        if contact:
            return (True, False, False)
        else:
            return (False, False, False)

    # pymsn.event.ContactEventInterface
    def on_contact_memberships_changed(self, contact):
        handle = MixerHandleFactory(self.con, 'contact',
                contact.account, contact.network_id)
        if contact.is_member(pymsn.Membership.FORWARD):
            self.MembersChanged('', [handle], (), (), (), 0,
                    telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED)
            if len(handle.pending_groups) > 0:
                ab = self._conn.msn_client.address_book
                for group in handle.pending_groups:
                    ab.add_contact_to_group(group, contact)
                handle.pending_groups = set()


class MixerPublishListChannel(MixerListChannel):

    def __init__(self, connection, handle):
        MixerListChannel.__init__(self, connection, handle)
        self.GroupFlagsChanged(0, 0)

    @logexceptions(logger)
    def AddMembers(self, contacts, message):       
        logger.info("Publishing...")
        for contact_handle_id in contacts:
            contact_handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, contact_handle_id)
            contact = contact_handle.contact
            self.con.mxit.accept_invite(contact)
            #ab.accept_contact_invitation(contact, False)
    
    @logexceptions(logger)
    def RemoveMembers(self, contacts, message):
        logger.info("removing members from publish list")
        
        for h in contacts:
            handle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, h)
            contact = handle.contact
            logger.info("Rejecting %s" % contact.jid)
            self._conn.mxit.reject_buddy(contact)
            
    @logexceptions(logger)
    def GetLocalPendingMembersWithInfo(self):
        result = []
        
        for contact in self.con.mxit.roster.all_buddies():
            if contact.presence != Presence.PENDING:
                continue
            
            handle = MixerHandleFactory(self.con, 'contact',
                        contact.jid)
            result.append((handle, handle,
                    telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED,
                    'you are invited!'))
        return result
            

    def _filter_contact(self, contact):
        if contact:
            return (contact.is_subscribed(), contact.presence == Presence.PENDING, False)
        else:
            return (False, False, False)

    # pymsn.event.ContactEventInterface
    def on_contact_memberships_changed(self, contact):
        handle = MixerHandleFactory(self._conn_ref(), 'contact',
                contact.account, contact.network_id)
        if self._contains_handle(handle):
            contact = handle.contact
            if contact.is_member(pymsn.Membership.PENDING):
                # Nothing worth our attention
                return

            if contact.is_member(pymsn.Membership.FORWARD):
                # Contact accepted
                self.MembersChanged('', [handle], (), (), (), 0,
                        telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED)
            else:
                # Contact rejected
                self.MembersChanged('', (), [handle], (), (), 0,
                        telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)
