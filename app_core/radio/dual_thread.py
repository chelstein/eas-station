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

"""Dual-thread SDR receiver implementation for reliable operation.

This module provides a robust SDR receiver implementation that separates
USB reading from sample processing using a producer-consumer architecture.
This design is inspired by dump1090 and other SDR applications that achieve
months of uninterrupted 24/7 operation.

Architecture:
                    ┌─────────────────┐
                    │   SoapySDR      │
                    │   USB Device    │
                    └────────┬────────┘
                             │ USB Transfers
                             ▼
            ┌────────────────────────────────────┐
            │      USB Reader Thread             │
            │  (Producer - Time Critical)        │
            │                                    │
            │  - Reads USB as fast as possible   │
            │  - Never blocks on processing      │
            │  - Writes to ring buffer           │
            └────────────────┬───────────────────┘
                             │ Lock-free ring buffer
                             ▼
            ┌────────────────────────────────────┐
            │      Processing Thread             │
            │  (Consumer - Can Block)            │
            │                                    │
            │  - Reads from ring buffer          │
            │  - FFT computation                 │
            │  - Signal strength calculation     │
            │  - Audio sample buffer updates     │
            │  - File capture handling           │
            └────────────────────────────────────┘

Key benefits:
1. USB reads never blocked by FFT or other processing
2. Ring buffer absorbs USB latency jitter
3. Processing delays don't cause USB overflow
4. Clean separation of concerns
5. Independent error recovery for each thread
"""

from __future__ import annotations

import datetime
import logging
import threading
import time
from typing import Optional, TYPE_CHECKING

from .ring_buffer import SDRRingBuffer, calculate_buffer_size

if TYPE_CHECKING:
    from .manager import ReceiverConfig

logger = logging.getLogger(__name__)


