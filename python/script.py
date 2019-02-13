import logging
import webiopi
import datetime
import time
import json
import configparser
import os
import socketserver
import threading
import sys
#import Adafruit_BMP.BMP085 as BMP085
from http.cookiejar import DAYS
from setuptools.command.build_ext import if_dl

sys.path.append('/home/pi/thermostat/python')

#import locale
from webiopi.clients import *
from _ctypes import addressof
from ThermostatParameters import *
from dblogging import *
from emailwarning import *

# Connection information for pulling operational info (sensor readings, equipment state, etc) 
HOST, PORT = "localhost", 50007


GPIO = webiopi.GPIO # Helper for LOW/HIGH values
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
email = emailNotifier()

serverthread = None
TempUpdateThread = None

# setup function is automatically called at WebIOPi startup

class MyTCPHandler(socketserver.BaseRequestHandler):
    
    #def obj_dict(obj):
    #    return obj.__dict__

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
            temp_change(1, 30)
        elif("temp_down" in self.data.decode("utf-8")):
            temp_change(-1, 30)            
        elif("change_mode_off" in self.data.decode("utf-8")):                        
            setMode(0)
        elif("change_mode_heat" in self.data.decode("utf-8")):
            setMode(1)
        elif("change_mode_cool" in self.data.decode("utf-8")):
            setMode(2)
        elif("fan_change" in self.data.decode("utf-8")):
            fan_change(5)
        elif("get_program_all" in self.data.decode("utf-8")):
            json_string = json.dumps(program)
            self.request.sendall(bytes(json_string, 'UTF-8'))
        elif("get_program_active" in self.data.decode("utf-8")):
            json_string = json.dumps(ActiveProgram)
            self.request.sendall(bytes(json_string, 'UTF-8'))



def setup():
    global CurrentState
    global server

    
    GPIO.setFunction(Tparams.HEATER, GPIO.OUT)
    GPIO.setFunction(Tparams.FAN, GPIO.OUT)
    GPIO.setFunction(Tparams.AC, GPIO.OUT)
    
    GPIO.digitalWrite(Tparams.HEATER, GPIO.HIGH)
    GPIO.digitalWrite(Tparams.FAN, GPIO.HIGH)
    GPIO.digitalWrite(Tparams.AC, GPIO.HIGH)

    
    loadProgramFromFile()
    updateProgram()
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

    #f = open(Tparams.ThermostatTempFile, 'r') 

    #f.close()


    # Create the data server and assigning the request handler            
    server = socketserver.TCPServer((HOST, PORT), MyTCPHandler)
    serverthread = threading.Thread(target=server.serve_forever)
    serverthread.daemon = True
    serverthread.start()
    my_logger.info("Data sockect listner started")
    
    
    # Create the temperature sensor reading thread
    TempUpdateThread = threading.Thread(target=updateTemps)    
    TempUpdateThread.daemon = True
    TempUpdateThread.start()
    my_logger.info("Sensor update thread started")
    
    # Check and possibly setup database to allow logging of data    
    CheckDatabase(DBparams, my_logger)
    
    
    # All done setup tasks
    my_logger.info("Setup Completed")    


