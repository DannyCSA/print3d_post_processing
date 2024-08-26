import time
import network
import ubinascii
import machine
import ufirebase as firebase
from machine import Pin, PWM, SoftI2C, SPI
from ssd1306 import SSD1306_I2C
import onewire, ds18x20
from max6675 import MAX6675
from umqtt.simple import MQTTClient

# Wi-Fi credentials
SSID = 'Print3d'
PASSWORD = 'Print3dbolivia1'

# Firebase URL
firebase.setURL("https://post-proce-default-rtdb.firebaseio.com/")

# MQTT details
MQTT_BROKER = 'test.mosquitto.org'
MQTT_PORT = 1883  # Default MQTT port
MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id())
MQTT_TOPIC_TIME = b'pp_time'
MQTT_TOPIC_HEATER_TEMP = b'pp_heater_temp'
MQTT_TOPIC_ACETONE_TEMP = b'pp_acetone_temp'
MQTT_TOPIC_STOP = b'pp_stop'
MQTT_TOPIC_SP_HEAT = b'pp_sp_heater'
MQTT_TOPIC_SP_ACETONE = b'pp_sp_acetone'

# Function to connect to Wi-Fi with timeout
def connect_wifi(ssid, password, timeout=5):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)  # Deactivate the WLAN interface
    time.sleep(1)  # Add a delay to ensure proper deactivation
    wlan.active(True)  # Activate the WLAN interface
    time.sleep(1)  # Add a longer delay to ensure proper activation
    
    if not wlan.isconnected():
        print('Connecting to network...')
        wlan.connect(ssid, password)
        start_time = time.time()
        while not wlan.isconnected():
            print('Trying to connect...')  # Debugging output
            if time.time() - start_time > timeout:
                print('Connection timed out')
                return False, None
            time.sleep(1)
    if wlan.isconnected():
        print('Network config:', wlan.ifconfig())
        return True, wlan.ifconfig()[0]
    else:
        return False, None

# Connect to MQTT broker and set up callbacks
def connect_mqtt():
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, MQTT_PORT)
    client.set_callback(mqtt_callback)
    client.connect()
    print('Connected to %s MQTT broker' % MQTT_BROKER)
    client.subscribe(MQTT_TOPIC_TIME)
    client.subscribe(MQTT_TOPIC_HEATER_TEMP)
    client.subscribe(MQTT_TOPIC_ACETONE_TEMP)
    client.subscribe(MQTT_TOPIC_STOP)
    client.subscribe(MQTT_TOPIC_SP_HEAT)
    client.subscribe(MQTT_TOPIC_SP_ACETONE)
    return client

# MQTT callback function
def mqtt_callback(topic, msg):
    global setpoint, control_started
    print((topic, msg))
    if topic == MQTT_TOPIC_SETPOINT:
        setpoint = float(msg)
    elif topic == MQTT_TOPIC_CONTROL:
        control_started = bool(int(msg))
    elif topic == MQTT_TOPIC_STOP and msg == b'true':
        reset()
    elif topic == MQTT_TOPIC_FAN_TEST:
        relay_pin.value(not bool(int(msg)))

# Function to publish data to MQTT
def publish_mqtt(client, topic, data):
    client.publish(topic, data)
    print(f'Sent {data} to {topic}')

# Initialize I2C for OLED
i2c = SoftI2C(scl=Pin(25), sda=Pin(26))
oled = SSD1306_I2C(128, 64, i2c)

# Define pin assignments for relays
cooling_relay_pin = Pin(23, Pin.OUT)
flowing_relay_pin = Pin(22, Pin.OUT)
acetone_relay_pin = Pin(27, Pin.OUT)
acetone_fan_pin = Pin(33, Pin.OUT)

# Buzzer setup
alert_buzzer_pin = Pin(2, Pin.OUT)
alert_buzzer_pwm = PWM(alert_buzzer_pin)
alert_buzzer_pwm.freq(1000)
alert_buzzer_pwm.duty(0)  # Start with duty cycle at 0

# Initialize SPI for MAX6675
spi = SPI(1, baudrate=5000000, polarity=0, phase=0, sck=Pin(16), miso=Pin(21))