class DualThreadSDRMixin:
    """Mixin providing dual-thread USB reader and processing architecture.
    
    This mixin is designed to be used with _SoapySDRReceiver to replace
    the single-threaded _capture_loop with a proper producer-consumer
    architecture.
    
    The mixin provides:
    - _usb_reader_loop: Producer thread that only reads USB
    - _processing_loop: Consumer thread that handles all processing
    - Proper lifecycle management for both threads
    - Health monitoring and statistics
    """
    
    # Buffer configuration
    _USB_READ_TIMEOUT_US = 100000  # 100ms USB read timeout
    _PROCESS_CHUNK_SIZE = 32768   # Samples per processing iteration
    _RING_BUFFER_SECONDS = 1.0    # 1 second of ring buffer
    
    def _init_dual_thread(self) -> None:
        """Initialize dual-thread state. Call from __init__."""
        self._usb_reader_thread: Optional[threading.Thread] = None
        self._processing_thread: Optional[threading.Thread] = None
        self._ring_buffer: Optional[SDRRingBuffer] = None
        self._handle_lock = threading.Lock()
        self._handle_ready = threading.Event()
    
    def _start_dual_threads(self) -> None:
        """Start both USB reader and processing threads."""
        base_name = f"{self.__class__.__name__}-{self.config.identifier}"
        
        self._usb_reader_thread = threading.Thread(
            target=self._usb_reader_loop,
            name=f"{base_name}-USB",
            daemon=True
        )
        self._processing_thread = threading.Thread(
            target=self._processing_loop,
            name=f"{base_name}-Process",
            daemon=True
        )
        
        self._usb_reader_thread.start()
        self._processing_thread.start()
        
        logger.info(
            "Started dual-thread SDR receiver for %s (USB reader + processing)",
            self.config.identifier
        )
    
    def _stop_dual_threads(self) -> None:
        """Stop both threads gracefully."""
        # Signal ring buffer to wake up processing thread
        if self._ring_buffer:
            self._ring_buffer.signal_shutdown()
        
        # Wait for threads to finish
        if self._usb_reader_thread:
            self._usb_reader_thread.join(timeout=2.0)
            if self._usb_reader_thread.is_alive():
                logger.warning("USB reader thread did not stop cleanly")
        
        if self._processing_thread:
            self._processing_thread.join(timeout=2.0)
            if self._processing_thread.is_alive():
                logger.warning("Processing thread did not stop cleanly")
        
        self._handle_ready.clear()
    
    def _initialize_ring_buffer(self, numpy_module) -> None:
        """Initialize the ring buffer for USB jitter absorption."""
        buffer_size = calculate_buffer_size(
            self.config.sample_rate,
            self._RING_BUFFER_SECONDS
        )
        
        self._ring_buffer = SDRRingBuffer(
            size=buffer_size,
            numpy_module=numpy_module,
            identifier=self.config.identifier
        )
    
    def _usb_reader_loop(self) -> None:
        """USB Reader Thread: Only reads USB data, writes to ring buffer.
        
        This thread has ONE job: read samples from the SDR as fast as possible
        and write them to the ring buffer. It NEVER does any processing that
        could cause USB underflows.
        
        This is the key to reliable SDR operation like dump1090.
        """
        handle = None
        buffer = None
        capture_buffer_size = self._calculate_buffer_size()
        retry_delay = self._retry_backoff
        consecutive_failures = 0
        
        # Wait for initial handle to be ready
        if self._handle_ready.wait(timeout=0.1):
            with self._handle_lock:
                handle = self._handle
                if handle is not None:
                    buffer = handle.numpy.zeros(capture_buffer_size, dtype=handle.numpy.complex64)
        
        logger.info("USB reader thread started for %s", self.config.identifier)
        
        while self._running.is_set():
            # Handle reconnection if needed
            if handle is None:
                if not self._running.is_set():
                    break
                
                consecutive_failures += 1
                self._connection_attempts += 1
                
                try:
                    logger.info(
                        "USB Reader: Opening device for %s (attempt #%d)...",
                        self.config.identifier,
                        consecutive_failures
                    )
                    new_handle = self._open_handle()
                    consecutive_failures = 0
                    self._last_successful_connection = datetime.datetime.now(datetime.timezone.utc)
                    
                    with self._handle_lock:
                        self._handle = new_handle
                        self._initialize_sample_buffer(new_handle.numpy)
                        self._initialize_ring_buffer(new_handle.numpy)
                        self._handle_ready.set()
                    
                    handle = new_handle
                    buffer = handle.numpy.zeros(capture_buffer_size, dtype=handle.numpy.complex64)
                    
                    logger.info(
                        "USB Reader: Device opened for %s",
                        self.config.identifier
                    )
                    retry_delay = self._retry_backoff
                    continue
                    
                except Exception as exc:
                    self._connection_failures += 1
                    self._update_status(
                        locked=False,
                        last_error=str(exc),
                        context="usb_reader_open",
                    )
                    time.sleep(min(retry_delay, self._max_retry_backoff))
                    retry_delay = min(retry_delay * 2.0, self._max_retry_backoff)
                    continue
            
            # Read samples from USB - this is time-critical
            try:
                result = handle.device.readStream(
                    handle.stream,
                    [buffer],
                    len(buffer),
                    timeoutUs=self._USB_READ_TIMEOUT_US
                )
                
                if result.ret < 0:
                    error_code = result.ret
                    
                    # TIMEOUT (-1) - retry immediately
                    if error_code == -1:
                        self._consecutive_timeouts += 1
                        if self._consecutive_timeouts > self._max_consecutive_timeouts:
                            raise RuntimeError(
                                f"SDR timed out {self._consecutive_timeouts} times consecutively"
                            )
                        continue
                    else:
                        self._consecutive_timeouts = 0
                    
                    # OVERFLOW (-4) - log but continue (ring buffer will handle)
                    if error_code == -4:
                        self._stream_errors_count += 1
                        if self._stream_errors_count == 1 or self._stream_errors_count % 100 == 0:
                            logger.warning(
                                "USB Reader: SoapySDR overflow for %s (total: %d)",
                                self.config.identifier,
                                self._stream_errors_count
                            )
                        continue
                    
                    # NOT_LOCKED (-7) - transient, continue
                    if error_code == -7:
                        self._stream_errors_count += 1
                        continue
                    
                    # Other errors require reconnection
                    message = self._describe_soapysdr_error(error_code)
                    raise RuntimeError(message)
                
                # Success - reset timeout counter
                self._consecutive_timeouts = 0
                
                if result.ret > 0:
                    # Write to ring buffer - this is the ONLY thing we do with samples here
                    if self._ring_buffer is not None:
                        samples = buffer[:result.ret]
                        written = self._ring_buffer.write(samples)
                        if written < result.ret:
                            # Ring buffer overflow - processing thread is too slow
                            # This is logged by the ring buffer, we just continue
                            pass
                
            except Exception as exc:
                consecutive_failures += 1
                self._stream_errors_count += 1
                logger.warning(
                    "USB Reader: Error for %s (failure #%d): %s",
                    self.config.identifier,
                    consecutive_failures,
                    exc
                )
                self._update_status(
                    locked=False,
                    last_error=str(exc),
                    context="usb_reader",
                )
                
                # Teardown and prepare for reconnection
                self._teardown_handle(handle)
                with self._handle_lock:
                    self._handle = None
                    self._handle_ready.clear()
                handle = None
                buffer = None
                
                if self._ring_buffer:
                    self._ring_buffer.reset()
                
                if not self._running.is_set():
                    break
                time.sleep(min(retry_delay, self._max_retry_backoff))
                retry_delay = min(retry_delay * 2.0, self._max_retry_backoff)
        
        logger.info("USB reader thread exiting for %s", self.config.identifier)
    
    def _processing_loop(self) -> None:
        """Processing Thread: Reads from ring buffer, does all processing.
        
        This thread handles:
        - FFT computation for spectrum display
        - Signal strength calculation
        - Audio sample buffer updates
        - File capture handling
        
        Processing delays here do NOT affect USB reading because the
        ring buffer decouples the two operations.
        """
        last_spectrum_time = 0.0
        numpy_module = None
        
        logger.info("Processing thread started for %s", self.config.identifier)
        
        # Wait for ring buffer to be initialized
        while self._running.is_set() and self._ring_buffer is None:
            if self._handle_ready.wait(timeout=0.1):
                with self._handle_lock:
                    if self._handle is not None:
                        numpy_module = self._handle.numpy
                break
        
        while self._running.is_set():
            # Get numpy module if we don't have it
            if numpy_module is None:
                with self._handle_lock:
                    if self._handle is not None:
                        numpy_module = self._handle.numpy
                if numpy_module is None:
                    time.sleep(0.01)
                    continue
            
            # Check ring buffer
            if self._ring_buffer is None:
                time.sleep(0.01)
                continue
            
            # Read samples from ring buffer
            samples = self._ring_buffer.read(
                self._PROCESS_CHUNK_SIZE,
                timeout=0.1
            )
            
            if samples is None or len(samples) == 0:
                # No data available, continue waiting
                continue
            
            try:
                # 1. Compute Spectrum (if interval elapsed)
                now = time.time()
                if now - last_spectrum_time > self._spectrum_update_interval:
                    self._compute_spectrum(samples, numpy_module)
                    last_spectrum_time = now
                
                # 2. Update Signal Strength
                magnitude = float(numpy_module.mean(numpy_module.abs(samples)))
                max_magnitude = float(numpy_module.max(numpy_module.abs(samples)))
                
                # Log diagnostic warning if signal looks like DC
                if max_magnitude > 0:
                    dynamic_range = max_magnitude / max(magnitude, self._MIN_MAGNITUDE)
                    if dynamic_range < self._MIN_DYNAMIC_RANGE and self._stream_errors_count == 0:
                        logger.warning(
                            "Processing: Low dynamic range for %s (%.2f). "
                            "May indicate DC offset or no antenna.",
                            self.config.identifier,
                            dynamic_range
                        )
                
                self._update_status(locked=True, signal_strength=magnitude)
                
                # 3. Update Audio Sample Buffer
                self._update_sample_buffer(samples)
                
                # 4. Process Capture Requests
                self._process_capture(samples)
                
            except Exception as exc:
                logger.error(
                    "Processing: Error for %s: %s",
                    self.config.identifier,
                    exc,
                    exc_info=True
                )
                # Don't crash the processing loop - continue with next samples
                time.sleep(0.01)
        
        self._cancel_capture_requests(RuntimeError("Processing loop exited"), teardown=False)
        logger.info("Processing thread exiting for %s", self.config.identifier)
    
    def get_ring_buffer_stats(self) -> Optional[dict]:
        """Get ring buffer health statistics."""
        if self._ring_buffer is None:
            return None
        return self._ring_buffer.get_stats().to_dict()
