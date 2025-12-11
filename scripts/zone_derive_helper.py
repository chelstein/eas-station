#!/usr/bin/env python3
"""
Helper script for deriving NWS zone codes from FIPS codes during installation.
Can be called from bash to derive zone codes.

This script is designed to work WITHOUT Flask/SQLAlchemy dependencies,
using only standard library + direct imports from fips_codes.py.
"""

import sys
import json
from pathlib import Path
import importlib.util
from typing import Dict, List, Set


# Import fips_codes module directly to avoid triggering app_utils/__init__.py
# which would require psutil and other dependencies not yet installed
parent_dir = Path(__file__).parent.parent
fips_module_path = parent_dir / 'app_utils' / 'fips_codes.py'

try:
    spec = importlib.util.spec_from_file_location('fips_codes', fips_module_path)
    fips_codes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fips_codes)
    get_us_state_county_tree = fips_codes.get_us_state_county_tree
except Exception as e:
    # Graceful error handling - return JSON error
    print(json.dumps({"error": f"Module import failed: {e}. Python dependencies may not be installed yet."}))
    sys.exit(0)  # Exit 0 so bash can handle it gracefully


def _build_state_fips_to_abbr() -> Dict[str, str]:
    """Build mapping from state FIPS code to state abbreviation."""
    mapping = {}
    for state in get_us_state_county_tree():
        state_fips = str(state.get("state_fips") or "").zfill(2)
        abbr = str(state.get("abbr") or "").upper()
        if state_fips and abbr and len(abbr) == 2:
            mapping[state_fips] = abbr
    return mapping


def derive_county_zone_codes_from_fips(fips_codes_list: List[str]) -> List[str]:
    """
    Derive NWS county zone codes from FIPS codes.

    This is a simplified version that derives county zone codes (e.g., OHC001)
    without requiring Flask/SQLAlchemy for forecast zone lookups.

    Args:
        fips_codes_list: List of FIPS codes (6 digits each, e.g., ["039001", "039003"])

    Returns:
        List of derived zone codes (e.g., ["OHC001", "OHC003"])
    """
    state_fips_to_abbr = _build_state_fips_to_abbr()
    derived: List[str] = []
    seen: Set[str] = set()

    for raw_code in fips_codes_list:
        # Extract only digits from the code
        digits = "".join(ch for ch in str(raw_code) if ch.isdigit())

        # Skip invalid codes - must be 6 digits and not a statewide code (ends with 000)
        if len(digits) != 6 or digits.endswith("000"):
            continue

        # Extract state FIPS (digits 1-2, skipping the leading subdivision digit)
        # and county suffix (last 3 digits)
        state_fips = digits[1:3]  # e.g., "03" from "039001"
        county_suffix = digits[3:]  # e.g., "001" from "039001"

        # Look up state abbreviation
        state_abbr = state_fips_to_abbr.get(state_fips)
        if not state_abbr or len(state_abbr) != 2:
            continue

        # Build county zone code: STATE + "C" + COUNTY_SUFFIX
        # e.g., "OH" + "C" + "001" = "OHC001"
        zone_code = f"{state_abbr}C{county_suffix}"
        normalized = zone_code.upper()

        if normalized in seen:
            continue

        seen.add(normalized)
        derived.append(normalized)

    return derived


def derive_zones(fips_codes_list: List[str]):
    """Derive NWS zone codes from FIPS codes."""
    try:
        # Derive zone codes
        derived = derive_county_zone_codes_from_fips(fips_codes_list)

        return {
            'fips_codes': fips_codes_list,
            'zone_codes': derived,
            'count': len(derived)
        }
    except Exception as e:
        return {'error': f'Error deriving zones: {e}'}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'Usage: zone_derive_helper.py <FIPS_CODE1> [FIPS_CODE2] ...'}))
        sys.exit(0)

    try:
        # Get FIPS codes from arguments
        fips_codes_list = [code.strip() for code in sys.argv[1:] if code.strip()]

        if not fips_codes_list:
            print(json.dumps({'error': 'No FIPS codes provided'}))
            sys.exit(0)

        result = derive_zones(fips_codes_list)
        print(json.dumps(result))

        # Always exit 0 for graceful handling in bash
        sys.exit(0)

    except Exception as e:
        print(json.dumps({'error': f'Unexpected error: {e}'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
