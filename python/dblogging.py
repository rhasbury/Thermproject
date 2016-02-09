import pymysql.cursors

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