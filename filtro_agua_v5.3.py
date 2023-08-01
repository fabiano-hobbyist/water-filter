# Filtro_agua_v5.3.py
# Programa para filtro de água: permite selecionar o voluume desejado a partir do potenciometro
# O botão gera um interrupt para abrir a válvula e o sensor de fluxo determina o fechamento
# Uso do PIO para fazer o led dentro do botão ficar piscando enquanto a válvula está ativa
# Futuras melhorias: Menu na fonte 18px

from machine import Pin, ADC, I2C
from rp2 import PIO, StateMachine, asm_pio
from time import sleep
from ssd1306 import SSD1306_I2C as display
from fonte_18px import figures
from definicoes import *
from metodos import *
from myconf import *
global sensor_pin, standby_flag, timeout, v0

# Definição dos pins
display_sda_pin = 0  # Conectado ao SDA do display - data
display_scl_pin = 1  # Conectado ao SCL do display - clock
sensor_pin      = 2  # Conectado ao fio amarelo do sensor - data
valve_pin       = 3  # Comando da vávula - base do transistor
blue_led_pin    = 4  # Comando do LED azul - base do transistor
blue_button_pin = 5  # Conectado ao data do botão azul
encoder_sw_pin  = 13 # Conectado ao switch do encoder
encoder_clk_pin = 14 # Conectado ao clock do encoder
encoder_dt_pin  = 15 # Conectado ao data do encoder

# Definição dos objetos
blue_button = Pin(blue_button_pin, Pin.IN, Pin.PULL_DOWN)
encoder_sw  = Pin(encoder_sw_pin, Pin.IN, Pin.PULL_UP)
blue_led    = sm_led(blue_led_pin)
encoder     = Encoder(encoder_dt_pin, encoder_clk_pin, 1)
valve       = Pin(valve_pin, Pin.OUT)

# Setup
valve.off() # Fecha a válvula após reinicialização do sistema, o hard-reset serve como botão de emergência
blue_led.sm2.active(1) # SM que acende o led azul
standby_flag = False # Quando True desliga o display e o led azul
timeout = parameters['timeout']
v0 = encoder.value

# Configuração do display
i2c  = I2C(0, sda=Pin(display_sda_pin), scl=Pin(display_scl_pin), freq=400000)
oled = display(128, 32, i2c)
pincel = Desenhista(figures, oled)

def oled_print(my_string, h, v):
    oled.fill(0)
    for i in range(0,len(my_string)):
        oled.text(my_string[i], h[i], v[i])
    oled.show()

def replace_parameter(key,value):
    with open('myconf.py', 'r') as file:
        replacement = ''
        for line in file:
            line = line.strip()
            changes = line.replace('"'+key+'":'+str(parameters[key]),
                                   '"'+key+'":'+str(value))
            replacement = replacement + changes + '\n'
    with open('myconf.py', 'w') as newfile:
        newfile.write(replacement)
    parameters[key]=value

# Interrupt handler: Parar o fluxo de água apertando o botão enquanto a válvula está ativa
def stop_flow(Pin):
    valve.off()
    blue_button.irq(handler=None)
    global interrupted
    interrupted = True
    oled_print(['Interrompido!'],[0],[0])
    blue_led.sm2.active(0)
    sleep(0.01)
    blue_led.sm1.active(0)
    sleep(0.5)

# Iniciar o fluxo de água
def start_flow():
    sleep(0.5)
    global interrupted
    interrupted = False
    blue_button.irq(trigger=Pin.IRQ_RISING, handler=stop_flow)
    encoder_sw.irq(trigger=Pin.IRQ_RISING, handler=stop_flow)
    blue_led.sm1.active(1)
    blue_led.sm2.active(1)
    oled.fill(0)
    oled.text(str(sensor.volume)+'mL - Aguarde!', 0, 0)
    oled.rect(0,12,108,20,1)
    oled.show()
    sleep(0.5)
    valve.on()
    while sensor.count > 0:
        fill = int(round(1 - sensor.count / sensor.count0, 2) * 100)
        oled.fill_rect(4, 16, fill, 12, 1)
        oled.show()
        #sensor.pulse(sensor_pin) #debug
        if interrupted == True:
            oled_print(['Aguarde!'], [0], [0])
            blue_led.sm2.active(1)
            replace_parameter('volume_total',parameters['volume_total']+round(sensor.count/2.63,0))
            sleep(0.5)
            break
        sleep(0.01)
    valve.off()
    replace_parameter('volume_total',parameters['volume_total']+sensor.volume)
    blue_led.sm1.active(0)
    interrupted = False
    blue_button.irq(handler=None)
    encoder_sw.irq(handler=None)

def standby():
    global standby_flag
    standby_flag = True
    valve.off()
    blue_led.sm2.active(0)
    blue_led.sm1.active(1)
    sleep(0.01)
    blue_led.sm1.active(0)
    oled.fill(0)
    oled.show()

def wakeup():
    global standby_flag, timeout, v0
    standby_flag = False
    pincel.draw_num(encoder.value)
    blue_led.sm2.active(1)
    timeout = t_out_reset
    v0 = encoder.value

