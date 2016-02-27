#   Copyright 2014 Takashi Ando <dodo5522@gmail.com>
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
from webiopi.devices.i2c import I2C
from webiopi.devices.sensor import Temperature
from webiopi.devices.sensor import Humidity

class HTU21D(I2C, Temperature, Humidity):
    _REG_TRIGGER_MEASURE_TEMPERATURE = 0xf3
    _REG_TRIGGER_MEASURE_HUMIDITY = 0xf5
    _REG_TRIGGER_SOFT_RESET = 0xfe

    def __init__(self):
        I2C.__init__(self, 0x40)

    def __str__(self):
        return 'HTU21D'

    def __family__(self):
        return [Temperature.__family__(self), Humidity.__family__(self)]

    def resetSoftware(self):
        # The soft reset takes less than 15ms as written on datasheet page 12.
        self.writeByte(self._REG_TRIGGER_SOFT_RESET)
        time.sleep(15.0/1000)

    def __getKelvin__(self):
        return self.Celsius2Kelvin(self.__getCelsius__())

    def __getCelsius__(self):
        self.writeByte(self._REG_TRIGGER_MEASURE_TEMPERATURE)
        time.sleep(50.0/1000)
        regs = self.readBytes(3)

        s_temp = regs[0] << 8 | regs[1]
        crc_reg = regs[2]
        crc = self._getCrc(s_temp, 16)

        if crc_reg != crc:
            raise ValueError('CRC unmatch : 0x%02x, 0x%02x.' % (crc_reg, crc))

        temp = -46.85 + 175.72 * s_temp / (1 << 16)
        return temp

    def __getFahrenheit__(self):
        return self.Celsius2Fahrenheit(self.__getCelsius__())

    def __getHumidity__(self):
        self.writeByte(self._REG_TRIGGER_MEASURE_HUMIDITY)
        time.sleep(16.0/1000)
        regs = self.readBytes(3)

        s_rh = regs[0] << 8 | regs[1]
        crc_reg = regs[2]
        crc = self._getCrc(s_rh, 16)

        if crc_reg != crc:
            raise ValueError('CRC unmatch : 0x%02x, 0x%02x.' % (crc_reg, crc))

        rh = -6.0 + 125.0 * s_rh / (1 << 16)
        return rh / 100.0

    def _getCrc(self, value, bitlen):
        '''
        Calculate and return CRC-8 correspoinding to the specified value with bit length.
        '''
        # x^8 + x^5 + x^4 + 1
        polynomial = 0b100110001

        # This is first padded with zeroes correspoinding to the bit length of the CRC.
        polynomial <<= bitlen + 8 - 9
        value <<= 8

        for i in range(0, bitlen):
            if value & (1 << (bitlen + 8 - 1 - i)):
                value ^= (polynomial >> i)

        return value
