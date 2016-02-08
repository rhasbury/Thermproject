import logging
import webiopi
import datetime
import pymysql.cursors
import json
import configparser
import os
#import locale
from webiopi.clients import *
from _ctypes import addressof
from ThermostatParameters import *


GPIO = webiopi.GPIO # Helper for LOW/HIGH values

loginterval = 10  # DB logging interval in minutes
lastlogtime = datetime.datetime.utcnow()
ActiveProgramIndex = 0 
my_logger = logging.getLogger('MyLogger')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
hdlr = logging.FileHandler('/home/pi/thermostat/thermostat.log')
hdlr.setFormatter(formatter)
my_logger.addHandler(hdlr)
my_logger.setLevel(logging.DEBUG)





Tparams = ThermostatParameters()
CurrentState = ProgramDataClass
program = []

# setup function is automatically called at WebIOPi startup
def setup():
    global program
    global CurrentState
    global Tparams

    GPIO.setFunction(Tparams.HEATER, GPIO.OUT)
    GPIO.setFunction(Tparams.FAN, GPIO.OUT)
    GPIO.setFunction(Tparams.AC, GPIO.OUT)
             
       
    loadProgramFromFile()
    CurrentState = program[0]
    Tparams.tempORtemp = CurrentState.TempSetPointHeat
    
    Tparams.heaterstate = 0
    Tparams.acstate = 0
    f = open(Tparams.ThermostatStateFile, 'r') 
    try:
        Tparams.mode = int(f.readline())
    except:
        Tparams.mode = 0
    f.close()

    my_logger.info("Setup Completed")
    #for x in range(0, program.__len__()):
    #    printProram(program[x])


# loop function is repeatedly called by WebIOPi 
def loop():
    global CurrentState
    global Tparams
    global graphfilecount
    global lastlogtime   
    global loginterval

    
        
    if (datetime.datetime.utcnow() - Tparams.tempORtime > datetime.timedelta(minutes=Tparams.tempORlength)):        
        Tparams.tempORactive = False
        
    if (datetime.datetime.utcnow() - Tparams.fanORtime > datetime.timedelta(minutes=Tparams.fanORlength)):        
        Tparams.fanORactive = False
            
    
    try:
        updateProgram()
    except:
        my_logger.debug("updateProgram() excepted", exc_info=True)
        #print("updateProgram() threw exception")
    
    updateTemps()
  

    
    # decide which temp we're using for control
    if(Tparams.RemoteSensors.get(CurrentState.MasterTempSensor) != None):        
        celsius = Tparams.RemoteSensors[CurrentState.MasterTempSensor]['temperature']
    
    elif(Tparams.LocalSensors.get(CurrentState.MasterTempSensor) != None):        
        celsius = Tparams.LocalSensors[CurrentState.MasterTempSensor]['temperature']
    
    else:
        celsius = 0
        my_logger.debug("Failed to determine master sensor. Falling back to any local sensor")
        for (key, value) in Tparams.LocalSensors.items():
            if(value['read_successful'] == True):
                celsius = value['temperature']


