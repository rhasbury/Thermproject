import logging
import datetime
import time
import json
import configparser
import os
import socketserver
import socket
import threading
import sys
from http.cookiejar import DAYS
from setuptools.command.build_ext import if_dl
# for sensor libraries
import board
import busio
from adafruit_htu21d import HTU21D
import Adafruit_BMP.BMP085 as BMP085

import RPi.GPIO as GPIO
from multiprocessing.managers import State
#from builtins import False

sys.path.append('/home/pi/thermostat/python')

#import locale
from _ctypes import addressof
from ThermostatParameters import *
from dblogging import *
#from emailwarning import *
from discordNotifier import *



# Connection information for pulling operational info (sensor readings, equipment state, etc) 
HOST, PORT = "localhost", 50007



lastlogtime = datetime.datetime.utcnow()
ActiveProgramID = 0
ActiveProgram = 0 
LastProgram = 0 
LastProgramID = 0
my_logger = logging.getLogger('MyLogger')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
hdlr = logging.FileHandler('/home/pi/thermostat/thermostat.log')
hdlr.setFormatter(formatter)
my_logger.addHandler(hdlr)
my_logger.setLevel(logging.DEBUG)


Tparams = ThermostatParameters()
Sparams = SensorParameters()
CurrentState = ThermostatState
program = []
DBparams = DatabaseParameters()
#email = emailNotifier()




serverthread = None
TempUpdateThread = None
Thermostat_thread = None

# HVAC control class
#This should be the only block in which the heater, fan and AC gpios are touched.     
class HVAC():
    global CurrentState  
#    def __init__(self):
         
    def set_heat(self, state):
        if(CurrentState.heaterstate == state):
            my_logger.debug("Set_heat called, but state matches so not doing anything.")
        elif(state == 1):
            my_logger.debug("Turning the heater on")
            self.set_cool(0)
            self.set_fan(0)            
            GPIO.output(Tparams.HEATER, GPIO.LOW)
            log_runtime_to_db(DBparams, CurrentState.heatlastchange, state, 'heater')             
            CurrentState.heatlastchange = datetime.datetime.utcnow()                   
            CurrentState.heaterstate = 1
            my_logger.info("Turned heater on and the last time it was switched was {0}".format(CurrentState.heatlastchange))
        elif(state == 0):
            my_logger.debug("Turning the heater off")
            GPIO.output(Tparams.HEATER, GPIO.HIGH)
            log_runtime_to_db(CurrentState.heatlastchange, my_logger, state, 'heater') 
            CurrentState.heatlastchange = datetime.datetime.utcnow()
            CurrentState.heaterstate = 0
            my_logger.info("Turned heater off and the last time it was switched was {0}".format(CurrentState.heatlastchange))
    
    def set_cool(self, state):
        if(CurrentState.acstate == state):
            my_logger.debug("Set_cool called, but state matches so not doing anything.")
        elif(state == 1):
            my_logger.debug("Turning the AC on")
            self.set_heat(0)
            self.set_fan(0)            
            GPIO.output(Tparams.AC, GPIO.LOW)
            log_runtime_to_db(DBparams, my_logger, CurrentState.coollastchange, state, 'ac') 
            CurrentState.coollastchange = datetime.datetime.utcnow()
            CurrentState.acstate = 1
            my_logger.info("Turned AC on and the last time it was switched was {0}".format(CurrentState.coollastchange))
        elif(state == 0):
            my_logger.debug("Turning the AC off")
            GPIO.output(Tparams.AC, GPIO.HIGH)
            log_runtime_to_db(DBparams, my_logger, CurrentState.coollastchange, state, 'ac')  
            CurrentState.coollastchange = datetime.datetime.utcnow()
            CurrentState.acstate  = 0
            my_logger.info("Turned AC off and the last time it was switched was {0}".format(CurrentState.coollastchange))
        
    def set_fan(self, state):
        if(CurrentState.fanState == state):
            my_logger.debug("Set_fan called, but state matches so not doing anything.")
        elif(state == 1):
            my_logger.debug("Turning the fan on")
            self.set_cool()
            self.set_heat(0)            
            GPIO.output(Tparams.FAN, GPIO.LOW)
            log_runtime_to_db(CurrentState.fanlastchange, state, 'fan')
            CurrentState.fanlastchange = datetime.datetime.utcnow()                            
            CurrentState.fanState = 1
            my_logger.info("Turned fan on and the last time it was switched was {0}".format(CurrentState.fanlastchange))
        elif(state == 0):
            my_logger.debug("Turning the fan off")
            GPIO.output(Tparams.FAN, GPIO.HIGH)
            log_runtime_to_db(CurrentState.fanlastchange, state, 'fan')  
            CurrentState.fanlastchange = datetime.datetime.utcnow()
            CurrentState.fanState  = 0
            my_logger.info("Turned fan off and the last time it was switched was {0}".format( CurrentState.fanlastchange))
        
    def turn_everything_off(self):
        self.set_cool(0)
        self.set_heat(0)
        self.set_fan(0)    
        my_logger.info("Turning everything off")




