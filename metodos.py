# Métodos usados no projeto do filtro de água
from rp2 import PIO, StateMachine, asm_pio
from machine import Pin
from time import sleep
from myconf import *

class sm_led:
    @asm_pio(set_init=PIO.OUT_LOW)
    def led_off():
        set(pins, 0)

    @asm_pio(set_init=PIO.OUT_LOW)
    def led_on():
        set(pins, 1)

    def __init__(self, led_pin):
        self.sm1 = StateMachine(1, self.led_off, freq=20000, set_base=Pin(led_pin))
        self.sm2 = StateMachine(2, self.led_on, freq=20001, set_base=Pin(led_pin))

class Sensor:
    def __init__(self, dt, volume, increment):
        self.volume = volume
        self.count0 = round(volume * 2.63) # was 4.38
        self.count = self.count0
        self.increment = increment
        self.data = Pin(dt, Pin.IN, Pin.PULL_DOWN)
        self.data.irq(handler=self.pulse, trigger = Pin.IRQ_RISING)

    def pulse(self, pin):
        self.count += self.increment
        if self.count == 0:
            self.data.irq(handler = None)

class Encoder:
    def __init__(self, dt_pin, clk_pin, menu_enabler=1, loop_enabler=0, value=parameters['volume_base'],
                 v_max=parameters['volume_max'],override_step=0):
        self.value = value
        self.v_max = v_max
        self.v_min = 0
        self.menu = menu_enabler # 1 ativo ou 0 inativo
        self.loop = loop_enabler # 1 ativo ou 0 inativo
        self.override = override_step # 0 default ou valor
        self.dt = Pin(dt_pin, Pin.IN, Pin.PULL_DOWN)
        self.clk = Pin(clk_pin, Pin.IN, Pin.PULL_DOWN)
        self.last_clk = self.clk.value()
        self.clk.irq(trigger = Pin.IRQ_RISING | Pin.IRQ_FALLING, handler = self.encoder_change)

    def v_step(self):
        if self.override != 0:
            return self.override
        elif self.value < 300:
            return 10
        elif self.value >= 300 and self.value < 600:
            return 20
        else:
            return 50

    def encoder_change(self, pin):
        if self.clk.value() == self.last_clk:
            return

        self.state = self.dt.value() + self.clk.value()
        self.last_clk = self.clk.value()
        if self.state % 2 == 1: # Giro no sentido horário (incremento)
            if self.value == 'Menu':
                self.value = 0
            elif self.value < self.v_max:
                self.value += self.v_step()
            elif self.value == self.v_max and self.loop ==1:
                self.value = self.v_min
        elif self.state % 2 == 0: # Giro no sentido anti-horário (decremento)
            if self.value == 'Menu':
                return
            if self.value > self.v_min:
                self.value -= self.v_step()
            elif self.value == self.v_min:
                if self.loop == 1:
                    self.value = self.v_max
                elif self.menu == 1:
                    self.value = 'Menu'

class Desenhista:
    def __init__(self,figures,oled):
        self.figures = figures
        self.oled = oled

    def draw_num(self,number,text='Volume de agua',unit='mL'):
        x_off = 0
        y_off = 14
        num_str = str(number)
        if len(num_str) == 4:
            num_str = num_str[:1] + "d" + num_str[1:]
        num_str = num_str + unit

        self.oled.fill(0)
        self.oled.text(text,0,0)
        for i in range(0, len(num_str)):
            for y, row in enumerate(self.figures[num_str[i]]):
                for x, c in enumerate(row):
                    if c==1:
                        self.oled.pixel(x+x_off, y+y_off, 1)
            offset = len(self.figures[num_str[i]][1])+4
            x_off = x_off + offset
        self.oled.show()
