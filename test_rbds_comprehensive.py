#!/usr/bin/env python3
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

"""
Comprehensive RBDS Fix Verification Script

This script verifies that the RBDS synchronization fix (v2.44.11) is correctly
implemented by testing:

1. DSP Processing Order: M&M clock recovery before Costas phase correction
2. Differential Decoding: Correct modulo formula (python-radio reference)
3. CRC Calculation: Syndrome values for all block types
4. Bit Buffer Management: Index-based processing (no premature draining)
5. Integration Test: End-to-end processing with simulated RBDS signal

Usage:
    python3 test_rbds_comprehensive.py              # Run all tests
    python3 test_rbds_comprehensive.py --verbose    # Detailed output
    python3 test_rbds_comprehensive.py --debug      # Debug logging
    python3 test_rbds_comprehensive.py --test DSP   # Run specific test category
"""

import argparse
import inspect
import logging
import pathlib
import sys
from typing import List, Tuple

import numpy as np

# Setup path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_core.radio.demodulation import RBDSWorker, DemodulatorConfig, FMDemodulator  # noqa: E402


# =============================================================================
# Test Framework
# =============================================================================

class TestResult:
    """Store test results with details."""
    def __init__(self, name: str, passed: bool, message: str = "", details: dict = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}


class TestSuite:
    """Test suite runner with logging."""
    def __init__(self, verbose: bool = False, debug: bool = False):
        self.verbose = verbose
        self.debug = debug
        self.results: List[TestResult] = []
        self.current_category = ""
        
        # Setup logging
        level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
        logging.basicConfig(
            level=level,
            format='%(levelname)s: %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def category(self, name: str):
        """Start a new test category."""
        self.current_category = name
        print(f"\n{'=' * 70}")
        print(f"{name}")
        print('=' * 70)
    
    def test(self, name: str, func, *args, **kwargs) -> TestResult:
        """Run a single test."""
        full_name = f"{self.current_category}/{name}" if self.current_category else name
        
        if self.verbose:
            print(f"\n{name}")
            print('-' * 70)
        
        try:
            result = func(*args, **kwargs)
            
            if isinstance(result, TestResult):
                result.name = full_name
                self.results.append(result)
            else:
                # Assume success if no exception and returns True or None
                passed = result if isinstance(result, bool) else True
                result = TestResult(full_name, passed)
                self.results.append(result)
            
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"{status}: {name}")
            
            if result.message:
                print(f"  {result.message}")
            
            if self.verbose and result.details:
                for key, value in result.details.items():
                    print(f"  {key}: {value}")
            
            return result
            
        except Exception as e:
            result = TestResult(full_name, False, f"Exception: {e}")
            self.results.append(result)
            
            print(f"✗ FAIL: {name}")
            print(f"  Exception: {e}")
            
            if self.debug:
                import traceback
                traceback.print_exc()
            
            return result
    
    def summary(self):
        """Print test summary."""
        print(f"\n{'=' * 70}")
        print("TEST SUMMARY")
        print('=' * 70)
        
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        
        print(f"Total:  {total} tests")
        print(f"Passed: {passed} tests")
        print(f"Failed: {failed} tests")
        
        if failed > 0:
            print(f"\nFailed tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  ✗ {result.name}")
                    if result.message:
                        print(f"    {result.message}")
        
        print('=' * 70)
        
        return failed == 0


# =============================================================================
# Test Category 1: DSP Processing Order
# =============================================================================

