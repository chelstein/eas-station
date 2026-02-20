# GPIO Relay Wiring Guide

EAS Station uses GPIO-controlled relays to key transmitters, activate external equipment, and signal alert states. This guide covers physical wiring, pin assignments, configuration, and safety procedures.

---

## Overview

The GPIO relay integration is handled by the `hardware_service` (systemd unit `eas-station-hardware`). When an EAS alert is broadcast, the service closes the transmit relay to key the transmitter, and optionally activates additional relays for auxiliary equipment.

---

## Supported GPIO Configurations

EAS Station supports GPIO relay control on:

- **Raspberry Pi** (all models with 40-pin header) — via `gpiochip0`
- **Raspberry Pi with relay HAT** — waveshare, Sequent Microsystems, SB Components, and similar
- Systems with `libgpiod`-compatible GPIO chips

The software uses `libgpiod` for GPIO access, which does not require root privileges when the `eas-station` user is added to the `gpio` group.

---

## Relay HAT Wiring

A relay HAT sits directly on the Raspberry Pi's 40-pin header. Each relay on the HAT is controlled by a specific BCM GPIO pin.

### Common Relay HAT Pin Assignments

**Waveshare RPi Relay Board (3-channel):**

| Relay | BCM Pin | Physical Pin | Function |
|-------|---------|-------------|----------|
| Relay 1 | BCM 26 | Pin 37 | Transmit (TX) key |
| Relay 2 | BCM 20 | Pin 38 | Auxiliary 1 |
| Relay 3 | BCM 21 | Pin 40 | Auxiliary 2 |

**4-channel relay HAT (generic):**

| Relay | BCM Pin | Physical Pin | Common Use |
|-------|---------|-------------|------------|
| CH1 | BCM 5 | Pin 29 | TX key |
| CH2 | BCM 6 | Pin 31 | Aux power |
| CH3 | BCM 13 | Pin 33 | Alert lamp |
| CH4 | BCM 19 | Pin 35 | Spare |

!!! note "Check your specific HAT"
    Pin assignments vary between HAT manufacturers. Always consult your HAT's schematic or documentation. Some HATs are active-low (relay closes when GPIO is LOW); EAS Station supports configuring pin polarity.

---

## Transmitter Connection

The transmit relay provides a dry contact closure to key an external transmitter or control system.

### PTT (Push-to-Talk) Wiring

A relay in the transmit path replaces or augments a PTT switch:

```
EAS Station Relay (Relay 1)
│
├── COM  ──── Transmitter PTT Common (GND)
└── NO   ──── Transmitter PTT Hot (+V or signal line)
```

**Use NO (Normally Open):** The relay is open when idle and closes to transmit. This is the safe-fail state — if the relay loses power, the transmitter is not keyed.

### Contact Ratings

Match the relay contact rating to your transmitter's PTT circuit requirements:

| Specification | Requirement |
|--------------|-------------|
| Contact voltage | Typically 3.3–12V for PTT |
| Contact current | Usually <10mA for PTT logic signals |
| Relay NO rating | Must exceed your application's voltage and current |

For standard ham radio PTT circuits, any relay rated for 10V/100mA is more than adequate.

---

## Reserved GPIO Pins

The following BCM pins are reserved by the Argon HAT OLED display and must not be used for relays if an Argon HAT is installed:

```python
ARGON_OLED_RESERVED_BCM = {2, 3}   # I2C SDA/SCL for OLED
```

The hardware settings page lists reserved pins and will warn you if you configure a relay on a reserved pin.

---

## Configuration

### Via the Web Interface

1. Navigate to **Admin → Hardware Settings**.
2. Enable **GPIO Relay Control**.
3. Set the **GPIO Chip** (default: `gpiochip0`).
4. Configure the **Transmit Relay Pin** (BCM number).
5. In the **GPIO Pin Map**, assign each relay function to a BCM pin:
   ```json
   {
     "transmit": 26,
     "aux1": 20,
     "aux2": 21
   }
   ```
6. In the **GPIO Behavior Matrix**, define which relay activates for which alert severity:
   ```json
   {
     "transmit": ["Extreme", "Severe", "Moderate", "Minor"],
     "aux1": ["Extreme", "Severe"],
     "aux2": ["Extreme"]
   }
   ```