class MyTCPHandler(socketserver.BaseRequestHandler):
    
    def obj_dict(self, obj):
        return obj.__dict__
 
    #The RequestHandler class for data requests from the web interface or any remote applications.   

    def handle(self):        
        date_handler = lambda obj: (
            obj.isoformat()
            if isinstance(obj, datetime.datetime)
            or isinstance(obj, datetime.date)
            else obj.__dict__            
        )
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(1024).strip()        
        if("get_tparams" in self.data.decode("utf-8")):
            self.request.sendall(bytes(Tparams.to_JSON(), 'UTF-8'))
        elif("get_sparams" in self.data.decode("utf-8")):
            self.request.sendall(bytes(Sparams.to_JSON(), 'UTF-8'))
        elif("get_state" in self.data.decode("utf-8")):
            self.request.sendall(bytes(CurrentState.to_JSON(), 'UTF-8'))            
        elif("temp_up" in self.data.decode("utf-8")):
            Thermostat_thread.temp_change(1, 30)
        elif("temp_down" in self.data.decode("utf-8")):
            Thermostat_thread.temp_change(-1, 30)            
        elif("change_mode_off" in self.data.decode("utf-8")):                        
            Thermostat_thread.setMode(0)
        elif("change_mode_heat" in self.data.decode("utf-8")):
            Thermostat_thread.setMode(1)
        elif("change_mode_cool" in self.data.decode("utf-8")):
            Thermostat_thread.setMode(2)
        elif("snooze_1hr" in self.data.decode("utf-8")):
            Thermostat_thread.snooze(60)
        elif("fan_change" in self.data.decode("utf-8")):
            Thermostat_thread.fan_change(5)
        elif("get_program_all" in self.data.decode("utf-8")):
            json_string = json.dumps(program)
            self.request.sendall(bytes(json_string, 'UTF-8'))
        elif("get_program_active" in self.data.decode("utf-8")):
            json_string = json.dumps(ActiveProgram)
            self.request.sendall(bytes(json_string, 'UTF-8'))
        
        
        def handle_error(self, request, client_address):
            my_logger.info("Baserequest handler crapped out for some reason: {}  {}".format(request, client_address))
            raise 
            


def setup():
    global CurrentState
    global server

    GPIO.setmode(GPIO.BCM)
    
    GPIO.setup(Tparams.HEATER, GPIO.OUT)
    GPIO.setup(Tparams.FAN, GPIO.OUT)
    GPIO.setup(Tparams.AC, GPIO.OUT)
    
    GPIO.output(Tparams.HEATER, GPIO.HIGH)
    GPIO.output(Tparams.HEATER, GPIO.HIGH)
    GPIO.output(Tparams.HEATER, GPIO.HIGH)
    
    CurrentState = ThermostatState()
    #CurrentState.tempORtemp = CurrentState.CurrentProgram.TempSetPointHeat    
    CurrentState.heaterstate = 0
    CurrentState.acstate = 0
    f = open(Tparams.ThermostatStateFile, 'r') 
    try:
        CurrentState.mode = int(f.readline())
    except:
        CurrentState.mode = 0
    f.close()


    # Create the temperature sensor reading thread
    #TempUpdateThread = threading.Thread(target=updateTemps)    
    TempUpdateThread = updateTemps()
    TempUpdateThread.excepthook = ThreadExceptionCatcher
    TempUpdateThread.start()
    my_logger.info("Sensor update thread started")
    
    time.sleep(1)
    #Thermostat_thread = threading.Thread(target=ThermostatThread)
    Thermostat_thread = ThermostatThread()
    Thermostat_thread.excepthook = ThreadExceptionCatcher    
    Thermostat_thread.start()
    my_logger.info("Thermostat thread started")
        
    # Create the data server and assigning the request handler            
    server = socketserver.TCPServer((HOST, PORT), MyTCPHandler)
    serverthread = threading.Thread(target=server.serve_forever)
    serverthread.excepthook = ThreadExceptionCatcher
    serverthread.daemon = True
    serverthread.start()
    my_logger.info("Data socket listener started")
    
    # Check and possibly setup database to allow logging of data    
    CheckDatabase(DBparams, my_logger)
    
    
    # All done setup tasks
    my_logger.info("Setup Completed")    