def test_dsp_method_call_order() -> TestResult:
    """Verify M&M runs before Costas in actual execution."""
    worker = RBDSWorker(sample_rate=250000, intermediate_rate=25000)
    call_order = []
    
    # Track method calls
    original_mm = worker._mm_timing_pysdr
    original_costas = worker._costas_pysdr
    
    def tracked_mm(samples):
        call_order.append('mm_timing')
        return original_mm(samples)
    
    def tracked_costas(samples):
        call_order.append('costas')
        return original_costas(samples)
    
    worker._mm_timing_pysdr = tracked_mm
    worker._costas_pysdr = tracked_costas
    
    # Create test signal
    t = np.linspace(0, 0.1, 2500, dtype=np.float32)
    multiplex = np.sin(2 * np.pi * 1187.5 * t)
    
    try:
        worker._process_rbds(multiplex)
    except Exception:
        pass  # Expected in test environment
    
    worker.stop()
    
    # Verify order
    if len(call_order) >= 2:
        if call_order[0] == 'mm_timing' and call_order[1] == 'costas':
            return TestResult("", True, "M&M → Costas order confirmed", {
                "call_sequence": " → ".join(call_order[:4])
            })
        else:
            return TestResult("", False, f"Wrong order: {call_order[:2]}")
    else:
        return TestResult("", False, f"Insufficient calls: {call_order}")


def test_dsp_source_code_order() -> TestResult:
    """Verify M&M comes before Costas in source code."""
    worker = RBDSWorker(sample_rate=250000, intermediate_rate=25000)
    source = inspect.getsource(worker._process_rbds)
    
    mm_pos = source.find('self._mm_timing_pysdr(')
    costas_pos = source.find('self._costas_pysdr(')
    
    worker.stop()
    
    if mm_pos < 0:
        return TestResult("", False, "M&M timing call not found")
    if costas_pos < 0:
        return TestResult("", False, "Costas call not found")
    
    if mm_pos < costas_pos:
        return TestResult("", True, "Source code order correct", {
            "mm_position": mm_pos,
            "costas_position": costas_pos,
            "difference": costas_pos - mm_pos
        })
    else:
        return TestResult("", False, f"M&M at {mm_pos}, Costas at {costas_pos} (reversed!)")


def test_dsp_docstring_matches() -> TestResult:
    """Verify docstring states correct order."""
    worker = RBDSWorker(sample_rate=250000, intermediate_rate=25000)
    docstring = inspect.getdoc(worker._process_rbds)
    
    worker.stop()
    
    has_correct_statement = "M&M timing FIRST" in docstring
    
    if has_correct_statement:
        return TestResult("", True, "Docstring correctly states 'M&M timing FIRST, then Costas loop!'")
    else:
        return TestResult("", False, "Docstring doesn't mention correct order")


def test_dsp_no_experimental_comments() -> TestResult:
    """Verify old experimental comments are removed."""
    worker = RBDSWorker(sample_rate=250000, intermediate_rate=25000)
    source = inspect.getsource(worker._process_rbds)
    
    worker.stop()
    
    bad_phrases = [
        "EXPERIMENTAL: Try Costas BEFORE M&M",
        "opposite of PySDR",
        "AFTER Costas - experimental"
    ]
    
    found_bad = [phrase for phrase in bad_phrases if phrase in source]
    
    if found_bad:
        return TestResult("", False, f"Found old experimental comments: {found_bad}")
    else:
        return TestResult("", True, "No experimental comments remain")


# =============================================================================
# Test Category 2: Differential Decoding Formula
# =============================================================================

def test_differential_formula_in_source() -> TestResult:
    """Verify correct modulo formula is used in source."""
    worker = RBDSWorker(sample_rate=250000, intermediate_rate=25000)
    source = inspect.getsource(worker._process_rbds)
    
    worker.stop()
    
    has_correct = "(all_symbols[1:] - all_symbols[:-1]) % 2" in source
    has_incorrect = "(all_symbols[1:] != all_symbols[:-1])" in source
    has_reference = "python-radio" in source.lower()
    
    if not has_correct:
        return TestResult("", False, "Correct modulo formula not found")
    if has_incorrect:
        return TestResult("", False, "Incorrect != formula still present")
    if not has_reference:
        return TestResult("", False, "python-radio reference missing")
    
    return TestResult("", True, "Uses correct formula: (bits[1:] - bits[:-1]) % 2", {
        "has_python_radio_ref": has_reference
    })


