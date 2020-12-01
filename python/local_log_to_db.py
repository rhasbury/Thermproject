import logging
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename='./dbfiller.log', level=logging.DEBUG)
import datetime
import socketserver
import threading
import json
import time
import board
import busio
import pymysql.cursors
import adafruit_mlx90614
from adafruit_htu21d import HTU21D


htusensor = None


def logTemplineDB(logger, location, temp):    
    try:
        connection = pymysql.connect(host='localhost', user='monitor', passwd='password', db='temps', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:
            #cursor.execute ("INSERT INTO " + DBparams.temptable + " values(NOW(), NOW(), %s, %s, 'empty')", (location, temp))
            cursor.execute ("INSERT INTO " + 'tempdat' + " values(NOW(), %s, %s)", (location, temp))
        connection.commit()
        connection.close()
    except:
        #print("logTemplineDB() exception thrown")
        logger.debug("logTemplineDB() exception thrown", exc_info=True)


if __name__ == "__main__":

    # Create logger and set options
    logging.getLogger().setLevel(logging.DEBUG)
    logging.info("Starting logging")
    
    try:
        i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
        htu21dsensor = HTU21D(i2c)
    except:
        logging.info("No htu21dsensor detected, or a fault happened.", exc_info=True)
        quit()
    try:        
        MLX_temp_sensor = adafruit_mlx90614.MLX90614(i2c)
    except:
        logging.info("No MLX90614 detected, or a fault happened.", exc_info=True)
        quit()
        
        
    
    while True:            
        htusensor = {"temperature" : htu21dsensor.temperature, "humidity" : htu21dsensor.relative_humidity}
        logging.debug("Read this from htu21d: {}".format(htusensor))                
        logging.info("Doing database logging now")
        logTemplineDB(logging, 'here', htu21dsensor.temperature)
        logTemplineDB(logging, 'MLXambient', MLX_temp_sensor.ambient_temperature)
        logTemplineDB(logging, 'MLXobject', MLX_temp_sensor.object_temperature)
        
        time.sleep(60)