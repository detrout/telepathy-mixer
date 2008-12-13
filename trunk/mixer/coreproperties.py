import telepathy
import logging
import dbus

from mixer.util.decorator import async, logexceptions

logger = logging.getLogger('Mixer.CoreProperties')

class MixerCoreProperties(dbus.service.Interface):
    
    def __init__(self):
        dbus.service.Interface.__init__(self)
        self._props = {}
        self._interfaces.add('org.freedesktop.DBus.Properties')
        
        
        
    
    @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        logger.info("getall %s" % interface)
        result = {}
        for name in self._interface(interface):
            result[name] = self._get(interface, name)
        #logger.info("%r" % (result))
        return result
            
    @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='ss', out_signature='v')
    def Get(self, interface, name):
        logger.info("Get %s, %s" % (interface, name))
        r = self._get(interface, name)
        logger.info("%r" % (r))
        return r
    
    
        
    @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='ssv', out_signature='')
    def Set(self, interface, name, value):
        logger.info("Set %s|%s=%s" % (interface, name, value))
        self._set(interface, name, value)
        
    def get_qualified(self, props):
        result = {}
        for interface in props:
            for name in props[interface]:
                result['%s.%s' % (interface, name)] = self._get(interface, name)
        return result
    
    def set_qualified(self, props):
        for name, value in props.items():
            i = name.rindex('.')
            self._set(name[:i], name[i+1:], value)
        
    def _interface(self, interface):
        if interface not in self._props:
            self._props[interface] = {}
        return self._props[interface]
        
    def _get(self, interface, name):
        attr, access = self._interface(interface)[name]
        if 'r' in access:
            return getattr(self, attr)
        else:
            #TODO: raise exception
            return getattr(self, attr)
    
    def _set(self, interface, name, value):
        attr, access = self._interface(interface)[name]
        if 'w' in access:
            setattr(self, attr, value)
        else:
            #TODO: raise exception
            pass
        
    def _register_rw(self, interface, *props, **properties):
        for name in props:
            self._interface(interface)[name] = (name, 'rw')
        for attr, name in properties.items():
            self._interface(interface)[name] = (attr, 'rw')
    
    def _register_r(self, interface, *props, **properties):
        for name in props:
            self._interface(interface)[name] = (name, 'r')
        for attr, name in properties.items():
            self._interface(interface)[name] = (attr, 'r')
            
    def identifiers(self):
        r = {}
        for interface, vals in self._props.items():
            for name, (attr, access) in vals.items():
                if access == 'r':
                    r["%s.%s" % (interface, name)] = self._get(interface, name)
        return r