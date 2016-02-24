import pymysql.cursors

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
        
        
def logControlLineDB(DBparams, my_logger, equipment, state):    
    try:
        connection = pymysql.connect(host=DBparams.host, user=DBparams.dbuser, passwd=DBparams.dbpassword, db=DBparams.db, charset=DBparams.charset, cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:
            cursor.execute ("Select tdate FROM controldat WHERE equipment='{}' ORDER by tdate DESC LIMIT 1".format(equipment))
            row = cursor.fetchone()
            
            if(row != None):                
                tdelta = datetime.datetime.now() - row['tdate']
                sqlquery = "INSERT INTO " + DBparams.controltable + " values(NOW(), %s, %s, %s, %s)", (equipment, bool(state), tdelta.strftime('%%H:%M:%S'), tdelta.seconds ) 
                print(sqlquery)
                cursor.execute (sqlquery) 
                    
            else:
                 cursor.execute ("INSERT INTO " + DBparams.controltable + " values(NOW(), %s, %s, 0)", (equipment, bool(state)))
        connection.commit()
        connection.close()
    except:
        #print("logHumlineDB() exception thrown")
        my_logger.debug("logControlLineDB() exception thrown", exc_info=True)
        
# Checks connection, and then the existence of the require table. If the table doesn't exist then it creates it. 

def CheckDatabase(DBparams, my_logger):
    try:
        connection = pymysql.connect(host=DBparams.host, user=DBparams.dbuser, passwd=DBparams.dbpassword, db=DBparams.db, charset=DBparams.charset, cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:        
            result = cursor.execute ("SHOW TABLES LIKE '" + DBparams.temptable + "'")       
            if(result == 0):
                my_logger.info("Temperature table '%s' not found in database, creating it.".format(DBparams.temptable))
                cursor.execute ("CREATE TABLE " + DBparams.temptable + " (tdate DATETIME, zone TEXT, temperature NUMERIC(10,5));")
            
            result = cursor.execute ("SHOW TABLES LIKE '" + DBparams.presstable + "'")       
            if(result == 0):
                my_logger.info("Pressure table '%s' not found in database, creating it.".format(DBparams.presstable))
                cursor.execute ("CREATE TABLE " + DBparams.presstable + " (tdate DATETIME, zone TEXT, pressure NUMERIC(10,5));")                            
            
            result = cursor.execute ("SHOW TABLES LIKE '" + DBparams.humiditytable + "'")       
            if(result == 0):
                my_logger.info("Humidity table '%s' not found in database, creating it.".format(DBparams.humiditytable))
                cursor.execute ("CREATE TABLE " + DBparams.humiditytable + " (tdate DATETIME, zone TEXT, humidity NUMERIC(10,5));")
            
            result = cursor.execute ("SHOW TABLES LIKE '" + DBparams.controltable + "'")       
            if(result == 0):
                my_logger.info("Control table '%s' not found in database, creating it.".format(DBparams.controltable))
                cursor.execute ("CREATE TABLE " + DBparams.controltable + " (tdate DATETIME, equipment TEXT, state BOOLEAN, dtime TIME);")
    
        
        connection.close()
    except:
        #print("logHumlineDB() exception thrown")
        my_logger.debug("CheckDatabase() exception thrown", exc_info=True)