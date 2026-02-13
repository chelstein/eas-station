#!/usr/bin/env python3
"""
EAS Station - Emergency Alert System  
Copyright (c) 2025-2026 Timothy Kramer (KR8MER)

Comprehensive RBDS Fix Verification Script (Standalone)

This script verifies the RBDS synchronization fix WITHOUT requiring dependencies.
It checks source code directly to verify:
1. DSP Processing Order: M&M clock recovery before Costas phase correction
2. Differential Decoding: Correct modulo formula (python-radio reference)
3. Comments and Documentation

Usage:
    python3 test_rbds_standalone.py              # Run all tests
    python3 test_rbds_standalone.py --verbose    # Detailed output
"""

import argparse
import pathlib
import re
import sys


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


def print_test(name: str, result: TestResult, verbose: bool = False):
    """Print test result."""
    status = "✓ PASS" if result.passed else "✗ FAIL"
    print(f"{status}: {name}")
    
    if result.message:
        print(f"  {result.message}")
    
    if verbose and result.details:
        for key, value in result.details.items():
            print(f"  {key}: {value}")


# =============================================================================
# Test Functions
# =============================================================================

def read_demodulation_source() -> str:
    """Read the demodulation.py source code."""
    demod_path = pathlib.Path(__file__).parent / "app_core" / "radio" / "demodulation.py"
    
    if not demod_path.exists():
        raise FileNotFoundError(f"Cannot find demodulation.py at {demod_path}")
    
    with open(demod_path, 'r') as f:
        return f.read()


def test_dsp_processing_order(source: str) -> TestResult:
    """Verify M&M comes before Costas in source code."""
    # Find the _process_rbds method
    match = re.search(r'def _process_rbds\(.*?\):(.*?)(?=\n    def |\nclass |\Z)', 
                     source, re.DOTALL)
    
    if not match:
        return TestResult("", False, "_process_rbds method not found")
    
    method_source = match.group(1)
    
    # Find positions of M&M and Costas calls
    mm_match = re.search(r'self\._mm_timing_pysdr\(', method_source)
    costas_match = re.search(r'self\._costas_pysdr\(', method_source)
    
    if not mm_match:
        return TestResult("", False, "M&M timing call not found")
    if not costas_match:
        return TestResult("", False, "Costas call not found")
    
    mm_pos = mm_match.start()
    costas_pos = costas_match.start()
    
    if mm_pos < costas_pos:
        # Count lines before each call
        mm_line = method_source[:mm_pos].count('\n')
        costas_line = method_source[:costas_pos].count('\n')
        
        return TestResult("", True, "M&M runs before Costas (correct PySDR order)", {
            "mm_line_offset": mm_line,
            "costas_line_offset": costas_line,
            "separation": costas_line - mm_line
        })
    else:
        return TestResult("", False, f"WRONG ORDER: Costas at {costas_pos}, M&M at {mm_pos}")


def test_no_experimental_comments(source: str) -> TestResult:
    """Verify old experimental comments are removed."""
    bad_phrases = [
        "EXPERIMENTAL: Try Costas BEFORE M&M",
        "opposite of PySDR",
        "AFTER Costas - experimental"
    ]
    
    found_bad = [phrase for phrase in bad_phrases if phrase in source]
    
    if found_bad:
        return TestResult("", False, f"Found old experimental comments", {
            "found": found_bad
        })
    else:
        return TestResult("", True, "No experimental comments remain")


def test_correct_comments_present(source: str) -> TestResult:
    """Verify correct explanatory comments are present."""
    good_phrases = [
        "M&M timing FIRST",
        "M&M must come BEFORE Costas",
        "PySDR standard"
    ]
    
    found_good = [phrase for phrase in good_phrases if phrase in source]
    
    if len(found_good) >= 2:
        return TestResult("", True, "Has correct explanatory comments", {
            "found": found_good
        })
    else:
        return TestResult("", False, "Missing explanatory comments", {
            "found": found_good,
            "expected": good_phrases
        })


