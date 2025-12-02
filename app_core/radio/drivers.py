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

from __future__ import annotations

"""Receiver driver implementations for specific SDR front-ends."""

import datetime
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from .manager import ReceiverConfig, ReceiverInterface, ReceiverStatus, RadioManager


# Default gain constants for different SDR drivers
# These are used when no gain is specified (gain=None)
AIRSPY_DEFAULT_GAIN = 21.0  # Overall gain for Airspy (distributes across LNA/MIX/VGA)
AIRSPY_DEFAULT_LNA_GAIN = 10  # LNA stage gain (0-15)
AIRSPY_DEFAULT_MIX_GAIN = 10  # Mixer stage gain (0-15)  
AIRSPY_DEFAULT_VGA_GAIN = 10  # VGA stage gain (0-15)
RTLSDR_DEFAULT_GAIN = 40.0  # TUNER gain for RTL-SDR (0-49.6)

# Network stabilization delay for remote SDR connections (seconds)
# Allows time for network connection to stabilize after stream activation
NETWORK_STABILIZATION_DELAY = 0.2


class _SoapySDRHandle:
    """Thin wrapper storing objects needed for a SoapySDR stream."""

    def __init__(self, device, stream, sdr_module, numpy_module) -> None:
        self.device = device
        self.stream = stream
        self.sdr = sdr_module
        self.numpy = numpy_module


class _CaptureTicket:
    """Track the progress of a capture request for a single receiver."""

    def __init__(
        self,
        *,
        identifier: str,
        path: Path,
        samples_required: int,
        mode: str,
        numpy_module,
    ) -> None:
        self.identifier = identifier
        self.path = path
        self.samples_required = samples_required
        self.mode = mode
        self.numpy = numpy_module
        self.samples_captured = 0
        self.error: Optional[Exception] = None
        self.event = threading.Event()
        self._file = None

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "wb")

    @property
    def completed(self) -> bool:
        return self.error is not None or self.samples_captured >= self.samples_required

    def write(self, samples) -> None:
        if self.completed or self._file is None:
            return

        remaining = self.samples_required - self.samples_captured
        if remaining <= 0:
            self.close()
            return

        to_take = min(len(samples), remaining)
        if to_take <= 0:
            return

        chunk = samples[:to_take]
        try:
            if self.mode == "pcm":
                interleaved = self.numpy.empty((to_take * 2,), dtype=self.numpy.float32)
                interleaved[0::2] = chunk.real.astype(self.numpy.float32, copy=False)
                interleaved[1::2] = chunk.imag.astype(self.numpy.float32, copy=False)
                interleaved.tofile(self._file)
            else:
                chunk.astype(self.numpy.complex64, copy=False).tofile(self._file)
        except Exception as exc:
            self.fail(exc)
            return

        self.samples_captured += to_take
        if self.samples_captured >= self.samples_required:
            self.close()

    def fail(self, exc: Exception) -> None:
        self.error = exc
        self.close()

    def close(self) -> None:
        if self._file is not None:
            try:
                self._file.close()
            finally:
                self._file = None
        self.event.set()