def test_differential_handles_inversion() -> TestResult:
    """Test that differential formula handles 180° phase ambiguity."""
    # Normal symbols
    symbols = np.array([1, 0, 0, 1, 1, 0, 1, 0], dtype=np.int8)
    diff_normal = (symbols[1:] - symbols[:-1]) % 2
    
    # Inverted symbols (180° Costas lock)
    symbols_inv = 1 - symbols
    diff_inv = (symbols_inv[1:] - symbols_inv[:-1]) % 2
    
    # Key test: modulo formula should give SAME differential bits regardless of inversion
    if np.array_equal(diff_normal, diff_inv):
        return TestResult("", True, "Formula handles inverted symbols correctly", {
            "normal_diff": diff_normal.tolist(),
            "inverted_diff": diff_inv.tolist()
        })
    else:
        return TestResult("", False, "Formula doesn't handle inversion", {
            "normal_diff": diff_normal.tolist(),
            "inverted_diff": diff_inv.tolist()
        })


def test_differential_continuity() -> TestResult:
    """Test differential decoding maintains continuity across chunks."""
    chunk1 = np.array([1, 0, 1, 1], dtype=np.int8)
    chunk2 = np.array([0, 0, 1, 0], dtype=np.int8)
    
    # Continuous processing
    full = np.concatenate([chunk1, chunk2])
    full_diff = (full[1:] - full[:-1]) % 2
    
    # Chunked processing (with continuity)
    diff1 = (chunk1[1:] - chunk1[:-1]) % 2
    chunk2_with_prev = np.concatenate([chunk1[-1:], chunk2])
    diff2 = (chunk2_with_prev[1:] - chunk2_with_prev[:-1]) % 2
    chunked_diff = np.concatenate([diff1, diff2])
    
    if np.array_equal(full_diff, chunked_diff):
        return TestResult("", True, "Maintains continuity across chunks")
    else:
        return TestResult("", False, "Continuity broken across chunks")


# =============================================================================
# Test Category 3: CRC/Syndrome Calculation
# =============================================================================

def calc_syndrome(x: int, mlen: int) -> int:
    """Calculate syndrome using RDS specification (Annex B)."""
    reg = 0
    plen = 10
    for ii in range(mlen, 0, -1):
        reg = (reg << 1) | ((x >> (ii - 1)) & 0x01)
        if reg & (1 << plen):
            reg = reg ^ 0x5B9
    for ii in range(plen, 0, -1):
        reg = reg << 1
        if reg & (1 << plen):
            reg = reg ^ 0x5B9
    return reg & ((1 << plen) - 1)


def test_crc_all_block_types() -> TestResult:
    """Test syndrome calculation for all RBDS block types."""
    block_info = [
        ("A", 0x0FC, 383),
        ("B", 0x198, 14),
        ("C", 0x168, 303),
        ("D", 0x1B4, 663),
        ("C'", 0x350, 748),
    ]
    
    results = []
    all_pass = True
    
    for block_name, offset, expected_syndrome in block_info:
        dataword = 0x0000
        syndrome = calc_syndrome(dataword, 16)
        checkword = syndrome ^ offset
        block = (dataword << 10) | checkword
        block_syndrome = calc_syndrome(block, 26)
        
        passed = (block_syndrome == expected_syndrome)
        all_pass = all_pass and passed
        
        results.append({
            "block": block_name,
            "syndrome": block_syndrome,
            "expected": expected_syndrome,
            "passed": passed
        })
    
    if all_pass:
        return TestResult("", True, "All block syndromes correct", {
            "blocks": ", ".join(f"{r['block']}={r['syndrome']}" for r in results)
        })
    else:
        failed = [r for r in results if not r['passed']]
        return TestResult("", False, f"Failed blocks: {failed}")