7. Click **Save Settings** and restart the hardware service.

### Via eas-config

```bash
sudo eas-config
```

Select **5. Hardware Integration → GPIO Relay Settings**.

### Via .env

```
GPIO_ENABLED=true
GPIO_CHIP=gpiochip0
GPIO_TRANSMIT_PIN=26
GPIO_AUX1_PIN=20
GPIO_AUX2_PIN=21
```

---

## GPIO Activation Log

Every relay activation and deactivation is recorded in the `gpio_activation_log` database table. View the log at **Admin → Hardware → GPIO Statistics**.

The log includes:
- Timestamp
- Relay channel
- Duration (seconds the relay was active)
- Triggering event (alert ID or manual activation)

---

## Testing GPIO Relays

### Via the Web Interface

1. Go to **Admin → Hardware Settings → GPIO Test**.
2. Click **Pulse Relay** next to each relay to test it independently.
3. You should hear the relay click and any connected equipment activate briefly.

### Via the API

```bash
# Pulse the transmit relay for 1 second
curl -X POST \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"channel": "transmit", "duration_ms": 1000}' \
  https://your-eas-station.example.com/api/hardware/gpio/pulse
```

### Via Command Line

```bash
# Test GPIO directly with gpioset (no service needed)
gpioset gpiochip0 26=1   # Close relay
sleep 1
gpioset gpiochip0 26=0   # Open relay
```

---

## Safety Procedures

!!! danger "High-voltage relay contacts"
    If your relay board is wired to mains voltage (AC power) for any reason, follow electrical safety standards and ensure all high-voltage wiring is performed by a licensed electrician. EAS Station relays are intended for low-voltage PTT and control circuits only.

### Before Making or Changing Wiring

1. **Power off** the Raspberry Pi and any connected transmitter before changing wiring.
2. **Discharge** any capacitors in the transmitter PTT circuit.
3. **Use appropriately rated wire** — 22 AWG or heavier for all relay connections.
4. **Insulate exposed terminals** — use heat shrink or terminal covers.

### Fail-Safe Configuration

Configure all relays to use **Normally Open (NO)** contacts for the transmitter:
- Transmitter is **not keyed** when power is off or the service is stopped.
- Transmitter is **not keyed** if the hardware service crashes.
- Transmitter is **keyed only** when EAS Station explicitly activates the relay.

### Preventing Stuck Relays

The hardware service enforces a maximum relay-active duration. If a broadcast exceeds the configured maximum, the relay is automatically released. Configure this limit in **Admin → Hardware Settings → Maximum Relay Duration (seconds)**.

---

## Permission Setup

The `eas-station` user needs access to `/dev/gpiochip0`:

```bash
# Add to gpio group
sudo usermod -a -G gpio eas-station

# Or create a udev rule (more reliable for non-Pi systems)
echo 'SUBSYSTEM=="gpio", GROUP="gpio", MODE="0660"' | \
  sudo tee /etc/udev/rules.d/99-gpio.rules
sudo udevadm control --reload-rules
```

Restart the hardware service after making permission changes:

```bash
sudo systemctl restart eas-station-hardware
```

---

## Troubleshooting

### "Permission denied" accessing GPIO

```bash
sudo usermod -a -G gpio eas-station
# Log out and back in, or restart the service
sudo systemctl restart eas-station-hardware
```

### Relay activates but transmitter does not key

- Verify NO vs. NC contact selection at the relay terminal.
- Check with a multimeter: with the relay in its active state, the NO contact should measure continuity.
- Confirm the transmitter PTT circuit voltage/polarity.

### Relay chatters (rapid clicking)

Usually caused by a loose connection or electrical noise on the GPIO line. Add a 0.1µF capacitor between the GPIO pin and GND at the relay driver input.

### Hardware service crashes on GPIO access

- Confirm `libgpiod2` is installed: `sudo apt-get install libgpiod2`
- Verify the GPIO chip name: `gpiodetect`
- Check for pin conflicts with other software (e.g., WiringPi, pigpio).

### GPIO Statistics page shows no activations

The `gpio_activation_log` table may not have been created yet. Run:

```bash
cd /opt/eas-station
source venv/bin/activate
alembic upgrade head
sudo systemctl restart eas-station-hardware
```
