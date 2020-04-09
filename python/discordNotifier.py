import configparser
import datetime
import logging
from discord_webhook import DiscordWebhook
my_logger = logging.getLogger('MyLogger') 

class discordNotifier:
      
    def __init__(self):
        my_logger.debug("Discord notifier trying to  setup") 
        config = configparser.RawConfigParser()            
        config.optionxform = str
        config.read('/home/pi/thermostat/python/thermostat.conf')        
        if(config.has_section('discordnotifications')):        
            settings = config['discordnotifications']            
            self.enabled = int(settings['enabled'])
            self.webhookurl = settings['webhookurl']            
            self.lowerlimit = float(settings['lowerlimit'])
            self.upperlimit = float(settings['upperlimit'])
            self.interval = int(settings['interval'])
            self.lastsend = datetime.datetime(2000,1,1)       
            my_logger.debug("Discord notifier setup") 
        else:
            self.enabled = False
            
        
    
    def sendNotification(self, contentTosend):        
        try:            
            my_logger.debug("Sending discord notification") 
            webhook = DiscordWebhook(url=self.webhookurl, content=contentTosend)
            response = webhook.execute()      
        except:
            my_logger.debug("Tried to send discord notification of {}".format(contentTosend), exc_info=True)