import webiopi
import datetime
import pymysql.cursors
#import locale
from webiopi.clients import *
from _ctypes import addressof


ThermostatProgramFile = '/home/pi/thermproj/python/ThermProgram.csv'
ThermostatLogFile = '/home/pi/thermproj/python/thermlog.txt'

GPIO = webiopi.GPIO # Helper for LOW/HIGH values
HEATER = 17 
FAN = 27
AC = 22

LocalTemp = 0
RemTemp1 = 0 
RemTemp2 = 0  
 
sensorlookup = ["Living Room", "Bedroom", "Basement" ]


#my_logger = logging.getLogger('MyLogger')




class ThermostatParameters:
    #def __init__(self):
    tempORtime = datetime.datetime.now()    
    tempORactive = False
    tempORlength = 1
    tempORtemp = 20
    fanORtime = datetime.datetime.now()
    fanORactive = 0
    fanORlength = 1
    fanORstate = 0
    mode = 1 # 1 = heat, 2 = cool, 0 = off 
        

class ProgramDataClass:     
    def __init__(self, TimeActive, MasterTempS, TempSetP, FanOnoff):
        self.TimeActiveFrom = TimeActive         # The time this program segment is active from
        self.MasterTempSensor = MasterTempS                            # The index of the active temp sensor
        self.TempSetPoint    = TempSetP                            # temperature set point
        self.fanon   = FanOnoff                                 # is the fan on or off
        self.sensorTemp   = 0    


Tparams = ThermostatParameters
CurrentState = ProgramDataClass
program = []

# setup function is automatically called at WebIOPi startup
def setup():
    global program
    global CurrentState

    GPIO.setFunction(HEATER, GPIO.OUT)
    GPIO.setFunction(FAN, GPIO.OUT)
    GPIO.setFunction(AC, GPIO.OUT)
       
    loadProgramFromFile()
    CurrentState = program[0]
    Tparams.tempORtemp = CurrentState.TempSetPoint
    
    for x in range(0, program.__len__()):
        printProram(program[x])


# loop function is repeatedly called by WebIOPi 
def loop():
    global CurrentState
    global Tparams
    global graphfilecount
        
    global LocalTemp
    global RemTemp1
    global RemTemp2 
    heaterstate = 0
    acstate = 0
    
    if (datetime.datetime.utcnow() - Tparams.tempORtime > datetime.timedelta(minutes=Tparams.tempORlength)):        
        Tparams.tempORactive = False
        
        
    if (datetime.datetime.utcnow() - Tparams.fanORtime > datetime.timedelta(minutes=Tparams.fanORlength)):        
        Tparams.fanORactive = 0
            
    updateProgram()

    tmp = webiopi.deviceInstance("bmp")

# Read local temperature    
    LocalTemp = tmp.getCelsius()
# Try to read remote temp and if fails use local temp instead.  
    try:
        RempTemp1 = readFromSensor("192.168.1.117")
    except:            
        RemTemp1 = LocalTemp
# Try to read remote temp and if fails use local temp instead. 
    try:
        RempTemp2 = readFromSensor("192.168.1.146")            
    except:            
        RemTemp2 = LocalTemp
    
# decide which temp we're using for control
    if(CurrentState.MasterTempSensor == 1):
        celsius = RemTemp1
    elif(CurrentState.MasterTempSensor == 2):
        celsius = RemTemp2        
    else:
        celsius = LocalTemp
        
#    Override section
    
    if(Tparams.tempORactive):
        tset = Tparams.tempORtemp
    else:
        tset = CurrentState.TempSetPoint
  
    
    if(Tparams.fanORactive == 1):
        fset = Tparams.fanORstate
    else:
        fset = CurrentState.fanon    
    
    
    CurrentState.sensorTemp = celsius
    
    if(Tparams.mode == 1):
        GPIO.digitalWrite(AC, GPIO.HIGH)
        if((tset - 0.5)  > celsius):
           GPIO.digitalWrite(HEATER, GPIO.LOW)
           heaterstate = 1
        elif((tset + 0.5) < celsius):
           GPIO.digitalWrite(HEATER, GPIO.HIGH)
           heaterstate = 0
    elif(Tparams.mode == 2):
        GPIO.digitalWrite(HEATER, GPIO.HIGH)
        if((tset - 0.5) > celsius):
           GPIO.digitalWrite(AC, GPIO.HIGH)
           acstate = 1
        elif((tset + 0.5) < celsius):
           GPIO.digitalWrite(AC, GPIO.LOW)
           acstate = 0
    else:
        GPIO.digitalWrite(AC, GPIO.HIGH)
        GPIO.digitalWrite(HEATER, GPIO.HIGH)

    	   
    if(fset == 1):
        GPIO.digitalWrite(FAN, GPIO.LOW)
    elif(fset == 0):
        GPIO.digitalWrite(FAN, GPIO.HIGH)    
       
    localPressure = tmp.getPascalAtSea()
    
    #logline("{0!s},{1!s},{2!s},{3!s},{4!s}, {5!s}".format(LocalTemp, RemTemp1, RemTemp2, CurrentState.fanon, heaterstate, localPressure))
    logTemplineDB(sensorlookup[0], LocalTemp)
    logTemplineDB(sensorlookup[1], RemTemp1)
    logTemplineDB(sensorlookup[2], RemTemp2)
    logPresslineDB(sensorlookup[0], localPressure)
      
    graphfilecount = 0
    webiopi.sleep(10)
  

#def destroy():
    

