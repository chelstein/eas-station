# FIPS and SAME Code Data Sources

This document explains where to find FIPS/SAME codes and how to update the EAS Station data files.

## Current Data Sources

The `app_utils/fips_codes.py` file contains:
- **US_FIPS_COUNTY_TABLE**: County FIPS codes for 50 states + DC
- **COUNTY_SUBDIVISIONS**: Partial county subdivisions for EAS

**Current Limitations:**
- Does not include US Territories (PR, VI, GU, AS, MP)
- Does not include Marine/Offshore areas (Gulf of America, Great Lakes, Atlantic, Pacific)

## Official Data Sources

### 1. NOAA Weather Service (NWS)

**SAME Location Codes Directory (Official)**
- URL: https://www.weather.gov/media/directives/010_pdfs/pd01005007curr.pdf
- Contains: All county SAME codes, territories, and subdivisions
- Format: PDF (requires manual extraction or OCR)

**GIS Data Files**
- URL: https://www.weather.gov/gis/EasNWR
- Contains: County codes, marine zones, offshore areas
- Format: Pipe-delimited text files, shapefiles

**Marine Zone Codes**
- URL: https://www.weather.gov/gis/MarineZones
- Contains: GMZ (Gulf of America), AMZ (Atlantic), PMZ (Pacific), LMZ/LEZ/LHZ/LSZ/LOZ (Great Lakes)

### 2. US Census Bureau

**County FIPS Codes**
- URL: https://www.census.gov/geographies/reference-files/2024/demo/popest/2024-fips.html
- Contains: State and county FIPS codes including territories
- Format: CSV/Excel downloads

**ANSI/FIPS Reference**
- URL: https://www.census.gov/library/reference/code-lists/ansi.html
- Contains: Official INCITS codes (successor to FIPS)

### 3. FCC

**EAS Location Codes (47 CFR Part 11)**
- URL: https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-11
- Contains: Official EAS protocol including SAME location code format

## FIPS Code Format

### County SAME Codes (6 digits)
```
PSSCCC
│││└── County code (001-999)
││└─── State FIPS (01-78)
│└──── P-digit: 0=entire county, 1-9=subdivision
```

### State FIPS Codes
| Code | State/Territory |
|------|-----------------|
| 01-56 | 50 States + DC |
| 60 | American Samoa |
| 66 | Guam |
| 69 | Northern Mariana Islands |
| 72 | Puerto Rico |
| 78 | Virgin Islands |

### Statewide Codes
Format: `0SS000` (e.g., `039000` for entire Ohio)

### Marine Area Codes
- **GMZ**: Gulf of America (formerly Gulf of Mexico)
- **AMZ**: Atlantic Marine Zones
- **PMZ**: Pacific Marine Zones
- **LMZ**: Lake Michigan
- **LEZ**: Lake Erie
- **LHZ**: Lake Huron
- **LSZ**: Lake Superior
- **LOZ**: Lake Ontario

## How to Update fips_codes.py

### Adding Territory Codes

1. Download the Census Bureau's territory FIPS file
2. Add entries to `US_FIPS_COUNTY_TABLE` in format:
   ```
   SSCCC|ST|County Name
   ```
   Example for Puerto Rico:
   ```
   72001|PR|Adjuntas Municipio
   72003|PR|Aguada Municipio
   ...
   ```

### Adding Marine Zones

Marine zones use a different format than FIPS codes. They should be added to the zone catalog (`assets/z_*.dbf`) rather than `fips_codes.py`.

1. Download marine zone shapefile from https://www.weather.gov/gis/MarineZones
2. Replace or merge with existing `assets/z_*.dbf`
3. Sync via web interface at `/admin/zones`

## Verification

After updating, verify codes work:

```bash
# Test FIPS lookup
python3 scripts/fips_lookup_helper.py list OH

# Test zone derivation
python3 scripts/zone_derive_helper.py 039001 039003
```

## Related Files

- `app_utils/fips_codes.py` - Main FIPS code data
- `app_utils/zone_catalog.py` - Zone DBF parser
- `app_core/zones.py` - Zone lookup functions
- `assets/z_*.dbf` - NWS zone catalog
- `scripts/fips_lookup_helper.py` - Installation helper
- `scripts/zone_derive_helper.py` - Zone derivation helper

## External Resources

- [NWS SAME Codes](https://www.weather.gov/nwr/nwrsame)
- [NWS County Coverage](https://www.weather.gov/nwr/counties)
- [Census FIPS Reference](https://www.census.gov/library/reference/code-lists/ansi.html)
- [Wikipedia: FIPS County Codes](https://en.wikipedia.org/wiki/List_of_United_States_FIPS_codes_by_county)
- [Wikipedia: FIPS State Codes](https://en.wikipedia.org/wiki/Federal_Information_Processing_Standard_state_code)
