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

import telepathy

from mixer.handle import MixerHandleFactory
from mixer.util.decorator import async, logexceptions

__all__ = ['MixerAliasing']

logger = logging.getLogger('Mixer.Aliasing')

class MixerAliasing(telepathy.server.ConnectionInterfaceAliasing):

    def __init__(self):
        telepathy.server.ConnectionInterfaceAliasing.__init__(self)

    @logexceptions(logger)
    def RequestAliases(self, contacts):
        result = []
        for handle_id in contacts:
            handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
            contact = handle.contact
            alias = contact.name
            if isinstance(alias, unicode):
                result.append(alias)
            else:
                result.append(unicode(alias, 'utf-8'))
        return result

    @logexceptions(logger)
    def SetAliases(self, aliases):
        for handle_id, alias in aliases.iteritems():
            handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
            if handle != MixerHandleFactory(self, 'self'):
                logger.info("Renaming %r to %s" % (handle, alias))
                buddy = handle.contact
                
                self.mxit.update_buddy(buddy, name=alias)
               
            else:
                logger.info("Self alias changed to '%s' - not implemented yet" % alias)
                #self.AliasesChanged(((MixerHandleFactory(self, 'self'), alias), ))"""
       
    @async
    def _contact_alias_changed(self, contact):
        handle = MixerHandleFactory(self, 'contact', contact.jid)

        alias = contact.name
        alias = unicode(alias, 'utf-8')
        #logger.info("Contact %r alias changed to '%s'" % (handle, alias))
        self.AliasesChanged(((handle, alias), ))