#    Override section
    
    if(Tparams.tempORactive):
        Tparams.tset = Tparams.tempORtemp
    elif(Tparams.mode == 2):
        Tparams.tset = CurrentState.TempSetPointCool
    else:
        Tparams.tset = CurrentState.TempSetPointHeat
  
    
    if(Tparams.fanORactive == True):
        Tparams.fanState = Tparams.fanORstate
    else:
        Tparams.fanState = CurrentState.fanon    
    
    
    CurrentState.sensorTemp = celsius
    
    try:
        if(Tparams.mode == 1 and celsius != 0):
            GPIO.digitalWrite(Tparams.AC, GPIO.HIGH)
            if((Tparams.tset - 0.5)  > celsius):
               GPIO.digitalWrite(Tparams.HEATER, GPIO.LOW)
               Tparams.heaterstate = 1
            elif((Tparams.tset + 0.5) < celsius):
               GPIO.digitalWrite(Tparams.HEATER, GPIO.HIGH)
               Tparams.heaterstate = 0
        elif(Tparams.mode == 2 and celsius != 0):
            GPIO.digitalWrite(Tparams.HEATER, GPIO.HIGH)
            if((Tparams.tset - 0.5) > celsius):
               GPIO.digitalWrite(Tparams.AC, GPIO.HIGH)
               Tparams.acstate = 0
            elif((Tparams.tset + 0.5) < celsius):
               GPIO.digitalWrite(Tparams.AC, GPIO.LOW)
               Tparams.acstate = 1
        else:
            GPIO.digitalWrite(Tparams.AC, GPIO.HIGH)
            GPIO.digitalWrite(Tparams.HEATER, GPIO.HIGH)
    except:
        my_logger.debug("Error setting GPIOs AC/Heater", exc_info=True)
    	   
    try:
        if(Tparams.fanState == 1):
            GPIO.digitalWrite(Tparams.FAN, GPIO.LOW)
        elif(Tparams.fanState == 0):
            GPIO.digitalWrite(Tparams.FAN, GPIO.HIGH)
    except:
        my_logger.debug("Error setting GPIOs Fan", exc_info=True)
       

    if (datetime.datetime.utcnow() - lastlogtime > datetime.timedelta(minutes=loginterval)):        
        lastlogtime = datetime.datetime.utcnow()        
        try:
            for (key, value) in Tparams.LocalSensors.items(): 
                logTemplineDB(key, value['temperature'])
                if(value['type'] == "bmp" ):                    
                    logPresslineDB(key, value['pressure'])
                if(value['type'] == "htu" ):
                    logHumlineDB(key, value['humidity'])               
                
            for (key, value) in Tparams.RemoteSensors.items(): 
                logTemplineDB(key, value['temperature'])
                
                
        except:
            my_logger.debug("Error logging temperatures to MYsql", exc_info=True)
      

    webiopi.sleep(10)
  

#def destroy():
    

def updateTemps():
    global Tparams
    
    # reading local sensors
    try:
        if(Tparams.webiopi == 1):
    
            for (key, value) in Tparams.LocalSensors.items():                
                try:
                    tmp = webiopi.deviceInstance(value['webiopi_name'])
                    value['temperature'] = tmp.getCelsius()
                    value['read_successful'] = True           
                                      
                except:
                    value['read_successful'] = False                    
                    my_logger.debug("Reading local temperature failed. Sensor: {}".format(key), exc_info=True)


                if(value['type'] == "bmp" ):
                    try:                       
                        value['pressure'] == tmp.getPascalAtSea()                          
                                          
                    except:
                        value['read_successful'] == False                    
                        my_logger.debug("Reading local pressure failed. Sensor: {}".format(key), exc_info=True)
                
                if(value['type'] == "htu" ):
                    try:                       
                        value['humidity'] == tmp.getHumidity()                     
                                          
                    except:
                        value['read_successful'] == False                    
                        my_logger.debug("Reading local pressure failed. Sensor: {}".format(key), exc_info=True)
      

    except:
        my_logger.debug("Reading local temperature failed for some reason on the outer", exc_info=True)

    # reading remote sensors
    if(Tparams.webiopi == 1):
        for (key, value) in Tparams.RemoteSensors.items():
            try:                
                value['temperature'] = readFromSensor(value['ip'])
                value['read_successful'] = True
            except:            
                my_logger.debug("Reading remote temperature failed. Sensor: [0]".format(key), exc_info=True)
                value['read_successful'] = False

            



def loadProgramFromFile():
    global program
    now = datetime.datetime.now()
    ThermostatProgramFile = Tparams.ProgramsFolder + "{0}.csv".format(now.strftime('%A'))
    f = open(ThermostatProgramFile , 'r')
    del program[:]
    linein = f.readline()
    
    for line in f:        
        parts = line.split(",")      
        #def __init__(self, TimeActive, MasterTempS, TempSetP, TempSetPC, FanOnoff, Day):
        program.append(ProgramDataClass(datetime.datetime.strptime(parts[0], '%H:%M'), parts[1], float(parts[2]), float(parts[3]), int(parts[4]), now.strftime('%A')))   
    
    f.close()
    program.sort(key = lambda x: x.TimeActiveFrom)
    
    
