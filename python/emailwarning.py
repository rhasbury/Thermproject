import smtplib
import configparser
import datetime


class emailNotifier:
      
    def __init__(self):
        config = configparser.RawConfigParser()            
        config.optionxform = str
        config.read('/home/pi/thermostat/python/thermostat.conf')        
        if(config.has_section('emailnotifications')):        
            settings = config['emailnotifications']            
            self.enabled = settings['enabled']
            self.sourceaddress = settings['sourceaddress']
            self.sourcepassword = settings['sourcepassword']            
            self.destinationaddress = settings['destinationaddress']
            self.lowerlimit = float(settings['lowerlimit'])
            self.upperlimit = float(settings['upperlimit'])
            self.interval = int(settings['interval'])
            self.mailserver = settings['mailserver']
            self.mailport = settings['mailport']
            self.lastsend = datetime.datetime(2000,1,1)
        else:
            self.enabled = False
        
    def sendNotification(self, content):        
   
        try:            
            
            message = """From: Thermostat rrthermostat@gmail.com
                        To: You
                        Subject: Thermostat Temperature Warning
                        
                        
                        """ + content
            
            
            mail = smtplib.SMTP_SSL(self.mailserver, self.mailport, timeout=10)
            mail.ehlo()                        
            mail.starttls()                        
            mail.login(self.sourceaddress, self.sourcepassword)
            mail.sendmail(self.sourceaddress, self.destinationaddress, message)
            mail.close()            
            
        except smtplib.SMTPException:
            print("Error: unable to send email")
            import traceback
            traceback.print_exc()