class _SoapySDRReceiver(ReceiverInterface):
    """Common functionality for receivers implemented via SoapySDR."""

    driver_hint: str = ""
    
    # Minimum dynamic range threshold for valid RF signal
    # Real RF signals typically have dynamic range > 1.5 (peak vs mean magnitude)
    # DC offset or constant signal has ratio very close to 1.0
    # Values below this threshold indicate potential hardware/configuration issues
    _MIN_DYNAMIC_RANGE = 1.1
    
    # Small value to avoid division by zero in magnitude calculations
    _MIN_MAGNITUDE = 1e-10
    
    _SOAPY_ERROR_DESCRIPTIONS = {
        -1: "Timeout waiting for samples (SOAPY_SDR_TIMEOUT)",
        -2: "Stream reported a driver error (SOAPY_SDR_STREAM_ERROR)",
        -3: "Corrupted data from device (SOAPY_SDR_CORRUPTION)",
        -4: "Buffer overflow - system cannot keep up with data rate (SOAPY_SDR_OVERFLOW)",
        -5: "Operation not supported by device (SOAPY_SDR_NOT_SUPPORTED)",
        -6: "Timing error in stream (SOAPY_SDR_TIME_ERROR)",
        -7: "PLL not locked - receiver tuner or reference clock issue (SOAPY_SDR_NOT_LOCKED)",
    }

    def __init__(
        self,
        config: ReceiverConfig,
        *,
        event_logger=None,
    ) -> None:
        super().__init__(config, event_logger=event_logger)
        self._handle: Optional[_SoapySDRHandle] = None
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._status = ReceiverStatus(identifier=config.identifier, locked=False)
        self._status_lock = threading.Lock()
        self._capture_requests: List[_CaptureTicket] = []
        self._capture_lock = threading.Lock()
        # Real-time sample buffer for audio streaming
        self._sample_buffer = None  # Will be a numpy array ring buffer
        self._sample_buffer_size = 32768  # Store ~0.67 seconds at 48kHz
        self._sample_buffer_pos = 0
        self._sample_buffer_lock = threading.Lock()
        
        # Spectrum/Waterfall support
        self._spectrum_buffer = None
        self._spectrum_update_interval = 0.1  # 100ms
        self._last_spectrum_update = 0.0
        self._fft_size = 2048
        self._window = None
        
        # Ring buffer for robust SDR reading (USB jitter absorption)
        self._ring_buffer = None
        self._ring_write_pos = 0
        self._ring_read_pos = 0
        self._ring_buffer_size = 0  # Will be set based on sample rate
        self._consecutive_timeouts = 0
        self._max_consecutive_timeouts = 10
        self._timeout_backoff = 0.01

        self._retry_backoff = 0.25
        self._max_retry_backoff = 5.0
        self._last_logged_error: Optional[str] = None
        # Connection health tracking
        self._connection_attempts = 0
        self._connection_failures = 0
        self._last_successful_connection: Optional[datetime.datetime] = None
        self._stream_errors_count = 0

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    @classmethod
    def _describe_soapysdr_error(cls, code: int) -> str:
        """Return a human-readable message for a SoapySDR error code."""

        description = cls._SOAPY_ERROR_DESCRIPTIONS.get(code)
        if description:
            return f"SoapySDR readStream error {code}: {description}"
        return f"SoapySDR readStream error {code}: Unknown error"

    @staticmethod
    def _annotate_lock_hint(message: str) -> str:
        """Attach a PLL lock hint when SoapySDR reports NOT_LOCKED conditions."""

        if not isinstance(message, str):
            return message

        lowered = message.lower()
        keywords = (
            "not locked",
            "pll lock",
            "pll unlock",
            "soapysdr readstream error -7",
            "error -7",
            "soapysdr_not_locked",
        )
        if any(keyword in lowered for keyword in keywords):
            hint = (
                "Receiver PLL is not locked; ensure the SDR has a valid antenna, "
                "reference clock, and that the tuner frequency is supported."
            )
            if hint not in message:
                return f"{message} (hint: {hint})"
        return message

    @staticmethod
    def _annotate_device_open_hint(message: str, driver: str, serial: Optional[str] = None) -> str:
        """Enhance device open errors with troubleshooting hints."""

        if not isinstance(message, str):
            return message

        lowered = message.lower()
        hints = []

        # Check for common error patterns
        if "unable to open" in lowered or "failed to open" in lowered:
            hints.append("Common causes: device not connected, USB permissions issue, "
                        "device in use by another process, or driver not installed")

        if "permission" in lowered or "access denied" in lowered:
            hints.append("USB permissions issue detected. On Linux, you may need to add udev rules "
                        "or run 'sudo usermod -aG plugdev $USER' and reboot")

        if "device busy" in lowered or "resource busy" in lowered:
            hints.append("Device is in use by another process. Check for other SDR applications "
                        "or kill processes using: 'lsof | grep sdr'")

        if serial and ("serial" in lowered or "not found" in lowered):
            hints.append(f"Device with serial '{serial}' not found. Verify device is connected "
                        f"and serial number is correct using: 'SoapySDRUtil --find=\"driver={driver}\"'")

        # Add device-specific hints
        if driver == "airspy":
            hints.append("For Airspy: ensure SoapyAirspy module is installed and libairspy is available. "
                        "Test with: 'SoapySDRUtil --probe=\"driver=airspy\"'")
        elif driver == "rtlsdr":
            hints.append("For RTL-SDR: ensure SoapyRTLSDR module is installed and blacklist dvb_usb_rtl28xxu "
                        "kernel module if needed")

        if hints:
            hint_text = "; ".join(hints)
            return f"{message} (troubleshooting: {hint_text})"
        return message

    def _enumerate_available_devices(self, sdr_module) -> List[Dict[str, str]]:
        """Enumerate available SoapySDR devices for diagnostic purposes."""
        try:
            devices = sdr_module.Device.enumerate()
            return [dict(d) for d in devices]
        except Exception as exc:
            self._interface_logger.warning("Failed to enumerate devices: %s", exc)
            return []

    def get_connection_health(self) -> Dict[str, object]:
        """Get diagnostic information about device connection health.

        Returns:
            Dictionary containing connection statistics and health metrics
        """
        uptime = None
        if self._last_successful_connection:
            uptime = (datetime.datetime.now(datetime.timezone.utc) -
                     self._last_successful_connection).total_seconds()

        health = {
            "connection_attempts": self._connection_attempts,
            "connection_failures": self._connection_failures,
            "stream_errors": self._stream_errors_count,
            "last_successful_connection": self._last_successful_connection.isoformat() if self._last_successful_connection else None,
            "uptime_seconds": uptime,
            "running": self._running.is_set(),
            "device_open": self._handle is not None,
        }

        # Calculate success rate
        if self._connection_attempts > 0:
            health["connection_success_rate"] = (
                (self._connection_attempts - self._connection_failures) /
                self._connection_attempts * 100.0
            )
        else:
            health["connection_success_rate"] = 0.0

        return health

    def is_running(self) -> bool:  # noqa: D401 - documented in base class
        """Check if the receiver capture thread is actively running."""
        return self._running.is_set()

    def start(self) -> None:  # noqa: D401 - documented in base class
        if self._running.is_set():
            return

        # Retry initial device open with exponential backoff for hardware reliability
        max_startup_retries = 3
        retry_delay = self._retry_backoff
        last_exception = None

        for attempt in range(max_startup_retries):
            try:
                handle = self._open_handle()
                break  # Success - exit retry loop
            except Exception as exc:
                last_exception = exc
                self._update_status(locked=False, last_error=str(exc), context="startup")

                if attempt < max_startup_retries - 1:
                    self._interface_logger.warning(
                        "Failed to open device for %s (attempt %d/%d): %s. Retrying in %.1f seconds...",
                        self.config.identifier,
                        attempt + 1,
                        max_startup_retries,
                        exc,
                        retry_delay
                    )
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2.0, self._max_retry_backoff)
                else:
                    self._interface_logger.error(
                        "Failed to open device for %s after %d attempts. "
                        "Device will continue retrying in background capture loop.",
                        self.config.identifier,
                        max_startup_retries
                    )
                    # Don't raise - let the capture loop handle retries
                    handle = None
        else:
            # All retries failed - start capture loop anyway to keep retrying
            handle = None

        self._handle = handle
        if handle is not None:
            self._initialize_sample_buffer(handle.numpy)

        self._running.set()

        thread_name = f"{self.__class__.__name__}-{self.config.identifier}"
        self._thread = threading.Thread(target=self._capture_loop, name=thread_name, daemon=True)
        self._thread.start()

    def stop(self) -> None:  # noqa: D401 - documented in base class
        if not self._running.is_set():
            return

        self._running.clear()
        if self._thread:
            self._thread.join(timeout=2.0)

        self._teardown_handle()
        self._cancel_capture_requests(RuntimeError("Receiver stopped"), teardown=False)
        self._update_status(locked=False)

    # ------------------------------------------------------------------
    # Status reporting
    # ------------------------------------------------------------------
    def get_status(self) -> ReceiverStatus:  # noqa: D401 - documented in base class
        with self._status_lock:
            return ReceiverStatus(
                identifier=self._status.identifier,
                locked=self._status.locked,
                signal_strength=self._status.signal_strength,
                last_error=self._status.last_error,
                capture_mode=self._status.capture_mode,
                capture_path=self._status.capture_path,
                reported_at=self._status.reported_at,
            )

    def _update_status(
        self,
        *,
        locked: Optional[bool] = None,
        signal_strength: Optional[float] = None,
        last_error: Optional[str] = None,
        capture_mode: Optional[str] = None,
        capture_path: Optional[str] = None,
        context: Optional[str] = None,
    ) -> None:
        with self._status_lock:
            if locked is not None:
                self._status.locked = locked
            if signal_strength is not None:
                self._status.signal_strength = signal_strength
            sanitized_error = last_error
            if isinstance(sanitized_error, str):
                sanitized_error = sanitized_error.strip()
            if sanitized_error == "":
                sanitized_error = None
            if sanitized_error is not None:
                self._status.last_error = sanitized_error
            elif locked:
                # Clear stale error state when the receiver reports healthy.
                self._status.last_error = None
            if capture_mode is not None:
                self._status.capture_mode = capture_mode
            if capture_path is not None:
                self._status.capture_path = capture_path
            self._status.reported_at = datetime.datetime.now(datetime.timezone.utc)

            current_error = self._status.last_error

        if sanitized_error is not None and current_error:
            details = self._build_event_details(context=context)
            details["error"] = current_error
            self._emit_event(
                "ERROR",
                f"{self.config.identifier}: {current_error}",
                details=details,
            )
            self._last_logged_error = current_error
        elif sanitized_error is None and locked and self._last_logged_error:
            details = self._build_event_details(context=context)
            details["previous_error"] = self._last_logged_error
            self._emit_event(
                "INFO",
                f"{self.config.identifier} recovered and resumed streaming",
                details=details,
            )
            self._last_logged_error = None

    def _build_event_details(self, *, context: Optional[str] = None) -> Dict[str, object]:
        with self._status_lock:
            locked = bool(self._status.locked)
            signal_strength = self._status.signal_strength
            capture_mode = self._status.capture_mode
            capture_path = self._status.capture_path
            reported_at = self._status.reported_at

        details: Dict[str, object] = {
            "identifier": self.config.identifier,
            "driver": self.config.driver,
            "driver_hint": self.driver_hint,
            "frequency_hz": self.config.frequency_hz,
            "sample_rate": self.config.sample_rate,
            "gain": self.config.gain,
            "serial": self.config.serial,
            "locked": locked,
            "signal_strength": signal_strength,
        }

        if capture_mode is not None:
            details["capture_mode"] = capture_mode
        if capture_path is not None:
            details["capture_path"] = capture_path
        if reported_at is not None:
            details["reported_at"] = reported_at.isoformat()
        if context:
            details["context"] = context

        return details

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _initialize_sample_buffer(self, numpy_module) -> None:
        """Reset the rolling IQ sample buffer using the provided numpy module."""
        with self._sample_buffer_lock:
            self._sample_buffer = numpy_module.zeros(self._sample_buffer_size, dtype=numpy_module.complex64)
            self._sample_buffer_pos = 0

    def _open_handle(self) -> _SoapySDRHandle:
        try:
            import SoapySDR  # type: ignore
        except ImportError as exc:  # pragma: no cover - dependency missing in CI
            raise RuntimeError(
                "SoapySDR Python bindings are required for SDR receivers."
            ) from exc

        try:
            import numpy  # type: ignore
        except ImportError as exc:  # pragma: no cover - dependency missing in CI
            raise RuntimeError("NumPy is required for SoapySDR based receivers.") from exc

        channel = self.config.channel if self.config.channel is not None else 0

        args: Dict[str, str] = {"driver": self.driver_hint}

        # Use the device serial number if available for precise device identification
        if self.config.serial:
            args["serial"] = self.config.serial
        # Use channel/device_id as fallback identification only if no serial
        elif self.config.channel is not None:
            # Only set device_id, not serial (serial is for hardware serial numbers only)
            args["device_id"] = str(self.config.channel)

        # Label is for human reference only, not device identification
        if self.config.identifier:
            args.setdefault("label", self.config.identifier)

        # Log available devices for diagnostics
        available_devices = self._enumerate_available_devices(SoapySDR)
        if available_devices:
            self._interface_logger.info(
                "Found %d SoapySDR device(s): %s",
                len(available_devices),
                [d.get("label", d.get("driver", "unknown")) for d in available_devices]
            )

            # Log detailed device information including serials for troubleshooting
            for dev in available_devices:
                dev_driver = dev.get("driver", "unknown")
                dev_serial = dev.get("serial", "N/A")
                dev_label = dev.get("label", "N/A")
                self._interface_logger.debug(
                    "  Device: driver=%s, serial=%s, label=%s",
                    dev_driver, dev_serial, dev_label
                )

            # Check if the requested device is in the list
            if self.config.serial:
                matching = [d for d in available_devices
                           if d.get("serial") == self.config.serial and
                           d.get("driver") == self.driver_hint]
                if not matching:
                    self._interface_logger.warning(
                        "Requested device with serial '%s' and driver '%s' not found in enumerated devices. "
                        "Available %s devices: %s",
                        self.config.serial,
                        self.driver_hint,
                        self.driver_hint,
                        [d.get("serial", "N/A") for d in available_devices
                         if d.get("driver") == self.driver_hint]
                    )
        else:
            self._interface_logger.warning(
                "No SoapySDR devices found. Ensure device is connected and drivers are installed."
            )

        try:
            device = SoapySDR.Device(args)
        except Exception as exc:
            device = self._retry_device_open_without_serial(
                SoapySDR, args, exc
            )

        try:
            device.setSampleRate(SoapySDR.SOAPY_SDR_RX, channel, self.config.sample_rate)
            device.setFrequency(SoapySDR.SOAPY_SDR_RX, channel, self.config.frequency_hz)
            
            # Configure gain - this is CRITICAL for receiving signals
            # Without proper gain, the SDR will output near-zero samples (just noise floor)
            if self.config.gain is not None:
                # User specified a gain value - use it directly
                device.setGain(SoapySDR.SOAPY_SDR_RX, channel, float(self.config.gain))
            else:
                # No gain specified - try to enable AGC, or set sensible defaults
                # Different SDRs have different gain structures and AGC support
                try:
                    # Try to enable AGC (automatic gain control) if supported
                    # This is the best option for hands-off operation
                    if device.hasGainMode(SoapySDR.SOAPY_SDR_RX, channel):
                        device.setGainMode(SoapySDR.SOAPY_SDR_RX, channel, True)
                        self._interface_logger.info(f"Enabled AGC for {self.driver_hint}")
                    else:
                        # AGC not supported - set driver-specific default gains
                        # These defaults are chosen for strong signal reception
                        self._set_default_gain(device, channel)
                except Exception as agc_exc:
                    # AGC failed, try setting default gain
                    self._interface_logger.debug(f"AGC not available ({agc_exc}), using default gain")
                    self._set_default_gain(device, channel)

            # Configure stream with appropriate MTU for USB bandwidth
            # AirSpy and other SDRs benefit from larger buffer sizes to prevent
            # USB transfer overhead and stream errors
            # SoapySDR setupStream signature: setupStream(direction, format, [channels], args={})
            # Note: Some drivers need bufflen as string, others as int - use string for compatibility
            stream_mtu = 131072  # Samples per USB transfer (optimized for AirSpy)
            stream_args = {}

            # Try setting buffer length if supported by the driver
            # AirSpy: uses internal buffering, bufflen may not be supported
            # RTL-SDR: supports bufflen parameter
            if self.driver_hint == "rtlsdr":
                stream_args["bufflen"] = str(stream_mtu)

            stream = device.setupStream(
                SoapySDR.SOAPY_SDR_RX,
                SoapySDR.SOAPY_SDR_CF32,
                [channel],  # channels list
                stream_args  # driver-specific stream args
            )
            device.activateStream(stream)
            
            # Allow SDR hardware time to stabilize after stream activation
            # This is especially important for Airspy and some RTL-SDR devices
            # that need time to start the data flow after activation
            time.sleep(0.1)  # 100ms stabilization delay
        except Exception as exc:
            # Ensure hardware resources are released before bubbling the error up.
            try:
                device.close()
            except Exception:  # pragma: no cover - best-effort cleanup
                pass
            message = self._annotate_lock_hint(str(exc))
            raise RuntimeError(f"Failed to configure SoapySDR device: {message}") from exc

        return _SoapySDRHandle(device=device, stream=stream, sdr_module=SoapySDR, numpy_module=numpy)

    def _retry_device_open_without_serial(
        self,
        sdr_module,
        original_args: Dict[str, str],
        original_exc: Exception,
    ) -> object:
        serial = original_args.get("serial")
        if not serial:
            message = self._annotate_lock_hint(str(original_exc))
            message = self._annotate_device_open_hint(message, self.driver_hint, serial)
            raise RuntimeError(
                f"Unable to open SoapySDR device for driver '{self.driver_hint}': {message}"
            ) from original_exc

        # First fallback: Try without serial but keep other parameters
        # Note: AirSpy doesn't support device_id, only RTL-SDR and some other drivers do
        fallback_args = dict(original_args)
        fallback_args.pop("serial", None)
        if not fallback_args.get("driver"):
            fallback_args["driver"] = self.driver_hint
        # Only add device_id for drivers that support it (not airspy)
        if self.driver_hint != "airspy" and "device_id" not in fallback_args and self.config.channel is not None:
            fallback_args["device_id"] = str(self.config.channel)

        # Check if fallback_args is different from minimal args (just driver)
        # If they're the same, skip this fallback to avoid duplicate attempts
        minimal_args = {"driver": self.driver_hint}
        skip_first_fallback = (fallback_args == minimal_args)

        # Initialize fallback_exc before try/except to avoid scoping issues
        # (exception variables in except clauses are deleted after the block)
        fallback_exc = None

        if not skip_first_fallback:
            self._emit_event(
                "warning",
                "Falling back to autodetected SDR device after serial open failure",
                details={
                    "driver": self.driver_hint,
                    "serial": serial,
                    "error": str(original_exc),
                },
            )
            self._interface_logger.warning(
                "Failed to open SDR %s with serial %s (%s); retrying without serial filter",
                self.driver_hint or "unknown",
                serial,
                original_exc,
            )

            try:
                device = sdr_module.Device(fallback_args)
                self._emit_event(
                    "info",
                    "Opened SDR device without serial filter after fallback",
                    details={"driver": self.driver_hint, "serial": serial},
                )
                return device
            except Exception as e:
                fallback_exc = e  # Capture exception to persist beyond except block
        else:
            fallback_exc = original_exc  # Skip first fallback, use original exception

        # Second fallback: Try with ONLY driver (no serial, no device_id)
        self._interface_logger.warning(
            "Attempting to open device with driver-only filter (serial '%s' was not found)",
            serial,
        )

        try:
            device = sdr_module.Device(minimal_args)
            self._emit_event(
                "info",
                "Opened SDR device with driver-only filter after fallback",
                details={"driver": self.driver_hint, "serial": serial},
            )
            return device
        except Exception as minimal_exc:
            # All retries failed - provide comprehensive error message
            annotated_original = self._annotate_lock_hint(str(original_exc))
            annotated_original = self._annotate_device_open_hint(annotated_original, self.driver_hint, serial)

            # Build error message based on what we tried
            if skip_first_fallback:
                # We only tried original (with serial) and minimal (driver only)
                annotated_minimal = self._annotate_lock_hint(str(minimal_exc))
                annotated_minimal = self._annotate_device_open_hint(annotated_minimal, self.driver_hint, None)

                raise RuntimeError(
                    "Unable to open SoapySDR device for driver "
                    f"'{self.driver_hint}' using serial '{serial}': {annotated_original}; "
                    f"retry with driver-only also failed: {annotated_minimal}"
                ) from minimal_exc
            else:
                # We tried all three: original, fallback, and minimal
                annotated_fallback = self._annotate_lock_hint(str(fallback_exc))
                annotated_fallback = self._annotate_device_open_hint(annotated_fallback, self.driver_hint, None)
                annotated_minimal = self._annotate_lock_hint(str(minimal_exc))
                annotated_minimal = self._annotate_device_open_hint(annotated_minimal, self.driver_hint, None)

                raise RuntimeError(
                    "Unable to open SoapySDR device for driver "
                    f"'{self.driver_hint}' using serial '{serial}': {annotated_original}; "
                    f"retry without serial also failed: {annotated_fallback}; "
                    f"retry with driver-only also failed: {annotated_minimal}"
                ) from minimal_exc

    def _set_default_gain(self, device, channel: int) -> None:
        """Set sensible default gain values when no gain is specified.
        
        Different SDR hardware has different gain structures:
        - RTL-SDR: Single "TUNER" gain (0-49.6 dB)
        - Airspy: Multiple stages (LNA, MIX, VGA) or linearity/sensitivity modes
        - Other SDRs: Various configurations
        
        This method sets reasonable defaults for strong signal reception.
        """
        try:
            # Get the SoapySDR module from our imports
            try:
                import SoapySDR
            except ImportError:
                self._interface_logger.warning("SoapySDR not available for default gain setting")
                return
            
            # Get available gain elements
            gain_names = device.listGains(SoapySDR.SOAPY_SDR_RX, channel)
            
            if not gain_names:
                # No gain elements available - nothing to set
                self._interface_logger.debug("No gain elements available on device")
                return
            
            # Driver-specific default gains for optimal reception
            # These are tuned for strong signal reception (like nearby FM stations)
            if self.driver_hint == "airspy":
                # Airspy has complex gain structure
                # For strong signals, use moderate gain to avoid ADC saturation
                # LNA: 0-15, MIX: 0-15, VGA: 0-15 (or linearity/sensitivity modes)
                if "LNA" in gain_names:
                    device.setGain(SoapySDR.SOAPY_SDR_RX, channel, "LNA", AIRSPY_DEFAULT_LNA_GAIN)
                if "MIX" in gain_names:
                    device.setGain(SoapySDR.SOAPY_SDR_RX, channel, "MIX", AIRSPY_DEFAULT_MIX_GAIN)
                if "VGA" in gain_names:
                    device.setGain(SoapySDR.SOAPY_SDR_RX, channel, "VGA", AIRSPY_DEFAULT_VGA_GAIN)
                # Also try setting overall gain if individual stages fail
                try:
                    device.setGain(SoapySDR.SOAPY_SDR_RX, channel, AIRSPY_DEFAULT_GAIN)
                except Exception:
                    pass
                self._interface_logger.info(
                    f"Set default Airspy gains (LNA={AIRSPY_DEFAULT_LNA_GAIN}, "
                    f"MIX={AIRSPY_DEFAULT_MIX_GAIN}, VGA={AIRSPY_DEFAULT_VGA_GAIN})"
                )
                
            elif self.driver_hint == "rtlsdr":
                # RTL-SDR has single TUNER gain
                # 49.6 is typically maximum, good for weak signals
                # For very strong signals, lower may be needed
                if "TUNER" in gain_names:
                    device.setGain(SoapySDR.SOAPY_SDR_RX, channel, "TUNER", RTLSDR_DEFAULT_GAIN)
                else:
                    device.setGain(SoapySDR.SOAPY_SDR_RX, channel, RTLSDR_DEFAULT_GAIN)
                self._interface_logger.info(f"Set default RTL-SDR gain (TUNER={RTLSDR_DEFAULT_GAIN})")
                
            else:
                # Unknown driver - try to set reasonable overall gain
                # Most SDRs accept a single gain value
                try:
                    # Get gain range to set a reasonable default (75% of max)
                    gain_range = device.getGainRange(SoapySDR.SOAPY_SDR_RX, channel)
                    default_gain = gain_range.minimum() + 0.75 * (gain_range.maximum() - gain_range.minimum())
                    device.setGain(SoapySDR.SOAPY_SDR_RX, channel, default_gain)
                    self._interface_logger.info(f"Set default gain to {default_gain:.1f} dB for {self.driver_hint}")
                except Exception as e:
                    self._interface_logger.warning(f"Could not set default gain: {e}")
                    
        except Exception as e:
            self._interface_logger.warning(f"Failed to set default gain: {e}")

    def _teardown_handle(self, handle: Optional[_SoapySDRHandle] = None) -> None:
        if handle is None:
            handle = self._handle
        if not handle:
            return

        try:
            handle.device.deactivateStream(handle.stream)
        except Exception:  # pragma: no cover - best-effort cleanup
            pass

        try:
            handle.device.closeStream(handle.stream)
        except Exception:  # pragma: no cover - best-effort cleanup
            pass

        try:
            handle.device.unmake()  # type: ignore[attr-defined]
        except AttributeError:
            # Older SoapySDR bindings expose `close()` instead of `unmake()`.
            try:
                handle.device.close()
            except Exception:  # pragma: no cover - best-effort cleanup
                pass
        except Exception:  # pragma: no cover - best-effort cleanup
            pass

        if handle is self._handle:
            self._handle = None

    def _compute_spectrum(self, samples, numpy_module) -> None:
        """Compute power spectral density using Welch method."""
        if len(samples) < self._fft_size:
            return

        # Initialize window if needed
        if self._window is None:
            self._window = numpy_module.hanning(self._fft_size)

        # Apply Hann window for spectral leakage reduction
        # Take the center samples if we have more than needed
        start_idx = (len(samples) - self._fft_size) // 2
        samples_slice = samples[start_idx:start_idx + self._fft_size]
        
        # Remove DC offset before FFT computation
        # This is critical for high-powered FM stations where the DC component
        # from the tuner's local oscillator leakage can dominate the spectrum
        # and make everything else look like "garbage" (horizontal lines)
        dc_removed = samples_slice - numpy_module.mean(samples_slice)
        
        windowed = dc_removed * self._window

        # FFT with zero-padding for better resolution (implicit in numpy if n > len)
        # Use fftshift to center DC at 0
        spectrum = numpy_module.abs(numpy_module.fft.fftshift(numpy_module.fft.fft(windowed, n=self._fft_size)))

        # Convert to dB (10*log10 for power)
        # Avoid log(0) by clamping to small value
        power_db = 20 * numpy_module.log10(numpy_module.maximum(spectrum, 1e-10))

        # Normalize to 0-100 scale for visualization (approximate -100dBm to 0dBm range)
        # This is somewhat arbitrary but works for visualization
        normalized = numpy_module.clip((power_db + 100) / 100 * 100, 0, 100)

        self._spectrum_buffer = normalized.astype(numpy_module.float32)
        self._last_spectrum_update = time.time()

    def get_spectrum(self) -> Optional[List[float]]:
        """Get the latest computed spectrum data."""
        if self._spectrum_buffer is None:
            return None
        # Return as list for JSON serialization
        return self._spectrum_buffer.tolist()

    def _capture_loop(self) -> None:
        handle = self._handle
        buffer = None
        if handle is not None:
            # Use larger buffer to reduce USB transfer overhead and prevent SOAPY_SDR_OVERFLOW (-4)
            # High-speed SDRs like AirSpy generate data faster than smaller buffers can handle
            buffer = handle.numpy.zeros(131072, dtype=handle.numpy.complex64)

        retry_delay = self._retry_backoff
        consecutive_failures = 0
        
        # Initialize ring buffer for jitter absorption
        # 0.5 seconds of buffer is usually enough to absorb USB jitter
        ring_buffer_size = int(self.config.sample_rate * 0.5)
        # Ensure buffer is at least 4x the read chunk size
        ring_buffer_size = max(ring_buffer_size, 65536)
        
        ring_buffer = None
        ring_write_pos = 0
        
        if handle:
             ring_buffer = handle.numpy.zeros(ring_buffer_size, dtype=handle.numpy.complex64)
        
        last_spectrum_time = 0

        while self._running.is_set():
            if handle is None:
                if not self._running.is_set():
                    break

                consecutive_failures += 1
                self._connection_attempts += 1
                try:
                    self._interface_logger.info(
                        "Attempting to open device for %s (retry #%d, waiting %.1f seconds)...",
                        self.config.identifier,
                        consecutive_failures,
                        min(retry_delay, self._max_retry_backoff)
                    )
                    new_handle = self._open_handle()
                    consecutive_failures = 0  # Reset on success
                    self._last_successful_connection = datetime.datetime.now(datetime.timezone.utc)
                except Exception as exc:
                    self._connection_failures += 1
                    self._update_status(
                        locked=False,
                        last_error=str(exc),
                        context="open_stream",
                    )
                    time.sleep(min(retry_delay, self._max_retry_backoff))
                    retry_delay = min(retry_delay * 2.0, self._max_retry_backoff)
                    continue

                self._interface_logger.info(
                    "Successfully opened device for %s after %d attempt(s)",
                    self.config.identifier,
                    consecutive_failures + 1
                )
                handle = self._handle = new_handle
                self._initialize_sample_buffer(new_handle.numpy)
                # Use larger buffer to reduce USB transfer overhead and prevent SOAPY_SDR_OVERFLOW (-4)
                buffer = new_handle.numpy.zeros(131072, dtype=new_handle.numpy.complex64)
                
                # Re-initialize ring buffer on new connection
                ring_buffer_size = int(self.config.sample_rate * 0.5)
                ring_buffer_size = max(ring_buffer_size, 65536)
                ring_buffer = new_handle.numpy.zeros(ring_buffer_size, dtype=new_handle.numpy.complex64)
                ring_write_pos = 0
                
                retry_delay = self._retry_backoff
                continue

            try:
                # Read samples from SDR with explicit timeout
                # Use 500ms timeout (500000 microseconds) to allow adequate time
                # for USB transfers and SDR hardware response, especially for
                # Airspy and RTL-SDR devices that may have USB latency
                result = handle.device.readStream(
                    handle.stream, 
                    [buffer], 
                    len(buffer),
                    timeoutUs=500000  # 500ms timeout for reliable reading
                )
                
                if result.ret < 0:
                    # Handle different error types differently
                    error_code = result.ret
                    message = self._describe_soapysdr_error(error_code)
                    message = self._annotate_lock_hint(message)
                    
                    # TIMEOUT (-1) - Implement backoff
                    if error_code == -1:
                        self._consecutive_timeouts += 1
                        if self._consecutive_timeouts > self._max_consecutive_timeouts:
                             # Too many timeouts, force reconnection
                             raise RuntimeError(f"SDR timed out {self._consecutive_timeouts} times")
                        
                        # Exponential backoff
                        backoff = min(self._timeout_backoff, 0.5)
                        time.sleep(backoff)
                        self._timeout_backoff = min(backoff * 2, 0.5)
                        continue
                    else:
                        self._consecutive_timeouts = 0
                        self._timeout_backoff = 0.01
                    
                    # OVERFLOW (-4) / NOT_LOCKED (-7) - These are transient conditions
                    # that can recover without reconnecting the device.
                    if error_code in (-4, -7):
                        self._stream_errors_count += 1
                        if self._stream_errors_count == 1 or self._stream_errors_count % 100 == 0:
                            self._interface_logger.warning(
                                "Transient stream error for %s (error %d, total: %d): %s. Continuing...",
                                self.config.identifier,
                                error_code,
                                self._stream_errors_count,
                                message
                            )
                        self._update_status(
                            locked=True,
                            last_error=message,
                            context="read_stream_transient",
                        )
                        continue
                    
                    # Other errors require full reconnection
                    raise RuntimeError(message)

                # Success - reset timeout counters
                self._consecutive_timeouts = 0
                self._timeout_backoff = 0.01

                if result.ret > 0:
                    samples = buffer[: result.ret]
                    
                    # 1. Compute Spectrum (if interval elapsed)
                    now = time.time()
                    if now - last_spectrum_time > self._spectrum_update_interval:
                        self._compute_spectrum(samples, handle.numpy)
                        last_spectrum_time = now
                    
                    # 2. Update Signal Strength with diagnostic checks
                    magnitude = float(handle.numpy.mean(handle.numpy.abs(samples)))
                    max_magnitude = float(handle.numpy.max(handle.numpy.abs(samples)))
                    
                    # Log diagnostic warning if signal looks like DC or constant value
                    # which indicates potential SDR configuration or hardware issue
                    if max_magnitude > 0:
                        dynamic_range = max_magnitude / max(magnitude, self._MIN_MAGNITUDE)
                        if dynamic_range < self._MIN_DYNAMIC_RANGE and self._stream_errors_count == 0:
                            # Only log once to avoid spam
                            self._interface_logger.warning(
                                "Low dynamic range detected for %s (%.2f). "
                                "This may indicate DC offset, no antenna, or SDR configuration issue. "
                                "Mean=%.6f, Max=%.6f",
                                self.config.identifier,
                                dynamic_range,
                                magnitude,
                                max_magnitude
                            )
                    
                    self._update_status(locked=True, signal_strength=magnitude)
                    
                    # 3. Update Audio Sample Buffer (existing logic)
                    self._update_sample_buffer(samples)
                    
                    # 4. Process Capture (existing logic)
                    self._process_capture(samples)
                    
                else:
                    self._update_status(locked=True, signal_strength=0.0)

            except Exception as exc:
                consecutive_failures += 1
                self._stream_errors_count += 1
                self._interface_logger.warning(
                    "Stream error for %s (failure #%d, total stream errors: %d): %s. Reconnecting...",
                    self.config.identifier,
                    consecutive_failures,
                    self._stream_errors_count,
                    exc
                )
                self._update_status(
                    locked=False,
                    last_error=str(exc),
                    context="read_stream",
                )
                self._teardown_handle(handle)
                handle = None
                buffer = None
                ring_buffer = None
                self._cancel_capture_requests(RuntimeError(f"Capture error: {exc}"), teardown=False)
                if not self._running.is_set():
                    break
                time.sleep(min(retry_delay, self._max_retry_backoff))
                retry_delay = min(retry_delay * 2.0, self._max_retry_backoff)

        self._cancel_capture_requests(RuntimeError("Capture loop exited"), teardown=False)

    def capture_to_file(
        self,
        duration_seconds: float,
        output_dir: Path,
        prefix: str,
        *,
        mode: str = "iq",
    ) -> Path:
        if not self._running.is_set() or not self._handle:
            raise RuntimeError("Receiver is not running")

        safe_mode = (mode or "iq").lower()
        if safe_mode not in {"iq", "pcm"}:
            raise ValueError("Capture mode must be 'iq' or 'pcm'")

        if duration_seconds <= 0:
            raise ValueError("Capture duration must be positive")

        total_samples = max(1, int(self.config.sample_rate * float(duration_seconds)))
        timestamp = time.strftime("%Y%m%dT%H%M%S")
        extension = "iq" if safe_mode == "iq" else "pcm"
        filename = f"{prefix}_{timestamp}.{extension}" if prefix else f"capture_{timestamp}.{extension}"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / filename

        ticket = _CaptureTicket(
            identifier=self.config.identifier,
            path=path,
            samples_required=total_samples,
            mode=safe_mode,
            numpy_module=self._handle.numpy,
        )

        with self._capture_lock:
            self._capture_requests.append(ticket)

        timeout = max(5.0, float(duration_seconds) * 2.0)
        completed = ticket.event.wait(timeout=timeout)

        with self._capture_lock:
            if ticket in self._capture_requests:
                self._capture_requests.remove(ticket)

        if not completed:
            ticket.fail(TimeoutError(f"Timed out capturing samples for {self.config.identifier}"))
            raise ticket.error  # type: ignore[misc]

        if ticket.error:
            raise ticket.error

        self._update_status(capture_mode=safe_mode, capture_path=str(path))
        return path

    def _process_capture(self, samples) -> None:
        with self._capture_lock:
            pending = list(self._capture_requests)

        if not pending:
            return

        for ticket in pending:
            if ticket.completed:
                continue
            ticket.write(samples)

        with self._capture_lock:
            self._capture_requests = [ticket for ticket in self._capture_requests if not ticket.completed]

    def _cancel_capture_requests(self, exc: Exception, *, teardown: bool = True) -> None:
        with self._capture_lock:
            pending = self._capture_requests
            self._capture_requests = []

        for ticket in pending:
            ticket.fail(exc)
            # Yield to the scheduler to avoid busy-spinning when readStream returns quickly.
            time.sleep(0.01)

        if teardown:
            self._teardown_handle()
        self._update_status(locked=False)

    def _update_sample_buffer(self, samples) -> None:
        """Update the real-time sample ring buffer with new samples."""
        if self._sample_buffer is None:
            return

        with self._sample_buffer_lock:
            num_samples = len(samples)
            if num_samples >= self._sample_buffer_size:
                # If we got more samples than buffer size, just take the latest
                self._sample_buffer[:] = samples[-self._sample_buffer_size:]
                self._sample_buffer_pos = 0
            else:
                # Write samples to ring buffer
                end_pos = self._sample_buffer_pos + num_samples
                if end_pos <= self._sample_buffer_size:
                    # Samples fit without wrapping
                    self._sample_buffer[self._sample_buffer_pos:end_pos] = samples
                else:
                    # Samples wrap around
                    first_chunk = self._sample_buffer_size - self._sample_buffer_pos
                    self._sample_buffer[self._sample_buffer_pos:] = samples[:first_chunk]
                    self._sample_buffer[:num_samples - first_chunk] = samples[first_chunk:]

                self._sample_buffer_pos = end_pos % self._sample_buffer_size

    def get_samples(self, num_samples: Optional[int] = None):
        """Get recent IQ samples from the receiver for real-time processing.

        Args:
            num_samples: Number of samples to retrieve. If None, returns all available samples.

        Returns:
            numpy array of complex64 samples, or None if receiver is not running
        """
        if not self._running.is_set() or self._sample_buffer is None:
            return None

        with self._sample_buffer_lock:
            if num_samples is None or num_samples >= self._sample_buffer_size:
                # Return entire buffer in correct order
                if self._sample_buffer_pos == 0:
                    return self._sample_buffer.copy()
                else:
                    # Reorder ring buffer to put oldest samples first
                    handle = self._handle
                    if not handle:
                        return None
                    result = handle.numpy.concatenate([
                        self._sample_buffer[self._sample_buffer_pos:],
                        self._sample_buffer[:self._sample_buffer_pos]
                    ])
                    return result
            else:
                # Return most recent num_samples
                if num_samples > self._sample_buffer_size:
                    num_samples = self._sample_buffer_size

                handle = self._handle
                if not handle:
                    return None

                # Calculate start position for most recent samples
                start_pos = (self._sample_buffer_pos - num_samples) % self._sample_buffer_size
                if start_pos < self._sample_buffer_pos:
                    # No wrap
                    return self._sample_buffer[start_pos:self._sample_buffer_pos].copy()
                else:
                    # Wrapped
                    return handle.numpy.concatenate([
                        self._sample_buffer[start_pos:],
                        self._sample_buffer[:self._sample_buffer_pos]
                    ])


