import time
import network
import ufirebase as firebase
from machine import Pin, PWM, SoftI2C, Timer, reset
import onewire, ds18x20
from ssd1306 import SSD1306_I2C

# Wi-Fi credentials
SSID = 'Print3d'
PASSWORD = 'Print3dbolivia1'

# Firebase URL
firebase.setURL("https://enclosure-63e1c-default-rtdb.firebaseio.com/")

# Function to connect to Wi-Fi with timeout
def connect_wifi(ssid, password, timeout=10):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to network...')
        wlan.connect(ssid, password)
        start_time = time.time()
        while not wlan.isconnected():
            if time.time() - start_time > timeout:
                print('Connection timed out')
                return False, None
            time.sleep(1)
    if wlan.isconnected():
        print('Network config:', wlan.ifconfig())
        return True, wlan.ifconfig()[0]
    else:
        return False, None

# Initialize peripherals
i2c = SoftI2C(scl=Pin(25), sda=Pin(26))
oled = SSD1306_I2C(128, 64, i2c)
ds_pin = Pin(22)
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
devices = ds_sensor.scan()

# Initialize pins for rotary encoder, buttons, buzzer, and LED
re_clk = Pin(32, Pin.IN)
re_dt = Pin(35, Pin.IN)
re_switch = Pin(34, Pin.IN, Pin.PULL_UP)
start_button = Pin(2, Pin.IN, Pin.PULL_DOWN)
stop_button = Pin(4, Pin.IN, Pin.PULL_DOWN)
alert_buzzer = Pin(13)
buzzer_pwm = PWM(alert_buzzer)
buzzer_pwm.duty(0)
alert_led = Pin(12, Pin.OUT)
relay_pin = Pin(23, Pin.OUT)
relay_pin.on()  # Ensure relay is initially off

# Flags and variables
setpoint = 35.0  # Initial setpoint value
last_setpoint = setpoint
clk_last = re_clk.value()
modifiable = False
control_started = False  # Initial control value
debounce_time = 200
last_press_start = 0
last_press_stop = 0
last_press_switch = 0
last_temperature = None
wifi_connected = False

# Function to read temperature
def read_temperature():
    ds_sensor.convert_temp()
    for device in devices:
        temperature = ds_sensor.read_temp(device)
        return temperature

# Function to send data to Firebase
def send_to_firebase(path, data):
    if wifi_connected:
        try:
            firebase.put(path, data, bg=0)
        except OSError as e:
            print(f"Failed to send data to Firebase: {e}")

# Function to read individual values from Firebase and update variables
def read_individual_from_firebase():
    global setpoint, control_started, wifi_connected
    if wifi_connected:
        try:
            firebase.get("fan_test", "firebase_fan_test", bg=0)
            firebase.get("setpoint", "firebase_setpoint", bg=0)
            firebase.get("control", "firebase_control", bg=0)
            firebase.get("stop", "firebase_stop", bg=0)

            # Update variables with values from Firebase
            if "firebase_setpoint" in firebase.__dict__:
                setpoint = firebase.firebase_setpoint.get("setpoint", setpoint)
            if "firebase_control" in firebase.__dict__:
                control_started = firebase.firebase_control.get("control", control_started)
            if "firebase_fan_test" in firebase.__dict__ and not control_started:
                relay_pin.value(not firebase.firebase_fan_test.get("fan_test", False))  # Control relay based on fan_test value
            if "firebase_stop" in firebase.__dict__:
                stop_value = firebase.firebase_stop.get("stop", False)
                print("stop:", stop_value)
                if stop_value == True:
                    reset()

            print("fan_test:", firebase.firebase_fan_test.get("fan_test", False))
            print("setpoint:", setpoint)
            print("control:", control_started)
        except OSError as e:
            print(f"Failed to read data from Firebase: {e}")

# Function to play a tone on the buzzer
def play_tone(frequency, duration):
    buzzer_pwm.freq(frequency)
    buzzer_pwm.duty(50)
    time.sleep_ms(duration)
    buzzer_pwm.duty(0)
    time.sleep_ms(20)

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

# Display initial big text
display_big_text("PRINT3D")
time.sleep(2)

# Attempt to connect to Wi-Fi
wifi_connected, ip_address = connect_wifi(SSID, PASSWORD)

# Print the IP address if connected and send initial values to Firebase
if wifi_connected:
    print(f'Connect to the ESP32 at http://{ip_address}')

    # Send initial values to Firebase
    send_to_firebase("setpoint", {"setpoint": 35})
    send_to_firebase("fan_test", {"fan_test": False})
    send_to_firebase("control", {"control": False})
    send_to_firebase("stop", {"stop": False})

# Rotary encoder callback
def rotary_callback(pin):
    global setpoint, clk_last
    clk_state = re_clk.value()
    dt_state = re_dt.value()
    if clk_state != clk_last:
        if modifiable:  # Only modify setpoint if modifiable is True
            if dt_state != clk_state:
                setpoint += 0.5
            else:
                setpoint -= 0.5
            setpoint = max(35.0, min(setpoint, 55.0))
            print("Setpoint:", setpoint)
        clk_last = clk_state

