import configparser
import datetime
import json

class ThermostatParameters:
    
    tempORtime = datetime.datetime.now()    
    tempORactive = False
    tempORlength = 1
    tempORtemp = 20
    fanORtime = datetime.datetime.now()
    fanORactive = False
    fanORlength = 1
    fanORstate = 0
    fanState = 0
    mode = 1 # 1 = heat, 2 = cool, 0 = off  
    tset = 0

    def __init__(self):
            config = configparser.RawConfigParser()            
            config.read('/home/pi/temperature/thermostat.conf')
            settings = config['main']            
            config.optionxform=str
            self.HEATER = int(settings['heater'])
            self.FAN = int(settings['fan'])
            self.AC = int(settings['ac'])
            self.webiopi = int(settings['webiopi'])
            self.ThermostatStateFile = settings['thermostatstatefile']
            self.ThermostatLogFile = settings['thermostatlogfile']
            self.ProgramsFolder = settings['programsfolder']
                  
            
            self.LocalSensors = dict(config.items('localsensors'))
            for (key, value) in self.LocalSensors.items():                 
                self.LocalSensors[key] = {'temperature' : 0, 'pressure' : 0 , 'humidity' : 0, 'read_successful' : False }
                cfg = value.split(',')
                self.LocalSensors[key]['type'] = cfg[0]
                self.LocalSensors[key]['i2c_address'] = cfg[1]
                self.LocalSensors[key]['webiopi_name'] = cfg[2]                
                
            
            self.RemoteSensors = dict(config.items('remotesensors'))
            for (key, value) in self.RemoteSensors.items():
                self.RemoteSensors[key] = { 'ip' : value, 'temperature' : 0, 'pressure' : 0 , 'humidity' : 0, 'read_successful' : False }

    
    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)