#   Copyright 2012-2013 Eric Ptak - trouch.com
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import time
from webiopi.utils.types import signInteger
#from webiopi.devices.i2c import I2C
from webiopi.devices.sensor import Temperature, Pressure

class TemperatureFeed():
           
    def __str__(self):
        return "TemperatureFeed"
    
    def __family__(self):
        return [Temperature.__family__(self), Pressure.__family__(self)]


    def __getChartData__(self):
           
        f = open('./thermproj/python/ThermProgram.csv', 'r')
              
        temps = {'date': 'a', 'temp1': 'b', 'temp2': 'c', 'temp3': 'd', 'fanstate': 'e', 'heatstate': 'f','pressure' : 'g' }
        for line in reversed(list(open("filename"))):
            parts = line.split(",")
            temps.append( {'date': parts[0], 'temp1': parts[1], 'temp2': parts[2], 'temp3': parts[3], 'fanstate': parts[4], 'heatstate': parts[5],'pressure' : parts[6]  } )
        
        print(json.dumps(temps))
              
        return json.dumps(temps)



    