def test_differential_formula(source: str) -> TestResult:
    """Verify correct differential decoding formula."""
    # Correct formula (python-radio)
    correct_pattern = r'\(all_symbols\[1:\]\s*-\s*all_symbols\[:-1\]\)\s*%\s*2'
    
    # Incorrect formula (old version)
    incorrect_pattern = r'\(all_symbols\[1:\]\s*!=\s*all_symbols\[:-1\]\)'
    
    has_correct = bool(re.search(correct_pattern, source))
    has_incorrect = bool(re.search(incorrect_pattern, source))
    
    if not has_correct:
        return TestResult("", False, "Correct modulo formula not found")
    if has_incorrect:
        return TestResult("", False, "Incorrect != formula still present!")
    
    return TestResult("", True, "Uses correct formula: (bits[1:] - bits[:-1]) % 2")


def test_python_radio_reference(source: str) -> TestResult:
    """Verify python-radio reference is present."""
    if "python-radio" in source.lower():
        # Find the context
        lines = source.split('\n')
        ref_lines = [i for i, line in enumerate(lines) if 'python-radio' in line.lower()]
        
        return TestResult("", True, f"Has python-radio reference (line {ref_lines[0] + 1})")
    else:
        return TestResult("", False, "Missing python-radio reference")


def test_docstring_accuracy(source: str) -> TestResult:
    """Verify _process_rbds docstring states correct order."""
    # Find the _process_rbds method and its docstring
    lines = source.split('\n')
    
    in_process_rbds = False
    in_docstring = False
    docstring_lines = []
    
    for line in lines:
        if 'def _process_rbds(' in line:
            in_process_rbds = True
            continue
        
        if in_process_rbds and '"""' in line:
            if not in_docstring:
                in_docstring = True
                # Check if docstring starts and ends on same line
                if line.count('"""') == 2:
                    docstring_lines.append(line)
                    break
                # Get content after opening """
                parts = line.split('"""', 1)
                if len(parts) > 1 and parts[1].strip():
                    docstring_lines.append(parts[1])
            else:
                # Closing """
                parts = line.split('"""')
                if parts[0].strip():
                    docstring_lines.append(parts[0])
                break
            continue
        
        if in_docstring:
            docstring_lines.append(line)
    
    docstring = '\n'.join(docstring_lines)
    
    if not docstring:
        return TestResult("", False, "_process_rbds docstring not found")
    
    if "M&M timing FIRST" in docstring:
        return TestResult("", True, "Docstring correctly states 'M&M timing FIRST'")
    else:
        return TestResult("", False, "Docstring doesn't mention correct order")


def test_buffer_index_based(source: str) -> TestResult:
    """Verify bit buffer uses index-based processing."""
    has_buffer_index = "_rbds_buffer_index" in source
    has_index_increment = "_rbds_buffer_index += 1" in source
    has_index_access = "_rbds_bit_buffer[self._rbds_buffer_index]" in source
    
    # Check for old pop(0) approach (should NOT be present)
    has_pop = ".pop(0)" in source
    
    if has_pop:
        return TestResult("", False, "Still uses pop(0) (inefficient)")
    
    if has_buffer_index and has_index_increment and has_index_access:
        return TestResult("", True, "Uses index-based buffer processing")
    else:
        missing = []
        if not has_buffer_index: missing.append("_rbds_buffer_index variable")
        if not has_index_increment: missing.append("index increment")
        if not has_index_access: missing.append("index-based access")
        
        return TestResult("", False, "Missing index-based components", {
            "missing": missing
        })


def test_version_updated(source: str = None) -> TestResult:
    """Verify VERSION file is 2.44.11."""
    version_path = pathlib.Path(__file__).parent / "VERSION"
    
    if not version_path.exists():
        return TestResult("", False, "VERSION file not found")
    
    with open(version_path, 'r') as f:
        version = f.read().strip()
    
    if version == "2.44.11":
        return TestResult("", True, f"Version is {version}")
    else:
        return TestResult("", False, f"Wrong version: {version} (expected 2.44.11)")


