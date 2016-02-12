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
        
        self.tempORtime = datetime.datetime.utcnow()    
        self.tempORactive = False
        self.tempORlength = 1
        self.tempORtemp = 20
        self.fanORtime = datetime.datetime.utcnow()
        self.fanORactive = False
        self.fanORlength = 1
        self.fanORstate = 0
        self.heaterstate = 0 
        self.fanState = 0
        self.acstate = 0 
        self.mode = 1 # 1 = heat, 2 = cool, 0 = off  
        self.tset = 0
        self.overrideexp = 0 
        self.hddspace = 0         
        self.sensorTemp = 0
    
    def to_JSON(self):
        date_handler = lambda obj: (
            obj.isoformat()
            if isinstance(obj, datetime.datetime)
            or isinstance(obj, datetime.date)
            else obj.__dict__            
        )
        return json.dumps(self, default=date_handler, sort_keys=True, indent=4)




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
            cfg = value.split(',')
            self.RemoteSensors[key] = { 'temperature' : 0, 'pressure' : 0 , 'humidity' : 0, 'read_successful' : False }
            self.RemoteSensors[key]['ip'] = cfg[0].strip()
            self.RemoteSensors[key]['type'] = cfg[1].strip()
            self.RemoteSensors[key]['webiopi_name'] = cfg[2].strip()
            
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
    

class DatabaseParameters:
    def __init__(self):
            config = configparser.RawConfigParser()            
            config.optionxform = str
            config.read('/home/pi/thermostat/python/thermostat.conf')
            settings = config['database']
            self.__dict__.update(settings)
            
            
                    
    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)