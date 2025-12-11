#!/usr/bin/env python3
"""
Helper script for FIPS code lookup during installation.
Can be called from bash to look up FIPS codes by state and county name.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app_utils.fips_codes import get_us_state_county_tree
except ImportError as e:
    # Graceful error handling - return JSON error
    print(json.dumps({"error": f"Module import failed: {e}. Python dependencies may not be installed yet."}))
    sys.exit(0)  # Exit 0 so bash can handle it gracefully
except Exception as e:
    print(json.dumps({"error": f"Unexpected error during import: {e}"}))
    sys.exit(0)


def list_counties_for_state(state_code: str):
    """List all counties for a given state code."""
    try:
        state_code = state_code.strip().upper()
        tree = get_us_state_county_tree()
        
        for state in tree:
            if state.get('abbr', '').upper() == state_code:
                counties = []
                for county in state.get('counties', []):
                    counties.append({
                        'name': county.get('name', ''),
                        'fips': county.get('same', ''),
                    })
                return {'state': state.get('name', ''), 'counties': counties}
        
        return {'error': f'State {state_code} not found'}
    except Exception as e:
        return {'error': f'Error listing counties: {e}'}


def search_counties(state_code: str, county_query: str):
    """Search for counties matching a query string."""
    try:
        state_code = state_code.strip().upper()
        county_query = county_query.strip().lower()
        tree = get_us_state_county_tree()
        
        for state in tree:
            if state.get('abbr', '').upper() == state_code:
                matching = []
                for county in state.get('counties', []):
                    county_name = county.get('name', '').lower()
                    if county_query in county_name:
                        matching.append({
                            'name': county.get('name', ''),
                            'fips': county.get('same', ''),
                        })
                return {
                    'state': state.get('name', ''),
                    'query': county_query,
                    'matches': matching
                }
        
        return {'error': f'State {state_code} not found'}
    except Exception as e:
        return {'error': f'Error searching counties: {e}'}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'Usage: fips_lookup_helper.py <command> [args]'}))
        sys.exit(0)
    
    command = sys.argv[1]
    
    try:
        if command == 'list':
            if len(sys.argv) < 3:
                print(json.dumps({'error': 'Usage: fips_lookup_helper.py list <STATE_CODE>'}))
                sys.exit(0)
            result = list_counties_for_state(sys.argv[2])
            print(json.dumps(result))
        
        elif command == 'search':
            if len(sys.argv) < 4:
                print(json.dumps({'error': 'Usage: fips_lookup_helper.py search <STATE_CODE> <COUNTY_QUERY>'}))
                sys.exit(0)
            result = search_counties(sys.argv[2], sys.argv[3])
            print(json.dumps(result))
        
        else:
            print(json.dumps({'error': f'Unknown command: {command}'}))
            sys.exit(0)
    
    except Exception as e:
        print(json.dumps({'error': f'Unexpected error: {e}'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