# loop function is repeatedly called by WebIOPi 
def loop():
    global CurrentState
    global program
    global ActiveProgram
    global ActiveProgramID

    
    webiopi.sleep(10)
    # Update harddrive space information. 
    diskstat = os.statvfs(Tparams.ThermostatStateFile)    
    CurrentState.hddspace = (diskstat.f_bavail * diskstat.f_frsize) / 1024000 

    
    try:    

        # Check the status of the temperature override and disable if it's expired
        if (datetime.datetime.utcnow() - CurrentState.tempORtime > datetime.timedelta(minutes=CurrentState.tempORlength)):        
            CurrentState.tempORactive = False
        
        # Check the status of the fan override and disable if it's expired
        if (datetime.datetime.utcnow() - CurrentState.fanORtime > datetime.timedelta(minutes=CurrentState.fanORlength)):        
            CurrentState.fanORactive = False
                
        
        try:
            # Check to see if we've changed program sections. 
            updateProgram()
        except:
            my_logger.debug("updateProgram() excepted", exc_info=True)

    
        
        # decide which temp we're using for control and test it, allowing for failures             
        try:
            SensName = ActiveProgram['TempSensor'] # added this to make the lines below more readable
            if(Sparams.RemoteSensors.get(SensName) != None):        
                if(Sparams.RemoteSensors[SensName]['read_successful'] == False):
                    raise ValueError('Remote sensor reading is untrustworthy')            
                celsius = Sparams.RemoteSensors[SensName]['temperature']
                
            elif(Sparams.LocalSensors.get(SensName) != None):        
                if(Sparams.LocalSensors[SensName]['read_successful'] == False):
                    raise ValueError('Local sensor reading is untrustworthy')            
                celsius = Sparams.LocalSensors[SensName]['temperature']
    
            else:
                raise ValueError('could not determine master sesnsor')           
        
        except ValueError:        
            celsius = 0
            my_logger.debug("Problem in sensor selection", exc_info=True)
            for (key, value) in Sparams.LocalSensors.items():
                if(value['read_successful'] == True and value['location'] == 'indoor'):
                    my_logger.debug("Falling back to {0} sensor for temp targeting at temp {1}".format(key, value['temperature']))
                    celsius = value['temperature']
                    break
     


        if(CurrentState.mode == 2):
            CurrentState.tset = ActiveProgram['TempSetPointCool']
        else:
            CurrentState.tset = ActiveProgram['TempSetPointHeat']

        
      
        # Check for fan override and apply
        if(CurrentState.fanORactive == True):            
            if(CurrentState.fanState != CurrentState.fanORstate):
                runningtime = datetime.datetime.utcnow() - CurrentState.fanlastchange 
                CurrentState.fanlastchange = datetime.datetime.utcnow()
                logControlLineDB(DBparams, my_logger, 'fan', CurrentState.fanORstate, runningtime.seconds)
            CurrentState.fanState = CurrentState.fanORstate
        else:
            if(CurrentState.fanState != ActiveProgram['EnableFan']):
                runningtime = datetime.datetime.utcnow() - CurrentState.fanlastchange 
                CurrentState.fanlastchange = datetime.datetime.utcnow()
                logControlLineDB(DBparams, my_logger, 'fan', ActiveProgram['EnableFan'], runningtime.seconds)
            CurrentState.fanState = ActiveProgram['EnableFan']   

            
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

  
        
        
        # email notification checker
        if (email.enabled == 1):            
            if (celsius < email.lowerlimit or celsius > email.upperlimit):
                if(datetime.datetime.utcnow() - email.lastsend > datetime.timedelta(minutes=email.interval)):
                    my_logger.debug("Temperature exceeded warning.  {0} < {1} < {2}  Sending email notification".format(email.lowerlimit, celsius, email.upperlimit))
                    try:
                        email.sendNotification("Temperature warning. Measured temperature has reached {0} C on the {1} sensor".format(celsius, SensName))
                        email.lastsend = datetime.datetime.utcnow()
                    except:
                        my_logger.debug("sending warning email failed", exc_info=True)                      
                
        
        
        # Furnace and AC control logic starts here
        # This should be the only block in which the heater, fan and AC gpios are touched.        
        try:
            if(CurrentState.mode == 1 and celsius != 0):
                GPIO.digitalWrite(Tparams.AC, GPIO.HIGH)
                CurrentState.acstate = 0 
                if((CurrentState.tset - 0.5)  > celsius and CurrentState.toohot == False):
                   CurrentState.fanState = 0
                   GPIO.digitalWrite(Tparams.HEATER, GPIO.LOW)                               
                   if(CurrentState.heaterstate == 0): 
                       runningtime = datetime.datetime.utcnow() - CurrentState.heatlastchange 
                       CurrentState.heatlastchange = datetime.datetime.utcnow()
                       logControlLineDB(DBparams, my_logger, 'heater', 1, runningtime.seconds)                       
                   CurrentState.heaterstate = 1
                   my_logger.info("HEAT - {0} > {1} and toohot is false".format((CurrentState.tset - 0.5), celsius))
                elif(CurrentState.toohot == True):
                   GPIO.digitalWrite(Tparams.HEATER, GPIO.HIGH)
                   CurrentState.fanState = 1
                   if(CurrentState.heaterstate == 0):
                       runningtime = datetime.datetime.utcnow() - CurrentState.heatlastchange 
                       CurrentState.heatlastchange = datetime.datetime.utcnow()
                       logControlLineDB(DBparams, my_logger, 'heater', 1, runningtime.seconds)
                   CurrentState.heaterstate = 1
                   my_logger.info("HEAT - {0} > {1} and toohot is true".format((CurrentState.tset - 0.5), celsius))
                elif((CurrentState.tset + 0.5) < celsius and CurrentState.toohot == False):
                   GPIO.digitalWrite(Tparams.HEATER, GPIO.HIGH)
                   CurrentState.fanState = 0
                   if(CurrentState.heaterstate == 1):
                       runningtime = datetime.datetime.utcnow() - CurrentState.heatlastchange 
                       CurrentState.heatlastchange = datetime.datetime.utcnow()
                       logControlLineDB(DBparams, my_logger, 'heater', 0, runningtime.seconds)
                   CurrentState.heaterstate = 0
                   my_logger.info("HEAT - {0} < {1} and toohot is false".format((CurrentState.tset - 0.5), celsius))
            elif(CurrentState.mode == 2 and celsius != 0 ):
                GPIO.digitalWrite(Tparams.HEATER, GPIO.HIGH)
                CurrentState.heaterstate = 0
                if((CurrentState.tset - 0.5) > celsius and CurrentState.toocold == False):
                   CurrentState.fanState = 0
                   GPIO.digitalWrite(Tparams.AC, GPIO.HIGH)
                   if(CurrentState.acstate == 1): 
                       runningtime = datetime.datetime.utcnow() - CurrentState.coollastchange 
                       CurrentState.coollastchange = datetime.datetime.utcnow()
                       logControlLineDB(DBparams, my_logger, 'ac', 0, runningtime.seconds)
                   CurrentState.acstate = 0                   
                elif(CurrentState.toocold == True):                 
                   GPIO.digitalWrite(Tparams.AC, GPIO.HIGH)
                   CurrentState.fanState = 1
                   if(CurrentState.acstate == 0): 
                       runningtime = datetime.datetime.utcnow() - CurrentState.coollastchange 
                       CurrentState.coollastchange = datetime.datetime.utcnow()
                       logControlLineDB(DBparams, my_logger, 'ac', 1, runningtime.seconds)
                   CurrentState.acstate = 1
                elif((CurrentState.tset + 0.5) < celsius and CurrentState.toocold == False):
                   CurrentState.fanState = 0
                   GPIO.digitalWrite(Tparams.AC, GPIO.LOW)
                   if(CurrentState.acstate == 0): 
                       runningtime = datetime.datetime.utcnow() - CurrentState.coollastchange 
                       CurrentState.coollastchange = datetime.datetime.utcnow()
                       logControlLineDB(DBparams, my_logger, 'ac', 1, runningtime.seconds)
                   CurrentState.acstate = 1
            else:
                GPIO.digitalWrite(Tparams.AC, GPIO.HIGH)
                GPIO.digitalWrite(Tparams.HEATER, GPIO.HIGH)
                GPIO.digitalWrite(Tparams.FAN, GPIO.HIGH)
        except:
            my_logger.debug("Error setting GPIOs AC/Heater/FAN", exc_info=True)
         
               
        try:
            if(CurrentState.fanState == 1):
                GPIO.digitalWrite(Tparams.FAN, GPIO.LOW)
                
            elif(CurrentState.fanState == 0):
                GPIO.digitalWrite(Tparams.FAN, GPIO.HIGH)
                
        except:
            my_logger.debug("Error setting GPIOs Fan", exc_info=True)
           
        # End of Furnace and AC logic block.

          
    
        
    except KeyboardInterrupt:
        print ("attempting to close threads.")
        serverthread.join()
        TempUpdateThread.cancel()
        serverthread.shutdown()
        serverthread.server_close()
        print ("threads successfully closed")

