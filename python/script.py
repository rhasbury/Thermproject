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


#ThermostatProgramFile = '/home/pi/thermostat/python/ThermProgram.csv'
#ThermostatStateFile = '/home/pi/thermostat/python/state.txt'
#ThermostatLogFile = '/home/pi/thermostat/python/thermlog.txt'

GPIO = webiopi.GPIO # Helper for LOW/HIGH values
#HEATER = 17 
#FAN = 27
#AC = 22

#LocalTemp = 0
#RemTemp1 = 0 
#RemTemp2 = 0  
 
#sensorlookup = ["Living Room", "Bedroom", "Basement", "Outside" ]
loginterval = 10  # DB logging interval in minutes
lastlogtime = 0
ActiveProgramIndex = 0 
my_logger = logging.getLogger('MyLogger')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
hdlr = logging.FileHandler('/home/pi/thermostat/thermostat.log')
hdlr.setFormatter(formatter)
my_logger.addHandler(hdlr)
my_logger.setLevel(logging.DEBUG)


class ThermostatParameters:
    def __init__(self):
            config = configparser.RawConfigParser()
            config.read('/home/pi/.thermostat/thermostat.conf')
            settings = config['main']
            self.HEATER = int(settings['HEATER'])
            self.FAN = int(settings['FAN'])
            self.AC = int(settings['AC'])
            self.ThermostatStateFile = settings['ThermostatStateFile']
            self.ThermostatLogFile = settings['ThermostatLogFile']
            self.ProgramsFolder = settings['ProgramsFolder']
            self.RemoteSensorAddress1 = settings['RemoteSensorAddress1']
            self.RemoteSensorAddress2 = settings['RemoteSensorAddress2']
            self.sensorlookup = settings['sensorlookup'].split(",")
                        
    tempORtime = datetime.datetime.now()    
    tempORactive = False
    tempORlength = 1
    tempORtemp = 20
    fanORtime = datetime.datetime.now()
    fanORactive = 0
    fanORlength = 1
    fanORstate = 0
    fanState = 0
    mode = 1 # 1 = heat, 2 = cool, 0 = off
    LocalTemp = 0
    LocalTemp2 = 0
    LocalHum = 0
    localPressure = 0  
    RemTemp1 = 0
    RemTemp2 = 0    
    tset = 0

class ProgramDataClass:     
    def __init__(self, TimeActive, MasterTempS, TempSetP, TempSetPC, FanOnoff, Day):
        self.TimeActiveFrom = TimeActive         # The time this program segment is active from
        self.MasterTempSensor = MasterTempS                            # The index of the active temp sensor
        self.TempSetPointHeat    = TempSetP
        self.TempSetPointCool    = TempSetPC                            # temperature set point
        self.fanon   = FanOnoff                                 # is the fan on or off
        self.sensorTemp   = 0
        self.Day   = Day               


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
    #global LocalTemp
    #global RemTemp1
    #global RemTemp2 
    heaterstate = 0
    acstate = 0
    
    
    diskstat = os.statvfs(Tparams.ThermostatStateFile)
    spacefree = (diskstat.f_bavail * diskstat.f_frsize) / 1024000   # 
    
    if (datetime.datetime.utcnow() - Tparams.tempORtime > datetime.timedelta(minutes=Tparams.tempORlength)):        
        Tparams.tempORactive = False
        
        
    if (datetime.datetime.utcnow() - Tparams.fanORtime > datetime.timedelta(minutes=Tparams.fanORlength)):        
        Tparams.fanORactive = 0
            
    try:
        updateProgram()
    except:
        my_logger.debug("updateProgram() excepted", exc_info=True)
        #print("updateProgram() threw exception")

    
    try:
        tmp = webiopi.deviceInstance("bmp")
        tmp2 = webiopi.deviceInstance("temp0")
    # Read local temperature    
        Tparams.LocalTemp = tmp.getCelsius()
        Tparams.LocalTemp2 = tmp2.getCelsius()
        Tparams.localPressure = tmp.getPascalAtSea()
        Tparams.LocalHum = tmp2.getHumidity()
    # Try to read remote temp and if fails use local temp instead.
    except:
        my_logger.debug("Reading local temperature failed", exc_info=True)
        #print("Reading local temperature failed")
        Tparams.LocalTemp = 0
        Tparams.LocalTemp2 = 0
          
    
    try:
        #Tparams.RemTemp1 = readFromSensor("192.168.1.117")
        Tparams.RemTemp1 = readFromSensor(Tparams.RemoteSensorAddress1)
    except:            
        my_logger.debug("Reading remote1 temperature failed", exc_info=True)
        Tparams.RemTemp1 = Tparams.LocalTemp
        