# loop function is repeatedly called by WebIOPi 
class ThermostatThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.current_value = None
        self.running = True #setting the thread running to true
        self.furnace = HVAC()
        self.loadProgramFromFile()
        self.updateProgram()
    
    
    def loadProgramFromFile(self):
        global program    
        my_logger.debug("Loading Program from file")
        try:
            with open(Tparams.ProgramsFile) as json_data:
                program = json.load(json_data)
    
        except:
            my_logger.error("Error reading program json", exc_info=True)
            program = 0

    
    def WriteProgramToFile(self):
        global program
        my_logger.debug("Writing program")
        with open(Tparams.ProgramsFile, 'w') as outfile:
            json.dump(program, outfile, indent=2)
    
        
    def updateProgram(self):
        global ActiveProgram
        global ActiveProgramID
        global program
        global LastProgram
        global LastProgramID
        my_logger.debug("Updating program")
        now = datetime.datetime.now()
        now_time = now.time()
        today = "Saturday" # set saturday to be the default program if all else fails.
        if(now.isoweekday() in range(1, 6)):
            today = "Weekday" 
        elif(now.isoweekday() == 7):
            today = "Sunday" 
        #elif() # Figure out if the day is on a known list of holidays. 
        #    today = "Holiday"
        #elif() # Figure out if today is part of a vacation
        #    today = "AwayMode"       
        try:
            LastProgram = program["programs"][today]["default"]
            LastProgramID = "default"
            for id, values  in program["programs"][today].items():    
                if(id != "default"):
                    start = datetime.datetime.strptime(values["start"], "%H:%M")
                    end = datetime.datetime.strptime(values["end"], "%H:%M") 
                    if(now_time >= start.time() and now_time > end.time()):
                        LastProgram = values
                        LastProgramID = id
                    if(now_time >= start.time() and now_time < end.time()):
                        ActiveProgram = values
                        ActiveProgramID = id
                        break
    
        except:
            my_logger.error("Error determining program section", exc_info=True)
            ActiveProgram = json.loads('{ "start" : "00:00" , "end" : "00:00", "TempSensor" : "Living Room", "TempSetPointHeat" :21, "TempSetPointCool" : 23, "EnableFan" : 0}')
            ActiveProgramID = "failed"
        
    
    
    def temp_change(self, amount, length):
        global CurrentState        
        global Tparams
        global program    
        global ActiveProgram
        global ActiveProgramID
        my_logger.debug("Temp change")
        if(CurrentState.mode == 2):
            ActiveProgram["TempSetPointCool"] = ActiveProgram["TempSetPointCool"] + (int(amount)* 0.5) 
        else:
            ActiveProgram["TempSetPointHeat"] = ActiveProgram["TempSetPointHeat"] + (int(amount)* 0.5)     
         
        self.WriteProgramToFile()
        self.updateProgram()
        
    
    def fan_change(self,length):
        global CurrentState        
        global Tparams
        global program
        my_logger.debug("Executing fan_change")
        if(CurrentState.fanORactive == False):
            CurrentState.fanORstate = program['EnableFan']            
        CurrentState.fanORstate = (CurrentState.fanORstate + 1) % 2    
        CurrentState.fanORtime = datetime.datetime.utcnow()
        CurrentState.fanORlength = int(length)
        CurrentState.fanORactive = True    
    
    
    def setMode(self, mode):    
        global CurrentState
        #CurrentState.mode = (CurrentState.mode + 1) % 3
        my_logger.debug("Changing mode to {}".format(mode))
        if(0 <= mode <= 2):
            CurrentState.mode = mode    
        f = open(Tparams.ThermostatStateFile, 'w') 
        f.write(str(CurrentState.mode))
        f.close()
    
    def Snooze(self, minutes):
        my_logger.debug("Enabling snooze mode for {} minutes".format(minutes))
        CurrentState.snooze = True
        CurrentState.snooze_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
    
    def FanOverride(self, minutes):
        my_logger.debug("Enabling fan override for {} minutes".format(minutes))
        CurrentState.fanORactive = True
        CurrentState.fanORtime = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
        
    def HeatBlast(self, minutes):
        my_logger.debug("Enabling heat blast for {} minutes".format(minutes))
        CurrentState.heatORactive = True
        CurrentState.heatORtime = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
    
    def ColdBlast(self, minutes):
        my_logger.debug("Enabling cold blast for {} minutes".format(minutes))
        CurrentState.coolORactive = True
        CurrentState.coolORtime = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
    
    
    def CancelAllOverrides(self):
        my_logger.debug("Cancelling all overrides")
        CurrentState.snooze = False
        CurrentState.fanORactive = False
        CurrentState.heatORactive = False
        CurrentState.coolORactive = False
    
    
    
    
    def run(self):      
        
        global CurrentState
        global program
        global ActiveProgram
        global ActiveProgramID
        global Sparams    
        discord = discordNotifier()
        discordMessage = ""
        my_logger.debug("Starting thermostat thread")
        while(True):
            # Update harddrive space information. 
            diskstat = os.statvfs(Tparams.ThermostatStateFile)    
            CurrentState.hddspace = (diskstat.f_bavail * diskstat.f_frsize) / 1024000     
            time.sleep(60)
            my_logger.debug("Thermostat loop")
            try:    
        
                #Check for all of the overrrides and unset any that have expired        
                if(CurrentState.snooze == True):
                    if(datetime.datetime.utcnow() > CurrentState.snooze_time):
                        CurrentState.snooze = False
                                                                
                if(CurrentState.heatORactive == True):
                    if(datetime.datetime.utcnow() > CurrentState.heatORtime):
                        CurrentState.heatORactive = False
                                                
                if(CurrentState.coolORactive == True):
                    if(datetime.datetime.utcnow() > CurrentState.coolORtime):
                        CurrentState.coolORactive = False
                                                
                if(CurrentState.fanORactive == True):
                    if(datetime.datetime.utcnow() > CurrentState.fanORtime):
                        CurrentState.fanORactive = False
                                
                try:
                    # Check to see if we've changed program sections. 
                    self.updateProgram()
                except:
                    my_logger.error("updateProgram() excepted", exc_info=True)
        
                            
                # decide which temp we're using for control and test it, allowing for failures             
                try:
                    #raise ValueError('forcing a valueerror to skip this section')
                    SensName = ActiveProgram['TempSensor'] # added this to make the lines below more readable
                        
                    if(Sparams.RemoteSensors.get(SensName) != None):        
                        if(datetime.datetime.utcnow() - Sparams.RemoteSensors[SensName]['last_read_time'] > datetime.timedelta(minutes=10)):
                            my_logger.debug("Sensor has not reported in for over 10 mins {}".format(Sparams.RemoteSensors[SensName]))
                            discordMessage = discordMessage + "! Sensor error. {0} hasn't reported in over 10 minutes \n".format(SensName)
                            raise ValueError('{0} Sensor has not had a reading in more than 10 minutes.'.format(SensName))                            
                        if(Sparams.RemoteSensors[SensName]['read_successful'] == False):
                            my_logger.debug("this is the untrustworth sensor {}".format(Sparams.RemoteSensors[SensName]))
                            raise ValueError('Remote sensor reading is untrustworthy')            
                        celsius = Sparams.RemoteSensors[SensName]['temperature']
                        CurrentState.sensor_that_actually_read = SensName
                        
                    elif(Sparams.LocalSensors.get(SensName) != None):        
                        if(datetime.datetime.utcnow() - Sparams.LocalSensors[SensName]['last_read_time'] > datetime.timedelta(minutes=10)):
                            my_logger.debug("Sensor has not reported in for over 10 mins {}".format(Sparams.LocalSensors[SensName]))
                            discordMessage = discordMessage + "! Sensor error. {0} hasn't reported in over 10 minutes \n".format(SensName)
                            raise ValueError('{0} Sensor has not had a reading in more than 10 minutes.'.format(SensName))
                            
                        if(Sparams.LocalSensors[SensName]['read_successful'] == False):
                            raise ValueError('Local sensor reading is untrustworthy')            
                        celsius = Sparams.LocalSensors[SensName]['temperature']
                        CurrentState.sensor_that_actually_read = SensName
            
                    else:
                        my_logger.debug("could not determine master sesnsor")
                        raise ValueError('could not determine master sesnsor')
                               
                
                except ValueError:        
                    celsius = 0
                    my_logger.error("Problem in sensor selection", exc_info=True)
                    for (key, value) in Sparams.LocalSensors.items():
                        if(value['read_successful'] == True and value['location'] == 'indoor' and (datetime.datetime.utcnow() - value['last_read_time'] < datetime.timedelta(minutes=10))):
                            my_logger.error("Falling back to {0} sensor for temp targeting at temp {1}".format(key, value['temperature']))
                            celsius = value['temperature']
                            CurrentState.sensor_that_actually_read = key
                            break
                    
             
        
        
                if(CurrentState.mode == 2):
                    CurrentState.tset = ActiveProgram['TempSetPointCool']
                else:
                    CurrentState.tset = ActiveProgram['TempSetPointHeat']
        
                
                    
                # Loop through sensors and detect if any of them are too hot or too cold, if they are further down it will cause just the fan to run and turn off heating or cooling. 
                CurrentState.toohot = False
                CurrentState.toocold = False
                for (key, value) in Sparams.LocalSensors.items():
                    #my_logger.info("comparing {0} to {1}.".format(value['temperature'], value['max_temp']))
                    if(value['temperature'] > value['max_temp'] and value['read_successful'] == True):
                        CurrentState.toohot = True
                        my_logger.info("Sensor at {0} reading too hot at {1}.".format(key, value['temperature']))
                        break            
                
                for (key, value) in Sparams.LocalSensors.items():
                    #my_logger.info("comparing {0} to {1}.".format(value['temperature'], value['min_temp']))
                    if(value['temperature'] < value['min_temp'] and value['read_successful'] == True):
                        CurrentState.toocold = True
                        my_logger.info("Sensor at {0} reading too cold at {1}.".format(key, value['temperature']))
                        break           
        
                               
                for (key, value) in Sparams.RemoteSensors.items():
                    #my_logger.info("comparing {0} to {1}.".format(value['temperature'], value['min_temp']))
                    if(value['temperature'] < value['min_temp'] and value['read_successful'] == True):
                        CurrentState.toocold = True
                        my_logger.info("Sensor at {0} reading too cold at {1}".format(key, value['temperature']))
                        break
                       
                        
                for (key, value) in Sparams.RemoteSensors.items():
                    #my_logger.info("comparing {0} to {1}.".format(value['temperature'], value['max_temp']))
                    if(value['temperature'] > value['max_temp'] and value['read_successful'] == True):
                        CurrentState.toohot = True
                        my_logger.info("Sensor at {0} reading too hot at {1}".format(key, value['temperature']))
                        break
        
                
                
                # Save sensor temp to state object for access by external apps
                CurrentState.sensorTemp = celsius
            
                
                # Check for things to send to discord. 
                if (celsius < discord.lowerlimit or celsius > discord.upperlimit):
                    my_logger.debug("Temperature exceeded warning.  {0} < {1} < {2}  adding to discord notification string".format(discord.lowerlimit, celsius, discord.upperlimit))
                    discordMessage = discordMessage + "!! Temperature warning. Measured temperature has reached {0} C on the {1} sensor \n".format(celsius, SensName)
                    
                if (discord.enabled == 1 and discordMessage != ""):
                    my_logger.debug("discordlogging is enabled")            
                    
                    if(datetime.datetime.utcnow() - discord.lastsend > datetime.timedelta(minutes=discord.interval)):
                        try:
                            discord.sendNotification(discordMessage)
                            discordMessage = ""
                            discord.lastsend = datetime.datetime.utcnow()
                        except:
                            my_logger.error("sending warning to discord failed", exc_info=True)               
                
                # Furnace and AC control logic starts here
                   
                my_logger.debug("CurrentState.mode {0} And celsius is {1}, CurrentState.tset {2}".format(CurrentState.mode, celsius, CurrentState.tset))
                try:
                    #Snooze/override block
                    if(CurrentState.snooze == True):
                        self.furnace.turn_everything_off()
                        my_logger.info("Snooze is active, turning everything off. celsius = {}".format(celsius))
                    elif(CurrentState.heatORactive == True and CurrentState.toohot == False):
                        my_logger.debug("Turning the heater on due to an override")
                        self.furnace.set_heat(1)
                    elif(CurrentState.coolORactive == True):
                        my_logger.debug("Turning the AC on due to an override")
                        self.furnace.set_cool(1)
                    elif(CurrentState.fanORactive == True):
                        my_logger.debug("Turning the fan on due to an override")
                        self.furnace.set_fan(1)                    

                    #Heat mode block
                    elif(CurrentState.mode == 1 and celsius != 0 and CurrentState.snooze == False ):                      
                        my_logger.debug("HEAT - temperature setpoint = {0},  measured temp = {1} and toohot is {}".format((CurrentState.tset - 0.5), celsius, CurrentState.toohot))
                        if((CurrentState.tset - 0.5)  > celsius and CurrentState.toohot == False):
                            my_logger.debug("Turning the heater on because sensor says its cold")
                            self.furnace.set_heat(1)                           
                        
                        elif(CurrentState.toohot == True):
                            my_logger.debug("Turning the heater off because some sensor is reading way too high")
                            self.furnace.set_heat(0)
                           
                        elif((CurrentState.tset + 0.5) < celsius and CurrentState.toohot == False):
                            my_logger.debug("Turning the heater off because sensor says its warm enough")
                            self.furnace.set_heat(0)                           
                           
                    #cool mode block       
                    elif(CurrentState.mode == 2 and celsius != 0 and CurrentState.snooze == False ):
                        my_logger.debug("COOL - temperature setpoint = {0},  measured temp = {1} and toocold is {}".format((CurrentState.tset - 0.5), celsius, CurrentState.toocold))
                        if((CurrentState.tset - 0.5) > celsius and CurrentState.toocold == False):                           
                            my_logger.debug("Turning the AC off because sensor says its cold enough")
                            self.furnace.set_cool(0)
                        elif(CurrentState.toocold == True):                 
                            my_logger.debug("Turning the AC off because some sensor is way too cold")
                            self.furnace.set_cool(0)
                        elif((CurrentState.tset + 0.5) < celsius and CurrentState.toocold == False):
                            my_logger.debug("Turning the AC on because sensor says its not cold enough")
                            self.furnace.set_cool(1)
                    else:                        
                        self.furnace.turn_everything_off()
                        my_logger.info("no conditions in gpio block were met so everything is off. celsius = {}".format(celsius))
                except:
                    my_logger.error("Error setting GPIOs AC/Heater/FAN", exc_info=True)
                 
                       

                   
                # End of Furnace and AC logic block.
        
                  
            
            
             
            except KeyboardInterrupt:
                print ("attempting to close threads.")
                serverthread.join()
                TempUpdateThread.cancel()
                serverthread.shutdown()
                serverthread.server_close()
                print ("threads successfully closed")
    

    


