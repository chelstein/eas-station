"""
Audio Pipeline Integration Tests

End-to-end tests validating the EAS FSK encoding pipeline and the
BroadcastQueue data-flow path that feeds the EAS decoder:

  encode_same_bits() + generate_fsk_samples()
      → BroadcastQueue.publish()
          → subscriber receives audio identical to what the EAS decoder sees

No hardware, Redis, or database required.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import List

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util


def _load(rel_path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_fsk = _load("app_utils/eas_fsk.py", "eas_fsk")
_bq  = _load("app_core/audio/broadcast_queue.py", "broadcast_queue_integration")

BroadcastQueue = _bq.BroadcastQueue
encode_same_bits   = _fsk.encode_same_bits
generate_fsk_samples = _fsk.generate_fsk_samples
same_preamble_bits   = _fsk.same_preamble_bits
SAME_BAUD       = _fsk.SAME_BAUD
SAME_MARK_FREQ  = _fsk.SAME_MARK_FREQ
SAME_SPACE_FREQ = _fsk.SAME_SPACE_FREQ
SAME_PREAMBLE_BYTE = _fsk.SAME_PREAMBLE_BYTE

SAMPLE_RATE = 16_000
AMPLITUDE   = 0.7 * 32_767
BIT_RATE    = float(SAME_BAUD)

_VALID_HEADER = "ZCZC-WXR-RWT-000000+0015-0231350-EASNODES-"


def _make_samples(header: str, *, preamble: bool = True) -> List[int]:
    bits = encode_same_bits(header, include_preamble=preamble)
    return generate_fsk_samples(
        bits, SAMPLE_RATE, BIT_RATE, SAME_MARK_FREQ, SAME_SPACE_FREQ, AMPLITUDE
    )


# ─────────────────────────────────────────────────────────────────────────────
# EAS FSK Encoding
# ─────────────────────────────────────────────────────────────────────────────

class TestEASFSKEncoding:
    def test_encode_produces_correct_bit_count(self):
        """Each 7-bit ASCII char + null bit = 8 bits; preamble = 16 × 8 = 128 bits; CR = 8 bits."""
        header_chars = len(_VALID_HEADER) + 1  # +1 for the CR terminator
        expected_bits = 128 + header_chars * 8  # preamble + message
        bits = encode_same_bits(_VALID_HEADER, include_preamble=True)
        assert len(bits) == expected_bits

    def test_encode_without_preamble_omits_preamble_bits(self):
        with_preamble    = encode_same_bits(_VALID_HEADER, include_preamble=True)
        without_preamble = encode_same_bits(_VALID_HEADER, include_preamble=False)
        assert len(with_preamble) - len(without_preamble) == 128  # 16 × 8

    def test_encode_without_cr(self):
        with_cr    = encode_same_bits(_VALID_HEADER, include_cr=True)
        without_cr = encode_same_bits(_VALID_HEADER, include_cr=False)
        assert len(with_cr) - len(without_cr) == 8  # one byte

    def test_bits_are_binary(self):
        bits = encode_same_bits(_VALID_HEADER, include_preamble=True)
        assert all(b in (0, 1) for b in bits)

    def test_preamble_byte_pattern(self):
        """Preamble must encode 0xAB, 16 times, LSB-first, 7 data + null = 8 bits."""
        bits = same_preamble_bits(1)
        reconstructed = 0
        for i in range(7):
            reconstructed |= bits[i] << i
        assert reconstructed == (SAME_PREAMBLE_BYTE & 0x7F)

    def test_eom_has_no_cr(self):
        """EOM (NNNN) per FCC §11.31 has no CR terminator."""
        eom_bits = encode_same_bits("NNNN", include_cr=False)
        with_cr_bits = encode_same_bits("NNNN", include_cr=True)
        assert len(eom_bits) < len(with_cr_bits)

    def test_lsb_first_encoding_matches_ascii(self):
        """First character 'Z' (0x5A) must be encoded LSB-first."""
        bits = encode_same_bits("Z", include_preamble=False, include_cr=False)
        Z_ascii = ord("Z") & 0x7F   # 0x5A = 0101 1010
        for i in range(7):
            assert bits[i] == (Z_ascii >> i) & 1
        assert bits[7] == 0  # null bit


# ─────────────────────────────────────────────────────────────────────────────
# EAS FSK Sample Generation
# ─────────────────────────────────────────────────────────────────────────────

class TestEASFSKSamples:
    def test_sample_count_is_correct(self):
        bits = [1, 0, 1, 0]
        samples = generate_fsk_samples(
            bits, SAMPLE_RATE, BIT_RATE, SAME_MARK_FREQ, SAME_SPACE_FREQ, AMPLITUDE
        )
        expected = len(bits) * int(round(SAMPLE_RATE / BIT_RATE))
        # Allow ±1 per bit for fractional carry
        assert abs(len(samples) - expected) <= len(bits)

    def test_samples_are_integers(self):
        bits = encode_same_bits(_VALID_HEADER)
        samples = generate_fsk_samples(
            bits, SAMPLE_RATE, BIT_RATE, SAME_MARK_FREQ, SAME_SPACE_FREQ, AMPLITUDE
        )
        assert all(isinstance(s, int) for s in samples[:100])

    def test_amplitude_within_range(self):
        bits = encode_same_bits(_VALID_HEADER)
        samples = generate_fsk_samples(
            bits, SAMPLE_RATE, BIT_RATE, SAME_MARK_FREQ, SAME_SPACE_FREQ, AMPLITUDE
        )
        arr = np.array(samples)
        assert arr.max() <= AMPLITUDE + 1    # +1 for int rounding
        assert arr.min() >= -(AMPLITUDE + 1)

    def test_mark_frequency_in_spectrum(self):
        """A pure mark (all-1s) signal must peak near SAME_MARK_FREQ in the FFT."""
        n_bits = 20
        bits = [1] * n_bits
        samples = generate_fsk_samples(
            bits, SAMPLE_RATE, BIT_RATE, SAME_MARK_FREQ, SAME_SPACE_FREQ, AMPLITUDE
        )
        arr = np.array(samples, dtype=np.float64)
        fft   = np.abs(np.fft.rfft(arr))
        freqs = np.fft.rfftfreq(len(arr), 1.0 / SAMPLE_RATE)
        peak_freq = freqs[np.argmax(fft)]
        assert abs(peak_freq - SAME_MARK_FREQ) < 100, (
            f"Expected mark freq ~{SAME_MARK_FREQ:.1f} Hz, got {peak_freq:.1f} Hz"
        )

    def test_space_frequency_in_spectrum(self):
        """A pure space (all-0s) signal must peak near SAME_SPACE_FREQ."""
        bits = [0] * 20
        samples = generate_fsk_samples(
            bits, SAMPLE_RATE, BIT_RATE, SAME_MARK_FREQ, SAME_SPACE_FREQ, AMPLITUDE
        )
        arr = np.array(samples, dtype=np.float64)
        fft   = np.abs(np.fft.rfft(arr))
        freqs = np.fft.rfftfreq(len(arr), 1.0 / SAMPLE_RATE)
        peak_freq = freqs[np.argmax(fft)]
        assert abs(peak_freq - SAME_SPACE_FREQ) < 100

    def test_full_same_header_samples_nonzero(self):
        samples = _make_samples(_VALID_HEADER)
        assert len(samples) > 0
        assert any(s != 0 for s in samples)


# ─────────────────────────────────────────────────────────────────────────────
# End-to-End Pipeline: Encode → Queue → Receive
# ─────────────────────────────────────────────────────────────────────────────

class TestEndToEndPipeline:
    def test_eas_audio_survives_broadcast_queue_roundtrip(self):
        """
        The full pipeline:
          1. Generate SAME header audio
          2. Chunk it (as the capture loop would)
          3. Publish each chunk to a BroadcastQueue
          4. Drain the subscriber queue
          5. Reassemble and compare with original
        """
        samples = _make_samples(_VALID_HEADER)
        original = np.array(samples, dtype=np.float32) / AMPLITUDE  # normalise to [-1,1]

        bq = BroadcastQueue("pipeline-test", max_queue_size=2000)
        sub = bq.subscribe("eas-monitor")

        chunk_size = 512
        chunks_sent = 0
        for offset in range(0, len(original), chunk_size):
            chunk = original[offset:offset + chunk_size]
            bq.publish(chunk)
            chunks_sent += 1

        # Drain and reassemble
        received_parts = []
        while not sub.empty():
            received_parts.append(sub.get_nowait())
        received = np.concatenate(received_parts)

        np.testing.assert_array_almost_equal(received, original, decimal=5)

    def test_multiple_consumers_get_identical_audio(self):
        """EAS monitor and web stream subscriber must receive identical data."""
        samples = _make_samples(_VALID_HEADER)
        chunk = np.array(samples, dtype=np.float32) / AMPLITUDE

        bq = BroadcastQueue("multi-consumer", max_queue_size=2000)
        eas_sub    = bq.subscribe("eas-monitor")
        stream_sub = bq.subscribe("web-stream")

        chunk_size = 256
        for offset in range(0, len(chunk), chunk_size):
            bq.publish(chunk[offset:offset + chunk_size])

        def drain(q):
            parts = []
            while not q.empty():
                parts.append(q.get_nowait())
            return np.concatenate(parts) if parts else np.array([])

        eas_recv    = drain(eas_sub)
        stream_recv = drain(stream_sub)

        np.testing.assert_array_almost_equal(eas_recv, stream_recv, decimal=5)

    def test_eom_audio_through_queue(self):
        """EOM (NNNN) audio must pass through the queue unchanged."""
        eom_bits = encode_same_bits("NNNN", include_preamble=True, include_cr=False)
        eom_samples = generate_fsk_samples(
            eom_bits, SAMPLE_RATE, BIT_RATE, SAME_MARK_FREQ, SAME_SPACE_FREQ, AMPLITUDE
        )
        original = np.array(eom_samples, dtype=np.float32) / AMPLITUDE

        bq = BroadcastQueue("eom-pipeline", max_queue_size=500)
        sub = bq.subscribe("eom-sub")

        bq.publish(original)
        received = sub.get_nowait()
        np.testing.assert_array_almost_equal(received, original, decimal=5)

    def test_no_chunks_dropped_for_fast_consumer(self):
        """A consumer that reads immediately should receive all published chunks."""
        bq = BroadcastQueue("no-drop", max_queue_size=1000)
        sub = bq.subscribe("fast-consumer")

        n_chunks = 200
        chunk = np.zeros(128, dtype=np.float32)
        for _ in range(n_chunks):
            bq.publish(chunk)

        received = 0
        while not sub.empty():
            sub.get_nowait()
            received += 1

        assert received == n_chunks
        assert bq.get_stats()["dropped_chunks"] == 0


class TestStreamInjectEASGating:
    """
    Regression test: injecting a SAME test signal through a live-stream source
    must NOT interleave live audio with the EAS FSK tones in the EAS broadcast
    queue.  Interleaving destroys the coherent preamble the SAME DLL needs to
    lock on, causing the decoder to miss the injected signal entirely.

    Fix (ingest.py): the capture loop now suppresses the live audio chunk from
    _eas_broadcast when _inject_pending is non-empty, letting the injected FSK
    chunks pass through uncontaminated.
    """

    NATIVE_RATE = 44_100  # Typical internet radio stream sample rate
    TARGET_RATE = 16_000  # EAS decoder always works at 16 kHz
    HEADER = "ZCZC-EAS-RWT-000000+0015-0231350-EASTEST-"
    TEST_QUEUE_SIZE = 10_000  # Large enough to hold all test chunks without dropping

    @staticmethod
    def _resample(chunk: np.ndarray, src_rate: int, dst_rate: int = 16_000) -> np.ndarray:
        new_len = max(1, int(len(chunk) * dst_rate / src_rate))
        return np.interp(
            np.linspace(0, len(chunk) - 1, new_len),
            np.arange(len(chunk)),
            chunk,
        ).astype(np.float32)

    def _make_eas_chunks_16k(self) -> list:
        """Generate SAME header at 16 kHz, upsample to native rate, then resample back."""
        bits = encode_same_bits(self.HEADER, include_preamble=True)
        samples_int = generate_fsk_samples(
            bits, SAMPLE_RATE, BIT_RATE, SAME_MARK_FREQ, SAME_SPACE_FREQ, AMPLITUDE
        )
        audio_16k = np.array(samples_int, dtype=np.float32) / AMPLITUDE

        # Upsample to native rate (as inject_eas_test_signal does)
        native_len = max(1, int(len(audio_16k) * self.NATIVE_RATE / self.TARGET_RATE))
        audio_native = np.interp(
            np.linspace(0, len(audio_16k) - 1, native_len),
            np.arange(len(audio_16k)),
            audio_16k,
        ).astype(np.float32)

        # Chunk at ~85 ms (as schedule_inject does)
        chunk_native = max(1, int(self.NATIVE_RATE * 0.085))
        chunks_native = [
            audio_native[i:i + chunk_native]
            for i in range(0, len(audio_native), chunk_native)
        ]

        # Resample each chunk back to 16 kHz (as _resample_for_eas does)
        return [self._resample(c, self.NATIVE_RATE) for c in chunks_native]

    def _make_live_chunk_16k(self) -> np.ndarray:
        """Simulate one live stream chunk (random music-like audio resampled to 16 kHz)."""
        chunk_native = max(1, int(self.NATIVE_RATE * 0.085))
        rng = np.random.default_rng(seed=42)
        live = (rng.standard_normal(chunk_native) * 0.5).astype(np.float32)
        return self._resample(live, self.NATIVE_RATE)

    def _decode_queue(self, eas_bcast) -> list:
        """Feed the EAS broadcast queue through the SAME decoder and return decoded messages."""
        import queue as q_mod
        from app_utils.eas_demod import SAMEDemodulatorCore

        detected = []

        def on_alert(msg, conf, ranges):
            detected.append(msg)

        core = SAMEDemodulatorCore(
            sample_rate=self.TARGET_RATE,
            message_callback=on_alert,
            apply_bandpass=True,
        )

        buf = np.array([], dtype=np.float32)
        chunk_size = 1600  # 100 ms at 16 kHz, same as UnifiedEASMonitorService
        while True:
            # Drain available chunks into buffer using try/except rather than .empty()
            while len(buf) < chunk_size:
                try:
                    buf = np.concatenate([buf, eas_bcast.get_nowait()])
                except q_mod.Empty:
                    break
            if len(buf) < chunk_size:
                break
            core.process_samples(buf[:chunk_size])
            buf = buf[chunk_size:]
        return detected

    def test_interleaved_live_and_inject_fails_detection(self):
        """Confirm that without the gate, interleaved audio prevents EAS detection.

        This test INTENTIONALLY verifies the pre-fix failure mode so that we
        have a baseline and the complementary gated test is meaningful.
        """
        import queue as q_mod

        eas_chunks = self._make_eas_chunks_16k()
        live_chunk = self._make_live_chunk_16k()

        bcast = q_mod.Queue(maxsize=self.TEST_QUEUE_SIZE)
        # Simulate old (buggy) behaviour: one live chunk before every inject chunk
        for inject_c in eas_chunks:
            bcast.put(live_chunk.copy())   # live audio interleaved
            bcast.put(inject_c.copy())     # EAS tones

        detected = self._decode_queue(bcast)
        # With interleaving the DLL cannot lock — expect 0 detections.
        assert detected == [], (
            "Unexpected EAS detection with interleaved live audio; "
            "the gating test may give a false positive"
        )

    def test_gated_inject_detects_eas_signal(self):
        """With the fix, live audio is suppressed from _eas_broadcast while
        inject_pending is non-empty, so the SAME decoder sees coherent FSK.

        Simulates the corrected capture-loop behaviour from ingest.py:
          - One live chunk arrives *before* the inject (already published)
          - All EAS chunks are published without any intervening live audio
          - Live audio resumes after the inject is fully drained
        """
        import queue as q_mod

        eas_chunks = self._make_eas_chunks_16k()
        live_chunk = self._make_live_chunk_16k()

        bcast = q_mod.Queue(maxsize=self.TEST_QUEUE_SIZE)
        # Iteration before inject: live audio goes through normally
        bcast.put(live_chunk.copy())
        # Iteration with inject: live audio suppressed, only EAS chunks
        for inject_c in eas_chunks:
            bcast.put(inject_c.copy())
        # Subsequent iterations: live audio resumes
        bcast.put(live_chunk.copy())

        detected = self._decode_queue(bcast)
        assert len(detected) >= 1, (
            "EAS test signal was not detected even though live audio was gated "
            "from _eas_broadcast during injection.  Check the _inject_pending "
            "gate in AudioSourceAdapter._capture_loop (ingest.py)."
        )