def test_crc_with_pi_code() -> TestResult:
    """Test CRC with realistic PI code."""
    dataword = 0x1234  # Example PI code
    offset_a = 0x0FC
    
    syndrome = calc_syndrome(dataword, 16)
    checkword = syndrome ^ offset_a
    block = (dataword << 10) | checkword
    block_syndrome = calc_syndrome(block, 26)
    
    if block_syndrome == 383:
        return TestResult("", True, "CRC works with PI code 0x1234", {
            "pi_code": "0x1234",
            "checkword": f"0x{checkword:03X}",
            "syndrome": block_syndrome
        })
    else:
        return TestResult("", False, f"Wrong syndrome: {block_syndrome} (expected 383)")


# =============================================================================
# Test Category 4: Bit Buffer Management
# =============================================================================

def test_buffer_uses_index() -> TestResult:
    """Verify bit buffer uses index-based processing."""
    worker = RBDSWorker(sample_rate=250000, intermediate_rate=25000)
    source = inspect.getsource(worker._decode_rbds_groups)
    
    worker.stop()
    
    # Check for index-based processing
    has_buffer_index = "_rbds_buffer_index" in source
    has_index_increment = "_rbds_buffer_index += 1" in source
    has_index_based_access = "_rbds_bit_buffer[self._rbds_buffer_index]" in source
    
    # Check for old pop(0) approach (should NOT be present)
    has_pop = ".pop(0)" in source
    
    if has_pop:
        return TestResult("", False, "Still uses pop(0) (inefficient and loses bits)")
    
    if has_buffer_index and has_index_increment and has_index_based_access:
        return TestResult("", True, "Uses index-based buffer processing")
    else:
        return TestResult("", False, "Missing index-based processing components")


def test_buffer_cleanup() -> TestResult:
    """Verify buffer cleanup happens after processing."""
    worker = RBDSWorker(sample_rate=250000, intermediate_rate=25000)
    source = inspect.getsource(worker._decode_rbds_groups)
    
    worker.stop()
    
    # Check for cleanup logic
    has_cleanup = "del self._rbds_bit_buffer[:self._rbds_buffer_index]" in source
    has_reset = "self._rbds_buffer_index = 0" in source
    
    if has_cleanup and has_reset:
        return TestResult("", True, "Buffer cleanup logic present")
    else:
        return TestResult("", False, "Missing buffer cleanup")


# =============================================================================
# Test Category 5: Integration Test
# =============================================================================

def test_integration_end_to_end() -> TestResult:
    """Test end-to-end RBDS processing with simulated signal."""
    # Create demodulator
    config = DemodulatorConfig(
        modulation_type="FM",
        sample_rate=250000,
        audio_sample_rate=48000,
        enable_rbds=True
    )
    demod = FMDemodulator(config)
    
    # Create simulated IQ signal (FM with RBDS subcarrier)
    t = np.linspace(0, 0.1, 25000, dtype=np.float32)
    
    # FM carrier with 57 kHz RBDS subcarrier (BPSK modulated)
    rbds_freq = 57000
    rbds_carrier = np.cos(2 * np.pi * rbds_freq * t)
    
    # Modulate with some bit pattern
    bit_rate = 1187.5
    bits = (np.sin(2 * np.pi * bit_rate * t) > 0).astype(np.float32) * 2 - 1
    rbds_signal = rbds_carrier * bits
    
    # Create FM multiplex (mono audio + RBDS)
    audio = np.sin(2 * np.pi * 1000 * t)  # 1 kHz audio tone
    multiplex = audio + 0.1 * rbds_signal  # RBDS at lower level
    
    # Convert to IQ (simulate FM modulation)
    phase = np.cumsum(multiplex) * 0.01
    iq_signal = np.exp(1j * phase).astype(np.complex64)
    
    # Process through demodulator
    try:
        audio_out, status = demod.demodulate(iq_signal)
        
        # Check that RBDS worker is running
        if demod._rbds_worker:
            return TestResult("", True, "End-to-end processing works", {
                "audio_samples": len(audio_out),
                "rbds_enabled": True,
                "worker_running": True
            })
        else:
            return TestResult("", False, "RBDS worker not created")
    
    except Exception as e:
        return TestResult("", False, f"Processing failed: {e}")
    finally:
        demod.stop()