class updateTemps(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.current_value = None
        self.running = True #setting the thread running to true
    
    def run(self):
        global Sparams
        global lastlogtime
        # reading local sensors
        while(True):
            try:
                if(Sparams.webiopi == 1):
                    my_logger.debug("reading local sensors")
                    for (key, value) in Sparams.LocalSensors.items():
                        if(value['type'] == "bmp"):
                            try:
                                my_logger.debug("Reading BMP085") 
                                bmpsensor = BMP085.BMP085()
                                time.sleep(0.1)
                                value['temperature'] = bmpsensor.read_temperature()
                                time.sleep(0.1)
                                value['pressure'] = bmpsensor.read_pressure()
                                time.sleep(0.1)   
                                value['read_successful'] = True  
                                value['last_read_time'] = datetime.datetime.utcnow()
                                my_logger.debug("bmp85 read fine")      
                            except:
                                value['read_successful'] = False  
                                my_logger.error("Opening local bmp085 failed. Sensor: {}".format(key), exc_info=True)
        
                        
                        if(value['type'] == "htu" ):
                            try:                       
                                time.sleep(0.1)
                                my_logger.debug("Reading HTU21D")
                                i2c = busio.I2C(board.SCL, board.SDA)
                                my_logger.debug("HTU21D bus acquired")   
                                htusensor = HTU21D(i2c)                            
                                my_logger.debug("HTU21D Init done")
                                time.sleep(0.1)
                                value['humidity'] = htusensor.relative_humidity   # somewhere after this line things are stoping but not throwing an exception.
                                my_logger.debug("HTU21D Read humidity")
                                time.sleep(0.1)
                                value['temperature'] = htusensor.temperature
                                my_logger.debug("HTU21D Read temperature")
                                time.sleep(0.1)                   
                                value['read_successful'] = True
                                value['last_read_time'] = datetime.datetime.utcnow()
                                my_logger.debug("HTU21D read fine")                  
                            except:
                                value['read_successful'] = False                                          
                                my_logger.error("Reading local htu21d failed. Sensor: {}".format(key), exc_info=True)
              
        
            except:
                my_logger.error("Reading local temperature failed for some reason on the outer", exc_info=True)
        
            # reading remote sensors
            if(Sparams.webiopi == 1):
                my_logger.debug("reading remote sensors")
                for (key, value) in Sparams.RemoteSensors.items():
                    value['read_successful'] = False
                    try:
                        HOST, PORT = value['ip'], 5010
                        my_logger.debug("Reading {}".format(key))                
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                            # Connect to server and send data
                            sock.settimeout(5)
                            sock.connect((HOST, PORT))							
                            sock.sendall(bytes("get_temp\n", "utf-8"))    
                            # Receive data from the server and shut down
                            received = str(sock.recv(1024), "utf-8")
                            my_logger.debug("recieved this from remote host {}".format(received))
                            sensordata = json.loads(received)
                            for (return_key, return_value) in sensordata.items():
                                if(return_value != None):
                                    value['temperature'] = return_value['temperature']
                                    value['last_read_time'] = datetime.datetime.utcnow()
                                    value['read_successful'] = True                                   
                                    if ('pressure' in return_value): value['pressure'] = return_value['pressure']
                                    if ('humidity' in return_value): value['humidity'] = return_value['humidity']                                    
                                    my_logger.debug("remote sensor {} read fine".format(key))
                                 
                    except:
                        value['read_successful'] = False
                        my_logger.error("Reading remote temperature failed. Sensor: {}".format(key), exc_info=True)
                        
         
             
            #logging sensor data to mysql
            my_logger.debug("Should we log? datetime.datetime.utcnow() {} - lastlogtime {} > datetime.timedelta(minutes=Tparams.loginterval){}".format(datetime.datetime.utcnow(), lastlogtime, datetime.timedelta(minutes=Tparams.loginterval)))
            if (datetime.datetime.utcnow() - lastlogtime > datetime.timedelta(minutes=Tparams.loginterval)):
                my_logger.info("Doing database logging now".format(key))        
                lastlogtime = datetime.datetime.utcnow()        
                try:
                    for (key, value) in Sparams.LocalSensors.items(): 
                        if(value['read_successful'] == True):
                            logTemplineDB(DBparams, my_logger, key, value['temperature'])
                            if(value['type'] == "bmp" ):                    
                                logPresslineDB(DBparams, my_logger, key, value['pressure'])
                            if(value['type'] == "htu" ):
                                logHumlineDB(DBparams, my_logger, key, value['humidity'])               
                        
                    for (key, value) in Sparams.RemoteSensors.items():
                        if(value['read_successful'] == True): 
                            logTemplineDB(DBparams, my_logger, key, value['temperature'])
                            if(value['type'] == "bmp" ):                    
                                logPresslineDB(DBparams, my_logger, key, value['pressure'])
                            if(value['type'] == "htu" ):
                                logHumlineDB(DBparams, my_logger, key, value['humidity'])  
                        
                except:
                    my_logger.error("Error logging temperatures to MYsql", exc_info=True)   
            time.sleep(10)    
    
    





def ThreadExceptionCatcher(exctype, value, tb):
    my_logger.debug("Type {}, Value {}, Traceback {}".format(exctype, value, tb))



def tail(f, n, offset=0):
    """Reads a n lines from f with an offset of offset lines."""
    avg_line_length = 74
    to_read = n + offset
    while 1:
        try:
            f.seek(-(avg_line_length * to_read), 2)
        except IOError:
            # woops.  apparently file is smaller than what we want
            # to step back, go to the beginning instead
            f.seek(0)
        pos = f.tell()
        lines = f.read().splitlines()
        if len(lines) >= to_read or pos == 0:
            return lines[-to_read:offset and -offset or None]
        avg_line_length *= 1.3




if __name__ == "__main__":
    setup()
    time.sleep(1)
    
    while True: 
        #my_logger.debug("Type {}, Value {}, Traceback {}".format(exctype, value, tb))
        time.sleep(600)
        
        