def test_changelog_updated(source: str = None) -> TestResult:
    """Verify CHANGELOG documents the fix."""
    changelog_path = pathlib.Path(__file__).parent / "docs" / "reference" / "CHANGELOG.md"
    
    if not changelog_path.exists():
        return TestResult("", False, "CHANGELOG.md not found")
    
    with open(changelog_path, 'r') as f:
        changelog = f.read()
    
    has_v2_44_11 = "2.44.11" in changelog
    has_dsp_order = "DSP" in changelog and "order" in changelog.lower()
    has_mm_before_costas = "M&M" in changelog and "before" in changelog.lower()
    
    if has_v2_44_11 and has_dsp_order and has_mm_before_costas:
        return TestResult("", True, "CHANGELOG documents v2.44.11 fix")
    else:
        missing = []
        if not has_v2_44_11: missing.append("v2.44.11 entry")
        if not has_dsp_order: missing.append("DSP order mention")
        if not has_mm_before_costas: missing.append("M&M before Costas")
        
        return TestResult("", False, "CHANGELOG incomplete", {
            "missing": missing
        })


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="RBDS Fix Verification (Standalone - No Dependencies)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script verifies the RBDS fix by checking source code directly.
No module imports or execution required.

Tests:
  1. DSP processing order (M&M before Costas)
  2. Differential decoding formula (modulo, not !=)
  3. Documentation and comments
  4. Version and changelog
        """
    )
    
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output with details')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("RBDS FIX VERIFICATION - Version 2.44.11 (Standalone)")
    print("=" * 70)
    print()
    print("Verifying fix by checking source code...")
    print()
    
    try:
        # Read source code
        source = read_demodulation_source()
        print(f"✓ Loaded demodulation.py ({len(source)} bytes)")
        print()
    except Exception as e:
        print(f"✗ Failed to load source: {e}")
        return 1
    
    results = []
    
    # Category 1: DSP Processing Order
    print("1. DSP Processing Order")
    print("-" * 70)
    
    result = test_dsp_processing_order(source)
    print_test("M&M before Costas in source", result, args.verbose)
    results.append(result)
    
    result = test_no_experimental_comments(source)
    print_test("No experimental comments", result, args.verbose)
    results.append(result)
    
    result = test_correct_comments_present(source)
    print_test("Has correct comments", result, args.verbose)
    results.append(result)
    
    result = test_docstring_accuracy(source)
    print_test("Docstring accuracy", result, args.verbose)
    results.append(result)
    
    print()
    
    # Category 2: Differential Decoding
    print("2. Differential Decoding Formula")
    print("-" * 70)
    
    result = test_differential_formula(source)
    print_test("Correct modulo formula", result, args.verbose)
    results.append(result)
    
    result = test_python_radio_reference(source)
    print_test("python-radio reference", result, args.verbose)
    results.append(result)
    
    print()
    
    # Category 3: Bit Buffer Management
    print("3. Bit Buffer Management")
    print("-" * 70)
    
    result = test_buffer_index_based(source)
    print_test("Index-based processing", result, args.verbose)
    results.append(result)
    
    print()
    
    # Category 4: Documentation
    print("4. Documentation")
    print("-" * 70)
    
    result = test_version_updated()
    print_test("VERSION file", result, args.verbose)
    results.append(result)
    
    result = test_changelog_updated()
    print_test("CHANGELOG.md", result, args.verbose)
    results.append(result)
    
    print()
    
    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)
    
    print(f"Total:  {total} tests")
    print(f"Passed: {passed} tests")
    print(f"Failed: {failed} tests")
    
    if failed > 0:
        print()
        print("Failed tests:")
        for result in results:
            if not result.passed:
                print(f"  ✗ {result.name}")
                if result.message:
                    print(f"    {result.message}")
    
    print("=" * 70)
    
    if failed == 0:
        print()
        print("🎉 All tests PASSED! The RBDS fix is correctly implemented.")
        print()
        print("Next steps:")
        print("  1. Deploy to production: sudo ./update.sh")
        print("  2. Monitor logs: journalctl -u eas-station-audio.service -f | grep RBDS")
        print("  3. Look for: 'RBDS SYNCHRONIZED' and 'RBDS group:' messages")
        return 0
    else:
        print()
        print("❌ Some tests FAILED. Please review the failures above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
