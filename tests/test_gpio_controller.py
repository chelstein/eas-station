"""
EAS Station - Emergency Alert System
Copyright (c) 2025-2026 Timothy Kramer (KR8MER)

This file is part of EAS Station.

EAS Station is dual-licensed software:
- GNU Affero General Public License v3 (AGPL-3.0) for open-source use
- Commercial License for proprietary use

You should have received a copy of both licenses with this software.
For more information, see LICENSE and LICENSE-COMMERCIAL files.

IMPORTANT: This software cannot be rebranded or have attribution removed.
See NOTICE file for complete terms.

Repository: https://github.com/KR8MER/eas-station
"""

"""Tests for GPIO controller configuration behavior."""

import json
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app_utils.gpio as gpio

from app_utils.gpio import (
    GPIOBehavior,
    GPIOBehaviorManager,
    GPIOController,
    GPIOPinConfig,
    GPIOState,
    NeopixelConfig,
    NeopixelController,
    TowerLightConfig,
    TowerLightController,
    _NullNeopixelStrip,
    _make_neo_color,
    _TOWER_CMD_GRN_ON,
    _TOWER_CMD_GRN_OFF,
    _TOWER_CMD_RED_ON,
    _TOWER_CMD_RED_OFF,
    _TOWER_CMD_RED_BLINK,
    _TOWER_CMD_YEL_OFF,
    _TOWER_CMD_YEL_BLINK,
    _TOWER_CMD_BUZ_OFF,
    _TOWER_CMD_BUZ_ON,
    load_gpio_behavior_matrix_from_db,
    load_gpio_pin_configs_from_db,
    load_neopixel_config_from_db,
    load_tower_light_config_from_db,
    serialize_gpio_behavior_matrix,
)


def test_add_pin_records_configuration_when_gpio_unavailable():
    """Configured pins should be visible even without GPIO hardware."""

    controller = GPIOController()
    controller.add_pin(GPIOPinConfig(pin=17, name="Test Pin"))

    states = controller.get_all_states()

    assert 17 in states
    assert states[17]["name"] == "Test Pin"
    assert states[17]["state"] == GPIOState.INACTIVE.value


def test_add_pin_uses_null_backend_when_hardware_unavailable(monkeypatch):
    """Null GPIO backend should be treated as a simulated but healthy pin."""

    controller = GPIOController()
    controller._gpiozero_available = False

    monkeypatch.setattr(
        gpio,
        "_create_gpio_backend",
        lambda exclude=None: gpio._NullGPIOBackend(),
    )

    controller.add_pin(GPIOPinConfig(pin=18, name="Simulated Pin"))

    assert controller.get_state(18) == GPIOState.INACTIVE


def test_load_gpio_pin_configs_from_database(monkeypatch):
    """Database pin map should produce structured GPIO configurations."""

    # Mock the database settings to return a pin map
    pin_map = {
        "12": {"name": "EAS Transmitter PTT", "active_high": False, "hold_seconds": 2.5, "watchdog_seconds": 90},
        "22": {"name": "Aux Relay", "active_high": True, "hold_seconds": 1.5, "watchdog_seconds": 45},
        "24": {},
        "25": {"name": "Backup Relay", "active_high": False, "hold_seconds": 3, "watchdog_seconds": 180},
    }

    monkeypatch.setattr(gpio, "_GPIO_SETTINGS_AVAILABLE", True)
    monkeypatch.setattr(gpio, "get_gpio_settings", lambda: {"pin_map": pin_map, "behavior_matrix": {}})

    configs = load_gpio_pin_configs_from_db()

    assert {cfg.pin for cfg in configs} == {12, 22, 24, 25}

    primary = next(cfg for cfg in configs if cfg.pin == 12)
    assert primary.name == "EAS Transmitter PTT"
    assert primary.active_high is False
    assert primary.hold_seconds == 2.5
    assert primary.watchdog_seconds == 90

    aux = next(cfg for cfg in configs if cfg.pin == 22)
    assert aux.name == "Aux Relay"
    assert aux.active_high is True
    assert aux.watchdog_seconds == 45

    fallback = next(cfg for cfg in configs if cfg.pin == 24)
    assert fallback.name == "GPIO Pin 24"
    assert fallback.active_high is True

    override = next(cfg for cfg in configs if cfg.pin == 25)
    assert override.name == "Backup Relay"
    assert override.active_high is False


