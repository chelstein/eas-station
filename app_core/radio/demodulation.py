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

"""
Audio demodulation for SDR receivers.

Supports FM (wideband and narrowband), AM, and includes stereo decoding and RBDS extraction.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Try to import Numba for JIT compilation of hot DSP functions
# Falls back to pure NumPy if Numba is not available
_NUMBA_AVAILABLE = False
try:
    from numba import jit, prange
    _NUMBA_AVAILABLE = True
    logger.info("Numba JIT compilation available - FM demodulation will use optimized code paths")
except ImportError:
    logger.info("Numba not available - FM demodulation will use pure NumPy (slower)")
    # Create a no-op decorator for when numba isn't available
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    prange = range


# =============================================================================
# JIT-compiled DSP functions for real-time FM demodulation
# These functions are the hot path and benefit significantly from JIT compilation
# =============================================================================

@jit(nopython=True, cache=True, fastmath=True)
def _fm_discriminator_numba(iq_real: np.ndarray, iq_imag: np.ndarray) -> np.ndarray:
    """JIT-compiled FM phase discriminator.

    Extracts instantaneous frequency from IQ samples using the arctangent
    of the product of consecutive samples. This is the core FM demodulation
    algorithm and runs millions of times per second.

    Args:
        iq_real: Real component of IQ samples (float32)
        iq_imag: Imaginary component of IQ samples (float32)

    Returns:
        Audio samples as phase differences (float32)
    """
    n = len(iq_real) - 1
    audio = np.empty(n, dtype=np.float32)

    for i in prange(n):
        # Compute: angle(iq[i+1] * conj(iq[i]))
        # = angle((r1 + j*i1) * (r0 - j*i0))
        # = angle((r1*r0 + i1*i0) + j*(i1*r0 - r1*i0))
        r0, i0 = iq_real[i], iq_imag[i]
        r1, i1 = iq_real[i + 1], iq_imag[i + 1]

        real_part = r1 * r0 + i1 * i0
        imag_part = i1 * r0 - r1 * i0

        audio[i] = np.arctan2(imag_part, real_part)

    return audio


@jit(nopython=True, cache=True, fastmath=True)
def _fast_decimate_numba(samples: np.ndarray, factor: int) -> np.ndarray:
    """JIT-compiled fast decimation by averaging.

    Reduces sample rate by averaging groups of samples. Much faster than
    convolution-based decimation for real-time processing.

    Args:
        samples: Input samples (float32)
        factor: Decimation factor (e.g., 10 means 10:1 reduction)

    Returns:
        Decimated samples (float32)
    """
    n_out = len(samples) // factor
    output = np.empty(n_out, dtype=np.float32)

    for i in prange(n_out):
        acc = np.float32(0.0)
        base = i * factor
        for j in range(factor):
            acc += samples[base + j]
        output[i] = acc / factor

    return output


def fm_discriminator(iq_samples: np.ndarray) -> np.ndarray:
    """FM phase discriminator - dispatches to JIT or NumPy implementation.

    Args:
        iq_samples: Complex IQ samples (complex64)

    Returns:
        Audio samples (float32)
    """
    if _NUMBA_AVAILABLE and len(iq_samples) > 100:
        # Use JIT-compiled version for larger arrays
        return _fm_discriminator_numba(
            iq_samples.real.astype(np.float32),
            iq_samples.imag.astype(np.float32)
        )
    else:
        # Pure NumPy fallback
        phase_diff = iq_samples[1:] * np.conj(iq_samples[:-1])
        return np.angle(phase_diff).astype(np.float32)


def fast_decimate(samples: np.ndarray, factor: int) -> np.ndarray:
    """Fast decimation - dispatches to JIT or NumPy implementation.

    Args:
        samples: Input samples (float32)
        factor: Decimation factor

    Returns:
        Decimated samples (float32)
    """
    if factor <= 1:
        return samples

    # Truncate to multiple of factor
    n_complete = (len(samples) // factor) * factor
    if n_complete == 0:
        return samples

    samples = samples[:n_complete].astype(np.float32)

    if _NUMBA_AVAILABLE and len(samples) > 100:
        return _fast_decimate_numba(samples, factor)
    else:
        # Pure NumPy using reshape+mean (still fast)
        return samples.reshape(-1, factor).mean(axis=1).astype(np.float32)


@dataclass
class DemodulatorConfig:
    """Configuration for audio demodulator."""
    modulation_type: str  # 'FM', 'WFM', 'NFM', 'AM', 'IQ'
    sample_rate: int  # Input sample rate (Hz)
    audio_sample_rate: int = 44100  # Output audio sample rate (native for streams/outputs)
    stereo_enabled: bool = True  # Enable FM stereo decoding
    deemphasis_us: float = 75.0  # De-emphasis time constant (75μs NA, 50μs EU, 0 to disable)
    enable_rbds: bool = False  # Extract RBDS data from FM multiplex


@dataclass
class RBDSData:
    """Decoded RBDS/RDS data from FM broadcast."""
    pi_code: Optional[str] = None  # Program Identification
    ps_name: Optional[str] = None  # Program Service name (8 chars)
    radio_text: Optional[str] = None  # Radio Text (64 chars)
    pty: Optional[int] = None  # Program Type
    tp: Optional[bool] = None  # Traffic Program flag
    ta: Optional[bool] = None  # Traffic Announcement flag
    ms: Optional[bool] = None  # Music/Speech flag


class FMDemodulator:
    """FM demodulator with stereo decoding and RBDS extraction.

    This demodulator uses a multi-stage decimation approach for high sample rate
    SDRs (like Airspy at 2.5 MHz). The signal processing chain is:

    1. IQ samples at SDR rate (e.g., 2.5 MHz)
    2. Phase discriminator to extract FM multiplex signal
    3. Decimate to intermediate rate (e.g., 250 kHz) for efficient filtering
    4. Apply audio lowpass filters at intermediate rate
    5. Stereo decode (if enabled) at intermediate rate
    6. Decimate/resample to final audio rate (e.g., 48 kHz)
    7. Apply de-emphasis filter

    This approach provides much better filter performance than trying to apply
    narrow audio filters directly at MHz sample rates.
    """

    # FM deviation constants for different modulation types
    # These determine the audio gain scaling factor
    FM_DEVIATION_HZ = {
        'WFM': 75000,   # Broadcast FM: ±75 kHz deviation
        'FM': 75000,    # Same as WFM
        'NFM': 5000,    # Narrowband FM: ±5 kHz deviation (NOAA, two-way radio)
    }

    # Default deviation for unknown modulation types (broadcast FM standard)
    DEFAULT_DEVIATION_HZ = 75000

    # Target intermediate sample rate for audio processing
    # 250 kHz is sufficient for FM stereo (needs > 76 kHz for 38 kHz subcarrier)
    # and provides good filter performance with reasonable tap counts
    INTERMEDIATE_SAMPLE_RATE = 250000

    def __init__(self, config: DemodulatorConfig):
        self.config = config

        # Normalize modulation type to uppercase for consistent lookup
        # This prevents issues with case sensitivity (fm vs FM vs Fm)
        self.config.modulation_type = config.modulation_type.upper()

        # Previous complex sample for phase continuity
        self._prev_sample: Optional[np.complex64] = None
        self._sample_index: int = 0

        # Calculate decimation factor for efficient processing
        # We want to get from SDR rate down to ~250 kHz for audio processing
        self._decimation_factor = 1
        self._intermediate_rate = config.sample_rate

        if config.sample_rate > self.INTERMEDIATE_SAMPLE_RATE * 2:
            # Calculate decimation to get close to target intermediate rate
            self._decimation_factor = max(1, int(config.sample_rate / self.INTERMEDIATE_SAMPLE_RATE))
            self._intermediate_rate = config.sample_rate // self._decimation_factor
            logger.info(
                "FM demodulator using %dx decimation: %d Hz -> %d Hz intermediate rate",
                self._decimation_factor, config.sample_rate, self._intermediate_rate
            )

        # Design decimation lowpass filter if needed
        # Cutoff at 80% of new Nyquist to prevent aliasing
        self._decim_filter = None
        if self._decimation_factor > 1:
            decim_cutoff = self._intermediate_rate * 0.4  # 40% of intermediate rate
            # More taps for better stopband rejection at high sample rates
            decim_taps = min(1024, max(256, config.sample_rate // 10000))
            self._decim_filter = self._design_fir_lowpass(decim_cutoff, config.sample_rate, taps=decim_taps)
            logger.debug("Decimation filter: %d taps, cutoff %.1f kHz", decim_taps, decim_cutoff / 1000)

        # Calculate FM audio gain based on modulation type and sample rate
        # The discriminator output is: phase_diff / π, which gives values in [-1, 1]
        # For FM, the actual audio values are much smaller because:
        #   phase_diff_per_sample = 2π × deviation / sample_rate
        # We need to scale up by: sample_rate / (2 × deviation) to get full-scale audio
        deviation_hz = self.FM_DEVIATION_HZ.get(self.config.modulation_type, self.DEFAULT_DEVIATION_HZ)
        # The discriminator already divides by π, so we scale by:
        # sample_rate / (2 × deviation) = the factor to convert frequency deviation to amplitude
        self._audio_gain = config.sample_rate / (2.0 * deviation_hz)

        # Clamp gain to reasonable range to prevent extreme amplification
        # Reduced max gain from 50 to 25 to prevent clipping on strong signals
        self._audio_gain = max(1.0, min(25.0, self._audio_gain))

        # De-emphasis filter state
        self._deemph_alpha = 0.0
        if config.deemphasis_us > 0:
            tau = config.deemphasis_us * 1e-6
            self._deemph_alpha = 1.0 - np.exp(-1.0 / (config.audio_sample_rate * tau))
        self._deemph_state = np.zeros(1, dtype=np.float32)

        # Stereo decoder state
        # Use intermediate rate for stereo processing (more efficient filters)
        self._stereo_enabled = (
            config.stereo_enabled
            and config.modulation_type in {"FM", "WFM"}
            and self._intermediate_rate >= 76000  # Minimum for 38kHz subcarrier
        )

        # Design audio filters at intermediate rate for better performance
        # Calculate adaptive tap count based on intermediate rate
        # Rule of thumb: taps ≈ 4 * sample_rate / transition_bandwidth
        # For 16 kHz cutoff with 2 kHz transition, at 250 kHz: ~500 taps
        audio_filter_taps = self._calculate_filter_taps(16000.0, self._intermediate_rate)
        self._lpr_filter = self._design_fir_lowpass(16000.0, self._intermediate_rate, taps=audio_filter_taps)
        self._dsb_filter = self._design_fir_lowpass(16000.0, self._intermediate_rate, taps=audio_filter_taps)
        self._pilot_filter = self._design_fir_bandpass(18500.0, 19500.0, self._intermediate_rate, taps=audio_filter_taps)

        # Stereo carrier tracking state
        self._pilot_phase = 0.0
        self._pilot_freq = 19000.0  # 19 kHz pilot tone
        self._pilot_pll_bandwidth = 50.0  # Hz - narrow bandwidth for stable lock

        # RBDS decoder state
        self._rbds_decoder = RBDSDecoder()
        self._rbds_enabled = config.enable_rbds and self._intermediate_rate >= 50000
        rbds_filter_taps = self._calculate_filter_taps(3000.0, self._intermediate_rate)
        self._rbds_bandpass = self._design_fir_bandpass(54000.0, 60000.0, self._intermediate_rate, taps=rbds_filter_taps)
        self._rbds_lowpass = self._design_fir_lowpass(2400.0, self._intermediate_rate, taps=rbds_filter_taps)
        self._rbds_symbol_rate = 1187.5
        self._rbds_target_rate = self._rbds_symbol_rate * 4.0
        self._rbds_symbol_phase = 0.0
        self._rbds_loop_gain = 0.02
        self._rbds_bit_buffer: List[int] = []
        self._rbds_expected_block: Optional[int] = None
        self._rbds_partial_group: List[int] = []
        # RBDS uses differential BPSK, so we must keep the previous symbol polarity
        self._rbds_prev_symbol: float = 1.0

    def _calculate_filter_taps(self, cutoff_hz: float, sample_rate: int, transition_bw_ratio: float = 0.125) -> int:
        """Calculate appropriate number of filter taps for given parameters.

        Args:
            cutoff_hz: Filter cutoff frequency in Hz
            sample_rate: Sample rate in Hz
            transition_bw_ratio: Transition bandwidth as fraction of cutoff (default 12.5%)

        Returns:
            Number of filter taps (odd number for symmetric filter)
        """
        # Transition bandwidth
        transition_bw = cutoff_hz * transition_bw_ratio

        # Kaiser formula approximation: taps ≈ (stopband_attenuation_dB - 8) / (2.285 * transition_bw_normalized)
        # For ~60 dB stopband attenuation:
        # taps ≈ (60 - 8) / (2.285 * (transition_bw / sample_rate)) = 52 / (2.285 * transition_bw / sample_rate)
        taps = int(52.0 * sample_rate / (2.285 * transition_bw))

        # Ensure odd number and reasonable range
        taps = max(65, min(1025, taps | 1))  # Clamp to 65-1025, ensure odd

        return taps

    def process(self, iq_samples: np.ndarray) -> np.ndarray:
        """
        Process IQ samples and return audio samples.
        
        This is the main entry point used by audio processing pipeline.
        RBDS data is intentionally discarded for simplicity in the audio pipeline.
        For full demodulation with RBDS data extraction, use demodulate() instead.
        
        Args:
            iq_samples: Complex IQ samples
            
        Returns:
            Audio samples (float32 numpy array) with RBDS data discarded
        """
        audio, _ = self.demodulate(iq_samples)
        return audio

    def demodulate(self, iq_samples: np.ndarray) -> Tuple[np.ndarray, Optional[RBDSData]]:
        """
        Demodulate FM signal from IQ samples.

        ULTRA-FAST VERSION: Minimal processing for real-time at 2.5 MHz.
        Skips filtering to keep up with sample rate.

        Args:
            iq_samples: Complex IQ samples

        Returns:
            Tuple of (audio samples, RBDS data if available)
        """
        if len(iq_samples) == 0:
            return np.array([], dtype=np.float32), None

        # FAST PATH: Using JIT-compiled functions when available
        iq_array = np.asarray(iq_samples, dtype=np.complex64)

        # Phase continuity - prepend last sample from previous block
        if self._prev_sample is not None:
            iq_array = np.concatenate(([self._prev_sample], iq_array))
        self._prev_sample = iq_array[-1]

        # Phase discriminator - uses Numba JIT if available (50-100x faster)
        # This is the core FM demodulation algorithm
        audio = fm_discriminator(iq_array)

        # Calculate decimation factor for coarse downsampling
        target_rate = self.config.audio_sample_rate
        decim = max(1, self.config.sample_rate // target_rate)

        # CRITICAL FIX: Use proper resampling to exact target rate instead of simple decimation
        # Simple decimation produces wrong sample rate: e.g., 2.5MHz / 52 = 48,077 Hz (not 48,000 Hz)
        # This causes "chipmunk" audio when played back at declared rate
        if decim > 1:
            # First decimate to get close to target rate (fast, low quality)
            audio = fast_decimate(audio, decim)
            # Calculate actual intermediate rate after decimation
            intermediate_rate = self.config.sample_rate // decim
        else:
            intermediate_rate = self.config.sample_rate

        # Scale to audio levels BEFORE resampling (at intermediate rate)
        # For 75 kHz deviation: phase_diff_per_sample = 2π × 75000 / sample_rate
        # We scale by sample_rate / (2 × deviation × decimation_factor) to normalize
        deviation_hz = self.FM_DEVIATION_HZ.get(self.config.modulation_type, self.DEFAULT_DEVIATION_HZ)
        audio = audio * (self.config.sample_rate / (2.0 * deviation_hz * decim))

        # Now resample from intermediate_rate to exact target_rate
        # This ensures audio is at the EXACT sample rate expected by downstream consumers
        if intermediate_rate != target_rate:
            audio = self._resample(audio, intermediate_rate, target_rate)

        # Clamp to prevent overflow
        audio = np.clip(audio, -1.5, 1.5)

        # Soft-clip to prevent harsh distortion on overmodulated signals
        # Uses tanh with reduced gain for smoother limiting
        # Scale down before tanh and back up after to preserve dynamics
        audio = np.tanh(audio * 0.7) / 0.7

        # ULTRA-FAST mode skips RBDS extraction entirely for performance
        return audio.astype(np.float32), None

    def _resample(self, signal: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
        """Resample signal using polyphase filtering (high quality) or linear interpolation (fallback)."""
        if from_rate == to_rate:
            return signal

        # Try using scipy.signal.resample_poly for high-quality resampling
        # This is critical for SDR demodulation to avoid aliasing artifacts
        try:
            from scipy import signal as scipy_signal
            import math
            
            # Calculate integer ratio for polyphase resampling
            gcd = math.gcd(int(from_rate), int(to_rate))
            up = int(to_rate // gcd)
            down = int(from_rate // gcd)
            
            # Use resample_poly which applies an anti-aliasing filter
            if signal.ndim == 1:
                return scipy_signal.resample_poly(signal, up, down).astype(signal.dtype)
            else:
                return scipy_signal.resample_poly(signal, up, down, axis=0).astype(signal.dtype)
        except ImportError:
            # Fallback to linear interpolation if scipy is not available
            pass

        ratio = to_rate / from_rate
        new_length = int(len(signal) * ratio)
        old_indices = np.arange(len(signal))
        new_indices = np.linspace(0, len(signal) - 1, new_length)

        if signal.ndim == 1:
            return np.interp(new_indices, old_indices, signal).astype(signal.dtype)

        channels = []
        for ch in range(signal.shape[1]):
            channel_data = signal[:, ch]
            channels.append(np.interp(new_indices, old_indices, channel_data))
        return np.column_stack(channels).astype(signal.dtype)

    def _apply_deemphasis(self, audio: np.ndarray) -> np.ndarray:
        """Apply de-emphasis filter (single-pole IIR lowpass)."""
        if audio.ndim == 1:
            output = np.zeros_like(audio)
            if self._deemph_state.shape[0] != 1:
                self._deemph_state = np.zeros(1, dtype=np.float32)
            for i in range(len(audio)):
                self._deemph_state[0] = (
                    self._deemph_state[0]
                    + self._deemph_alpha * (audio[i] - self._deemph_state[0])
                )
                output[i] = self._deemph_state[0]
            return output

        channels = audio.shape[1]
        if self._deemph_state.shape[0] != channels:
            self._deemph_state = np.zeros(channels, dtype=np.float32)

        output = np.zeros_like(audio)
        for ch in range(channels):
            state = self._deemph_state[ch]
            for i in range(audio.shape[0]):
                state = state + self._deemph_alpha * (audio[i, ch] - state)
                output[i, ch] = state
            self._deemph_state[ch] = state
        return output

    def _design_fir_lowpass(self, cutoff: float, fs: int, taps: int = 129) -> np.ndarray:
        """Design a FIR lowpass filter using windowed sinc method.

        Args:
            cutoff: Cutoff frequency in Hz
            fs: Sample rate in Hz
            taps: Number of filter taps (should be odd)

        Returns:
            Filter coefficients as float32 numpy array
        """
        nyquist = fs / 2.0
        norm_cutoff = min(cutoff / nyquist, 0.99)

        # Ensure odd number of taps for symmetric filter
        taps = taps | 1

        indices = np.arange(taps) - (taps - 1) / 2.0

        # Handle center sample to avoid division by zero in sinc
        with np.errstate(divide='ignore', invalid='ignore'):
            sinc = np.sinc(norm_cutoff * indices)

        # Blackman window has better stopband attenuation than Hamming
        window = np.blackman(taps)
        kernel = norm_cutoff * sinc * window

        # Normalize for unity DC gain
        kernel_sum = np.sum(kernel)
        if kernel_sum != 0:
            kernel /= kernel_sum

        return kernel.astype(np.float32)

    def _design_fir_bandpass(self, low_cut: float, high_cut: float, fs: int, taps: int = 129) -> np.ndarray:
        """Design a FIR bandpass filter.

        Args:
            low_cut: Lower cutoff frequency in Hz
            high_cut: Upper cutoff frequency in Hz
            fs: Sample rate in Hz
            taps: Number of filter taps (should be odd)

        Returns:
            Filter coefficients as float32 numpy array
        """
        # Bandpass = lowpass(high) - lowpass(low)
        low = self._design_fir_lowpass(high_cut, fs, taps)
        high = self._design_fir_lowpass(low_cut, fs, taps)
        kernel = low - high
        return kernel.astype(np.float32)

    def _lpr_filter_signal(self, signal: np.ndarray) -> np.ndarray:
        filtered = np.convolve(signal, self._lpr_filter, mode="same")
        return filtered

    def _decode_stereo(self, multiplex: np.ndarray, sample_indices: np.ndarray) -> Optional[np.ndarray]:
        """Decode FM stereo from multiplex signal.

        Uses the 19 kHz pilot tone to generate a coherent 38 kHz carrier for
        demodulating the L-R stereo difference signal.

        Args:
            multiplex: FM multiplex signal (after discriminator)
            sample_indices: Sample indices at intermediate rate

        Returns:
            Stereo audio as Nx2 array (left, right) or None if stereo disabled
        """
        if not self._stereo_enabled or len(multiplex) == 0:
            return None

        # Extract L+R (mono) using lowpass filter
        lpr = np.convolve(multiplex, self._lpr_filter, mode="same")

        # Generate 38 kHz carrier using time at intermediate rate
        # The carrier must be coherent with the 19 kHz pilot (doubled)
        time = sample_indices / float(self._intermediate_rate)

        # Try to extract pilot tone and lock to it for better carrier coherence
        # For now, use a synthetic carrier (can be improved with PLL later)
        pilot_filtered = np.convolve(multiplex, self._pilot_filter, mode="same")

        # Generate 38 kHz carrier from pilot (pilot is at 19 kHz)
        # Use analytical signal approach: pilot × 2 for phase doubling
        carrier = 2.0 * np.cos(2.0 * np.pi * 38000.0 * time)

        # Demodulate L-R signal by mixing with 38 kHz carrier
        suppressed = multiplex * carrier
        lmr = np.convolve(suppressed, self._dsb_filter, mode="same")

        # Matrix decode: L = (L+R) + (L-R), R = (L+R) - (L-R)
        # Scale by 0.5 to normalize
        left = 0.5 * (lpr + lmr)
        right = 0.5 * (lpr - lmr)

        stereo = np.column_stack((left, right))
        return stereo

    def _extract_rbds(self, multiplex: np.ndarray, sample_indices: np.ndarray) -> Optional[RBDSData]:
        if not self._rbds_enabled or len(multiplex) == 0:
            return None

        rbds_band = np.convolve(multiplex, self._rbds_bandpass, mode="same")
        # Use intermediate rate for RBDS processing
        time = sample_indices / float(self._intermediate_rate)
        baseband = rbds_band * np.exp(-1j * 2.0 * np.pi * 57000.0 * time)
        baseband_real = np.convolve(baseband.real, self._rbds_lowpass, mode="same")

        resampled = self._resample(
            baseband_real,
            self._intermediate_rate,
            int(self._rbds_target_rate),
        )

        if len(resampled) == 0:
            return None

        samples_per_symbol = max(self._rbds_target_rate / self._rbds_symbol_rate, 1.0)
        phase = self._rbds_symbol_phase
        bits: List[int] = []

        while phase + samples_per_symbol < len(resampled):
            center = phase + samples_per_symbol / 2.0
            idx = int(min(max(int(center), 0), len(resampled) - 1))
            sample = resampled[idx]
            bits.append(self._rbds_symbol_to_bit(float(sample)))

            early_idx = int(min(max(int(center - samples_per_symbol / 4.0), 0), len(resampled) - 1))
            late_idx = int(min(max(int(center + samples_per_symbol / 4.0), 0), len(resampled) - 1))
            early = resampled[early_idx]
            late = resampled[late_idx]
            error = (late - early) * sample
            phase += samples_per_symbol - (self._rbds_loop_gain * error)

        self._rbds_symbol_phase = phase - len(resampled)

        if bits:
            self._rbds_bit_buffer.extend(bits)

        return self._decode_rbds_groups()

    def _decode_rbds_groups(self) -> Optional[RBDSData]:
        changed = False
        while len(self._rbds_bit_buffer) >= 26:
            block_bits = self._rbds_bit_buffer[:26]
            block_type, data_word = self._decode_rbds_block(block_bits)

            if block_type is None:
                del self._rbds_bit_buffer[0]
                self._rbds_expected_block = None
                self._rbds_partial_group.clear()
                continue

            if self._rbds_expected_block is None:
                if block_type != "A":
                    del self._rbds_bit_buffer[0]
                    continue
                self._rbds_partial_group = [data_word]
                self._rbds_expected_block = 1
                del self._rbds_bit_buffer[:26]
                continue

            sequence = ["A", "B", "C", "D"]
            expected = sequence[self._rbds_expected_block]
            if expected == "C" and block_type == "C":
                pass
            elif expected != block_type:
                self._rbds_expected_block = None
                self._rbds_partial_group.clear()
                del self._rbds_bit_buffer[0]
                continue

            self._rbds_partial_group.append(data_word)
            self._rbds_expected_block += 1
            del self._rbds_bit_buffer[:26]

            if self._rbds_expected_block >= 4:
                group_changed = self._rbds_decoder.process_group(tuple(self._rbds_partial_group))
                changed = group_changed or changed
                self._rbds_partial_group = []
                self._rbds_expected_block = None

        if changed:
            return self._rbds_decoder.get_current_data()
        return None

    def _rbds_symbol_to_bit(self, sample: float) -> int:
        """Decode a differentially-encoded RBDS symbol into a data bit."""

        symbol = 1.0 if sample >= 0 else -1.0
        previous = self._rbds_prev_symbol
        self._rbds_prev_symbol = symbol

        if previous is None:
            return 0

        # Differential BPSK: bit=0 when polarity stays the same, 1 when it flips
        return 0 if symbol == previous else 1

    def _decode_rbds_block(self, bits: List[int]) -> Tuple[Optional[str], Optional[int]]:
        value = 0
        for bit in bits:
            value = (value << 1) | int(bit)

        data_word = value >> 10
        check_word = value & 0x3FF

        remainder = self._rbds_crc(data_word << 10)
        syndrome = remainder ^ check_word

        offset_map = {
            0x0FC: "A",
            0x198: "B",
            0x168: "C",
            0x350: "C",
            0x1B4: "D",
        }
        block_type = offset_map.get(syndrome)
        if block_type is None:
            return None, None
        return block_type, data_word

    def _rbds_crc(self, value: int) -> int:
        polynomial = 0b11101101001
        for bit in range(value.bit_length() - 1, 9, -1):
            if value & (1 << bit):
                value ^= polynomial << (bit - 10)
        return value & 0x3FF


class AMDemodulator:
    """AM envelope demodulator."""

    def __init__(self, config: DemodulatorConfig):
        self.config = config
        self.dc_offset = 0.0
        self.dc_alpha = 0.001  # DC removal filter coefficient

    def process(self, iq_samples: np.ndarray) -> np.ndarray:
        """
        Process IQ samples and return audio samples.
        
        This is the main entry point used by audio processing pipeline.
        
        Args:
            iq_samples: Complex IQ samples
            
        Returns:
            Audio samples (float32 numpy array)
        """
        audio, _ = self.demodulate(iq_samples)
        return audio

    def demodulate(self, iq_samples: np.ndarray) -> Tuple[np.ndarray, None]:
        """
        Demodulate AM signal from IQ samples using envelope detection.

        Args:
            iq_samples: Complex IQ samples

        Returns:
            Tuple of (audio samples, None) - consistent with FM demodulator interface
        """
        if len(iq_samples) == 0:
            return np.array([], dtype=np.float32), None

        # Envelope detection - compute magnitude
        audio = np.abs(iq_samples)

        # Remove DC offset (high-pass filter)
        for i in range(len(audio)):
            self.dc_offset = self.dc_offset + self.dc_alpha * (audio[i] - self.dc_offset)
            audio[i] -= self.dc_offset

        # Resample to audio sample rate if needed
        if self.config.sample_rate != self.config.audio_sample_rate:
            audio = self._resample(audio, self.config.sample_rate, self.config.audio_sample_rate)

        # Normalize amplitude
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val

        return audio.astype(np.float32), None

    def _resample(self, signal: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
        """Simple resampling using linear interpolation."""
        if from_rate == to_rate:
            return signal

        ratio = to_rate / from_rate
        new_length = int(len(signal) * ratio)
        old_indices = np.arange(len(signal))
        new_indices = np.linspace(0, len(signal) - 1, new_length)

        return np.interp(new_indices, old_indices, signal)


class RBDSDecoder:
    """
    RBDS/RDS decoder for FM radio.

    Decodes Program Service name, Radio Text, and other metadata from the
    57kHz RBDS subcarrier in FM broadcasts.
    """

    def __init__(self):
        self.pi_code = None
        self.ps_name = [' '] * 8  # 8 characters
        self.radio_text = [' '] * 64  # 64 characters
        self.pty = None
        self.tp = None
        self.ta = None
        self.ms = None
        self._radio_text_ab = 0

    def process_group(self, group_data: Tuple[int, int, int, int]) -> Optional[bool]:
        """
        Process a decoded RBDS group.

        Args:
            group_data: Tuple of four 16-bit RBDS blocks (A, B, C, D)

        Returns:
            True if metadata changed, otherwise False/None
        """
        a, b, c, d = group_data
        changed = False

        pi_code = f"{a:04X}"
        if self.pi_code != pi_code:
            self.pi_code = pi_code
            changed = True

        pty = (b >> 5) & 0x1F
        if self.pty != pty:
            self.pty = pty
            changed = True

        tp = bool((b >> 10) & 0x1)
        if self.tp != tp:
            self.tp = tp
            changed = True

        ta = bool((b >> 4) & 0x1)
        if self.ta != ta:
            self.ta = ta
            changed = True

        ms = bool((b >> 3) & 0x1)
        if self.ms != ms:
            self.ms = ms
            changed = True

        group_type = (b >> 12) & 0xF
        version_b = bool((b >> 11) & 0x1)

        if group_type == 0:
            address = b & 0x3
            chars = d
            changed = self._update_ps_name(address, chars) or changed
        elif group_type == 2:
            text_segment = b & 0xF
            ab_flag = (b >> 4) & 0x1
            if ab_flag != self._radio_text_ab:
                self._radio_text_ab = ab_flag
                self.radio_text = [' '] * 64
                changed = True

            if not version_b:
                blocks = (c, d)
                for offset, block in enumerate(blocks):
                    chars = [
                        (block >> 8) & 0x7F,
                        block & 0x7F,
                    ]
                    for i, code in enumerate(chars):
                        idx = text_segment * 4 + offset * 2 + i
                        if idx < len(self.radio_text):
                            if self._update_radio_text(idx, code):
                                changed = True
            else:
                chars = [(d >> 8) & 0x7F, d & 0x7F]
                for i, code in enumerate(chars):
                    idx = text_segment * 2 + i
                    if idx < len(self.radio_text):
                        if self._update_radio_text(idx, code):
                            changed = True

        return changed

    def get_current_data(self) -> RBDSData:
        """Get the currently decoded RBDS data."""
        return RBDSData(
            pi_code=self.pi_code,
            ps_name=''.join(self.ps_name).strip(),
            radio_text=''.join(self.radio_text).strip(),
            pty=self.pty,
            tp=self.tp,
            ta=self.ta,
            ms=self.ms
        )

    def _update_ps_name(self, address: int, chars: int) -> bool:
        idx = address * 2
        updated = False
        for offset in range(2):
            char_code = (chars >> (8 * (1 - offset))) & 0xFF
            if 32 <= char_code < 127:
                char = chr(char_code)
            else:
                char = ' '
            pos = idx + offset
            if pos < len(self.ps_name) and self.ps_name[pos] != char:
                self.ps_name[pos] = char
                updated = True
        return updated

    def _update_radio_text(self, index: int, code: int) -> bool:
        if index >= len(self.radio_text):
            return False
        char = chr(code) if 32 <= code < 127 else ' '
        if self.radio_text[index] != char:
            self.radio_text[index] = char
            return True
        return False


def create_demodulator(config: DemodulatorConfig):
    """Factory function to create the appropriate demodulator."""
    # Normalize modulation type to uppercase for consistent comparison
    mod_type = config.modulation_type.upper()

    if mod_type in ('FM', 'WFM', 'NFM'):
        return FMDemodulator(config)
    elif mod_type == 'AM':
        return AMDemodulator(config)
    elif mod_type == 'IQ':
        # No demodulation, return raw IQ
        return None
    else:
        raise ValueError(
            f"Unsupported modulation type: {config.modulation_type}. "
            f"Valid types: FM, WFM, NFM, AM, IQ"
        )