def WriteProgramToFile():
    global program
    #now = datetime.datetime.now()
    #ThermostatProgramFile = "/home/pi/thermostat/python/Programs/{0}.csv".now.strftime('%A')
    now = datetime.datetime.now()
    ThermostatProgramFile = "/home/pi/thermostat/python/Programs/{0}.csv".format(now.strftime('%A'))

    f = open(ThermostatProgramFile, 'w')    
    f.write("# TimeActiveFrom, MasterTempSensor (0=localsensor, 1=?, 2=? ), temperature set point, enable fan\n")
    
    for x in range(0, (program.__len__())):         
#        line = "{0!s},{1!d},{2!f},{3!d}\n".format(datetime.datetime.strftime(program[x].TimeActiveFrom, '%H:%M'), program[x].MasterTempSensor, program[x].TempSetPoint, program[x].fanon )
        #f.write("{0!s},{1!d},{2!f},{3!d}\n".format(datetime.datetime.strftime(program[x].TimeActiveFrom, '%H:%M'), program[x].MasterTempSensor, program[x].TempSetPoint, program[x].fanon ))
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




def logTemplineDB(location, temp):    
    try:
        connection = pymysql.connect(host='localhost', user='monitor', passwd='password', db='temps', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:
            cursor.execute ("INSERT INTO tempdat values(NOW(), NOW(), %s, %s, 'empty')", (location, temp))
        connection.commit()
        connection.close()
    except:
        #print("logTemplineDB() exception thrown")
        my_logger.debug("logTemplineDB() exception thrown", exc_info=True)

def logPresslineDB(location, pressure):    
    try:
        connection = pymysql.connect(host='localhost', user='monitor', passwd='password', db='temps', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:        
            cursor.execute ("INSERT INTO pressdat values(NOW(), %s, %s)", (location, pressure))        
        connection.commit()
        connection.close()
    except:
        #print("logPresslineDB() exception thrown")
        my_logger.debug("logPresslineDB() exception thrown", exc_info=True)

def logHumlineDB(location, humidity):    
    try:
        connection = pymysql.connect(host='localhost', user='monitor', passwd='password', db='temps', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:        
            cursor.execute ("INSERT INTO humdat values(NOW(), %s, %s)", (location, humidity))        
        connection.commit()
        connection.close()
    except:
        #print("logHumlineDB() exception thrown")
        my_logger.debug("logHumlineDB() exception thrown", exc_info=True)


def printProram(prg):
    print(prg.TimeActiveFrom, prg.MasterTempSensor, prg.TempSetPointHeat, prg.fanon)
    
    
def updateProgram():
    global CurrentState
    global program    
    global Tparams
    global ActiveProgramIndex
    now = datetime.datetime.now()
    if(program[0].Day != now.strftime('%A')):
        loadProgramFromFile()
    
    progfound = False
    for x in range((program.__len__()-1), -1, -1):
        for y in range(now.minute, -1, -1):
            if(program[x].TimeActiveFrom.hour == now.hour and program[x].TimeActiveFrom.minute == y):
                CurrentState = program[x]
                ActiveProgramIndex = x
                #printProram(CurrentState)
                progfound = True
                break
        if(progfound):
            break
   

def readFromSensor(address):
    client = PiHttpClient(address)            
    client.setCredentials("webiopi", "raspberry")
    remoteTemp = Temperature(client, "bmp0")         
    return remoteTemp.getCelsius()
   


@webiopi.macro
def getCurrentState():    
    global Tparams
    if(Tparams.tempORactive):            
        Tparams.overrideexp = str(datetime.timedelta(minutes=Tparams.tempORlength) - (datetime.datetime.utcnow() - Tparams.tempORtime))[:7]   
    elif(Tparams.fanORactive):    
        Tparams.overrideexp = str(datetime.timedelta(minutes=Tparams.fanORlength) - (datetime.datetime.utcnow() - Tparams.fanORtime))[:7]        
    else:
        Tparams.overrideexp = "No override"        
    diskstat = os.statvfs(Tparams.ThermostatStateFile)    
    Tparams.hddspace = (diskstat.f_bavail * diskstat.f_frsize) / 1024000   # 
    Tparams.TimeActiveFrom = datetime.datetime.strftime(CurrentState.TimeActiveFrom, '%H:%M')                       # The time this program segment is active from
    Tparams.MasterTempSensor = CurrentState.MasterTempSensor            # The index of the active temp sensor
    Tparams.TempSetPointHeat    = CurrentState.TempSetPointHeat                     # temperature set point for AC
    Tparams.TempSetPointCool    = CurrentState.TempSetPointCool                    # temperature set point for AC       
    Tparams.Day   = CurrentState.Day
        
    #print (Tparams.to_JSON())
    
    return Tparams.to_JSON()
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



@webiopi.macro
def getProgram(index):    
    global program
    ind = int(index) 
    if(ind < 0):
        ind = 0
    if(ind > (program.__len__()-1)):
        ind = (program.__len__()-1) 
       
    return "%s;%d;%f;%d;%d;%d" % (datetime.datetime.strftime(program[ind].TimeActiveFrom, '%H;%M'), program[ind].MasterTempSensor, program[ind].TempSetPointHeat, program[ind].fanon, program.__len__(), ind)
    
@webiopi.macro
def setProgram(index, time, sensor, temp, fanon ):
    global program
    ind = int(index) 
    #for x in range(0, (program.__len__())):
        #printProram(program[x])
    
    if(ind == (program.__len__())):    # new entry
        program.append(ProgramDataClass(datetime.datetime.strptime(time, '%H:%M'), int(sensor), float(temp), int(fanon)))
#        print("added new") 
    else:        
        program[ind].TimeActiveFrom = datetime.datetime.strptime(time, '%H:%M')
        program[ind].MasterTempSensor = int(sensor)
        program[ind].TempSetPointHeat    = float(temp) 
        program[ind].fanon = int(fanon)
   
    program.sort(key = lambda x: x.TimeActiveFrom)
    
    WriteProgramToFile()
    
    



@webiopi.macro
def temp_change(amount, length):
    global CurrentState        
    global Tparams
    global program
    global ActiveProgramIndex
    if(Tparams.tempORactive == False):
        Tparams.tempORtemp = Tparams.tset
 
    Tparams.tempORtemp = Tparams.tempORtemp + (int(amount)* 0.5)
    Tparams.tempORtime = datetime.datetime.utcnow() 
    Tparams.tempORlength = int(length)
    #Tparams.tempORactive = True
    
    if(Tparams.mode == 1):
        program[ActiveProgramIndex].TempSetPointHeat = Tparams.tempORtemp 
    elif(Tparams.mode == 2):
        program[ActiveProgramIndex].TempSetPointCool = Tparams.tempORtemp
    WriteProgramToFile()

@webiopi.macro
def fan_change(length):
    global CurrentState        
    global Tparams
    if(Tparams.fanORactive == False):
        Tparams.fanORstate = CurrentState.fanon 
    Tparams.fanORstate = (Tparams.fanORstate + 1) % 2    
    Tparams.fanORtime = datetime.datetime.utcnow() 
    Tparams.fanORlength = int(length)
    Tparams.fanORactive = True    

@webiopi.macro
def getMode():
    if(Tparams.mode == 0):
        return "OFF"
    elif(Tparams.mode == 1):
        return "HEAT"
    elif(Tparams.mode == 2):
        return "COOL"
    else:
        return "Error"


@webiopi.macro
def setMode():
    global Tparams 
    Tparams.mode = (Tparams.mode + 1) % 3
    f = open(Tparams.ThermostatStateFile, 'w') 
    f.write(str(Tparams.mode))
    f.close()

@webiopi.macro

def clearOverride():
    Tparams.tempORactive = False
    Tparams.fanORactive = False
    my_logger.info("Override cleared")
  



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

    
    

    