# Initialize MAX6675 with SPI and Chip Select pin
cs = Pin(17, Pin.OUT)
sensor = MAX6675(spi, cs)

# Initial values and states
num_bits = 8
last_pressed_button_index_0_to_2 = 0
last_pressed_button_index_3_to_5 = 3
alert_led_state = 0
total_time = 0
countdown_running = False
cooling_time = 180
initial_temp = 25.00
counter_heater = 0
counter_max_temp = 15  # 15 = 200

# Time values and setpoints
time_durations = {
    (0, 3): 1260, (0, 4): 1440, (0, 5): 1560,
    (1, 3): 1680, (1, 4): 1740, (1, 5): 1800,
    (2, 3): 1800, (2, 4): 1920, (2, 5): 2040
}
setpoints = {0: 25.00, 1: 35.00, 2: 35.00}

counter_max_temps = {0: 5.00, 1: 15.00, 2: 15.00}

# Create a DS18X20 object for temperature sensor
ds_pin = Pin(19)
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
devices = ds_sensor.scan()

# Define system states
STATE_SELECTING_TIME = 0
STATE_ACETONE_HEATING = 1  # New state for heating acetone
STATE_RUNNING = 2
STATE_COOLING = 3
STATE_ACETONE_COOLING = 4  # New state for cooling acetone
STATE_ENDED = 5
system_state = STATE_SELECTING_TIME

# Initial states for acetone control
heater_control_running = False
acetone_control_running = False
heater_on = False
fan_on = False
heater_setpoint = 50.0  # initial setpoint temperature for heater
acetone_setpoint = 40.0  # Setpoint temperature for acetone
initial_lower_hysteresis = None
initial_upper_hysteresis = 5.0  # Initial upper hysteresis
lower_hysteresis = None
upper_hysteresis = None
heater_setpoint_reached = False
heater_setpoint_counter = 0
acetone_setpoint_reached = False

# Additional delay for initialization stability
time.sleep(0.2)  # Delay for 2 seconds to allow system to stabilize

def read_temperature_heater():
    temperature = sensor.read()
    if temperature >= 60:
        time.sleep(0.1)
        temperature = sensor.read()
        if temperature >= 60:
            time.sleep(0.1)
            temperature = sensor.read()
    return temperature

def read_ds18x20_temperature():    
    ds_sensor.convert_temp()
    for device in devices:
        temperature = ds_sensor.read_temp(device)
        return temperature

def read_buttons():
    latch_in_pin.off()
    latch_in_pin.on()
    bits_string = ""
    for i in range(num_bits):
        bit = data_in_pin.value()
        bits_string += "1" if bit == 0 else "0"
        clock_in_pin.on()
        clock_in_pin.off()
    time.sleep_ms(10)  # Debounce
    return bits_string

def get_pressed_button_index(button_states):
    """Returns the index of the last pressed button"""
    for i, state in enumerate(button_states):
        if state == '1':
            return i
    return None

# Function to display big text on the OLED
def display_big_text(text):
    oled.fill(0)
    text_width = 8 * len(text)
    x_position = (128 - text_width) // 2
    y_position = (64 - 16) // 2
    oled.text(text, x_position, y_position, 1)
    oled.show()

# Function to display a check symbol on the OLED
def display_check_symbol():
    oled.pixel(117, 15, 1)
    oled.pixel(118, 16, 1)
    oled.pixel(119, 17, 1)
    oled.pixel(120, 16, 1)
    oled.pixel(121, 15, 1)
    oled.pixel(122, 14, 1)
    oled.pixel(123, 13, 1)
    oled.pixel(124, 12, 1)
    oled.show()

# Function to display a '?' symbol on the OLED
def display_question_symbol():
    oled.text('?', 117, 10, 1)
    oled.show()

# Initialize relays to safe state
cooling_relay_pin.on()
flowing_relay_pin.on()
acetone_relay_pin.on()
acetone_fan_pin.on()

# Display initial big text
display_big_text("PRINT3D")
#time.sleep(2)

# Attempt to connect to Wi-Fi
try:
    wifi_connected, ip_address = connect_wifi(SSID, PASSWORD)
except OSError as e:
    print('Failed to connect to Wi-Fi:', e)
    wifi_connected, ip_address = False, None
    