#def destroy():
    

def updateTemps():    
    global Sparams
    global lastlogtime
    # reading local sensors
    while(True):
        try:
            if(Sparams.webiopi == 1):
        
                for (key, value) in Sparams.LocalSensors.items():
                    try:                    
                        tmp = webiopi.deviceInstance(value['webiopi_name'])
                    except:
                        my_logger.debug("Opening local temperature failed. Sensor: {}".format(key), exc_info=True)
                                    
                    try:                    
                        value['temperature'] = tmp.getCelsius()
                        value['read_successful'] = True           
                                          
                    except:
                        value['read_successful'] = False                    
                        my_logger.debug("Reading local temperature failed. Sensor: {}".format(key), exc_info=True)
    
                    if(value['type'] == "bmp" ):
                        try:                                               
                            value['pressure'] = tmp.getPascalAtSea()                          
                                              
                        except:
                            value['read_successful'] == False                    
                            my_logger.debug("Reading local pressure failed. Sensor: {}".format(key), exc_info=True)
                    
                    if(value['type'] == "htu" ):
                        try:                       
                            value['humidity'] = tmp.getHumidity()                     
                                              
                        except:
                            value['read_successful'] == False                    
                            my_logger.debug("Reading local pressure failed. Sensor: {}".format(key), exc_info=True)
          
    
        except:
            my_logger.debug("Reading local temperature failed for some reason on the outer", exc_info=True)
    
        # reading remote sensors
        if(Sparams.webiopi == 1):
            for (key, value) in Sparams.RemoteSensors.items():
                try:                
                    value['temperature'] = readFromSensor(value['ip'], value['webiopi_name'])
                    value['read_successful'] = True                    
                except:            
                    my_logger.debug("Reading remote temperature failed. Sensor: {}".format(key), exc_info=True)
                    value['read_successful'] = False
    
                if(value['type'] == "bmp" ):
                    try:                       
                        value['pressure'] = readPressureFromSensor(value['ip'], value['webiopi_name'])
                        value['read_successful'] = True        
                    except:
                        value['read_successful'] = False                    
                        my_logger.debug("Reading remote pressure failed. Sensor: {}".format(key), exc_info=True)
                
                
                if(value['type'] == "htu" ):
                    try:                       
                        value['humidity'] =  readHumidityFromSensor(value['ip'], value['webiopi_name'])                
                        value['read_successful'] = True                    
                                          
                    except:
                        value['read_successful'] = False                    
                        my_logger.debug("Reading remote humidity failed. Sensor: {}".format(key), exc_info=True)
        
        # logging sensor data to mysql
        if (datetime.datetime.utcnow() - lastlogtime > datetime.timedelta(minutes=Tparams.loginterval)):        
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
                    my_logger.debug("Error logging temperatures to MYsql", exc_info=True)   
        time.sleep(4)    