def menu_show():
    timeout = 5
    encoder = Encoder(encoder_dt_pin, encoder_clk_pin,menu_enabler=0, loop_enabler=0,value=0, v_max=30)
    while True:
        if encoder.value < 20:
            pincel.draw_num(int(parameters['volume_total']/1000),text='Volume total:',unit='L')
        elif encoder.value == 20:
            oled_print(['Override Volume','Total?'],[0,5],[0,10])
        elif encoder.value == 30:
            oled_print(['Reiniciar', 'Volume Total?'],[0,5],[0,10])

        if encoder_sw.value() == 0:
            if encoder.value < 20:
                sleep(0.5)
                return
            elif encoder.value == 20:
                sleep(0.2)
                menu_change('volume_total',v_max=10000,unit='L', step=10, mult=1000)
                oled_print(['Alterado!'],[12],[10])
                sleep(0.5)
                return
            elif encoder.value == 30:
                sleep(0.2)
                replace_parameter('volume_total',0)
                oled_print(['Reiniciado!'],[12],[10])
                sleep(0.5)
                return

        if timeout <= 0:
            sleep(0.5)
            return
        else:
            sleep(0.02)
            timeout -= 0.02

def menu_change(param,v_max=parameters['volume_max'],confirmation='Volume alterado',unit='mL',step=0,mult=1):
    timeout = parameters["timeout"]
    encoder = Encoder(encoder_dt_pin, encoder_clk_pin, menu_enabler=0, loop_enabler=0, value=int(parameters[param]/mult),
                      v_max=v_max, override_step=step)
    while True:
        pincel.draw_num(encoder.value, text='Novo valor:',unit=unit)
        if encoder_sw.value() == 0:
            pincel.draw_num(encoder.value, text=confirmation, unit=unit)
            replace_parameter(param,encoder.value*mult)
            sleep(2)
            return
        sleep(0.02)
        if timeout > 0:
            timeout -= 0.02
        else:
            standby()

def menu_default():
    oled_print(['Restaurando',' padroes'],[0,0],[0,10])
    for key in default:
        replace_parameter(key,default[key])
    oled_print(['Restaurado!!!'],[12],[10])
    sleep(1)
    return

def main_menu():
    timeout = parameters["timeout"]
    encoder = Encoder(encoder_dt_pin, encoder_clk_pin, menu_enabler=0, loop_enabler=1, value=0, v_max=60)
    while True:
        oled_print(menu[encoder.value],[0,0],[0,10])
        if encoder_sw.value() == 0:
            if encoder.value == 0:    #Exibir volume
                sleep(0.2)
                menu_show()
                encoder = Encoder(encoder_dt_pin, encoder_clk_pin, menu_enabler=0, loop_enabler=1, value=0, v_max=60)
            elif encoder.value == 10: #Ajustar volume inicial
                sleep(0.2)
                menu_change('volume_base')
                encoder = Encoder(encoder_dt_pin, encoder_clk_pin, menu_enabler=0, loop_enabler=1, value=10, v_max=60)
            elif encoder.value == 20: #Ajustar volume máximo
                sleep(0.2)
                menu_change('volume_max',v_max=10000)
                encoder = Encoder(encoder_dt_pin, encoder_clk_pin, menu_enabler=0, loop_enabler=1, value=20, v_max=60)
            elif encoder.value == 30: #Ajustar fast fill
                sleep(0.2)
                menu_change('volume_fast_fill',v_max=parameters['volume_max'])
                encoder = Encoder(encoder_dt_pin, encoder_clk_pin, menu_enabler=0, loop_enabler=1, value=30, v_max=60)
            elif encoder.value == 40: #Ajustar timeout
                sleep(0.2)
                menu_change('timeout',confirmation='Tempo alterado:',unit='s',step=5)
                encoder = Encoder(encoder_dt_pin, encoder_clk_pin, menu_enabler=0, loop_enabler=1, value=40, v_max=60)
            elif encoder.value == 50: #Restaurar Padrões
                sleep(0.2)
                menu_default()
            elif encoder.value == 60: #Retornar
                sleep(0.5)
                return

        sleep(0.02)
        if timeout > 0:
            timeout -= 0.02
        else:
            standby()


# Main Loop
while True:
    if standby_flag == False:
        if encoder.value == "Menu":
            oled_print(['Menu'],[0],[0])
        else:
            pincel.draw_num(encoder.value)

    if encoder.value != v0:
        if standby_flag == False:
            v0 = encoder.value
            timeout = parameters["timeout"]
        else:
            wakeup()

    if encoder_sw.value() == 0:
        if standby_flag == True:
            wakeup()
        elif encoder.value == "Menu":
            encoder = None
            sleep(0.2)
            main_menu()
            encoder = Encoder(encoder_dt_pin, encoder_clk_pin, 1, value = parameters['volume_base'])
        else:
            sensor = Sensor(sensor_pin, encoder.value, -1)
            start_flow()
            sensor = None
        timeout = parameters["timeout"]

    if blue_button.value() == 1:
        if standby_flag == True:
            wakeup()
        sensor = Sensor(sensor_pin, parameters["volume_fast_fill"], -1)
        start_flow()
        sensor = None
        timeout = parameters["timeout"]

    sleep(0.02)
    if timeout > 0:
        timeout -= 0.02
    else:
        standby()
