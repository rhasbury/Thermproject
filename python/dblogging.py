import pymysql.cursors
import datetime
import logging
my_logger = logging.getLogger('MyLogger')

def logTemplineDB(DBparams, my_logger, location, temp):    
    try:
        connection = pymysql.connect(host=DBparams.host, user=DBparams.dbuser, passwd=DBparams.dbpassword, db=DBparams.db, charset=DBparams.charset, cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:
            #cursor.execute ("INSERT INTO " + DBparams.temptable + " values(NOW(), NOW(), %s, %s, 'empty')", (location, temp))
            cursor.execute ("INSERT INTO " + DBparams.temptable + " values(NOW(), %s, %s)", (location, temp))
        connection.commit()
        connection.close()
    except:
        #print("logTemplineDB() exception thrown")
        my_logger.debug("logTemplineDB() exception thrown", exc_info=True)

def logPresslineDB(DBparams, my_logger, location, pressure):    
    try:
        connection = pymysql.connect(host=DBparams.host, user=DBparams.dbuser, passwd=DBparams.dbpassword, db=DBparams.db, charset=DBparams.charset, cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:        
            cursor.execute ("INSERT INTO " + DBparams.presstable + " values(NOW(), %s, %s)", (location, pressure))        
        connection.commit()
        connection.close()
    except:
        #print("logPresslineDB() exception thrown")
        my_logger.debug("logPresslineDB() exception thrown", exc_info=True)

def logHumlineDB(DBparams, my_logger, location, humidity):    
    try:
        connection = pymysql.connect(host=DBparams.host, user=DBparams.dbuser, passwd=DBparams.dbpassword, db=DBparams.db, charset=DBparams.charset, cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:        
            cursor.execute ("INSERT INTO " + DBparams.humiditytable + " values(NOW(), %s, %s)", (location, humidity))        
        connection.commit()
        connection.close()
    except:
        #print("logHumlineDB() exception thrown")
        my_logger.debug("logHumlineDB() exception thrown", exc_info=True)
        
        
# def logControlLineDB(DBparams, my_logger, equipment, state, runtime):    
#     try:
#         connection = pymysql.connect(host=DBparams.host, user=DBparams.dbuser, passwd=DBparams.dbpassword, db=DBparams.db, charset=DBparams.charset, cursorclass=pymysql.cursors.DictCursor)
#         with connection.cursor() as cursor:
#             cursor.execute ("Select tdate FROM controldat WHERE equipment='{}' ORDER by tdate DESC LIMIT 1".format(equipment))
#             row = cursor.fetchone()
#
#             if(row != None):                
#                 tdelta = datetime.datetime.now() - row['tdate']
#                 sqlquery = "INSERT INTO " + DBparams.controltable + " values(NOW(), '{}', {}, {}, {})".format(equipment, bool(state),  tdelta.total_seconds(), runtime )
#
#                 #my_logger.debug(sqlquery)
#                 cursor.execute (sqlquery) 
#
#             else:
#                 cursor.execute ("INSERT INTO " + DBparams.controltable + " values(NOW(), '{}', {}, 0, {})".format(equipment, bool(state), runtime))
#         connection.commit()
#         connection.close()
#     except:
#         #print("logHumlineDB() exception thrown")
#         my_logger.debug("logControlLineDB() exception thrown", exc_info=True)
#



def log_runtime_to_db(DBparams, my_logger, last_change_time, state, equipment):    
    tdelta = datetime.datetime.now() - last_change_time
    try:
        connection = pymysql.connect(host=DBparams.host, user=DBparams.dbuser, passwd=DBparams.dbpassword, db=DBparams.db, charset=DBparams.charset, cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:
            cursor.execute ("INSERT INTO " + DBparams.controltable + " values(NOW(), '{}', {}, 0, {})".format(equipment, bool(state), tdelta.seconds))            
            connection.commit()
            #connection.close()
    except:        
        my_logger.debug("logControlLineDB() exception thrown", exc_info=True)

# Checks connection, and then the existence of the require table. If the table doesn't exist then it creates it. 

def CheckDatabase(DBparams, my_logger):
    try:
        connection = pymysql.connect(host=DBparams.host, user=DBparams.dbuser, passwd=DBparams.dbpassword, db=DBparams.db, charset=DBparams.charset, cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:        
            result = cursor.execute ("SHOW TABLES LIKE '" + DBparams.temptable + "'")       
            if(result == 0):
                my_logger.info("Temperature table '{}' not found in database, creating it.".format(DBparams.temptable))
                cursor.execute ("CREATE TABLE " + DBparams.temptable + " (tdate DATETIME, zone TEXT, temperature NUMERIC(10,5));")
            
            result = cursor.execute ("SHOW TABLES LIKE '" + DBparams.presstable + "'")       
            if(result == 0):
                my_logger.info("Pressure table '{}' not found in database, creating it.".format(DBparams.presstable))
                cursor.execute ("CREATE TABLE " + DBparams.presstable + " (tdate DATETIME, zone TEXT, pressure NUMERIC(10,5));")                            
            
            result = cursor.execute ("SHOW TABLES LIKE '" + DBparams.humiditytable + "'")       
            if(result == 0):
                my_logger.info("Humidity table '{}' not found in database, creating it.".format(DBparams.humiditytable))
                cursor.execute ("CREATE TABLE " + DBparams.humiditytable + " (tdate DATETIME, zone TEXT, humidity NUMERIC(10,5));")
            
            result = cursor.execute ("SHOW TABLES LIKE '" + DBparams.controltable + "'")       
            if(result == 0):
                my_logger.info("Control table '{}' not found in database, creating it.".format(DBparams.controltable))
                cursor.execute ("CREATE TABLE " + DBparams.controltable + " (tdate DATETIME, equipment TEXT, state BOOLEAN, dtime TIME, rtime NUMERIC(10,5));")
    
        
        connection.close()
    except:
        #print("logHumlineDB() exception thrown")
        my_logger.debug("CheckDatabase() exception thrown", exc_info=True)