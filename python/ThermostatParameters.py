import configparser
import datetime
import json
#from _overlapped import NULL




class ProgramDataClass:     
    def __init__(self, TimeActive, MasterTempS, TempSetP, TempSetPC, FanOnoff, Day):
        self.TimeActiveFrom = TimeActive                        # The time this program segment is active from
        self.MasterTempSensor = MasterTempS                     # The index of the active temp sensor
        self.TempSetPointHeat    = TempSetP                     # temperature set point for AC
        self.TempSetPointCool    = TempSetPC                    # temperature set point for AC
        self.fanon   = FanOnoff                                 # is the fan on or off
        self.Day   = Day               
    


class ThermostatState:
    def __init__(self, program): 
        self.CurrentProgram = program       
    tempORtime = datetime.datetime.now()    
    tempORactive = False
    tempORlength = 1
    tempORtemp = 20
    fanORtime = datetime.datetime.now()
    fanORactive = False
    fanORlength = 1
    fanORstate = 0
    heaterstate = 0 
    fanState = 0
    acstate = 0 
    mode = 1 # 1 = heat, 2 = cool, 0 = off  
    tset = 0
    overrideexp = 0 
    hddspace = 0         
    sensorTemp = 0


class SensorParameters:
    def __init__(self):    
        config = configparser.RawConfigParser()            
        config.optionxform = str
        config.read('/home/pi/thermostat/python/thermostat.conf')
        settings = config['main']
        
        self.webiopi = int(settings['webiopi'])
        self.LocalSensors = dict(config.items('localsensors'))
        for (key, value) in self.LocalSensors.items():                 
            self.LocalSensors[key] = {'temperature' : 0, 'pressure' : 0 , 'humidity' : 0, 'read_successful' : False }
            cfg = value.split(',')
            self.LocalSensors[key]['type'] = cfg[0].strip()
            self.LocalSensors[key]['i2c_address'] = cfg[1].strip()
            self.LocalSensors[key]['webiopi_name'] = cfg[2].strip()                
            
        
        self.RemoteSensors = dict(config.items('remotesensors'))
        for (key, value) in self.RemoteSensors.items():
            self.RemoteSensors[key] = { 'ip' : value, 'temperature' : 0, 'pressure' : 0 , 'humidity' : 0, 'read_successful' : False }
            
    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class ThermostatParameters:
    def __init__(self):
            config = configparser.RawConfigParser()            
            config.optionxform = str
            config.read('/home/pi/thermostat/python/thermostat.conf')
            settings = config['main']            
            self.HEATER = int(settings['HEATER'])
            self.FAN = int(settings['FAN'])
            self.AC = int(settings['AC'])            
            self.ThermostatStateFile = settings['ThermostatStateFile']
            self.ThermostatLogFile = settings['ThermostatLogFile']
            self.ProgramsFolder = settings['ProgramsFolder']
            self.loginterval = int(settings['loginterval'])
    
    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)