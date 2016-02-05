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
            global RemoteSensors
            config = configparser.RawConfigParser()            
            config.read('/home/pi/temperature/thermostat.conf')
            settings = config['main']
            self.HEATER = int(settings['HEATER'])
            self.FAN = int(settings['FAN'])
            self.AC = int(settings['AC'])
            self.ThermostatStateFile = settings['ThermostatStateFile']
            self.ThermostatLogFile = settings['ThermostatLogFile']
            self.ProgramsFolder = settings['ProgramsFolder']
            self.RemoteSensors = []
            for (name, ip_addr) in config.items('remotesensors'):
                RemoteSensors[name] = ip_addr
            self.sensorlookup = settings['sensorlookup'].split(",")
    


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
        self.request.sendall(self.data.upper())

if __name__ == "__main__":
    HOST, PORT = "localhost", 50007

    # Create the server, binding to localhost on port 9999
    server = socketserver.TCPServer((HOST, PORT), MyTCPHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()