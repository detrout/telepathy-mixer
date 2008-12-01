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
import exceptions

from mixer.util.decorator import async, logexceptions
from mixer.channel.text import MixerTextChannel
from mixer.channel.multitext import MixerRoomChannel

from mxit.handles import Mood

__all__ = ['CommandHandler']

logger = logging.getLogger('Mixer.Commands')

class CommandHandler:
    def __init__(self, con):
        self.con = con
        
    def get_buddy(self, channel, args):
        if isinstance(channel, MixerTextChannel):
            buddy = channel.contact_handle.contact
            if buddy and not buddy.is_room():
                return (buddy, args)
        if args:
            buddy = self.con.mxit.roster.get_buddy(args[0])
            
            if not buddy:
                buddy = self.con.mxit.roster.find_buddy(args[0])
                
            return (buddy, args[1:])
        else:
            return (None, args)
        
    def get_room(self, channel, args):
        if isinstance(channel, MixerTextChannel):
            buddy = channel.contact_handle.contact
            if buddy and buddy.is_room():
                return (buddy, args)
        
        if args:
            room = self.con.mxit.roster.get_room(args[0])
            
            if not room:
                room = self.con.mxit.roster.find_room(args[0])
                
            return (room, args[1:])
        else:
            return (None, args)
    
    def _get_func(self, name):
        return getattr(self, name)
    
    def get_mood(self, text):
        if text.isdigit():
            return Mood.byid(int(text))
        else:
            return getattr(Mood, text)
        
    def _handle_command(self, command, channel, *args):
        logger.info("COMMAND %s, %s, %s" % (command, channel, args))
        if hasattr(self, command):
            f = self._get_func(command)
            try:
                f(channel, *args)
            except Exception, e:
                self.help(channel, command)
                raise
        else:
            logger.info("command not found")
    
    def handle_command(self, channel, message):
        args = message.split()
        cmd = args[0][1:]
        args = args[1:]
        
        self._handle_command(cmd, channel, *args)
        
        
    def help(self, channel, *args):
        if args:
            name = args[0]
            func = self._get_func(name)
            doc = unicode(func.__doc__)
        else:
            doc = """ Available commands:
            /mood - set your mood
            /create - create a MultiMX room
            /invite - invite a buddy to a MultiMX room
            """
        self.con.info(doc, channel)
        
    def invite(self, channel, *args):
        """ Usage: /invite <buddy>
        
        Must be called from a room.
        
        buddy can be either the name or the id of the buddy
        """
        room, args = self.get_room(channel, args)
        buddy, args = self.get_buddy(None, args)
        logger.info("Inviting %s to room %s" % (buddy, room))
        if room and buddy:
            self.con.mxit.invite_buddies_room(room, [buddy])
        else:
            raise exceptions.Exception("Invalid room or buddy")
        
    def leave(self, channel, *args):
        """ Usage: /leave
        
        Leaves the room.
        
        Must be called from a room.
        """
        room, args = self.get_room(channel, args)
        
        if room:
            logger.info("Leaving room %s" % (room))
            self.con.mxit.leave_room(room)
        else:
            raise exceptions.Exception("Invalid room")
        
    def create(self, channel, *args):
        """ Usage: /create <name>
        
        Create a room with the specified name.
        """
        if args:
            name = args[0]
            
            self.con.mxit.create_room(name)
        else:
            raise exceptions.Exception("Name must be specified")
        
    def mood(self, channel, *args):
        """ Usage: /mood <mood>
        
        moods: none, happy, sad, grumpy, angry, excited, inlove, invincible, hot, sick, sleepy
        """
        if args:
            name = args[0].upper()
            mood = self.get_mood(name)
        else:
            mood = Mood.NONE
        
        self.con.mxit.set_mood(mood)