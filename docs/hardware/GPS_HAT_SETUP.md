# GPS HAT Setup (Adafruit Ultimate GPS HAT #2324)

EAS Station supports the [Adafruit Ultimate GPS HAT for Raspberry Pi](https://www.adafruit.com/product/2324) (product #2324) and compatible NMEA-0183 serial GPS receivers. When enabled, the GPS module provides:

- **Station coordinates** — automatic lat/lon for location-based alert filtering
- **Precision time** — PPS (Pulse Per Second) output for sub-millisecond NTP synchronization
- **Satellite status** — live fix quality, satellite count, and HDOP display in the web UI

---

## Hardware Overview

| Feature | Specification |
|---------|--------------|
| Interface | UART (serial) via /dev/serial0 |
| Default baud rate | 9600 |
| PPS output | GPIO BCM 4 |
| Fix indicator LED | 1 Hz blink when no fix; 15 s pulse with fix |
| Supported NMEA sentences | GGA, RMC, GSV |
| Update rate | 1 Hz default (configurable via PMTK commands) |

---

## Hardware Installation

1. **Power off the Raspberry Pi** before installing the HAT.
2. Align the HAT's 40-pin header with the Pi's GPIO header and press firmly.
3. Attach the included ceramic antenna to the SMA connector (or connect an external active antenna for better sky view).
4. Power on the Pi. The GPS fix LED will begin blinking at 1 Hz.

---

## Software Prerequisites

### 1. Enable UART on the Raspberry Pi

The Adafruit GPS HAT uses the primary UART (`/dev/serial0`). By default the Pi uses this port for the Linux console. You must disable the serial console and enable the UART hardware:

```bash
sudo raspi-config
```

Navigate to: **Interface Options → Serial Port**

- **Would you like a login shell to be accessible over the serial?** → **No**
- **Would you like the serial port hardware to be enabled?** → **Yes**

Reboot after making changes:

```bash
sudo reboot
```

Verify the port appears:

```bash
ls -la /dev/serial0
# Should show: /dev/serial0 -> ttyAMA0  (or ttyS0 on Pi 3/4)
```

### 2. Add user to dialout group

The EAS Station service user needs access to the serial port:

```bash
sudo usermod -aG dialout eas-station
```

### 3. Install Python dependencies

```bash
pip install pyserial pynmea2
```

---

## EAS Station Configuration

1. Navigate to **Admin → Hardware Settings → GPS**.
2. Check **Enable GPS Receiver**.
3. Set the serial port (default: `/dev/serial0`).
4. Set the baud rate (default: **9600** for Adafruit GPS HAT #2324).
5. Set the **PPS GPIO Pin** (default: **4** for Adafruit GPS HAT #2324).
6. Optionally enable:
   - **Use GPS for station location** — populates lat/lon in location settings after first fix
   - **Use GPS for time sync** — requires additional kernel module (see below)
7. Set **Minimum Satellites for Fix** (default: 4).
8. Click **Save Settings**.

The hardware service will restart the GPS reader with the new configuration. Click **Refresh** in the Live GPS Status card to see current fix data.

---

## PPS Time Synchronization (Optional)

The Adafruit GPS HAT outputs a 1 Hz PPS pulse on GPIO BCM 4. This pulse can discipline the system clock to within microseconds of UTC when combined with `gpsd` and `chrony`.

### Install required packages

```bash
sudo apt install gpsd gpsd-clients chrony
```

### Enable the pps-gpio kernel module

Add to `/boot/config.txt` (or `/boot/firmware/config.txt` on newer Pi OS):

```ini
dtoverlay=pps-gpio,gpiopin=4
```

Reboot, then verify:

```bash
ls /dev/pps0
```

### Configure gpsd

Edit `/etc/default/gpsd`:

```bash
DEVICES="/dev/serial0 /dev/pps0"
GPSD_OPTIONS="-n"
START_DAEMON="true"
```

Restart gpsd:

```bash
sudo systemctl restart gpsd
sudo systemctl enable gpsd
```

Verify gpsd can see the GPS fix:

```bash
gpsmon /dev/serial0
# or
cgps -s
```

### Configure chrony for GPS/PPS

Edit `/etc/chrony/chrony.conf`, adding:

```
# GPS via gpsd (NMEA time, low precision)
refclock SHM 0 offset 0.5 delay 0.2 refid GPS

# GPS PPS (high precision — requires NMEA fix from above)
refclock PPS /dev/pps0 lock GPS refid PPS
```

Restart chrony:

```bash
sudo systemctl restart chrony
```

Verify time sources:

```bash
chronyc sources -v
```

A `*` next to PPS indicates it is selected as the primary reference. Offset should be sub-millisecond.

---

## Verifying GPS Operation

### Live status in the web UI

**Admin → Hardware Settings → GPS → Refresh**

The status card shows:
- Fix status (No Fix / Acquiring / Fix Acquired)
- Serial port and baud rate
- Satellite count
- Latitude, longitude, altitude
- UTC time from GPS
- HDOP (horizontal dilution of precision)

### Command-line verification

```bash
# Read raw NMEA sentences
stty -F /dev/serial0 9600 raw && cat /dev/serial0

# Example output:
# $GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A
# $GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
```

A sentence starting with `$GPGGA` with a non-zero fix quality (field 6) indicates a valid fix.

### Redis status key

The hardware service publishes GPS data to Redis:

```bash
redis-cli GET gps:status | python3 -m json.tool
```

---

## Troubleshooting

### No NMEA data on serial port

- Verify `raspi-config` disabled the serial console and enabled UART hardware.
- Check for conflicting Bluetooth usage: on Pi 3/4/5, Bluetooth also uses UART. Some configurations require disabling Bluetooth to free the primary UART:
  ```bash
  # In /boot/config.txt:
  dtoverlay=disable-bt
  ```
  Then reboot and run `sudo systemctl disable hciuart`.
- Confirm the port path: `ls -la /dev/serial*`

### Fix LED blinks but no fix reported

- Move to a location with clear sky view. The first cold start can take 30–60 seconds outdoors.
- Verify the antenna is connected.
- The fix LED changes from 1 Hz blink to a slow 15-second pulse when a fix is acquired.

### PPS device not found (`/dev/pps0` missing)

- Confirm the dtoverlay line in `/boot/config.txt` and reboot.
- Verify the module is loaded: `lsmod | grep pps_gpio`
- Load manually to test: `sudo modprobe pps-gpio gpiopin=4`

### chrony not using PPS

- PPS requires an active NMEA fix (the `lock GPS` directive). Run `cgps -s` to confirm gpsd has a fix before expecting PPS to be selected.
- Check chrony sources: `chronyc sources -v`

---

## Hardware Documentation

- [Adafruit Ultimate GPS HAT product page (#2324)](https://www.adafruit.com/product/2324)
- [Adafruit GPS HAT guide](https://learn.adafruit.com/adafruit-ultimate-gps-hat-for-raspberry-pi)
- [pps-gpio kernel module](https://www.kernel.org/doc/html/latest/driver-api/pps.html)
