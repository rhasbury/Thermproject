import pymysql.cursors

def logTemplineDB(DBparams, mylogger, location, temp):    
    try:
        connection = pymysql.connect(host=DBparams.host, user=DBparams.dbuser, passwd=DBparams.dbpassword, db=DBparams.db, charset=DBparams.charset, cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:
            cursor.execute ("INSERT INTO " + DBparams.temptable + " values(NOW(), %s, %s)", (location, temp))
        connection.commit()
        connection.close()
    except:
        #print("logTemplineDB() exception thrown")
        my_logger.debug("logTemplineDB() exception thrown", exc_info=True)

def logPresslineDB(DBparams, mylogger, location, pressure):    
    try:
        connection = pymysql.connect(host=DBparams.host, user=DBparams.dbuser, passwd=DBparams.dbpassword, db=DBparams.db, charset=DBparams.charset, cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:        
            cursor.execute ("INSERT INTO " + DBparams.presstable + " values(NOW(), %s, %s)", (location, pressure))        
        connection.commit()
        connection.close()
    except:
        #print("logPresslineDB() exception thrown")
        my_logger.debug("logPresslineDB() exception thrown", exc_info=True)

def logHumlineDB(DBparams, mylogger, location, humidity):    
    try:
        connection = pymysql.connect(host=DBparams.host, user=DBparams.dbuser, passwd=DBparams.dbpassword, db=DBparams.db, charset=DBparams.charset, cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:        
            cursor.execute ("INSERT INTO " + DBparams.humiditytable + " values(NOW(), %s, %s)", (location, humidity))        
        connection.commit()
        connection.close()
    except:
        #print("logHumlineDB() exception thrown")
        my_logger.debug("logHumlineDB() exception thrown", exc_info=True)
        
# Checks connection, and then the existence of the require table. If the table doesn't exist then it creates it. 

def CheckDatabase(DBparams, my_logger):
    try:
        connection = pymysql.connect(host=DBparams.host, user=DBparams.dbuser, passwd=DBparams.dbpassword, db=DBparams.db, charset=DBparams.charset, cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:        
            result = cursor.execute ("SHOW TABLES LIKE '" + DBparams.temptable + "'")       
            if(result == 0):
                cursor.execute ("CREATE TABLE " + DBparams.temptable + " (tdate DATETIME, zone TEXT, pressure NUMERIC(10,5));")
            
            result = cursor.execute ("SHOW TABLES LIKE '" + DBparams.presstable + "'")       
            if(result == 0):
                cursor.execute ("CREATE TABLE " + DBparams.presstable + " (tdate DATETIME, zone TEXT, pressure NUMERIC(10,5));")            
            
            result = cursor.execute ("SHOW TABLES LIKE '" + DBparams.humiditytable + "'")       
            if(result == 0):
                cursor.execute ("CREATE TABLE " + DBparams.humiditytable + " (tdate DATETIME, zone TEXT, pressure NUMERIC(10,5));")
    
        
        connection.close()
    except:
        #print("logHumlineDB() exception thrown")
        my_logger.debug("CheckDatabase() exception thrown", exc_info=True)