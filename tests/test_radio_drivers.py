"""
EAS Station - Emergency Alert System
Copyright (c) 2025 Timothy Kramer (KR8MER)

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

import pathlib
import sys
import time
import types

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_core.radio.drivers import RTLSDRReceiver, _SoapySDRReceiver
from app_core.radio.manager import ReceiverConfig


class _Result:
    def __init__(self, ret: int) -> None:
        self.ret = ret


class _FailingDevice:
    def __init__(self) -> None:
        self.stream = object()

    def setSampleRate(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def setFrequency(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def setGain(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def setupStream(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        return "stream"

    def activateStream(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def readStream(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        # Return -2 (STREAM_ERROR) which triggers reconnection,
        # unlike -4 (OVERFLOW) which is treated as transient
        return _Result(-2)

    def deactivateStream(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def closeStream(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def unmake(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def close(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass


class _WorkingDevice:
    def __init__(self) -> None:
        self.stream = object()

    def setSampleRate(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def setFrequency(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def setGain(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def setupStream(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        return "stream"

    def activateStream(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def readStream(self, stream, buffers, length, **kwargs):  # noqa: N802 - mimic Soapy API
        buffer = buffers[0]
        buffer[:length] = 0.25 + 0.25j
        return _Result(length)

    def deactivateStream(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def closeStream(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def unmake(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass

    def close(self, *args, **kwargs):  # noqa: N802 - mimic Soapy API
        pass


class _DeviceFactory:
    open_count = 0

    def __new__(cls, args):
        cls.open_count += 1
        if cls.open_count == 1:
            return _FailingDevice()
        return _WorkingDevice()

    @classmethod
    def enumerate(cls):
        return []


class _SoapyModule(types.SimpleNamespace):
    pass


def _install_soapysdr_stub(monkeypatch):
    module = _SoapyModule()
    module.SOAPY_SDR_RX = 1
    module.SOAPY_SDR_CF32 = 2
    module.Device = _DeviceFactory
    monkeypatch.setitem(sys.modules, "SoapySDR", module)
    return module


def test_receiver_recovers_from_stream_error(monkeypatch):
    _DeviceFactory.open_count = 0
    _install_soapysdr_stub(monkeypatch)

    config = ReceiverConfig(
        identifier="test",
        driver="rtlsdr",
        frequency_hz=162_550_000,
        sample_rate=2_400_000,
        gain=10.0,
        auto_start=True,
    )

    receiver = RTLSDRReceiver(config)
    receiver.start()

    try:
        deadline = time.time() + 2.0
        success = False
        while time.time() < deadline:
            status = receiver.get_status()
            samples = receiver.get_samples(512)
            if status.locked and samples is not None and len(samples) == 512:
                # Ensure samples look like complex64 numpy array
                assert isinstance(samples, np.ndarray)
                assert samples.dtype == np.complex64
                success = True
                break
            time.sleep(0.05)

        assert success, "receiver did not recover from initial stream error"
    finally:
        receiver.stop()
        monkeypatch.delitem(sys.modules, "SoapySDR", raising=False)
        _DeviceFactory.open_count = 0


def test_receiver_logs_error_and_recovery(monkeypatch):
    _DeviceFactory.open_count = 0
    _install_soapysdr_stub(monkeypatch)

    events = []

    def recorder(level, message, *, module, details=None):
        events.append((level, message, module, details))

    config = ReceiverConfig(
        identifier="test",
        driver="rtlsdr",
        frequency_hz=162_550_000,
        sample_rate=2_400_000,
        gain=10.0,
        auto_start=True,
    )

    receiver = RTLSDRReceiver(config, event_logger=recorder)
    receiver.start()

    try:
        deadline = time.time() + 2.0
        recovered = False
        while time.time() < deadline:
            if any(event[0] == "INFO" and "recovered" in event[1] for event in events):
                recovered = True
                break
            time.sleep(0.05)

        assert any(
            event[0] == "ERROR" and "SoapySDR readStream error" in event[1]
            for event in events
        ), "expected readStream error to be logged"
        assert recovered, "receiver did not emit recovery log entry"

        assert any(
            (details or {}).get("identifier") == "test" and details.get("driver") == "rtlsdr"
            for _, _, _, details in events
        ), "event details should include receiver metadata"
    finally:
        receiver.stop()
        monkeypatch.delitem(sys.modules, "SoapySDR", raising=False)
        _DeviceFactory.open_count = 0


def test_read_error_description_includes_lock_hint():
    description = _SoapySDRReceiver._describe_soapysdr_error(-7)
    assert "not locked" in description.lower()

    annotated = _SoapySDRReceiver._annotate_lock_hint(description)
    assert "pll" in annotated.lower()
    assert "hint" in annotated.lower()


def test_unknown_error_code_still_formats_message():
    description = _SoapySDRReceiver._describe_soapysdr_error(-99)
    assert "unknown" in description.lower()

    annotated = _SoapySDRReceiver._annotate_lock_hint("generic error")
    assert annotated == "generic error"


def test_dynamic_buffer_size_calculation():
    """Test that buffer size is calculated dynamically based on sample rate."""
    # Test with low sample rate (48kHz) - should use minimum buffer
    config_low = ReceiverConfig(
        identifier="test-low",
        driver="rtlsdr",
        frequency_hz=162_550_000,
        sample_rate=48_000,  # Low sample rate
        gain=10.0,
        auto_start=False,
    )
    receiver_low = RTLSDRReceiver(config_low)
    buffer_size_low = receiver_low._calculate_buffer_size()
    # 48kHz * 50ms = 2400 samples, but min is 16384
    assert buffer_size_low == 16384, f"Expected minimum buffer 16384, got {buffer_size_low}"

    # Test with medium sample rate (2.4MHz RTL-SDR) - should be proportional
    config_med = ReceiverConfig(
        identifier="test-med",
        driver="rtlsdr",
        frequency_hz=162_550_000,
        sample_rate=2_400_000,  # 2.4 MHz
        gain=10.0,
        auto_start=False,
    )
    receiver_med = RTLSDRReceiver(config_med)
    buffer_size_med = receiver_med._calculate_buffer_size()
    # 2.4MHz * 50ms = 120000 samples
    assert buffer_size_med == 120000, f"Expected 120000, got {buffer_size_med}"

    # Test with high sample rate (10MHz Airspy) - should cap at maximum
    config_high = ReceiverConfig(
        identifier="test-high",
        driver="airspy",
        frequency_hz=162_550_000,
        sample_rate=10_000_000,  # 10 MHz
        gain=10.0,
        auto_start=False,
    )
    receiver_high = RTLSDRReceiver(config_high)
    buffer_size_high = receiver_high._calculate_buffer_size()
    # 10MHz * 50ms = 500000 samples, but max is 262144
    assert buffer_size_high == 262144, f"Expected maximum buffer 262144, got {buffer_size_high}"

    # Test with typical Airspy R2 rate (2.5MHz)
    config_airspy = ReceiverConfig(
        identifier="test-airspy",
        driver="airspy",
        frequency_hz=162_550_000,
        sample_rate=2_500_000,  # 2.5 MHz typical Airspy
        gain=10.0,
        auto_start=False,
    )
    receiver_airspy = RTLSDRReceiver(config_airspy)
    buffer_size_airspy = receiver_airspy._calculate_buffer_size()
    # 2.5MHz * 50ms = 125000 samples
    assert buffer_size_airspy == 125000, f"Expected 125000, got {buffer_size_airspy}"