# Print the IP address if connected and send initial values to Firebase
if wifi_connected:
    print(f'Connect to the ESP32 at http://{ip_address}')
    client = connect_mqtt()
    # Send initial values
    publish_mqtt(client, MQTT_TOPIC_TIME, str(total_time))  # Initial control value
    publish_mqtt(client, MQTT_TOPIC_HEATER_TEMP, str(read_temperature_heater()))  # Initial fan test value
    publish_mqtt(client, MQTT_TOPIC_ACETONE_TEMP, str(read_ds18x20_temperature()))  # Initial setpoint value
    publish_mqtt(client, MQTT_TOPIC_STOP, '0')  # Initial temperature value
    publish_mqtt(client, MQTT_TOPIC_SP_HEAT, str(heater_setpoint))  # Initial temperature value
    publish_mqtt(client, MQTT_TOPIC_SP_ACETONE, str(acetone_setpoint))  # Initial temperature value
else:
    client = None


# Define pin assignments for 74LS165 (button input)
latch_in_pin = Pin(4, Pin.OUT)
clock_in_pin = Pin(5, Pin.OUT)
data_in_pin = Pin(18, Pin.IN)

# Define pin assignments for 74HC595 (LED output)
latch_out_pin = Pin(14, Pin.OUT)
clock_out_pin = Pin(12, Pin.OUT)
data_out_pin = Pin(13, Pin.OUT)

def shift_out_leds(bits):
    """Shift out LED states to the 74HC595 shift register"""
    latch_out_pin.off()
    for bit in bits:
        data_out_pin.value(int(bit))
        clock_out_pin.on()
        clock_out_pin.off()
    latch_out_pin.on()

def update_alert_state():
    global alert_led_state
    if total_time == 0 and countdown_running:
        alert_led_state = 1
    else:
        alert_led_state = 0

def set_setpoint(index):
    global acetone_setpoint
    if index in setpoints:
        acetone_setpoint = setpoints[index]
        print("Setpoint:", acetone_setpoint)
        counter_max_temp = counter_max_temps[index]
        print("Max counter:", counter_max_temp)
        if client:
            publish_mqtt(client, MQTT_TOPIC_SP_ACETONE, str(acetone_setpoint))  # Initial temperature value

def update_button_indices(pressed_button_index):
    global last_pressed_button_index_0_to_2, last_pressed_button_index_3_to_5
    global total_time, countdown_running, system_state
    if pressed_button_index is not None:
        print(f"Pressed button index: {pressed_button_index}")  # Debugging output
        if pressed_button_index == 7:
            reset_countdown()
            play_tone(200, 200)
            total_time = 0
            update_display()
            ountdown_running = False
            heater_setpoint_reached = False
            heater_setpoint_reached_again = False
            acetone_setpoint_reached = False
            heater_setpoint = 50.0  # initial setpoint temperature for heater
            system_state = STATE_SELECTING_TIME
            if client:
                publish_mqtt(client, MQTT_TOPIC_HEATER_TEMP, str(heater_setpoint))  # Initial fan test value
            return
        if system_state == STATE_SELECTING_TIME:  # Only process other buttons in SELECTING_TIME state
            if pressed_button_index == 6:
                play_tone(1000, 200)
                system_state = STATE_ACETONE_HEATING  # Start with heating acetone
                return  # Exit after changing the state to prevent further checks
            if pressed_button_index in range(0, 3):
                last_pressed_button_index_0_to_2 = pressed_button_index
                set_setpoint(last_pressed_button_index_0_to_2)
            elif pressed_button_index in range(3, 6):
                last_pressed_button_index_3_to_5 = pressed_button_index
            key = (last_pressed_button_index_0_to_2, last_pressed_button_index_3_to_5)
            if key in time_durations:
                total_time = time_durations[key]
                if client:
                    publish_mqtt(client, MQTT_TOPIC_TIME, str(total_time))  # Initial control value
                update_display()
                system_state = STATE_SELECTING_TIME