def test_reserved_oled_pins_rejected(monkeypatch, caplog):
    """Pins reserved for the OLED module should not be configurable when OLED is enabled."""

    # Mock database returning OLED-reserved pins (BCM 2, 4, 14)
    pin_map = {
        "4": {"name": "Button Override"},
        "2": {"name": "Aux", "active_high": True, "hold_seconds": 1, "watchdog_seconds": 60},
        "14": {"name": "Serial", "active_high": True, "hold_seconds": 1, "watchdog_seconds": 60},
    }

    monkeypatch.setattr(gpio, "_GPIO_SETTINGS_AVAILABLE", True)
    monkeypatch.setattr(gpio, "get_gpio_settings", lambda: {"pin_map": pin_map, "behavior_matrix": {}})

    test_logger = logging.getLogger("gpio-test")
    with caplog.at_level(logging.ERROR, logger="gpio-test"):
        configs = load_gpio_pin_configs_from_db(logger=test_logger, oled_enabled=True)

    assert configs == []
    assert any("reserved" in record.message for record in caplog.records)


def test_load_gpio_behavior_matrix_from_database(monkeypatch):
    """Database behavior matrix should deserialize to enums per pin."""

    behavior_matrix = {
        "18": ["duration_of_alert", "incoming_alert"],
        "22": "flash",
        "bad": ["unknown"],
    }

    monkeypatch.setattr(gpio, "_GPIO_SETTINGS_AVAILABLE", True)
    monkeypatch.setattr(gpio, "get_gpio_settings", lambda: {"pin_map": {}, "behavior_matrix": behavior_matrix})

    matrix = load_gpio_behavior_matrix_from_db()

    assert 18 in matrix
    assert matrix[18] == {GPIOBehavior.DURATION_OF_ALERT, GPIOBehavior.INCOMING_ALERT}
    assert 22 in matrix
    assert matrix[22] == {GPIOBehavior.FLASH}
    assert "bad" not in matrix


def test_serialize_gpio_behavior_matrix_round_trip():
    """Behavior matrix serialization should produce stable JSON."""

    matrix = {
        18: {GPIOBehavior.DURATION_OF_ALERT, GPIOBehavior.PLAYOUT},
        22: {GPIOBehavior.FLASH},
    }

    json_value = serialize_gpio_behavior_matrix(matrix)
    assert json_value

    restored = json.loads(json_value)
    assert restored == {
        "18": ["duration_of_alert", "playout"],
        "22": ["flash"],
    }


class _FakeController:
    def __init__(self):
        self.activations = []
        self.deactivations = []

    def activate(self, pin, activation_type=None, alert_id=None, reason=None):
        self.activations.append((pin, activation_type, alert_id, reason))
        return True

    def deactivate(self, pin, force=False):
        self.deactivations.append((pin, force))
        return True




def test_gpio_state_includes_output_verification(monkeypatch):
    """GPIO status should expose output verification details for UI/diagnostics."""

    controller = GPIOController()
    controller._gpiozero_available = False
    monkeypatch.setattr(
        gpio,
        "_create_gpio_backend",
        lambda exclude=None: gpio._NullGPIOBackend(),
    )

    controller.add_pin(GPIOPinConfig(pin=17, name="Verified Pin"))

    assert controller.activate(17) is True
    states = controller.get_all_states()
    verification = states[17].get("verification")

    assert verification is not None
    assert verification["verified"] is True
    assert verification["observed"] == "active"


def test_behavior_manager_flash_alternates_partner_pin():
    """Flash behavior should alternate phase across partner pins when configured."""

    controller = _FakeController()
    configs = [
        GPIOPinConfig(pin=18, name="Red", flash_enabled=True, flash_interval_ms=50, flash_partner_pin=23),
        GPIOPinConfig(pin=23, name="Amber", flash_enabled=True, flash_interval_ms=50, flash_partner_pin=18),
    ]
    manager = GPIOBehaviorManager(
        controller=controller,
        pin_configs=configs,
        behavior_matrix={18: {GPIOBehavior.FLASH}, 23: {GPIOBehavior.FLASH}},
    )

    handled = manager.start_alert(alert_id="flash", event_code="RWT")
    assert handled is True

    import time
    time.sleep(0.18)
    manager.end_alert(alert_id="flash", event_code="RWT")

    activated_pins = [call[0] for call in controller.activations]
    assert 18 in activated_pins
    assert 23 in activated_pins