class RTLSDRReceiver(_SoapySDRReceiver):
    """Driver for RTL2832U based SDRs via the SoapyRTLSDR module."""

    driver_hint = "rtlsdr"


class AirspyReceiver(_SoapySDRReceiver):
    """Driver for Airspy R2/Mini receivers using the SoapyAirspy module.
    
    Airspy R2 Specific Quirks:
    --------------------------
    1. Sample Rates: ONLY 2.5 MHz and 10 MHz are supported (no decimation)
    2. Gain Structure: Three independent stages (LNA, MIX, VGA) each 0-15
       - Also supports "linearity" and "sensitivity" gain modes
       - setGain() with a single value distributes across stages
    3. Bias-T: Has bias-T for powering external LNAs (off by default)
    4. No device_id: Airspy uses serial numbers only, not device indices
    5. Buffer handling: Uses internal buffering, doesn't support bufflen parameter
    """

    driver_hint = "airspy"
    
    # Airspy R2 ONLY supports these sample rates - others will fail!
    VALID_SAMPLE_RATES = {2500000, 10000000}  # 2.5 MHz and 10 MHz

    def __init__(self, config: ReceiverConfig, *, event_logger=None) -> None:
        # Store the effective sample rate (may differ from config if invalid)
        self._effective_sample_rate: Optional[int] = None
        super().__init__(config, event_logger=event_logger)

    def _open_device(self):
        """Open Airspy device with Airspy-specific configuration."""
        # Validate sample rate before opening - store effective rate without modifying config
        effective_rate = self.config.sample_rate
        if effective_rate not in self.VALID_SAMPLE_RATES:
            closest = min(self.VALID_SAMPLE_RATES, key=lambda x: abs(x - effective_rate))
            self._interface_logger.warning(
                f"Airspy R2 only supports 2.5 MHz and 10 MHz sample rates. "
                f"Configured rate {effective_rate/1e6:.3f} MHz is invalid. "
                f"Using closest valid rate: {closest/1e6:.1f} MHz"
            )
            effective_rate = closest
        
        # Store effective rate for use in _open_device_impl
        self._effective_sample_rate = effective_rate
        
        # Temporarily update config sample rate for parent implementation
        # This is necessary because _SoapySDRReceiver._open_device reads from config
        original_rate = self.config.sample_rate
        try:
            self.config.sample_rate = effective_rate
            handle = super()._open_device()
        finally:
            # Restore original config to avoid side effects
            self.config.sample_rate = original_rate
        
        # Airspy-specific post-configuration
        if handle and handle.device:
            try:
                import SoapySDR
                device = handle.device
                channel = self.config.channel or 0
                
                # Disable Bias-T by default (it powers external LNAs)
                # Only enable if user specifically needs it
                try:
                    device.writeSetting("biastee", "false")
                    self._interface_logger.debug("Disabled Airspy Bias-T")
                except Exception:
                    pass  # Setting may not be available
                    
                # Set Airspy to linearity gain mode for best dynamic range
                # This is better for strong signals like local FM stations
                try:
                    device.writeSetting("gainmode", "linearity")
                    self._interface_logger.debug("Set Airspy to linearity gain mode")
                except Exception:
                    pass  # Setting may not be available
                    
            except Exception as e:
                self._interface_logger.debug(f"Airspy post-configuration skipped: {e}")
        
        return handle