# Try to read remote temp and if fails use local temp instead. 
    try:
        #Tparams.RemTemp2 = readFromSensor("192.168.1.146")
        Tparams.RemTemp2 = readFromSensor(Tparams.RemoteSensorAddress2)          
    except:            
        my_logger.debug("Reading remote2 temperature", exc_info=True)
        Tparams.RemTemp2 = Tparams.LocalTemp
    
# decide which temp we're using for control
    if(CurrentState.MasterTempSensor == 1):
        celsius = Tparams.RemTemp1
    elif(CurrentState.MasterTempSensor == 2):
        celsius = Tparams.RemTemp2        
    else:
        celsius = Tparams.LocalTemp
        
#    Override section
    
    if(Tparams.tempORactive):
        Tparams.tset = Tparams.tempORtemp
    elif(Tparams.mode == 2):
        Tparams.tset = CurrentState.TempSetPointCool
    else:
        Tparams.tset = CurrentState.TempSetPointHeat
  
    
    if(Tparams.fanORactive == 1):
        Tparams.fanState = Tparams.fanORstate
    else:
        Tparams.fanState = CurrentState.fanon    
    
    
    CurrentState.sensorTemp = celsius
    try:
        if(Tparams.mode == 1 and celsius != 0):
            GPIO.digitalWrite(Tparams.AC, GPIO.HIGH)
            if((Tparams.tset - 0.5)  > celsius):
               GPIO.digitalWrite(Tparams.HEATER, GPIO.LOW)
               heaterstate = 1
            elif((Tparams.tset + 0.5) < celsius):
               GPIO.digitalWrite(Tparams.HEATER, GPIO.HIGH)
               heaterstate = 0
        elif(Tparams.mode == 2 and celsius != 0):
            GPIO.digitalWrite(Tparams.HEATER, GPIO.HIGH)
            if((Tparams.tset - 0.5) > celsius):
               GPIO.digitalWrite(Tparams.AC, GPIO.HIGH)
               acstate = 0
            elif((Tparams.tset + 0.5) < celsius):
               GPIO.digitalWrite(Tparams.AC, GPIO.LOW)
               acstate = 1
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
            logTemplineDB("Living Room", Tparams.LocalTemp)
            logTemplineDB("Outside", Tparams.LocalTemp2)
            logTemplineDB("Basement", Tparams.RemTemp2)
            logTemplineDB("Bedroom", Tparams.RemTemp1)
            logPresslineDB("Living Room", Tparams.localPressure)
            logHumlineDB("Outside", Tparams.LocalHum)       
        except:
            my_logger.debug("Error logging temperatures to MYsql", exc_info=True)
        
    #logline("{0!s},{1!s},{2!s},{3!s},{4!s}, {5!s}".format(LocalTemp, RemTemp1, RemTemp2, CurrentState.fanon, heaterstate, localPressure))
    #logTemplineDBNew(LocalTemp, RemTemp1, RemTemp2, localPressure)    

      
    graphfilecount = 0
    webiopi.sleep(10)
  

#def destroy():
    