def loadProgramFromFile():
    global program    
    try:
        with open(Tparams.ProgramsFile) as json_data:
            program = json.load(json_data)

    except:
        program = 0
    

    
    
def WriteProgramToFile():
    global program
    with open(Tparams.ProgramsFile, 'w') as outfile:
        json.dump(program, outfile, indent=2)


    
    
def updateProgram():
    global ActiveProgram
    global ActiveProgramID
    global program
    global LastProgram
    global LastProgramID
           
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
        ActiveProgram = json.loads('{ "start" : "00:00" , "end" : "00:00", "TempSensor" : "Living Room", "TempSetPointHeat" :21, "TempSetPointCool" : 23, "EnableFan" : 0}')
        ActiveProgramID = "failed"
    
    #print(ActiveProgram)
    #print(ActiveProgramID)
   

def readFromSensor(address, name):
    client = PiHttpClient(address)            
    client.setCredentials("webiopi", "raspberry")
    remoteTemp = Temperature(client, name)        
    return remoteTemp.getCelsius()
   
def readHumidityFromSensor(address, name):
    client = PiHttpClient(address)            
    client.setCredentials("webiopi", "raspberry")
    remoteTemp = Humidity(client, name)        
    return remoteTemp.getHumidity()

def readPressureFromSensor(address, name):
    client = PiHttpClient(address)            
    client.setCredentials("webiopi", "raspberry")
    remoteTemp = Pressure(client, name)        
    return remoteTemp.getPascalAtSea()



#@webiopi.macro
def temp_change(amount, length):
    global CurrentState        
    global Tparams
    global program    
    global ActiveProgram
    global ActiveProgramID
    #if(CurrentState.tempORactive == False):
    #    CurrentState.tempORtemp = CurrentState.tset
 
    #CurrentState.tempORtemp = CurrentState.tempORtemp + (int(amount)* 0.5)
    #CurrentState.tempORtime = datetime.datetime.utcnow()
    #CurrentState.tempORlength = int(length)
    #CurrentState.tempORactive = True
     
    if(CurrentState.mode == 2):
        ActiveProgram["TempSetPointCool"] = ActiveProgram["TempSetPointCool"] + (int(amount)* 0.5) 
    else:
        ActiveProgram["TempSetPointHeat"] = ActiveProgram["TempSetPointHeat"] + (int(amount)* 0.5)     
     

    WriteProgramToFile()
    #updateProgram()
    

#@webiopi.macro
def fan_change(length):
    global CurrentState        
    global Tparams
    global program
    if(CurrentState.fanORactive == False):
        CurrentState.fanORstate = program['EnableFan'] 
    CurrentState.fanORstate = (CurrentState.fanORstate + 1) % 2    
    CurrentState.fanORtime = datetime.datetime.utcnow()
    CurrentState.fanORlength = int(length)
    CurrentState.fanORactive = True    


#@webiopi.macro
def setMode(mode):    
    global CurrentState
    #CurrentState.mode = (CurrentState.mode + 1) % 3
    if(0 <= mode <= 2):
        CurrentState.mode = mode    
    f = open(Tparams.ThermostatStateFile, 'w') 
    f.write(str(CurrentState.mode))
    f.close()




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
    