class SoapyRemoteReceiver(_SoapySDRReceiver):
    """Driver for remote SDR devices via SoapyRemote protocol.
    
    This enables connection to:
    - SDR++ Server (recommended for advanced visualization and demodulation)
    - SoapyRemote servers
    - Any SoapySDR-compatible network SDR source
    
    SDR++ Server Setup:
    -------------------
    1. Install SDR++ with server module
    2. Start SDR++ and enable the server module (Module Manager → Add → sdrpp_server)
    3. Configure server to listen on desired port (default: 5259)
    4. In EAS Station, configure receiver with:
       - Driver: "remote" or "soapyremote"
       - Serial: "tcp://hostname:port" (e.g., "tcp://192.168.1.100:5259")
    
    Benefits of SDR++ Server:
    - Professional spectrum analyzer GUI for monitoring
    - Advanced demodulation options
    - Multiple clients can share one SDR device
    - Better signal visualization and tuning
    - Can run on separate hardware from EAS Station
    """

    driver_hint = "remote"

    def _open_handle(self) -> _SoapySDRHandle:
        """Open remote SoapySDR device with network-specific configuration."""
        try:
            import SoapySDR
        except ImportError as exc:
            raise RuntimeError(
                "SoapySDR Python bindings are required for remote SDR receivers."
            ) from exc

        try:
            import numpy
        except ImportError as exc:
            raise RuntimeError("NumPy is required for SoapySDR based receivers.") from exc

        channel = self.config.channel if self.config.channel is not None else 0

        # Build connection arguments for SoapyRemote
        # The serial field should contain the remote address (e.g., "tcp://host:port")
        args: Dict[str, str] = {"driver": "remote"}
        
        if self.config.serial:
            # Validate remote address format
            remote_addr = self.config.serial.strip()
            if not remote_addr.startswith(("tcp://", "udp://")):
                raise RuntimeError(
                    f"Invalid remote address format: '{remote_addr}'. "
                    f"Must start with 'tcp://' or 'udp://'. "
                    f"Example: tcp://192.168.1.100:5259"
                )
            # Basic validation of address structure
            if ":" not in remote_addr[6:]:  # Check for port after protocol
                raise RuntimeError(
                    f"Invalid remote address format: '{remote_addr}'. "
                    f"Must include port number. Example: tcp://192.168.1.100:5259"
                )
            args["remote"] = remote_addr
        else:
            raise RuntimeError(
                "Remote SDR requires a connection address in the 'serial' field. "
                "Format: tcp://hostname:port (e.g., tcp://192.168.1.100:5259 for SDR++ Server)"
            )

        if self.config.identifier:
            args.setdefault("label", self.config.identifier)

        self._interface_logger.info(
            "Connecting to remote SDR at %s for receiver %s",
            self.config.serial,
            self.config.identifier
        )

        try:
            device = SoapySDR.Device(args)
        except Exception as exc:
            message = self._annotate_lock_hint(str(exc))
            raise RuntimeError(
                f"Unable to connect to remote SDR at '{self.config.serial}': {message}. "
                f"Ensure SDR++ Server or SoapyRemote is running and accessible."
            ) from exc

        try:
            device.setSampleRate(SoapySDR.SOAPY_SDR_RX, channel, self.config.sample_rate)
            device.setFrequency(SoapySDR.SOAPY_SDR_RX, channel, self.config.frequency_hz)
            
            # Configure gain if specified
            if self.config.gain is not None:
                device.setGain(SoapySDR.SOAPY_SDR_RX, channel, float(self.config.gain))
            else:
                # Try AGC for remote devices
                try:
                    if device.hasGainMode(SoapySDR.SOAPY_SDR_RX, channel):
                        device.setGainMode(SoapySDR.SOAPY_SDR_RX, channel, True)
                        self._interface_logger.info("Enabled AGC for remote SDR")
                except Exception:
                    pass

            # Setup stream - remote devices may have different buffer requirements
            stream = device.setupStream(
                SoapySDR.SOAPY_SDR_RX,
                SoapySDR.SOAPY_SDR_CF32,
                [channel],
                {}  # Let the remote server handle buffering
            )
            device.activateStream(stream)
            
            # Allow extra time for network connection to stabilize
            time.sleep(NETWORK_STABILIZATION_DELAY)
            
            self._interface_logger.info(
                "Successfully connected to remote SDR at %s",
                self.config.serial
            )
            
        except Exception as exc:
            try:
                device.close()
            except Exception:
                pass
            message = self._annotate_lock_hint(str(exc))
            raise RuntimeError(f"Failed to configure remote SDR device: {message}") from exc

        return _SoapySDRHandle(device=device, stream=stream, sdr_module=SoapySDR, numpy_module=numpy)


def register_builtin_drivers(manager: RadioManager) -> None:
    """Register the built-in SDR drivers against a radio manager instance."""

    manager.register_driver("rtl2832u", RTLSDRReceiver)
    manager.register_driver("rtl-sdr", RTLSDRReceiver)
    manager.register_driver("rtlsdr", RTLSDRReceiver)

    manager.register_driver("airspy", AirspyReceiver)

    # Remote/Network SDR support (for SDR++ Server, SoapyRemote, etc.)
    manager.register_driver("remote", SoapyRemoteReceiver)
    manager.register_driver("soapyremote", SoapyRemoteReceiver)
    manager.register_driver("sdrpp", SoapyRemoteReceiver)  # Alias for SDR++ Server


__all__ = [
    "AirspyReceiver",
    "RTLSDRReceiver",
    "SoapyRemoteReceiver",
    "register_builtin_drivers",
]