def loadProgramFromFile():
    global program
    f = open(ThermostatProgramFile , 'r')
    
    linein = f.readline()
    
    for line in f:        
        parts = line.split(",")      
        program.append(ProgramDataClass(datetime.datetime.strptime(parts[0], '%H:%M'),int(parts[1]), float(parts[2]), int(parts[3]) ))   
    
    f.close()
    program.sort(key = lambda x: x.TimeActiveFrom)
    
    
def WriteProgramToFile():
    global program
    f = open(ThermostatProgramFile, 'w')
    
    f.write("# TimeActiveFrom, MasterTempSensor (0=localsensor, 1=?, 2=? ), temperature set point, enable fan\n")
    
    for x in range(0, (program.__len__())):         
#        line = "{0!s},{1!d},{2!f},{3!d}\n".format(datetime.datetime.strftime(program[x].TimeActiveFrom, '%H:%M'), program[x].MasterTempSensor, program[x].TempSetPoint, program[x].fanon )
        #f.write("{0!s},{1!d},{2!f},{3!d}\n".format(datetime.datetime.strftime(program[x].TimeActiveFrom, '%H:%M'), program[x].MasterTempSensor, program[x].TempSetPoint, program[x].fanon ))
        f.write(datetime.datetime.strftime(program[x].TimeActiveFrom, '%H:%M'))
        f.write(",")
        f.write(str(program[x].MasterTempSensor))
        f.write(",")
        f.write(str(program[x].TempSetPoint))
        f.write(",")
        f.write(str(program[x].fanon))
        f.write("\n")
       
    f.close()


def logline(linetolog):
    f = open(ThermostatLogFile, 'a')
    now = datetime.datetime.now()
    send = "{0},{1};\n".format(now.strftime('%a %b %d %Y %X'), linetolog)
    #print(locale.getlocale())
    f.write(send)
    f.close



def logTemplineDB(location, temp):    
    connection = pymysql.connect(host='localhost', user='monitor', passwd='password', db='temps', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    with connection.cursor() as cursor:
        cursor.execute ("INSERT INTO tempdat values(NOW(), NOW(), %s, %s, 'empty')", (location, temp))
    connection.commit()
    connection.close()

def logPresslineDB(location, pressure):    
    connection = pymysql.connect(host='localhost', user='monitor', passwd='password', db='temps', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    with connection.cursor() as cursor:
        cursor.execute ("INSERT INTO pressdat values(CURRENT_DATE(), NOW(), %s, %s)", (location, pressure))
    connection.commit()
    connection.close()


def printProram(prg):
    print(prg.TimeActiveFrom, prg.MasterTempSensor, prg.TempSetPoint, prg.fanon)
    
    
def updateProgram():
    global CurrentState
    global program    
    global Tparams
    now = datetime.datetime.now()
    progfound = False
    for x in range((program.__len__()-1), -1, -1):
        for y in range(now.minute, -1, -1):
            if(program[x].TimeActiveFrom.hour == now.hour and program[x].TimeActiveFrom.minute == y):
                CurrentState = program[x]
                printProram(CurrentState)
                progfound = True
                break
        if(progfound):
            break
   

def readFromSensor(address):
    with PiHttpClient(address) as client:            
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
    
    return "%d;%d;%s;%s;%d;%s;%s;%s" % (CurrentState.TimeActiveFrom.hour, CurrentState.TimeActiveFrom.minute, sensorlookup[CurrentState.MasterTempSensor], str(CurrentState.TempSetPoint)[:6], CurrentState.fanon, overrideexp, str(Tparams.tempORtemp)[:6], str(CurrentState.sensorTemp)[:6]) 



@webiopi.macro
def getProgram(index):    
    global program
    ind = int(index) 
    if(ind < 0):
        ind = 0
    if(ind > (program.__len__()-1)):
        ind = (program.__len__()-1) 
       
    return "%s;%d;%f;%d;%d;%d" % (datetime.datetime.strftime(program[ind].TimeActiveFrom, '%H;%M'), program[ind].MasterTempSensor, program[ind].TempSetPoint, program[ind].fanon, program.__len__(), ind)
    
@webiopi.macro
def setProgram(index, time, sensor, temp, fanon ):
    global program
    ind = int(index) 
    for x in range(0, (program.__len__())):
        printProram(program[x])
    
    if(ind == (program.__len__())):    # new entry
        program.append(ProgramDataClass(datetime.datetime.strptime(time, '%H:%M'), int(sensor), float(temp), int(fanon)))
#        print("added new") 
    else:        
        program[ind].TimeActiveFrom = datetime.datetime.strptime(time, '%H:%M')
        program[ind].MasterTempSensor = int(sensor)
        program[ind].TempSetPoint    = float(temp) 
        program[ind].fanon = int(fanon)
   
    program.sort(key = lambda x: x.TimeActiveFrom)
    
    WriteProgramToFile()
    
    



@webiopi.macro
def temp_change(amount, length):
    global CurrentState        
    global Tparams
    if(Tparams.tempORactive == False):
        Tparams.tempORtemp = CurrentState.TempSetPoint
 
    Tparams.tempORtemp = Tparams.tempORtemp + (int(amount)* 0.5)
    Tparams.tempORtime = datetime.datetime.utcnow() 
    Tparams.tempORlength = int(length)
    Tparams.tempORactive = True    
    

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

@webiopi.macro
def send_graph_data():
    f = open(ThermostatLogFile, 'r')
    temps = tail(f, 20, 0)
    f.close
    return temps

@webiopi.macro
def send_graph_points():
    global LocalTemp
    global RemTemp1
    global RemTemp2 
    now = datetime.datetime.now()
    linetolog = "{0!s},{1!s},{2!s}".format(LocalTemp, RemTemp1, RemTemp2)
    send = "{0},{1};\n".format(now.strftime('%a %b %d %Y %X'), linetolog)
                  
    return send
  


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

    
    

    