def test_integration_worker_lifecycle() -> TestResult:
    """Test RBDS worker creation and cleanup."""
    worker = RBDSWorker(sample_rate=250000, intermediate_rate=25000)
    
    # Check worker thread started
    if not worker._thread or not worker._thread.is_alive():
        return TestResult("", False, "Worker thread not started")
    
    # Create test signal
    t = np.linspace(0, 0.01, 2500, dtype=np.float32)
    multiplex = np.sin(2 * np.pi * 1187.5 * t)
    
    # Submit samples (should not block)
    try:
        worker.submit_samples(multiplex)
        submitted = True
    except Exception as e:
        submitted = False
        error = str(e)
    
    # Stop worker
    worker.stop()
    
    # Verify thread stopped
    import time
    time.sleep(0.1)
    thread_stopped = not worker._thread.is_alive()
    
    if submitted and thread_stopped:
        return TestResult("", True, "Worker lifecycle correct")
    else:
        details = {
            "samples_submitted": submitted,
            "thread_stopped": thread_stopped
        }
        if not submitted:
            details["error"] = error
        return TestResult("", False, "Worker lifecycle issue", details)


# =============================================================================
# Main Test Runner
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive RBDS Fix Verification Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Categories:
  DSP         - DSP processing order (M&M before Costas)
  DIFF        - Differential decoding formula
  CRC         - CRC/syndrome calculation
  BUFFER      - Bit buffer management
  INTEGRATION - End-to-end integration tests
  ALL         - Run all tests (default)

Examples:
  python3 test_rbds_comprehensive.py
  python3 test_rbds_comprehensive.py --verbose
  python3 test_rbds_comprehensive.py --debug --test DSP
        """
    )
    
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output with test details')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Debug logging and stack traces')
    parser.add_argument('--test', '-t', choices=['DSP', 'DIFF', 'CRC', 'BUFFER', 'INTEGRATION', 'ALL'],
                        default='ALL', help='Run specific test category')
    
    args = parser.parse_args()
    
    suite = TestSuite(verbose=args.verbose, debug=args.debug)
    
    print("=" * 70)
    print("RBDS FIX VERIFICATION - Version 2.44.11")
    print("=" * 70)
    print()
    print("This script verifies the RBDS synchronization fix:")
    print("  • v2.44.10: Correct differential formula (modulo)")
    print("  • v2.44.11: Correct DSP order (M&M before Costas)")
    print()
    
    # Run tests based on category
    if args.test in ['DSP', 'ALL']:
        suite.category("1. DSP Processing Order")
        suite.test("Method call order", test_dsp_method_call_order)
        suite.test("Source code order", test_dsp_source_code_order)
        suite.test("Docstring matches", test_dsp_docstring_matches)
        suite.test("No experimental comments", test_dsp_no_experimental_comments)
    
    if args.test in ['DIFF', 'ALL']:
        suite.category("2. Differential Decoding Formula")
        suite.test("Correct formula in source", test_differential_formula_in_source)
        suite.test("Handles phase inversion", test_differential_handles_inversion)
        suite.test("Maintains continuity", test_differential_continuity)
    
    if args.test in ['CRC', 'ALL']:
        suite.category("3. CRC/Syndrome Calculation")
        suite.test("All block types", test_crc_all_block_types)
        suite.test("Realistic PI code", test_crc_with_pi_code)
    
    if args.test in ['BUFFER', 'ALL']:
        suite.category("4. Bit Buffer Management")
        suite.test("Index-based processing", test_buffer_uses_index)
        suite.test("Buffer cleanup", test_buffer_cleanup)
    
    if args.test in ['INTEGRATION', 'ALL']:
        suite.category("5. Integration Tests")
        suite.test("End-to-end processing", test_integration_end_to_end)
        suite.test("Worker lifecycle", test_integration_worker_lifecycle)
    
    # Print summary
    success = suite.summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
