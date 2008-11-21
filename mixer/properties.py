import telepathy
import logging

from mixer.util.decorator import async, logexceptions

logger = logging.getLogger('Mixer.Properties')

class MixerProperties(telepathy.server.PropertiesInterface):
    
    def __init__(self, properties):
        telepathy.server.PropertiesInterface.__init__(self)
        #self.props = [(i) + p for p in properties]
        self.ids = {}
        self.props = []
        for i, p in enumerate(properties):
            self.props.append((i,) + p)
            self.ids[p[0]] = i
            
        self.values = [None for p in properties]
        
        
        
        
    @logexceptions(logger)
    def ListProperties(self):
        #logger.info("list properties: %r" % self.props)
        return self.props
        
    @logexceptions(logger)
    def GetProperties(self, ids):
        #logger.info("get properties")
        props = []
        for i in ids:
            if self.values[i]:
                props.append((i, self.values[i]))
        return props
    
    def _set_property(self, name, value):
        i = self.ids[name]
        self.values[i] = value
        self.PropertiesChanged([(i, value)])
        
    def _set(self, **properties):
        props = []
        for key, value in properties.items():
            i = self.ids[key]
            self.values[i] = value
            props.append((i, value))
        self.PropertiesChanged(props)