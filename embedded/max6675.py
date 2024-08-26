import time
from machine import Pin, SPI

class MAX6675:
    def __init__(self, spi, cs):
        self.spi = spi
        self.cs = cs
        self.cs.init(self.cs.OUT, value=1)

    def read(self):
        self.cs.value(0)
        data = self.spi.read(2)
        self.cs.value(1)
        value = (data[0] << 8 | data[1]) >> 3
        if value & 0x800:
            value -= 4096
        return value * 0.25