def test_behavior_manager_hold_lifecycle(monkeypatch):
    """Behavior manager should activate and release pins for alert duration."""

    controller = _FakeController()
    configs = [GPIOPinConfig(pin=18, name="Alert Relay")]
    manager = GPIOBehaviorManager(
        controller=controller,
        pin_configs=configs,
        behavior_matrix={18: {GPIOBehavior.DURATION_OF_ALERT}},
    )

    handled = manager.start_alert(alert_id="test", event_code="TOR")
    assert handled is True
    assert controller.activations

    manager.end_alert(alert_id="test", event_code="TOR")
    assert controller.deactivations


def test_behavior_manager_pulse_only(monkeypatch):
    """Pulse-only behaviors should prevent fallback activation."""

    controller = _FakeController()
    configs = [GPIOPinConfig(pin=18, name="Beacon")]
    manager = GPIOBehaviorManager(
        controller=controller,
        pin_configs=configs,
        behavior_matrix={18: {GPIOBehavior.FIVE_SECONDS}},
    )

    calls = []

    def fake_pulse(**kwargs):  # pragma: no cover - simple test hook
        controller.activate(kwargs["pin"])
        controller.deactivate(kwargs["pin"], force=True)
        calls.append(kwargs["pin"])

    monkeypatch.setattr(manager, "_pulse_pin", fake_pulse)

    handled = manager.start_alert(alert_id="pulse", event_code="RWT")
    assert handled is True
    assert calls == [18]


# ---------------------------------------------------------------------------
# NeoPixel tests
# ---------------------------------------------------------------------------


def test_null_neopixel_strip_tracks_pixel_values():
    """_NullNeopixelStrip should store and return pixel colour values."""
    strip = _NullNeopixelStrip(4)
    assert strip.numPixels() == 4

    strip.setPixelColor(0, 0xFF0000)
    strip.setPixelColor(3, 0x00FF00)
    strip.show()  # no-op; must not raise

    assert strip.pixels[0] == 0xFF0000
    assert strip.pixels[1] == 0
    assert strip.pixels[3] == 0x00FF00


def test_make_neo_color_without_rpi_ws281x(monkeypatch):
    """_make_neo_color should pack RGB correctly even without the real library."""
    monkeypatch.setattr(gpio, "NeopixelColor", None)
    packed = _make_neo_color(255, 128, 0)
    assert packed == (255 << 16) | (128 << 8) | 0


def test_neopixel_controller_starts_in_null_mode(monkeypatch):
    """NeopixelController should start cleanly when rpi_ws281x is unavailable."""
    monkeypatch.setattr(gpio, "_NEOPIXEL_LIB_AVAILABLE", False)

    config = NeopixelConfig(gpio_pin=18, num_pixels=3, brightness=64)
    ctrl = NeopixelController(config)
    available = ctrl.start()

    assert available is False
    assert ctrl.is_available is False


def test_neopixel_controller_set_color(monkeypatch):
    """set_color should push the colour to every pixel."""
    monkeypatch.setattr(gpio, "_NEOPIXEL_LIB_AVAILABLE", False)

    config = NeopixelConfig(gpio_pin=18, num_pixels=4, brightness=128)
    ctrl = NeopixelController(config)
    ctrl.start()

    ctrl.set_color(10, 20, 30)
    expected = _make_neo_color(10, 20, 30)
    assert all(p == expected for p in ctrl._strip.pixels)


def test_neopixel_controller_standby_and_off(monkeypatch):
    """set_standby and off should use the configured standby colour and black."""
    monkeypatch.setattr(gpio, "_NEOPIXEL_LIB_AVAILABLE", False)

    config = NeopixelConfig(
        gpio_pin=18, num_pixels=2, brightness=128, standby_color=(0, 5, 0)
    )
    ctrl = NeopixelController(config)
    ctrl.start()

    ctrl.set_standby()
    standby_val = _make_neo_color(0, 5, 0)
    assert all(p == standby_val for p in ctrl._strip.pixels)

    ctrl.off()
    assert all(p == 0 for p in ctrl._strip.pixels)


