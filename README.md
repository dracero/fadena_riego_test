# Sistema de Riego IoT — ESP32-S3 + HiveMQ Cloud + Astro

Proyecto de monitoreo de temperatura/humedad (DHT22) y control remoto de riego por MQTT (HiveMQ Cloud con TLS) usando MicroPython en un **ESP32-S3 N16R8** y un panel web en **Astro** (`riego-web/`).

## Estructura del proyecto

- `esp32-temp.py`: código MicroPython para el ESP32-S3 (lee credenciales desde `.env`).
- `.env.example`: plantilla de variables de entorno para el ESP32.
- `riego-web/`: aplicación web en Astro para visualizar lecturas y enviar comandos (`regar`, `no_regar`, `reset`).
- `riego-web/.env.example`: plantilla de variables de entorno para la app web.

---

## 1. Requisitos previos (Linux / Ubuntu)

1. Instalar `esptool` y `mpremote` (por ejemplo con `uv` o `pipx`):
   ```bash
   uv tool install esptool
   uv tool install mpremote
   ```
2. Dar permisos de acceso al puerto serie USB (una sola vez; luego cerrar sesión y volver a entrar):
   ```bash
   sudo usermod -aG dialout $USER
   ```
3. Conectar el ESP32-S3 por USB y verificar el puerto asignado (normalmente `/dev/ttyACM0` o `/dev/ttyUSB0`):
   ```bash
   ls /dev/ttyACM* /dev/ttyUSB*
   ```

---

## 2. Flashear MicroPython (solo la primera vez)

Si la placa todavía no tiene MicroPython (se requiere **v1.23+** con soporte `tls`, recomendado `ESP32_GENERIC_S3-SPIRAM_OCT` para el modelo N16R8):

1. Descargá el `.bin` `SPIRAM_OCT` desde https://micropython.org/download/ESP32_GENERIC_S3/
2. Si hace falta entrar manualmente en modo bootloader, mantené apretado **BOOT**, tocá **RST** y soltá **BOOT**.
3. Borrá la flash y grabá el firmware:
   ```bash
   esptool --chip esp32s3 --port /dev/ttyACM0 erase-flash
   esptool --chip esp32s3 --port /dev/ttyACM0 --baud 460800 write-flash -z 0 ESP32_GENERIC_S3-SPIRAM_OCT-*.bin
   ```
4. Presioná **RST** en la placa e instalá la librería `umqtt.simple`:
   ```bash
   mpremote connect /dev/ttyACM0 mip install umqtt.simple
   ```

---

## 3. Configurar y subir el `.env` al ESP32-S3

`esp32-temp.py` no tiene claves hardcodeadas: al iniciar, ejecuta `load_env()` y lee el archivo `.env` guardado en la memoria flash del ESP32.

### Paso 1: Crear tu `.env` local
Copiá la plantilla y completá tus datos reales de Wi-Fi y HiveMQ Cloud:
```bash
cp .env.example .env
```
Contenido esperado de `.env`:
```env
WIFI_SSID=tu_red_wifi
WIFI_PASSWORD=tu_password_wifi

MQTT_BROKER=tu-cluster.s1.eu.hivemq.cloud
MQTT_PORT=8883
MQTT_USER=tu_usuario_mqtt
MQTT_PASS=tu_password_mqtt
CLIENT_ID=fadena_id_riego
```
> **Nota:** no uses espacios alrededor del `=`. Si un valor tiene espacios (por ejemplo el nombre de tu Wi-Fi), podés dejarlo tal cual o entre comillas (`"Mi WiFi"`).

### Paso 2: Subir `.env` y el programa al ESP32
El prefijo `:` en `mpremote` indica la raíz de la memoria flash del ESP32. Subí ambos archivos:
```bash
mpremote connect /dev/ttyACM0 cp .env :.env
mpremote connect /dev/ttyACM0 cp esp32-temp.py :main.py
```

### Paso 3: Verificar que quedaron en el ESP32
Podés listar los archivos internos de la placa para confirmar que `:.env` y `:main.py` están presentes:
```bash
mpremote connect /dev/ttyACM0 ls
```
Deberías ver `boot.py`, `lib/`, `.env` y `main.py`.

### Paso 4: Reiniciar y ver los logs
Reiniciá la placa para que arranque `main.py` con el nuevo `.env` y abrí la consola serie para confirmar la conexión a Wi-Fi y MQTT:
```bash
mpremote connect /dev/ttyACM0 reset
mpremote connect /dev/ttyACM0 repl
```
*(Para salir del `repl`, presioná `Ctrl + ]` o `Ctrl + X`).*

---

## 4. App web en Astro (`riego-web`)

1. Copiá el `.env.example` de la web y completá las mismas credenciales de HiveMQ Cloud (usando `wss://` en el puerto `8884`):
   ```bash
   cd riego-web
   cp .env.example .env
   ```
2. Instalá dependencias y levantá el servidor de desarrollo:
   ```bash
   npm install
   npm run dev
   ```