def loadProgramFromFile():
    global program
    now = datetime.datetime.now()
    ThermostatProgramFile = Tparams.ProgramsFolder + "{0}.csv".format(now.strftime('%A'))
    f = open(ThermostatProgramFile , 'r')
    del program[:]
    linein = f.readline()
    
    for line in f:        
        parts = line.split(",")      
        program.append(ProgramDataClass(datetime.datetime.strptime(parts[0], '%H:%M'),int(parts[1]), float(parts[2]), float(parts[3]), int(parts[4]), now.strftime('%A')))   
    
    f.close()
    program.sort(key = lambda x: x.TimeActiveFrom)
    
    
def WriteProgramToFile():
    global program
    now = datetime.datetime.now()
    ThermostatProgramFile = "/home/pi/thermostat/python/Programs/{0}.csv".now.strftime('%A')
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


def logline(linetolog):
    f = open(Tparams.ThermostatLogFile , 'a')
    now = datetime.datetime.now()
    send = "{0},{1};\n".format(now.strftime('%a %b %d %Y %X'), linetolog)
    #print(locale.getlocale())
    f.write(send)
    f.close



#def logTemplineDBNew(temp1, temp2, temp3, temp4):    
#    connection = pymysql.connect(host='localhost', user='monitor', passwd='password', db='temps', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
#    with connection.cursor() as cursor:
#        cursor.execute ("INSERT INTO ltempdat values(NOW(), %s, %s, %s, %s, 'empty')", (temp1, temp2, temp3, temp4))
#    connection.commit()
#    connection.close()

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
            cursor.execute ("INSERT INTO pressdat values(NOW(), NOW(), %s, %s)", (location, pressure))        
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
    remoteTemp = Temperature(client, "temp0")         
    return remoteTemp.getCelsius()
   

@webiopi.macro
def getTempHistory():    
    return temphistory

@webiopi.macro
def getCurrentState():    
    if(Tparams.tempORactive):            
        overrideexp = str(datetime.timedelta(minutes=Tparams.tempORlength) - (datetime.datetime.utcnow() - Tparams.tempORtime))[:7]   
    elif(Tparams.fanORactive):    
        overrideexp = str(datetime.timedelta(minutes=Tparams.fanORlength) - (datetime.datetime.utcnow() - Tparams.fanORtime))[:7]        
    else:
        overrideexp = "No override"        
    return "%d;%d;%s;%s;%d;%s;%s;%s;%s;%s;%s;%s;%s;%s" % (CurrentState.TimeActiveFrom.hour, 
                                        CurrentState.TimeActiveFrom.minute, 
                                        Tparams.sensorlookup[CurrentState.MasterTempSensor], 
                                        str(Tparams.tset)[:6], 
                                        Tparams.fanState, 
                                        overrideexp, 
                                        str(Tparams.tempORtemp)[:6], 
                                        str(CurrentState.sensorTemp)[:6],
                                        str(Tparams.LocalTemp)[:6],
                                        str(Tparams.RemTemp1)[:6],
                                        str(Tparams.RemTemp2)[:6],
                                        str(Tparams.LocalTemp2)[:6],
                                        str(Tparams.LocalHum)[:6],
                                        str(Tparams.localPressure)[:6]) 



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
    if(Tparams.tempORactive == False):
        Tparams.tempORtemp = Tparams.tset
 
    Tparams.tempORtemp = Tparams.tempORtemp + (int(amount)* 0.5)
    Tparams.tempORtime = datetime.datetime.utcnow() 
    Tparams.tempORlength = int(length)
    Tparams.tempORactive = True
    if(Tparams.mode == 1):
        program[ind].TempSetPointHeat = Tparams.tempORtemp 
    elif(Tparams.mode == 2):
        program[ind].TempSetPointCool = Tparams.tempORtemp
    WriteProgramToFile()

@webiopi.macro
def fan_change(length):
    global CurrentState        
    global Tparams
    if(Tparams.fanORactive == 0):
        Tparams.fanORstate = CurrentState.fanon 
    Tparams.fanORstate = (Tparams.fanORstate + 1) % 2    
    Tparams.fanORtime = datetime.datetime.utcnow() 
    Tparams.fanORlength = int(length)
    Tparams.fanORactive = 1    

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
    Tparams.fanORactive = 0
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

    
    

    