def test_neopixel_controller_start_and_end_alert(monkeypatch):
    """start_alert should show the alert colour; end_alert restores standby."""
    monkeypatch.setattr(gpio, "_NEOPIXEL_LIB_AVAILABLE", False)

    config = NeopixelConfig(
        gpio_pin=18,
        num_pixels=2,
        brightness=128,
        standby_color=(0, 5, 0),
        alert_color=(200, 0, 0),
        flash_on_alert=False,
    )
    ctrl = NeopixelController(config)
    ctrl.start()

    ctrl.start_alert()
    alert_val = _make_neo_color(200, 0, 0)
    assert all(p == alert_val for p in ctrl._strip.pixels)

    ctrl.end_alert()
    standby_val = _make_neo_color(0, 5, 0)
    assert all(p == standby_val for p in ctrl._strip.pixels)


def test_neopixel_controller_flash_and_stop(monkeypatch):
    """Flash pattern should toggle the strip; stop_flash cleans up the thread."""
    import time

    monkeypatch.setattr(gpio, "_NEOPIXEL_LIB_AVAILABLE", False)

    config = NeopixelConfig(
        gpio_pin=18,
        num_pixels=1,
        brightness=128,
        standby_color=(0, 5, 0),
        alert_color=(200, 0, 0),
        flash_on_alert=True,
        flash_interval_ms=50,
    )
    ctrl = NeopixelController(config)
    ctrl.start()

    ctrl.start_flash(200, 0, 0)
    assert ctrl._flash_thread is not None and ctrl._flash_thread.is_alive()

    # Let at least two toggles happen
    time.sleep(0.15)

    ctrl.stop_flash()
    assert ctrl._flash_thread is None


def test_neopixel_controller_cleanup(monkeypatch):
    """cleanup should stop flash and turn the strip off."""
    monkeypatch.setattr(gpio, "_NEOPIXEL_LIB_AVAILABLE", False)

    config = NeopixelConfig(gpio_pin=18, num_pixels=2, brightness=128)
    ctrl = NeopixelController(config)
    ctrl.start()

    ctrl.start_flash(255, 0, 0)
    ctrl.cleanup()

    # Strip reference should be cleared after cleanup
    assert ctrl._strip is None
    assert ctrl._flash_thread is None


def test_neopixel_controller_get_status(monkeypatch):
    """get_status should return a dict with all expected keys."""
    monkeypatch.setattr(gpio, "_NEOPIXEL_LIB_AVAILABLE", False)

    config = NeopixelConfig(
        gpio_pin=18,
        num_pixels=5,
        brightness=100,
        led_order="RGB",
        flash_interval_ms=250,
    )
    ctrl = NeopixelController(config)
    ctrl.start()

    status = ctrl.get_status()
    assert status["gpio_pin"] == 18
    assert status["num_pixels"] == 5
    assert status["brightness"] == 100
    assert status["led_order"] == "RGB"
    assert status["flash_interval_ms"] == 250
    assert status["available"] is False
    assert status["flashing"] is False


def test_load_neopixel_config_disabled(monkeypatch):
    """load_neopixel_config_from_db should return None when disabled."""
    monkeypatch.setattr(gpio, "_GPIO_SETTINGS_AVAILABLE", True)

    fake_settings = {
        "enabled": False,
        "gpio_pin": 18,
        "num_pixels": 1,
        "brightness": 128,
        "led_order": "GRB",
        "standby_color": {"r": 0, "g": 10, "b": 0},
        "alert_color": {"r": 255, "g": 0, "b": 0},
        "flash_on_alert": True,
        "flash_interval_ms": 500,
    }

    # Patch the hardware_settings import inside gpio.py
    import types
    fake_module = types.ModuleType("app_core.hardware_settings")
    fake_module.get_neopixel_settings = lambda: fake_settings
    monkeypatch.setitem(
        __import__("sys").modules, "app_core.hardware_settings", fake_module
    )

    result = load_neopixel_config_from_db()
    assert result is None


