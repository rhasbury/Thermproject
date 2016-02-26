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
import Adafruit_BMP.BMP085 as BMP085

sys.path.append('/home/pi/thermostat/python')

#import locale
from webiopi.clients import *
from _ctypes import addressof
from ThermostatParameters import *
from dblogging import *
from emailwarning import *


HOST, PORT = "localhost", 50007

GPIO = webiopi.GPIO # Helper for LOW/HIGH values
lastlogtime = datetime.datetime.utcnow()
ActiveProgramIndex = 0 
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
    """
    The RequestHandler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):        
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
        elif("change_mode" in self.data.decode("utf-8")):
            setMode()
        elif("fan_change" in self.data.decode("utf-8")):
            fan_change(5)


def setup():
    #global program
    global CurrentState
    #global Tparams
    #global Sparams
    global server
   #global DBparams
    
    GPIO.setFunction(Tparams.HEATER, GPIO.OUT)
    GPIO.setFunction(Tparams.FAN, GPIO.OUT)
    GPIO.setFunction(Tparams.AC, GPIO.OUT)
    
    
    loadProgramFromFile()
    CurrentState = ThermostatState(program[0])
    CurrentState.tempORtemp = CurrentState.CurrentProgram.TempSetPointHeat    
    CurrentState.heaterstate = 0
    CurrentState.acstate = 0
    f = open(Tparams.ThermostatStateFile, 'r') 
    try:
        CurrentState.mode = int(f.readline())
    except:
        CurrentState.mode = 0
    f.close()

        # Create the server, binding to localhost on port 9999
    

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server = socketserver.TCPServer((HOST, PORT), MyTCPHandler)
    serverthread = threading.Thread(target=server.serve_forever)
    serverthread.daemon = True
    serverthread.start()
    my_logger.info("Data sockect listner started")
    
    TempUpdateThread = threading.Thread(target=updateTemps)    
    TempUpdateThread.daemon = True
    TempUpdateThread.start()
    my_logger.info("Sensor update thread started")
    
    # Check and possibly setup database. 
    #print(DBparams.to_JSON())
    CheckDatabase(DBparams, my_logger)
    
    

    my_logger.info("Setup Completed")
    #for x in range(0, program.__len__()):
    #    printProram(program[x])


# loop function is repeatedly called by WebIOPi 
def loop():
    global CurrentState
    #global Tparams
    
    #global Sparams
    #global serverthread
    
    webiopi.sleep(10)
    # Update harddrive space information. 
    diskstat = os.statvfs(Tparams.ThermostatStateFile)    
    CurrentState.hddspace = (diskstat.f_bavail * diskstat.f_frsize) / 1024000 
    
    try:    
        if (datetime.datetime.utcnow() - CurrentState.tempORtime > datetime.timedelta(minutes=CurrentState.tempORlength)):        
            CurrentState.tempORactive = False
            
        if (datetime.datetime.utcnow() - CurrentState.fanORtime > datetime.timedelta(minutes=CurrentState.fanORlength)):        
            CurrentState.fanORactive = False
                
        
        try:
            updateProgram()
        except:
            my_logger.debug("updateProgram() excepted", exc_info=True)
            #print("updateProgram() threw exception")
        
        
        
    
        
        # decide which temp we're using for control
        if(Sparams.RemoteSensors.get(CurrentState.CurrentProgram.MasterTempSensor) != None):        
            celsius = Sparams.RemoteSensors[CurrentState.CurrentProgram.MasterTempSensor]['temperature']
        
        elif(Sparams.LocalSensors.get(CurrentState.CurrentProgram.MasterTempSensor) != None):        
            celsius = Sparams.LocalSensors[CurrentState.CurrentProgram.MasterTempSensor]['temperature']
        
        else:
            celsius = 0
            my_logger.debug("Failed to determine master sensor. Falling back to any local sensor")
            for (key, value) in Sparams.LocalSensors.items():
                if(value['read_successful'] == True):
                    celsius = value['temperature']
    
    
    #    Override section
        
        if(CurrentState.tempORactive):
            CurrentState.tset = CurrentState.tempORtemp
        elif(CurrentState.mode == 2):
            CurrentState.tset = CurrentState.CurrentProgram.TempSetPointCool
        else:
            CurrentState.tset = CurrentState.CurrentProgram.TempSetPointHeat
      
        
        if(CurrentState.fanORactive == True):            
            if(CurrentState.fanState != CurrentState.fanORstate):
                logControlLineDB(DBparams, my_logger, 'fan', CurrentState.fanORstate)
            CurrentState.fanState = CurrentState.fanORstate
        else:
            if(CurrentState.fanState != CurrentState.CurrentProgram.fanon):
                logControlLineDB(DBparams, my_logger, 'fan', CurrentState.CurrentProgram.fanon)
            CurrentState.fanState = CurrentState.CurrentProgram.fanon    
        
        
        CurrentState.sensorTemp = celsius
        
        # email notification checker
        if (email.enabled == True):
            if (celsius < email.lowerlimit or celsius > email.upperlimit):
                if(datetime.datetime.utcnow() - email.lastsend > datetime.timedelta(minutes=email.interval)):
                    my_logger.debug("Temperature exceeeded warning.  {0] < {1} < {2}  Sending email notification".format(email.lowerlimit, celsius, email.upperlimit))
                    try:
                        email.sendNotification("Temperature warning. Measured temperature has reached {0} C on the {1} sensor".format(celsius, CurrentState.CurrentProgram.MasterTempSensor))
                        email.lastsend = datetime.datetime.utcnow()
                    except:
                        my_logger.debug("sending warning email failed", exc_info=True)                      
                
                 
        try:
            if(CurrentState.mode == 1 and celsius != 0):
                GPIO.digitalWrite(Tparams.AC, GPIO.HIGH)
                CurrentState.acstate = 0 
                if((CurrentState.tset - 0.5)  > celsius):
                   GPIO.digitalWrite(Tparams.HEATER, GPIO.LOW)
                   if(CurrentState.heaterstate == 0): 
                       logControlLineDB(DBparams, my_logger, 'heater', 1)
                   CurrentState.heaterstate = 1                       
                elif((CurrentState.tset + 0.5) < celsius):
                   GPIO.digitalWrite(Tparams.HEATER, GPIO.HIGH)
                   if(CurrentState.heaterstate == 1):
                       logControlLineDB(DBparams, my_logger, 'heater', 0)
                   CurrentState.heaterstate = 0
            elif(CurrentState.mode == 2 and celsius != 0):
                GPIO.digitalWrite(Tparams.HEATER, GPIO.HIGH)
                CurrentState.heaterstate = 0
                if((CurrentState.tset - 0.5) > celsius):
                   GPIO.digitalWrite(Tparams.AC, GPIO.HIGH)
                   if(CurrentState.acstate == 1): 
                       logControlLineDB(DBparams, my_logger, 'ac', 0)
                   CurrentState.acstate = 0                   
                elif((CurrentState.tset + 0.5) < celsius):
                   GPIO.digitalWrite(Tparams.AC, GPIO.LOW)
                   if(CurrentState.acstate == 0): 
                       logControlLineDB(DBparams, my_logger, 'ac', 1)
                   CurrentState.acstate = 1
            else:
                GPIO.digitalWrite(Tparams.AC, GPIO.HIGH)
                GPIO.digitalWrite(Tparams.HEATER, GPIO.HIGH)
        except:
            my_logger.debug("Error setting GPIOs AC/Heater", exc_info=True)
        	   
        try:
            if(CurrentState.fanState == 1):
                GPIO.digitalWrite(Tparams.FAN, GPIO.LOW)
                
            elif(CurrentState.fanState == 0):
                GPIO.digitalWrite(Tparams.FAN, GPIO.HIGH)
                
        except:
            my_logger.debug("Error setting GPIOs Fan", exc_info=True)
           
    

          
    
        
    except KeyboardInterrupt:
        print ("attempting to close threads.")
        serverthread.join()
        TempUpdateThread.cancel()
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
                        logTemplineDB(DBparams, my_logger, key, value['temperature'])
                        if(value['type'] == "bmp" ):                    
                            logPresslineDB(DBparams, my_logger, key, value['pressure'])
                        if(value['type'] == "htu" ):
                            logHumlineDB(DBparams, my_logger, key, value['humidity'])               
                        
                    for (key, value) in Sparams.RemoteSensors.items(): 
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
    now = datetime.datetime.now()
    ThermostatProgramFile = Tparams.ProgramsFolder + "{0}.csv".format(now.strftime('%A'))
    f = open(ThermostatProgramFile , 'r')
    del program[:]
    linein = f.readline()
    
    for line in f:        
        parts = line.split(",")        
        program.append(ProgramDataClass(datetime.datetime.strptime(parts[0], '%H:%M'), parts[1], float(parts[2]), float(parts[3]), int(parts[4]), now.strftime('%A')))   
    
    f.close()
    program.sort(key = lambda x: x.TimeActiveFrom)
    
    
def WriteProgramToFile():
    now = datetime.datetime.now()
    ThermostatProgramFile = "/home/pi/thermostat/python/Programs/{0}.csv".format(now.strftime('%A'))

    f = open(ThermostatProgramFile, 'w')    
    f.write("# TimeActiveFrom, MasterTempSensor (0=localsensor, 1=?, 2=? ), temperature set point, enable fan\n")
    
    for x in range(0, (program.__len__())):
        f.write(datetime.datetime.strftime(program[x].TimeActiveFrom, '%H:%M'))
        f.write(",")
        f.write(str(program[x].MasterTempSensor))
        f.write(",")
        f.write(str(program[x].TempSetPointHeat))
        f.write(",")
        f.write(str(program[x].TempSetPointCool))
        f.write(",")
        f.write(str(program[x].fanon))
        f.write("\n")
       
    f.close()




def printProram(prg):
    print(prg.TimeActiveFrom, prg.MasterTempSensor, prg.TempSetPointHeat, prg.fanon)
    
    
def updateProgram():
    global CurrentState    
    global ActiveProgramIndex
    
    now = datetime.datetime.now()
    if(program[0].Day != now.strftime('%A')):
        loadProgramFromFile()
    
    progfound = False
    for x in range((program.__len__()-1), -1, -1):
        for y in range(now.minute, -1, -1):
            if(program[x].TimeActiveFrom.hour == now.hour and program[x].TimeActiveFrom.minute == y):
                CurrentState.CurrentProgram = program[x]
                ActiveProgramIndex = x
                #printProram(CurrentState.CurrentProgram)
                progfound = True
                break
        if(progfound):
            break
   

def readFromSensor(address, name):
    client = PiHttpClient(address)            
    client.setCredentials("webiopi", "raspberry")
    remoteTemp = Temperature(client, name)        
    return remoteTemp.getCelsius()
   
def readHumidityFromSensor(address, name):
    client = PiHttpClient(address)            
    client.setCredentials("webiopi", "raspberry")
    remoteTemp = Temperature(client, name)        
    return remoteTemp.getHumidity()

def readPressureFromSensor(address, name):
    client = PiHttpClient(address)            
    client.setCredentials("webiopi", "raspberry")
    remoteTemp = Temperature(client, name)        
    return remoteTemp.getPascalAtSea()




# @webiopi.macro
# def getCurrentState():    
#     global CurrentState
#     if(CurrentState.tempORactive):            
#         CurrentState.overrideexp = str(datetime.timedelta(minutes=CurrentState.tempORlength) - (datetime.datetime.utcnow() - CurrentState.tempORtime))[:7]   
#     elif(CurrentState.fanORactive):    
#         CurrentState.overrideexp = str(datetime.timedelta(minutes=CurrentState.fanORlength) - (datetime.datetime.utcnow() - CurrentState.fanORtime))[:7]        
#     else:
#         CurrentState.overrideexp = "No override"        
#     diskstat = os.statvfs(Tparams.ThermostatStateFile)    
#     CurrentState.hddspace = (diskstat.f_bavail * diskstat.f_frsize) / 1024000   # 
#         
#     #print (Tparams.to_JSON())
#     
#     return CurrentState.to_JSON()
#     return "%d;%d;%s;%s;%d;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s" % (CurrentState.TimeActiveFrom.hour, 
#                                         CurrentState.TimeActiveFrom.minute, 
#                                         CurrentState.MasterTempSensor, 
#                                         str(Tparams.tset)[:6], 
#                                         Tparams.fanState, 
#                                         overrideexp, 
#                                         str(Tparams.tempORtemp)[:6], 
#                                         str(CurrentState.sensorTemp)[:6],
#                                         str(25)[:6],
#                                         str(30)[:6],
#                                         str(35)[:6],
#                                         str(40)[:6],
#                                         str(45)[:6],
#                                         str(50)[:6],
#                                         str(55)) 



# @webiopi.macro
# def getProgram(index):    
#     #global program
#     ind = int(index) 
#     if(ind < 0):
#         ind = 0
#     if(ind > (program.__len__()-1)):
#         ind = (program.__len__()-1) 
#        
#     return "%s;%s;%f;%d;%d;%d" % (datetime.datetime.strftime(program[ind].TimeActiveFrom, '%H;%M'), program[ind].MasterTempSensor, program[ind].TempSetPointHeat, program[ind].fanon, program.__len__(), ind)
#     
# @webiopi.macro
# def setProgram(index, time, sensor, temp, fanon ):
#     global program
#     ind = int(index) 
#     #for x in range(0, (program.__len__())):
#         #printProram(program[x])
#     
#     if(ind == (program.__len__())):    # new entry
#         program.append(ProgramDataClass(datetime.datetime.strptime(time, '%H:%M'), int(sensor), float(temp), int(fanon)))
# #        print("added new") 
#     else:        
#         program[ind].TimeActiveFrom = datetime.datetime.strptime(time, '%H:%M')
#         program[ind].MasterTempSensor = int(sensor)
#         program[ind].TempSetPointHeat    = float(temp) 
#         program[ind].fanon = int(fanon)
#    
#     program.sort(key = lambda x: x.TimeActiveFrom)
#     
#     WriteProgramToFile()
#     
    



#@webiopi.macro
def temp_change(amount, length):
    global CurrentState        
    global Tparams
    global program
    ActiveProgramIndex
    #if(CurrentState.tempORactive == False):
    #    CurrentState.tempORtemp = CurrentState.tset
 
    #CurrentState.tempORtemp = CurrentState.tempORtemp + (int(amount)* 0.5)
    #CurrentState.tempORtime = datetime.datetime.utcnow()
    #CurrentState.tempORlength = int(length)
    #CurrentState.tempORactive = True
     
    if(CurrentState.mode == 1):
        program[ActiveProgramIndex].TempSetPointHeat = program[ActiveProgramIndex].TempSetPointHeat + (int(amount)* 0.5) 
        CurrentState.tset = CurrentState.CurrentProgram.TempSetPointHeat
    elif(CurrentState.mode == 2):
        program[ActiveProgramIndex].TempSetPointCool = program[ActiveProgramIndex].TempSetPointCool + (int(amount)* 0.5)
        CurrentState.tset = CurrentState.CurrentProgram.TempSetPointCool
    
    WriteProgramToFile()
    


#@webiopi.macro
def fan_change(length):
    global CurrentState        
    global Tparams
    if(CurrentState.fanORactive == False):
        CurrentState.fanORstate = CurrentState.CurrentProgram.fanon 
    CurrentState.fanORstate = (CurrentState.fanORstate + 1) % 2    
    CurrentState.fanORtime = datetime.datetime.utcnow()
    CurrentState.fanORlength = int(length)
    CurrentState.fanORactive = True    

#@webiopi.macro
#def getMode():
#    if(CurrentState.mode == 0):
#        return "OFF"
#    elif(CurrentState.mode == 1):
#        return "HEAT"
#    elif(CurrentState.mode == 2):
#        return "COOL"
 #   else:
 #       return "Error"





#@webiopi.macro
def setMode():    
    global CurrentState
    CurrentState.mode = (CurrentState.mode + 1) % 3
    f = open(Tparams.ThermostatStateFile, 'w') 
    f.write(str(CurrentState.mode))
    f.close()

#@webiopi.macro

#def clearOverride():
#    CurrentState.tempORactive = False
#    CurrentState.fanORactive = False
#    my_logger.info("Override cleared")
  



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
    