def update_display():
    global total_time, countdown_running, system_state, client
    oled.fill(0)
    if countdown_running and total_time > 1:
        total_time -= 1
        if client:
            publish_mqtt(client, MQTT_TOPIC_TIME, str(total_time))  # Initial control value
        
        
    if total_time == 1 and countdown_running:
        system_state = STATE_ACETONE_COOLING
    if system_state == STATE_ACETONE_HEATING:
        ambient_temperature = read_ds18x20_temperature()
        current_heater_temperature = read_temperature_heater()
        oled.text("Heating acetone:", 10, 10, 1)
        oled.text(f"T[C]: {ambient_temperature:.2f}", 10, 25, 1)
        oled.text(f"SP: {initial_temp}", 10, 35, 1)
        oled.text(f"H-T[C]: {current_heater_temperature:.2f}", 10, 45, 1)
    elif system_state == STATE_ACETONE_COOLING:
        ambient_temperature = read_ds18x20_temperature()
        current_heater_temperature = read_temperature_heater()
        oled.text("Cooling acetone:", 10, 10, 1)
        oled.text(f"T[C]: {ambient_temperature:.2f}", 10, 25, 1)
        oled.text(f"SP: {initial_temp:.2f}", 10, 35, 1)
        oled.text(f"H-T[C]: {current_heater_temperature:.2f}", 10, 45, 1)
    elif system_state == STATE_ENDED:
        oled.text("Process", 25, 25, 1)
        oled.text("ended", 45, 35, 1)
    elif system_state == STATE_SELECTING_TIME:
        display_total_time()
        system_state = STATE_SELECTING_TIME
    else:    
        if total_time <= cooling_time and countdown_running:
            display_cooling_time()
            system_state = STATE_COOLING
        elif total_time > cooling_time and countdown_running:
            display_remaining_time()
            system_state = STATE_RUNNING
        
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        display_check_symbol()
    else:
        display_question_symbol()
        client = None
        
    if client:
        publish_mqtt(client, MQTT_TOPIC_HEATER_TEMP, str(read_temperature_heater()))  # Initial fan test value
        publish_mqtt(client, MQTT_TOPIC_ACETONE_TEMP, str(read_ds18x20_temperature()))  # Initial setpoint value
        publish_mqtt(client, MQTT_TOPIC_SP_HEAT, str(heater_setpoint))  # Initial temperature value
    oled.show()
    print(f"System state: {system_state}, Total time: {total_time}, Countdown running: {countdown_running}")  # Debugging output

def display_cooling_time():
    minutes = total_time // 60
    seconds = total_time % 60
    time_str = "{:02d}:{:02d}".format(minutes, seconds)
    oled.fill(0)  # Clear the display
    oled.text("Cooling heater:", 10, 0, 1)
    oled.text(time_str, 10, 10, 1)
    current_temp = read_ds18x20_temperature()
    current_heater_temperature = read_temperature_heater()
    oled.text(f"T[C]: {current_temp:.2f}", 10, 30, 1)
    oled.text(f"SP: {initial_temp}", 10, 40, 1)
    oled.text(f"H-T[C]: {current_heater_temperature:.2f}", 10, 50, 1)
    oled.show()

def display_remaining_time():
    minutes = total_time // 60
    seconds = total_time % 60
    time_str = "{:02d}:{:02d}".format(minutes, seconds)
    oled.fill(0)  # Clear the display
    oled.text("Remaining:", 10, 0, 1)
    oled.text(time_str, 10, 10, 1)
    current_temp = read_ds18x20_temperature()
    current_heater_temperature = read_temperature_heater()
    oled.text(f"T[C]: {current_temp:.2f}", 10, 30, 1)
    oled.text(f"SP: {acetone_setpoint}", 10, 40, 1)
    oled.text(f"H-T[C]: {current_heater_temperature:.2f}", 10, 50, 1)
    oled.show()

def display_total_time():
    minutes = total_time // 60
    seconds = total_time % 60
    time_str = "{:02d}:{:02d}".format(minutes, seconds)
    oled.fill(0)  # Clear the display
    oled.text("Total time:", 10, 10, 1)
    oled.text(time_str, 10, 20, 1)
    current_temp = read_ds18x20_temperature()
    current_heater_temperature = read_temperature_heater()
    oled.text(f"T[C]: {current_temp:.2f}", 10, 30, 1)
    oled.text(f"SP: {acetone_setpoint}", 10, 40, 1)
    oled.text(f"H-T[C]: {current_heater_temperature:.2f}", 10, 50, 1)
    oled.show()

