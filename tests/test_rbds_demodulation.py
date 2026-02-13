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
import unittest.mock as mock

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_core.radio.demodulation import DemodulatorConfig, FMDemodulator  # noqa: E402


def _make_demodulator():
    config = DemodulatorConfig(
        modulation_type="FM",
        sample_rate=200_000,
        audio_sample_rate=48_000,
        enable_rbds=True,
    )
    return FMDemodulator(config)


def test_rbds_symbol_to_bit_handles_differential_bpsk():
    demod = _make_demodulator()

    samples = np.array([0.25, 0.3, -0.2, -0.18, 0.5, -0.4], dtype=np.float32)
    bits = [demod._rbds_symbol_to_bit(float(sample)) for sample in samples]

    assert bits == [0, 0, 1, 0, 1, 1]


def test_rbds_symbol_to_bit_handles_zero_crossings():
    demod = _make_demodulator()

    zero_crossing = np.array([0.0, -0.01, 0.02], dtype=np.float32)
    bits = [demod._rbds_symbol_to_bit(float(sample)) for sample in zero_crossing]

    assert bits[0] == 0
    assert bits[1] == 1
    assert bits[2] == 1


def test_rbds_throttling_reduces_array_allocations():
    """Test that RBDS throttling reduces np.arange allocations to 1 per interval."""
    config = DemodulatorConfig(
        modulation_type="FM",
        sample_rate=2_500_000,  # High rate like Airspy
        audio_sample_rate=48_000,
        enable_rbds=True,
    )
    demod = FMDemodulator(config)
    
    # Create mock IQ samples (small for testing)
    iq_samples = np.exp(1j * 2 * np.pi * 0.1 * np.arange(1000))
    
    # Track how many times np.arange is called with large arrays
    original_arange = np.arange
    arange_call_count = 0
    large_array_sizes = []
    
    def mock_arange(*args, **kwargs):
        nonlocal arange_call_count
        result = original_arange(*args, **kwargs)
        # Only count large arrays (> 100 elements) that would be for RBDS sample indices
        if len(result) > 100 and kwargs.get('dtype') == np.float64:
            arange_call_count += 1
            large_array_sizes.append(len(result))
        return result
    
    # Process multiple chunks and verify throttling
    with mock.patch('numpy.arange', side_effect=mock_arange):
        # Process interval + 1 chunks to trigger one RBDS processing cycle
        interval = demod._rbds_process_interval
        for i in range(interval + 1):
            demod.process(iq_samples)
    
    # Should have created large array only once (when processing actually happened)
    # Not interval+1 times (which would be if array was created every chunk)
    assert arange_call_count <= 2, (
        f"Expected <= 2 large array allocations, got {arange_call_count}. "
        f"Array sizes: {large_array_sizes}. This suggests np.arange is being called "
        f"on skipped cycles too."
    )
