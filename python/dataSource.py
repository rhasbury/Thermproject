# # Echo server program
# import socket
# 
# HOST = ''                 # Symbolic name meaning all available interfaces
# PORT = 50007              # Arbitrary non-privileged port
# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# s.bind((HOST, PORT))
# s.listen(1)
# conn, addr = s.accept()
# print 'Connected by', addr
# while 1:
#     data = conn.recv(1024)
#     if not data: break
#     print(data)
#     #conn.sendall(data)
# conn.close()

import configparser
import socketserver
import datetime
import json

class ThermostatParameters:
    
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

    def __init__(self):
            config = configparser.RawConfigParser()            
            config.read('/home/pi/temperature/thermostat.conf')
            settings = config['main']            
            config.optionxform=str
            self.HEATER = int(settings['heater'])
            self.FAN = int(settings['fan'])
            self.AC = int(settings['ac'])
            self.ThermostatStateFile = settings['thermostatstatefile']
            self.ThermostatLogFile = settings['thermostatlogfile']
            self.ProgramsFolder = settings['programsfolder']
            self.sensorlookup = settings['sensorlookup'].split(",")            
            self.RemoteSensors = dict(config.items('remotesensors'))
            #for (name, ip_addr) in config.items('remotesensors'):
            #    RemoteSensors[name] = ip_addr
    
    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
    


Tparams = ThermostatParameters()



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
        print ("{} wrote:".format(self.client_address[0]))
        print (self.data)
        # just send back the same data, but upper-cased
        #self.request.sendall(self.data.upper())
        self.request.sendall(bytes(Tparams.to_JSON(), 'UTF-8'))
        
        

if __name__ == "__main__":
    HOST, PORT = "localhost", 50007
    #print (Tparams.RemoteSensors)
    #print (Tparams.HEATER)
    #print (Tparams.to_JSON())
    # Create the server, binding to localhost on port 9999
    server = socketserver.TCPServer((HOST, PORT), MyTCPHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()