def adaptive_hysteresis_control(heater_temperature):
    global heater_on, fan_on, lower_hysteresis, upper_hysteresis, heater_setpoint, heater_setpoint_reached, heater_setpoint_counter
    if heater_setpoint_reached == False and heater_temperature > heater_setpoint:
        heater_setpoint_counter += 1
        heater_setpoint += 10
        if heater_setpoint_counter >= counter_max_temp:
            heater_setpoint_reached = True
    if heater_setpoint_reached:
        error = abs(heater_setpoint - heater_temperature)
        if heater_temperature <= heater_setpoint:
            lower_hysteresis = max(1.0, initial_lower_hysteresis * (error / 100))  # Adaptive lower hysteresis
        elif heater_temperature >= heater_setpoint:
            upper_hysteresis = max(1.0, initial_upper_hysteresis * (error / 100))  # Adaptive upper hysteresis
    lower_threshold = heater_setpoint - lower_hysteresis
    upper_threshold = heater_setpoint + upper_hysteresis
    if heater_temperature <= lower_threshold:
        heater_on = True
        acetone_relay_pin.off()
        acetone_fan_pin.on()
    elif heater_temperature > lower_threshold and heater_temperature < upper_threshold:
        acetone_relay_pin.on()
        acetone_fan_pin.on()
    elif heater_temperature >= upper_threshold:
        heater_on = False
        acetone_relay_pin.on()
        acetone_fan_pin.off()
    return lower_hysteresis, upper_hysteresis

def heater_control_system(acetone_input):
    global heater_on, fan_on, initial_temp, initial_lower_hysteresis, lower_hysteresis, upper_hysteresis
    # Read temperatures
    heater_temperature = read_temperature_heater()
    if acetone_input:
        lower_hysteresis, upper_hysteresis = adaptive_hysteresis_control(heater_temperature)
    else:
        heater_on = False
        fan_on = False
        acetone_relay_pin.on()
        acetone_fan_pin.on()

def acetone_control_system(control_input):
    global heater_on, fan_on, initial_temp, initial_lower_hysteresis, lower_hysteresis, upper_hysteresis
    # Read temperatures
    heater_temperature = read_temperature_heater()
    ambient_temperature = read_ds18x20_temperature()
    if control_input:# Simple ON/OFF control for acetone temperature
        if ambient_temperature < acetone_setpoint:
            heater_control_system(True)  # Turn on heater control system
        elif ambient_temperature >= acetone_setpoint:
            heater_control_system(False)  # Turn off heater control system
    else:
        acetone_relay_pin.on()
        acetone_fan_pin.on()
        heater_on = False
        fan_on = False

