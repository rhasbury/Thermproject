import logging
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename='./remotetempdaemon.log', level=logging.DEBUG)
import datetime
import socketserver
import threading
import json
import time
import board
import busio
from adafruit_htu21d import HTU21D
import Adafruit_BMP.BMP085 as BMP085

HOST, PORT = "", 5010
currentLocation = 'basement' 
 
class MyTCPHandler(socketserver.BaseRequestHandler):
    def handle(self):        
        date_handler = lambda obj: (
            obj.isoformat()
            if isinstance(obj, datetime.datetime)
            or isinstance(obj, datetime.date)
            else obj.__dict__            
        )
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(1024).strip()        
        
        if("get_temp" in self.data.decode("utf-8")):
            logging.info("Temps requested. Sending")
            bmpsensor = None
            htusensor = None
            if(htu21dsensor != None):
                htusensor = {"temperature" : htu21dsensor.temperature, "humidity" : htu21dsensor.relative_humidity}
                logging.info("Sending this for htu21d: {}".format(htusensor))

            if(bmp085sensor != None):
                bmpsensor = {"temperature" : bmp085sensor.read_temperature() , "pressure" : bmp085sensor.read_pressure(), "altitude" : bmp085sensor.bmp085sensor, "sealevelpressure" : bmp085sensor.bmp085sensor}
                logging.info("Sending this for bmp085: {}".format(bmpsensor))
            json_to_send = json.dumps({'sensor1' : htusensor, 'sensor2' : bmpsensor})
            logging.info("Sending this json string: {}".format(json_to_send))
            self.request.sendall(bytes(json_to_send, 'UTF-8'))
        elif("get_something" in self.data.decode("utf-8")):
            self.request.sendall(bytes("whattt?", 'UTF-8'))

 
if __name__ == "__main__":

    # Create logger and set options
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Starting logging")
    
    # Create the data server and assigning the request handler        
    logging.info("Starting socket server")
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        htu21dsensor = HTU21D(i2c)
    except:
        logging.info("No htu21dsensor detected, or a fault happened.", exc_info=True)
        htu21dsensor = None
    
    try:
        bmp085sensor = BMP085.BMP085()
    except:
        logging.info("No bmp085 detected, or a fault happened.", exc_info=True)
        bmp085sensor = None
    if(htu21dsensor == None and bmp085sensor == None):
        logging.info("No sensors detected. Quitting.")
        quit()
        
    try:
        server = socketserver.TCPServer((HOST, PORT), MyTCPHandler)
        serverthread = threading.Thread(target=server.serve_forever)
        serverthread.daemon = True
        serverthread.start()
        logging.info("Socket Server listening")
    except:        
        logging.error("Socket Server start failed", exc_info=True)
        raise
  
    while True:            
        time.sleep(100)
  