# Switch button callback
def switch_callback(pin):
    global modifiable, last_press_switch, last_setpoint
    current_time = time.ticks_ms()
    if (current_time - last_press_switch) > debounce_time:
        alert_led.on()
        play_tone(1000, 200)
        alert_led.off()
        print("Switch pressed")
        modifiable = not modifiable
        if not modifiable and setpoint != last_setpoint:
            send_to_firebase("setpoint", {"setpoint": setpoint})
            last_setpoint = setpoint
        last_press_switch = current_time

# Start button callback
def start_callback(pin):
    global last_press_start, control_started
    current_time = time.ticks_ms()
    if (current_time - last_press_start) > debounce_time:
        alert_led.on()
        play_tone(2000, 200)
        alert_led.off()
        print("Start")
        control_started = True
        send_to_firebase("control", {"control": True})  # Update control value in Firebase
        last_press_start = current_time

# Stop button callback
def stop_callback(pin):
    global last_press_stop, control_started
    current_time = time.ticks_ms()
    if (current_time - last_press_stop) > debounce_time:
        alert_led.on()
        play_tone(200, 200)
        alert_led.off()
        print("Stop")
        control_started = False
        send_to_firebase("control", {"control": False})  # Update control value in Firebase
        last_press_stop = current_time

# Timer-based button checking for start and stop buttons
button_timer = Timer(0)

def button_check(timer):
    if start_button.value() == 1:
        start_callback(start_button)
    if stop_button.value() == 1:
        stop_callback(stop_button)
    if re_switch.value() == 0:
        switch_callback(re_switch)

button_timer.init(period=50, mode=Timer.PERIODIC, callback=button_check)

# Attach interrupt to CLK pin for rotary encoder
re_clk.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=rotary_callback)

# Display waiting screen
def display_waiting_screen():
    oled.fill(0)
    oled.text("Waiting for", 0, 10)
    oled.text("start...", 0, 20)
    temperature = read_temperature()
    temperature_text = "T[C]: {:.2f}".format(temperature)
    text_width = len(temperature_text) * 8
    x_position = (128 - text_width) // 2
    oled.text(temperature_text, x_position, 40)
    if wifi_connected:
        display_check_symbol()
    else:
        display_question_symbol()
    oled.show()
    relay_pin.on()  # Ensure relay is off in the waiting screen

# Display control screen
def display_control_screen():
    oled.fill(0)
    temperature = read_temperature()
    temperature_text = "T[C]: {:.2f}".format(temperature)
    text_width = len(temperature_text) * 8
    x_position = (128 - text_width) // 2
    oled.text(temperature_text, x_position, 20)
    if modifiable:
        setpoint_text = "{:.2f}".format(setpoint)
        text_width = len(setpoint_text) * 8
        x_position = (128 - text_width) // 2
        oled.text(setpoint_text, x_position, 36)
    else:
        setpoint_text = "SP: {:.2f}".format(setpoint)
        text_width = len(setpoint_text) * 8
        x_position = (128 - text_width) // 2
        oled.text(setpoint_text, x_position, 36)
    if wifi_connected:
        display_check_symbol()
    else:
        display_question_symbol()
    oled.show()

# Timer-based function to read temperature and update Firebase
def update_database(timer):
    global last_temperature, last_setpoint
    temperature = read_temperature()
    data_changed = False

    if temperature != last_temperature:
        send_to_firebase("temperature", {"temperature": temperature})
        last_temperature = temperature
        data_changed = True

    if setpoint != last_setpoint:
        send_to_firebase("setpoint", {"setpoint": setpoint})
        last_setpoint = setpoint
        data_changed = True

    if data_changed:
        print("Database updated")

# Timer-based function to read values from Firebase
def read_database(timer):
    read_individual_from_firebase()

# Timer-based function to update OLED display
def update_display(timer):
    if control_started: 
        display_control_screen()
        temperature = read_temperature()
        if temperature > setpoint:
            relay_pin.off()
        else:
            relay_pin.on()
    else:
        display_waiting_screen()

# Initialize and start timers
database_timer = Timer(1)
read_timer = Timer(2)
display_timer = Timer(3)

database_timer.init(period=5000, mode=Timer.PERIODIC, callback=update_database)  # Update temperature and setpoint every 5 seconds
read_timer.init(period=5000, mode=Timer.PERIODIC, callback=read_database)  # Read values from Firebase every 5 seconds
display_timer.init(period=500, mode=Timer.PERIODIC, callback=update_display)  # Update display every 0.5 seconds

try:
    while True:
        time.sleep(0.01)  # Small delay to prevent watchdog timer reset
except KeyboardInterrupt:
    print("Exiting...")