def test_load_neopixel_config_enabled(monkeypatch):
    """load_neopixel_config_from_db should return NeopixelConfig when enabled."""
    monkeypatch.setattr(gpio, "_GPIO_SETTINGS_AVAILABLE", True)

    fake_settings = {
        "enabled": True,
        "gpio_pin": 18,
        "num_pixels": 8,
        "brightness": 200,
        "led_order": "GRB",
        "standby_color": {"r": 0, "g": 20, "b": 0},
        "alert_color": {"r": 255, "g": 50, "b": 0},
        "flash_on_alert": True,
        "flash_interval_ms": 300,
    }

    import types
    fake_module = types.ModuleType("app_core.hardware_settings")
    fake_module.get_neopixel_settings = lambda: fake_settings
    monkeypatch.setitem(
        __import__("sys").modules, "app_core.hardware_settings", fake_module
    )

    result = load_neopixel_config_from_db()
    assert result is not None
    assert result.gpio_pin == 18
    assert result.num_pixels == 8
    assert result.brightness == 200
    assert result.led_order == "GRB"
    assert result.standby_color == (0, 20, 0)
    assert result.alert_color == (255, 50, 0)
    assert result.flash_on_alert is True
    assert result.flash_interval_ms == 300


# ---------------------------------------------------------------------------
# USB Tower Light tests (Adafruit #5125 / CH34x serial)
# ---------------------------------------------------------------------------


class _FakeSerial:
    """Minimal pyserial stub that records written bytes."""

    def __init__(self):
        self.written: list[int] = []

    def write(self, data: bytes) -> None:
        self.written.extend(data)

    def close(self) -> None:
        pass


def _make_tower_ctrl(config: TowerLightConfig | None = None) -> tuple:
    """Return a TowerLightController with a fake serial port injected."""
    if config is None:
        config = TowerLightConfig(serial_port="/dev/null")
    ctrl = TowerLightController(config)
    fake_ser = _FakeSerial()
    ctrl._serial = fake_ser
    ctrl._available = True
    return ctrl, fake_ser


def test_tower_light_standby_sends_correct_commands():
    """set_standby should turn green on and everything else off."""
    ctrl, ser = _make_tower_ctrl()
    ser.written.clear()

    ctrl.set_standby()

    assert _TOWER_CMD_RED_OFF in ser.written
    assert _TOWER_CMD_YEL_OFF in ser.written
    assert _TOWER_CMD_BUZ_OFF in ser.written
    assert _TOWER_CMD_GRN_ON in ser.written


def test_tower_light_all_off_sends_correct_commands():
    """all_off should turn all four segments off."""
    ctrl, ser = _make_tower_ctrl()
    ser.written.clear()

    ctrl.all_off()

    from app_utils.gpio import _TOWER_CMD_RED_OFF, _TOWER_CMD_YEL_OFF, _TOWER_CMD_GRN_OFF, _TOWER_CMD_BUZ_OFF
    for cmd in (_TOWER_CMD_RED_OFF, _TOWER_CMD_YEL_OFF, _TOWER_CMD_GRN_OFF, _TOWER_CMD_BUZ_OFF):
        assert cmd in ser.written


def test_tower_light_start_alert_solid():
    """start_alert with blink_on_alert=False should send red on, not blink."""
    ctrl, ser = _make_tower_ctrl(
        TowerLightConfig(serial_port="/dev/null", blink_on_alert=False, alert_buzzer=False)
    )
    ser.written.clear()

    ctrl.start_alert()

    assert _TOWER_CMD_RED_ON in ser.written
    assert _TOWER_CMD_RED_BLINK not in ser.written
    assert _TOWER_CMD_BUZ_ON not in ser.written


def test_tower_light_start_alert_blink():
    """start_alert with blink_on_alert=True should use the blink command."""
    ctrl, ser = _make_tower_ctrl(
        TowerLightConfig(serial_port="/dev/null", blink_on_alert=True, alert_buzzer=False)
    )
    ser.written.clear()

    ctrl.start_alert()

    assert _TOWER_CMD_RED_BLINK in ser.written
    assert _TOWER_CMD_RED_ON not in ser.written


