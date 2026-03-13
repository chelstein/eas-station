"""
EAS Station - Emergency Alert System
Copyright (c) 2025-2026 Timothy Kramer (KR8MER)

Streaming SAME/EAS Decoder

This module implements a real-time streaming decoder for SAME (Specific Area Message Encoding)
headers, processing audio samples continuously as they arrive - similar to how commercial
EAS decoders like DASDEC and multimon-ng operate.

CRITICAL: This is a life-safety system. The decoder MUST process every audio sample
with zero dropouts or gaps. Commercial EAS decoders operate this way.
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Callable, Tuple

import numpy as np

from app_utils.eas_fsk import SAME_BAUD, SAME_MARK_FREQ, SAME_SPACE_FREQ
from app_utils import utc_now
from app_utils.eas_decode import (
    _compute_burst_timing_gaps_ms,
    _detect_endec_mode,
    ENDEC_MODE_UNKNOWN,
)

logger = logging.getLogger(__name__)


@dataclass
class StreamingSAMEAlert:
    """Detected SAME alert from streaming decoder."""
    message: str
    confidence: float
    timestamp: datetime
    raw_bits: List[int]
    endec_mode: str = ENDEC_MODE_UNKNOWN
    burst_timing_gaps_ms: List[float] = field(default_factory=list)


class StreamingSAMEDecoder:
    """
    Real-time streaming SAME decoder.

    Processes audio samples continuously as they arrive, maintaining decoder state
    across calls. This mimics commercial EAS decoder behavior (DASDEC, multimon-ng).

    Based on multimon-ng correlation+DLL algorithm but refactored for streaming operation
    with batch-vectorized correlation to minimize CPU usage on embedded hardware.

    Usage:
        decoder = StreamingSAMEDecoder(sample_rate=16000, callback=handle_alert)

        # In audio loop:
        while audio_streaming:
            samples = get_audio_chunk()  # Get new samples
            decoder.process_samples(samples)  # Process immediately

        # Callback is invoked when alert is detected
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        alert_callback: Optional[Callable[['StreamingSAMEAlert'], None]] = None
    ):
        """
        Initialize streaming SAME decoder.

        Args:
            sample_rate: Audio sample rate in Hz
            alert_callback: Function called when alert detected
        """
        self.sample_rate = sample_rate
        self.alert_callback = alert_callback

        # SAME FSK parameters
        self.baud_rate = float(SAME_BAUD)  # 520.83 baud
        self.mark_freq = SAME_MARK_FREQ     # 2083.3 Hz (logic 1)
        self.space_freq = SAME_SPACE_FREQ   # 1562.5 Hz (logic 0)

        # Correlation parameters
        self.SUBSAMP = 2  # Downsampling factor
        self.corr_len = int(sample_rate / self.baud_rate)  # Samples per bit

        # Generate correlation tables as numpy float32 arrays for vectorized ops
        self._mark_i, self._mark_q, self._space_i, self._space_q = (
            self._generate_correlation_tables()
        )

        # Initialize bandpass filter coefficients once (never recomputed on reset)
        self._init_bandpass_filter()

        # Decoder state variables (persistent across process_samples calls)
        self._reset_decoder_state()

        # Statistics
        self.samples_processed = 0
        self.alerts_detected = 0
        self.bytes_decoded = 0

        logger.info(
            f"Initialized StreamingSAMEDecoder: sample_rate={sample_rate}Hz, "
            f"baud_rate={self.baud_rate:.2f}, corr_len={self.corr_len} samples/bit"
        )

    # ------ backward-compatible aliases for correlation tables ------
    @property
    def mark_i(self):
        return self._mark_i

    @property
    def mark_q(self):
        return self._mark_q

    @property
    def space_i(self):
        return self._space_i

    @property
    def space_q(self):
        return self._space_q

    def _init_bandpass_filter(self) -> None:
        """Initialize scipy IIR bandpass filter for noise rejection.

        Centered between SAME mark (2083.3 Hz) and space (1562.5 Hz) frequencies.
        Matches EAS-Tools decoder-bundle.js SoftwareBandpass(1822.9 Hz, Q=3).
        Filter state is preserved across process_samples() calls for seamless
        streaming operation. Falls back silently if scipy is unavailable.
        """
        self._bandpass_sos = None
        self._bandpass_zi = None
        self._bandpass_available = False
        try:
            from scipy.signal import butter
            nyq = self.sample_rate / 2.0
            low = 1200.0 / nyq
            high = min(2500.0, nyq * 0.95) / nyq
            if 0 < low < high < 1.0:
                self._bandpass_sos = butter(4, [low, high], btype="bandpass", output="sos")
                self._bandpass_zi = np.zeros((self._bandpass_sos.shape[0], 2))
                self._bandpass_available = True
                logger.debug(
                    "Bandpass filter initialized: 1200–2500 Hz, 4th-order Butterworth "
                    "(sample_rate=%d Hz)", self.sample_rate
                )
        except Exception as exc:
            logger.debug("Bandpass filter unavailable: %s", exc)

    def _reset_decoder_state(self) -> None:
        """Reset decoder state variables."""
        # DLL (Delay-Locked Loop) state
        self.dcd_shreg = 0  # Shift register for bit history
        self.dcd_integrator = 0  # Integrator for noise immunity
        self.sphase = 1  # Sampling phase (16-bit fixed point)
        self.lasts = 0  # Last 8 bits received
        self.byte_counter = 0  # Bits received in current byte
        self.synced = False  # Whether we've found preamble

        # Message assembly state
        self.current_msg = []
        self.in_message = False

        # Confidence tracking
        self.bit_confidences = []

        # Prefix buffer: holds the last (corr_len - 1) samples so that the
        # first correlation window of the next chunk has context.
        self._prefix = np.zeros(self.corr_len - 1, dtype=np.float32)
        self._buffer_primed = False  # True once we've received >= corr_len samples
        self._warmup_remaining = self.corr_len  # Samples needed before processing starts

        # Legacy buffer attributes kept for test compatibility
        self.sample_buffer = np.zeros(self.corr_len, dtype=np.float32)
        self.buffer_pos = 0
        self._correlation_window = np.zeros(self.corr_len, dtype=np.float32)

        # Constants
        self.PREAMBLE_BYTE = 0xAB
        self.DLL_GAIN = 0.4
        self.INTEGRATOR_MAX = 12
        self.MAX_MSG_LEN = 268
        self.sphaseinc = int(0x10000 * self.baud_rate / self.sample_rate)

        # Bandpass filter state — reset to zero initial conditions on full restart
        if getattr(self, "_bandpass_available", False) and self._bandpass_sos is not None:
            self._bandpass_zi = np.zeros((self._bandpass_sos.shape[0], 2))

        # ENDEC mode detection state
        self._burst_start_sample: Optional[int] = None
        self._burst_sample_history: List[Tuple[int, int]] = []
        self.endec_mode: str = ENDEC_MODE_UNKNOWN
        self.burst_timing_gaps_ms: List[float] = []

    def reset(self) -> None:
        """
        Reset decoder to initial state.

        Call this when the monitor thread restarts to ensure consistent
        statistics and state. This resets all counters including samples_processed.
        """
        self._reset_decoder_state()
        self.samples_processed = 0
        self.alerts_detected = 0
        self.bytes_decoded = 0
        logger.debug("StreamingSAMEDecoder reset to initial state")

    def _generate_correlation_tables(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Generate correlation tables for mark and space frequencies as numpy arrays."""
        t = 2.0 * np.pi * np.arange(self.corr_len, dtype=np.float64) / self.sample_rate
        mark_i = np.cos(self.mark_freq * t).astype(np.float32)
        mark_q = np.sin(self.mark_freq * t).astype(np.float32)
        space_i = np.cos(self.space_freq * t).astype(np.float32)
        space_q = np.sin(self.space_freq * t).astype(np.float32)
        return mark_i, mark_q, space_i, space_q

    def process_samples(self, samples: np.ndarray) -> None:
        """
        Process audio samples in real-time using batch-vectorized correlation.

        CPU optimization strategy:
        1. Prepend the prefix buffer (last corr_len-1 samples from previous call)
           to the incoming chunk to form a contiguous linear buffer.
        2. Build a (N, corr_len) sliding-window matrix using stride_tricks (zero-copy).
        3. Compute all 4 correlations with a single matrix multiplication each,
           replacing N×4 individual np.dot calls with 4 BLAS-accelerated matmuls.
        4. Loop through the pre-computed correlation values for DLL state decisions
           (inherently sequential due to state dependencies).

        For a typical 100ms chunk at 16kHz (N=1600), this reduces numpy call overhead
        from ~6400 np.dot calls to 4 matrix multiplications - roughly 1600× fewer
        Python→C boundary crossings.

        Args:
            samples: Audio samples as numpy array (float32, normalized to [-1.0, 1.0])
        """
        if len(samples) == 0:
            return

        num_samples = len(samples)
        self.samples_processed += num_samples

        # Ensure input is float32 for consistent dtype
        if samples.dtype != np.float32:
            samples = samples.astype(np.float32)

        # Apply stateful IIR bandpass filter to reject out-of-band noise.
        # Filter state (zi) is preserved across chunks for seamless streaming.
        if self._bandpass_available and self._bandpass_sos is not None:
            try:
                from scipy.signal import sosfilt
                filtered, self._bandpass_zi = sosfilt(
                    self._bandpass_sos,
                    samples.astype(np.float64),
                    zi=self._bandpass_zi,
                )
                samples = filtered.astype(np.float32)
            except Exception:
                pass  # Fallback: continue with unfiltered samples

        # Handle warmup: need corr_len samples before processing starts
        if self._warmup_remaining > 0:
            if num_samples < self._warmup_remaining:
                # Not enough samples yet; update prefix and wait
                self._warmup_remaining -= num_samples
                # Store what we have so far in the prefix
                keep = min(num_samples, self.corr_len - 1)
                if keep > 0:
                    if num_samples >= self.corr_len - 1:
                        self._prefix[:] = samples[-(self.corr_len - 1):]
                    else:
                        # Shift prefix left and append new samples
                        self._prefix = np.roll(self._prefix, -num_samples)
                        self._prefix[-num_samples:] = samples
                return
            else:
                # We have enough to start processing
                warmup_count = self._warmup_remaining
                self._warmup_remaining = 0
                self._buffer_primed = True
                # The warmup samples fill the prefix
                prefix_len = self.corr_len - 1
                if warmup_count >= prefix_len:
                    self._prefix[:] = samples[warmup_count - prefix_len:warmup_count]
                else:
                    shift = prefix_len - warmup_count
                    self._prefix[:shift] = self._prefix[warmup_count:]
                    self._prefix[shift:] = samples[:warmup_count]
                # Process the remaining samples after warmup
                samples = samples[warmup_count:]
                num_samples = len(samples)
                if num_samples == 0:
                    return

        # ---- Phase 1: Build contiguous linear buffer ----
        # Prepend prefix (last corr_len-1 samples from previous call) to new samples
        prefix_len = self.corr_len - 1
        linear = np.empty(prefix_len + num_samples, dtype=np.float32)
        linear[:prefix_len] = self._prefix
        linear[prefix_len:] = samples

        # Save the new prefix for next call (last corr_len-1 samples)
        self._prefix[:] = linear[-(self.corr_len - 1):]

        # ---- Phase 2: Build sliding window matrix (zero-copy) ----
        # Each row is a correlation window of corr_len samples
        # Shape: (num_samples, corr_len)
        windows = np.lib.stride_tricks.sliding_window_view(linear, self.corr_len)
        # windows has shape (prefix_len + num_samples - corr_len + 1, corr_len)
        # = (num_samples, corr_len) since prefix_len = corr_len - 1

        # ---- Phase 3: Batch correlation via matrix multiply ----
        # 4 BLAS-accelerated matmuls replace 4*N individual np.dot calls
        mark_i_all = windows @ self._mark_i     # (num_samples,)
        mark_q_all = windows @ self._mark_q     # (num_samples,)
        space_i_all = windows @ self._space_i   # (num_samples,)
        space_q_all = windows @ self._space_q   # (num_samples,)

        mark_power = mark_i_all * mark_i_all + mark_q_all * mark_q_all
        space_power = space_i_all * space_i_all + space_q_all * space_q_all
        correlations = mark_power - space_power
        total_powers = mark_power + space_power

        # ---- Phase 4: Sequential DLL + bit decision processing ----
        # The DLL state machine is inherently sequential (each sample depends
        # on previous state), but now we operate on pre-computed float scalars
        # instead of calling np.dot 4 times per sample.
        for i in range(num_samples):
            self._process_dll_and_bits(float(correlations[i]), float(total_powers[i]))

    def _process_dll_and_bits(self, correlation: float, total_power: float) -> None:
        """
        Process DLL timing recovery and bit decisions for one sample.

        This handles the sequential state machine that cannot be vectorized:
        shift register updates, integrator, DLL phase adjustment, and bit assembly.

        Args:
            correlation: Pre-computed (mark_power - space_power) for this sample
            total_power: Pre-computed (mark_power + space_power) for this sample
        """
        # Update DCD shift register
        self.dcd_shreg = (self.dcd_shreg << 1) & 0xFFFFFFFF
        if correlation > 0:
            self.dcd_shreg |= 1

        # Update integrator
        if correlation > 0 and self.dcd_integrator < self.INTEGRATOR_MAX:
            self.dcd_integrator += 1
        elif correlation < 0 and self.dcd_integrator > -self.INTEGRATOR_MAX:
            self.dcd_integrator -= 1

        # DLL: Check for bit transitions and adjust timing
        if (self.dcd_shreg ^ (self.dcd_shreg >> 1)) & 1:
            if self.sphase < 0x8000:
                if self.sphase > self.sphaseinc // 2:
                    adjustment = min(int(self.sphase * self.DLL_GAIN), 8192)
                    self.sphase -= adjustment
            else:
                if self.sphase < 0x10000 - self.sphaseinc // 2:
                    adjustment = min(int((0x10000 - self.sphase) * self.DLL_GAIN), 8192)
                    self.sphase += adjustment

        # Advance sampling phase
        self.sphase += self.sphaseinc

        # End of bit period?
        if self.sphase >= 0x10000:
            self.sphase &= 0xFFFF
            self.lasts = (self.lasts >> 1) & 0x7F

            # Make bit decision based on integrator
            if self.dcd_integrator >= 0:
                self.lasts |= 0x80

            curbit = (self.lasts >> 7) & 1

            # Estimate confidence for this bit
            if self.synced or self.in_message:
                if total_power > 0:
                    bit_confidence = min(abs(correlation) / total_power, 1.0)
                else:
                    bit_confidence = 0.0
                self.bit_confidences.append(bit_confidence)

            # Check for preamble sync
            if (self.lasts & 0xFF) == self.PREAMBLE_BYTE and not self.in_message:
                self.synced = True
                self.byte_counter = 0
            elif self.synced:
                self.byte_counter += 1
                if self.byte_counter == 8:
                    # Got a complete byte
                    byte_val = self.lasts & 0xFF
                    self.bytes_decoded += 1

                    # Check if it's a valid ASCII character
                    if 32 <= byte_val <= 126 or byte_val in (10, 13):
                        char = chr(byte_val)

                        if not self.in_message and char == 'Z':
                            # Possible start of ZCZC — record burst start for timing
                            self.in_message = True
                            self._burst_start_sample = self.samples_processed
                            self.current_msg = [char]
                        elif self.in_message:
                            self.current_msg.append(char)

                            # Check for end of message
                            msg_text = ''.join(self.current_msg)

                            # Check if message is complete
                            if self._is_message_complete(msg_text, char):
                                self._emit_alert(msg_text)
                                self._reset_message_state()
                            elif len(self.current_msg) > self.MAX_MSG_LEN:
                                # Runaway message exceeded max length without a valid
                                # SAME header (no ZCZC/NNNN found).  Reset so preamble
                                # detection is not permanently blocked by in_message=True.
                                logger.debug(
                                    "Message exceeded MAX_MSG_LEN (%d chars) without "
                                    "valid SAME header — resetting decoder state",
                                    self.MAX_MSG_LEN,
                                )
                                self._reset_message_state()
                    else:
                        # Invalid character, lost sync
                        self.synced = False
                        if self.in_message:
                            self._reset_message_state()

                    self.byte_counter = 0

    # Keep old method name as alias for any external callers
    def _process_one_sample_at(self, logical_buffer_pos: int) -> None:
        """Legacy per-sample method - redirects to vectorized path."""
        # This should not be called in the optimized path, but kept for compatibility.
        # Compute correlation manually for a single sample.
        if logical_buffer_pos == 0:
            correlation_window = self.sample_buffer
        else:
            tail_len = self.corr_len - logical_buffer_pos
            self._correlation_window[:tail_len] = self.sample_buffer[logical_buffer_pos:]
            self._correlation_window[tail_len:] = self.sample_buffer[:logical_buffer_pos]
            correlation_window = self._correlation_window

        mark_i_corr = np.dot(correlation_window, self._mark_i)
        mark_q_corr = np.dot(correlation_window, self._mark_q)
        space_i_corr = np.dot(correlation_window, self._space_i)
        space_q_corr = np.dot(correlation_window, self._space_q)

        mark_power = mark_i_corr**2 + mark_q_corr**2
        space_power = space_i_corr**2 + space_q_corr**2
        correlation = mark_power - space_power
        total_power = mark_power + space_power

        self._process_dll_and_bits(float(correlation), float(total_power))

    def _is_message_complete(self, msg_text: str, last_char: str) -> bool:
        """Check if SAME message is complete."""
        # Carriage return or line feed terminates message
        if last_char in ('\r', '\n'):
            return 'ZCZC' in msg_text or 'NNNN' in msg_text

        # Check for proper SAME format completion
        if last_char == '-' and len(self.current_msg) > 40:
            dash_count = msg_text.count('-')
            location_count = 0
            has_time_section = '+' in msg_text

            if has_time_section:
                try:
                    pre_expiration, _ = msg_text.split('+', 1)
                    location_segments = pre_expiration.split('-')[3:]
                    for segment in location_segments:
                        cleaned = segment.strip()
                        if len(cleaned) == 6 and cleaned.isdigit():
                            location_count += 1

                    if location_count <= 0:
                        min_dashes = 6
                    else:
                        min_dashes = 6 + max(location_count - 1, 0)

                    if dash_count >= min_dashes:
                        return 'ZCZC' in msg_text or 'NNNN' in msg_text
                except (ValueError, IndexError, AttributeError) as e:
                    # Ignore parse errors in message validation - not critical
                    logger.debug(f"Error parsing message structure: {e}")

        # Safety: prevent runaway messages
        if len(self.current_msg) > self.MAX_MSG_LEN:
            return 'ZCZC' in msg_text or 'NNNN' in msg_text

        return False

    def _reset_message_state(self) -> None:
        """Reset message assembly state."""
        self.current_msg = []
        self.in_message = False
        self.synced = False
        self.bit_confidences = []
        self._burst_start_sample = None

    def _emit_alert(self, msg_text: str) -> None:
        """Emit decoded alert via callback."""
        msg_text = msg_text.strip()

        # Calculate average confidence
        if self.bit_confidences:
            confidence = sum(self.bit_confidences) / len(self.bit_confidences)
        else:
            confidence = 0.0

        # Record burst end and update ENDEC mode fingerprint
        if self._burst_start_sample is not None:
            self._burst_sample_history.append(
                (self._burst_start_sample, self.samples_processed)
            )
            self._burst_start_sample = None
            # Keep only the last 4 bursts for gap calculation
            if len(self._burst_sample_history) > 4:
                self._burst_sample_history = self._burst_sample_history[-4:]
            self.burst_timing_gaps_ms = _compute_burst_timing_gaps_ms(
                self._burst_sample_history, self.sample_rate
            )
            if self.burst_timing_gaps_ms:
                self.endec_mode = _detect_endec_mode([msg_text], self.burst_timing_gaps_ms)

        # Create alert object
        alert = StreamingSAMEAlert(
            message=msg_text,
            confidence=confidence,
            timestamp=utc_now(),
            raw_bits=list(self.bit_confidences),
            endec_mode=self.endec_mode,
            burst_timing_gaps_ms=list(self.burst_timing_gaps_ms),
        )

        self.alerts_detected += 1

        logger.info(
            f"SAME Alert Detected: {msg_text[:50]}... "
            f"(confidence: {confidence:.1%}, endec={self.endec_mode}, "
            f"alert #{self.alerts_detected})"
        )

        # Invoke callback
        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}", exc_info=True)

    def get_stats(self) -> dict:
        """Get decoder statistics."""
        return {
            'samples_processed': self.samples_processed,
            'alerts_detected': self.alerts_detected,
            'bytes_decoded': self.bytes_decoded,
            'synced': self.synced,
            'in_message': self.in_message,
            'current_message_length': len(self.current_msg),
            'endec_mode': self.endec_mode,
            'burst_timing_gaps_ms': list(self.burst_timing_gaps_ms),
            'bandpass_filter_active': self._bandpass_available,
        }


__all__ = ['StreamingSAMEDecoder', 'StreamingSAMEAlert', 'ENDEC_MODE_UNKNOWN']
