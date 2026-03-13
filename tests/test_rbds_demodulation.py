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

import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_core.radio.demodulation import DemodulatorConfig, FMDemodulator, RBDSWorker  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_demodulator(sample_rate: int = 200_000) -> FMDemodulator:
    config = DemodulatorConfig(
        modulation_type="FM",
        sample_rate=sample_rate,
        audio_sample_rate=48_000,
        enable_rbds=True,
    )
    return FMDemodulator(config)


def _make_worker(sample_rate: int = 250_000) -> RBDSWorker:
    return RBDSWorker(sample_rate=sample_rate, intermediate_rate=25_000)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_rbds_differential_bpsk_decoding():
    """Inline differential BPSK decoding in the worker produces correct bits.

    The current implementation handles differential decoding inside
    _process_rbds via numpy operations.  We verify the arithmetic directly:
    given a sequence of raw BPSK symbol values, sign-detection followed by
    differential XOR must produce the expected transition sequence.
    """
    # Raw BPSK symbols: + means "1", - means "0" in the raw decision
    samples = np.array([0.25, 0.3, -0.2, -0.18, 0.5, -0.4], dtype=np.float32)
    raw_bits = (np.real(samples) > 0).astype(np.int8)  # [1, 1, 0, 0, 1, 0]

    prev_sym = 0  # same initialisation used by RBDSWorker
    all_symbols = np.concatenate(([prev_sym], raw_bits))
    diff = (np.diff(all_symbols.astype(np.int32)) % 2).astype(np.int8)

    expected = [1, 0, 1, 0, 1, 1]
    assert list(diff) == expected, f"Differential bits {list(diff)} != expected {expected}"


def test_rbds_differential_bpsk_zero_crossing():
    """Values at 0.0 are decoded as raw bit 0; transitions are still correct."""
    samples = np.array([0.0, -0.01, 0.02], dtype=np.float32)
    raw_bits = (np.real(samples) > 0).astype(np.int8)  # [0, 0, 1]

    prev_sym = 0
    all_symbols = np.concatenate(([prev_sym], raw_bits))
    diff = (np.diff(all_symbols.astype(np.int32)) % 2).astype(np.int8)

    # 0→0 = no transition (0), 0→0 = no transition (0), 0→1 = transition (1)
    assert diff[0] == 0
    assert diff[1] == 0
    assert diff[2] == 1


def test_rbds_pilot_reference_uses_absolute_offset():
    """_generate_pilot_reference must honour the supplied sample_offset.

    This is the core of the phase-continuity fix: when chunks are dropped
    from the RBDS queue the worker must still generate the correct carrier
    phase for each chunk.  Previously the method used an internal counter
    that only advanced on *processed* chunks, causing large phase errors
    when chunks were skipped.
    """
    worker = _make_worker(sample_rate=250_000)

    n = 1000
    offset_a = 0
    offset_b = 250_000  # 1 second later (same as the real stream advancing 1 s)

    phases_a = worker._generate_pilot_reference(n, offset_a)
    phases_b = worker._generate_pilot_reference(n, offset_b)

    # phases_a should start at exactly 0 * 2π * 19000 / 250000 = 0
    assert abs(phases_a[0]) < 1e-9, f"phases_a[0] should be 0, got {phases_a[0]}"

    # phases_b should start at 2π * 19000 * (250000 / 250000) = 2π * 19000
    expected_start_b = 2.0 * np.pi * 19000.0 * (offset_b / 250_000)
    assert abs(phases_b[0] - expected_start_b) < 1e-6, (
        f"phases_b[0]={phases_b[0]:.6f} but expected {expected_start_b:.6f}"
    )


def test_rbds_pilot_reference_independent_of_call_order():
    """Each call to _generate_pilot_reference is stateless w.r.t. the offset.

    Calling it with offset 500 should give the same result whether or not
    we previously called it with offset 0 (old code would not because it
    relied on a mutable internal counter).
    """
    worker_cold = _make_worker()
    worker_warm = _make_worker()

    n = 256
    # warm worker: process a chunk at offset 0 first
    worker_warm._generate_pilot_reference(n, sample_offset=0)

    # Both workers should produce identical output for the same offset/n
    phases_cold = worker_cold._generate_pilot_reference(n, sample_offset=500)
    phases_warm = worker_warm._generate_pilot_reference(n, sample_offset=500)

    np.testing.assert_array_equal(phases_cold, phases_warm)


def test_rbds_submit_samples_accepts_offset():
    """submit_samples must accept a sample_offset positional argument."""
    worker = _make_worker()
    multiplex = np.zeros(512, dtype=np.float32)
    # Should not raise
    worker.submit_samples(multiplex, sample_offset=0)
    worker.submit_samples(multiplex, sample_offset=512)
    worker.stop()


def test_fmdemodulator_tracks_sample_index():
    """FMDemodulator._sample_index must advance by the multiplex length each call.

    On the very first call there is no previous IQ sample to prepend, so the
    FM discriminator yields len(iq) - 1 multiplex samples.  On every subsequent
    call the demodulator prepends the last IQ sample, yielding exactly len(iq)
    multiplex samples.  The _sample_index must reflect this accurately so that
    the RBDS worker receives the correct absolute stream offset.
    """
    demod = _make_demodulator(sample_rate=200_000)
    assert demod._sample_index == 0

    chunk = np.exp(1j * 2 * np.pi * 0.01 * np.arange(1024)).astype(np.complex64)

    demod.process(chunk)
    # First call: no previous sample prepended → fm_discriminator produces 1023 samples
    first_call_multiplex_len = len(chunk) - 1
    assert demod._sample_index == first_call_multiplex_len

    demod.process(chunk)
    # Second call: previous sample prepended → fm_discriminator produces 1024 samples
    assert demod._sample_index == first_call_multiplex_len + len(chunk)

    demod.stop()
    time.sleep(0.05)