def control_relays():
    global total_time, system_state, acetone_setpoint, heater_on, fan_on, initial_temp, initial_lower_hysteresis, lower_hysteresis, upper_hysteresis, acetone_setpoint_reached
    ambient_temperature = read_ds18x20_temperature()
    heater_temperature = read_temperature_heater()
    if system_state == STATE_ACETONE_HEATING:
        acetone_control_system(True)
        if ambient_temperature >= initial_temp:
            acetone_setpoint_reached = True
            system_state = STATE_RUNNING
            start_countdown()
    elif system_state == STATE_RUNNING:
        flowing_relay_pin.off()
        cooling_relay_pin.on()
        acetone_control_system(True)  # Integrate the acetone control system
        print("System state: RUNNING, Temperature:", ambient_temperature, "Setpoint:", acetone_setpoint)  # Debugging output
    elif system_state == STATE_COOLING:
        acetone_control_system(False)  # Integrate the acetone control system
        flowing_relay_pin.off()
        cooling_relay_pin.off()
        acetone_relay_pin.on()            
        if ambient_temperature > initial_temp:
            acetone_fan_pin.off()            
        else:
            acetone_fan_pin.on()            
        print("System state: COOLING, Temperature:", ambient_temperature, "Setpoint:", acetone_setpoint)  # Debugging output
    elif system_state == STATE_ACETONE_COOLING:
        acetone_control_system(False)  # Integrate the acetone control system
        flowing_relay_pin.off()
        cooling_relay_pin.off()
        acetone_relay_pin.on()
        if ambient_temperature > initial_temp:
            acetone_fan_pin.off()            
        else:
            acetone_fan_pin.on()
            cooling_relay_pin.on()
            total_time = 0
            system_state = STATE_ENDED
    else:
        flowing_relay_pin.on()
        cooling_relay_pin.on()
        acetone_relay_pin.on()
        heater_setpoint_reached = False
        acetone_setpoint_reached = False
        if ambient_temperature > initial_temp:
            acetone_fan_pin.off()
        else:
            acetone_fan_pin.on()
        initial_lower_hysteresis = 2
        lower_hysteresis = max(1.0, initial_lower_hysteresis)
        upper_hysteresis = max(1.0, initial_upper_hysteresis)
        print("System state: SELECTING_TIME, Temperature:", ambient_temperature, "Setpoint:", acetone_setpoint)  # Debugging output
    print("Heater Temperature: {:.2f} °C".format(heater_temperature))  # Print heater temperature
    print("Ambient Temperature: {:.2f} °C".format(ambient_temperature))  # Print ambient temperature
    print('initial_lower_hysteresis: {:.2f} °C'.format(initial_lower_hysteresis))
    print('initial_upper_hysteresis: {:.2f} °C'.format(initial_upper_hysteresis))
    print('Lower Hysteresis: {:.2f} °C'.format(lower_hysteresis))
    print('Upper Hysteresis: {:.2f} °C'.format(upper_hysteresis))
    print('Heater setpoint: {:.2f} °C'.format(heater_setpoint))

def play_tone(frequency, duration):
    alert_buzzer_pwm.freq(frequency)
    alert_buzzer_pwm.duty(50)
    print(f"Playing tone: {frequency}Hz for {duration}ms")  # Debugging output
    time.sleep_ms(duration)
    alert_buzzer_pwm.duty(0)
    print("Tone stopped")  # Debugging output
    time.sleep_ms(20)

def start_countdown():
    global countdown_running, countdown_start_time
    countdown_running = True
    countdown_start_time = time.time()
    print("Countdown started")  # Debugging output

def reset_countdown():
    global total_time, countdown_running
    total_time = 0
    countdown_running = False
    print("Countdown reset")  # Debugging output

def generate_selected_bits(alert_led_state):
    bits_list = ['0'] * num_bits
    bits_list[last_pressed_button_index_0_to_2] = '1'
    bits_list[last_pressed_button_index_3_to_5] = '1'
    if alert_led_state == 1:
        bits_list[-1] = '1'
    return ''.join(bits_list)

def main():
    global alert_led_state, total_time, countdown_running, system_state
    while True:
        button_states = read_buttons()
        pressed_button_index = get_pressed_button_index(button_states)
        alert_led_state = 0
        update_button_indices(pressed_button_index)
        update_alert_state()
        # Ensure a delay between sensor read and LED shift
        time.sleep_ms(50)
        selected_bits = generate_selected_bits(alert_led_state)
        shift_out_leds(selected_bits)
        update_display()
        control_relays()
        if total_time == 0 and countdown_running:
            while True:
                update_display()
                alert_buzzer_pwm.duty(512)
                selected_bits_l = list(selected_bits)
                selected_bits_l[-1] = '1'
                shift_out_leds(''.join(selected_bits_l))
                time.sleep(0.5)
                alert_buzzer_pwm.duty(0)
                selected_bits_l[-1] = '0'
                shift_out_leds(''.join(selected_bits_l))
                time.sleep(0.5)
                if read_buttons()[7] == '1':
                    countdown_running = False
                    heater_setpoint_reached = False
                    heater_setpoint_reached_again = False
                    acetone_setpoint_reached = False
                    heater_setpoint = 50.0  # initial setpoint temperature for heater
                    system_state = STATE_SELECTING_TIME
                    if client:
                        publish_mqtt(client, MQTT_TOPIC_HEATER_TEMP, str(heater_setpoint))  # Initial fan test value
                    break
        time.sleep(0.5)

main()

