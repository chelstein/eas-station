#!/usr/bin/env python3
"""
Helper script for deriving NWS zone codes from FIPS codes during installation.
Can be called from bash to derive zone codes.
"""

import sys
import json
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app_core.location import _derive_county_zone_codes_from_fips
    from app_core.zones import get_zone_lookup
except ImportError as e:
    # Graceful error handling - return JSON error
    print(json.dumps({"error": f"Module import failed: {e}. Python dependencies may not be installed yet."}))
    sys.exit(0)  # Exit 0 so bash can handle it gracefully
except Exception as e:
    print(json.dumps({"error": f"Unexpected error during import: {e}"}))
    sys.exit(0)


def derive_zones(fips_codes: List[str]):
    """Derive NWS zone codes from FIPS codes."""
    try:
        # Load zone lookup
        zone_lookup = get_zone_lookup()
        
        # Derive zone codes
        derived = _derive_county_zone_codes_from_fips(fips_codes, zone_lookup)
        
        return {
            'fips_codes': fips_codes,
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
        fips_codes = [code.strip() for code in sys.argv[1:] if code.strip()]
        
        if not fips_codes:
            print(json.dumps({'error': 'No FIPS codes provided'}))
            sys.exit(0)
        
        result = derive_zones(fips_codes)
        print(json.dumps(result))
        
        # Always exit 0 for graceful handling in bash
        sys.exit(0)
    
    except Exception as e:
        print(json.dumps({'error': f'Unexpected error: {e}'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
