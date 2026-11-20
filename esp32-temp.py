"""
ESP32 + DHT22 - Código actualizado para el sistema de riego IoT.

Este código se ejecuta en un ESP32 con MicroPython y:
1. Lee temperatura y humedad del sensor DHT22
2. Publica datos al broker MQTT (HiveMQ Cloud)
3. Recibe comandos de riego ('regar', 'no_regar', 'reset')
"""

import network
import time
from machine import Pin
import dht
import ujson
from umqtt.simple import MQTTClient

def load_env(path=".env"):
    """Load key=value pairs from a .env file on the device."""
    env = {}
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                env[key] = value
    except OSError:
        raise RuntimeError(f"Missing {path} file on device. Upload .env to the ESP32.")
    return env


_env = load_env()

# ============================================================================
# CONFIGURATION
# ============================================================================
WIFI_SSID     = _env["WIFI_SSID"]
WIFI_PASSWORD = _env["WIFI_PASSWORD"]

MQTT_BROKER = _env["MQTT_BROKER"]
MQTT_PORT   = int(_env.get("MQTT_PORT", "8883"))
MQTT_USER   = _env["MQTT_USER"]
MQTT_PASS   = _env["MQTT_PASS"]
CLIENT_ID   = _env.get("CLIENT_ID", "fadena_id_riego")

TOPIC_SUB = b"fadena/riego/cmd"
TOPIC_PUB = b"fadena/riego/estado"
DHT_PIN   = 15
RELAY_PIN = 2

# ============================================================================
# SETUP
# ============================================================================
led = Pin(RELAY_PIN, Pin.OUT)
led.value(0)

irrigation_active = False


def connect_wifi():
    """Connect to WiFi network."""
    print("Connecting to Wi-Fi...", end="")
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect(WIFI_SSID, WIFI_PASSWORD)

    timeout = 100
    while not sta_if.isconnected() and timeout > 0:
        print(".", end="")
        time.sleep(0.1)
        timeout -= 1

    if sta_if.isconnected():
        print(" Connected!")
        print("Network config:", sta_if.ifconfig())
        return True
    else:
        print(" Failed to connect!")
        return False


def sub_cb(topic, msg):
    """
    Callback for received MQTT messages.

    Handles commands:
    - 'regar'   : Start irrigation (activate relay/pump)
    - 'no_regar': Stop irrigation (deactivate relay/pump)
    - 'reset'   : Reset the ESP32
    """
    global irrigation_active

    print(f"Received: topic={topic}, msg={msg}")

    if topic == TOPIC_SUB:
        if msg == b'reset':
            print('Resetting ESP32...')
            import machine
            machine.reset()

        elif msg == b'regar':
            print('IRRIGATION STARTED!')
            led.value(1)
            irrigation_active = True

        elif msg == b'no_regar':
            print('IRRIGATION STOPPED')
            led.value(0)
            irrigation_active = False

        else:
            print(f'Unknown command: {msg}')


def connect_mqtt():
    """Connect to MQTT broker with TLS and subscribe to command topic."""
    print("Connecting to MQTT Broker...", end="")

    ssl_params = {
        "server_hostname": MQTT_BROKER
    }

    client = MQTTClient(
        CLIENT_ID,
        MQTT_BROKER,
        MQTT_PORT,
        user=MQTT_USER,
        password=MQTT_PASS,
        ssl=True,
        ssl_params=ssl_params
    )
    client.set_callback(sub_cb)

    try:
        client.connect()
        client.subscribe(TOPIC_SUB, qos=0)
        print(" Connected!")
        print(f"Subscribed to: {TOPIC_SUB}")
        return client
    except Exception as e:
        print(f" Failed: {e}")
        return None


def main():
    """Main application loop."""
    global irrigation_active

    if not connect_wifi():
        print("WiFi connection failed. Retrying in 5 seconds...")
        time.sleep(5)
        return main()

    client = connect_mqtt()
    if client is None:
        print("MQTT connection failed. Retrying in 5 seconds...")
        time.sleep(5)
        return main()

    sensor = dht.DHT22(Pin(DHT_PIN))

    print("\n" + "="*50)
    print("ESP32 IoT Irrigation System Ready!")
    print("="*50)
    print(f"Publishing to : {TOPIC_PUB}")
    print(f"Listening on  : {TOPIC_SUB}")
    print("Commands: 'regar', 'no_regar', 'reset'")
    print("="*50 + "\n")

    last_publish     = 0
    publish_interval = 10

    while True:
        try:
            client.check_msg()

            current_time = time.time()

            if current_time - last_publish >= publish_interval:
                sensor.measure()
                temp = sensor.temperature()
                hum  = sensor.humidity()

                msg = ujson.dumps({
                    "temp"             : temp,
                    "humidity"         : hum,
                    "client_id"        : CLIENT_ID,
                    "irrigation_active": irrigation_active
                })

                irrigation_status = "ACTIVE" if irrigation_active else "OFF"
                print(f"Temp: {temp}C | Humidity: {hum}% | Irrigation: {irrigation_status}")

                client.publish(TOPIC_PUB, msg, qos=0)
                last_publish = current_time

            time.sleep(0.1)

        except OSError as e:
            print(f"Error: {e}")
            print("Attempting to reconnect...")
            try:
                client = connect_mqtt()
                if client is None:
                    time.sleep(5)
            except Exception as reconnect_error:
                print(f"Reconnection failed: {reconnect_error}")
                time.sleep(5)


if __name__ == "__main__":
    main()