def test_tower_light_start_alert_with_buzzer():
    """start_alert with alert_buzzer=True should also send the buzzer on command."""
    ctrl, ser = _make_tower_ctrl(
        TowerLightConfig(serial_port="/dev/null", blink_on_alert=False, alert_buzzer=True)
    )
    ser.written.clear()

    ctrl.start_alert()

    assert _TOWER_CMD_BUZ_ON in ser.written


def test_tower_light_start_incoming_alert_blink():
    """start_incoming_alert should blink yellow when blink_on_alert=True."""
    ctrl, ser = _make_tower_ctrl(
        TowerLightConfig(serial_port="/dev/null", blink_on_alert=True)
    )
    ser.written.clear()

    ctrl.start_incoming_alert()

    assert _TOWER_CMD_YEL_BLINK in ser.written
    assert _TOWER_CMD_GRN_OFF in ser.written
    assert _TOWER_CMD_RED_OFF in ser.written


def test_tower_light_start_incoming_alert_disabled_sends_nothing():
    """start_incoming_alert should send no commands when incoming_uses_yellow=False."""
    ctrl, ser = _make_tower_ctrl(
        TowerLightConfig(serial_port="/dev/null", blink_on_alert=True, incoming_uses_yellow=False)
    )
    ser.written.clear()

    ctrl.start_incoming_alert()

    assert len(ser.written) == 0


def test_tower_light_end_alert_returns_to_standby():
    """end_alert should restore the standby (green on) state."""
    ctrl, ser = _make_tower_ctrl()
    ctrl.start_alert()
    ser.written.clear()

    ctrl.end_alert()

    assert _TOWER_CMD_GRN_ON in ser.written
    assert _TOWER_CMD_RED_OFF in ser.written


def test_tower_light_get_status():
    """get_status should return a dict with expected keys."""
    ctrl, _ = _make_tower_ctrl(
        TowerLightConfig(
            serial_port="/dev/ttyUSB1",
            baudrate=9600,
            alert_buzzer=True,
            blink_on_alert=False,
        )
    )

    status = ctrl.get_status()
    assert status["available"] is True
    assert status["serial_port"] == "/dev/ttyUSB1"
    assert status["baudrate"] == 9600
    assert status["alert_buzzer"] is True
    assert status["blink_on_alert"] is False


def test_tower_light_cleanup_closes_serial():
    """cleanup should close the serial port and clear state."""
    ctrl, ser = _make_tower_ctrl()
    ctrl.cleanup()

    assert ctrl._serial is None
    assert ctrl._available is False


def test_load_tower_light_config_disabled(monkeypatch):
    """load_tower_light_config_from_db should return None when disabled."""
    monkeypatch.setattr(gpio, "_GPIO_SETTINGS_AVAILABLE", True)

    fake_settings = {
        "enabled": False,
        "serial_port": "/dev/ttyUSB0",
        "baudrate": 9600,
        "alert_buzzer": False,
        "incoming_uses_yellow": True,
        "blink_on_alert": True,
    }

    import types
    fake_module = types.ModuleType("app_core.hardware_settings")
    fake_module.get_tower_light_settings = lambda: fake_settings
    monkeypatch.setitem(
        __import__("sys").modules, "app_core.hardware_settings", fake_module
    )

    result = load_tower_light_config_from_db()
    assert result is None


def test_load_tower_light_config_enabled(monkeypatch):
    """load_tower_light_config_from_db should return TowerLightConfig when enabled."""
    monkeypatch.setattr(gpio, "_GPIO_SETTINGS_AVAILABLE", True)

    fake_settings = {
        "enabled": True,
        "serial_port": "/dev/ttyUSB1",
        "baudrate": 9600,
        "alert_buzzer": True,
        "incoming_uses_yellow": True,
        "blink_on_alert": False,
    }

    import types
    fake_module = types.ModuleType("app_core.hardware_settings")
    fake_module.get_tower_light_settings = lambda: fake_settings
    monkeypatch.setitem(
        __import__("sys").modules, "app_core.hardware_settings", fake_module
    )

    result = load_tower_light_config_from_db()
    assert result is not None
    assert result.serial_port == "/dev/ttyUSB1"
    assert result.baudrate == 9600
    assert result.alert_buzzer is True
    assert result.blink_on_alert is False
