# EAS Audio Samples

This directory contains sample EAS (Emergency Alert System) SAME-encoded audio files for testing and verification.

## Files

### Required Weekly Test (RWT) Samples
- `ZCZC-EAS-RWT-039137+0015-3042020-KR8MER.wav` - Standard RWT test alert
- `ZCZC-EAS-RWT-039137+0015-3051204-KR8MER.wav` - Alternative RWT test alert
- `ZCZC-EAS-RWT-042001-042071-042133+0300-3040858-WJONTV.wav` - Multi-county RWT

### Civil Authority Messages
- `ZCZC-CIV-LEW-004013+1000-3032318-WOLFIP.wav` - Law Enforcement Warning (CIV-LEW)

### General Test Files
- `Same.wav` - Basic SAME audio test file
- `manual_eas_41_composite.wav` - Manual EAS composite test
- `E6EF551DAD142E4C3828A9E68A92B832B3130596.mp3` - MP3 format test
- `valideas.mp3` - Valid EAS format verification

## Usage

These samples are used by:
1. **Alert Self-Test** - Tools → Alert Verification → Alert Self-Test
2. **EAS Decoder Testing** - Verify SAME decoding functionality
3. **Audio Pipeline Testing** - Test audio processing chain
4. **Development** - Unit tests and integration tests

## Format

All files contain valid SAME (Specific Area Message Encoding) headers with:
- AFSK (Audio Frequency Shift Keying) at 520.83 baud
- Mark frequency: 2083.3 Hz
- Space frequency: 1562.5 Hz
- Attention signal: Two-tone (853 Hz and 960 Hz)

## Source

These are genuine EAS alert recordings captured from:
- NOAA Weather Radio stations
- Local broadcast stations (with permission)
- Generated using FCC-compliant EAS encoding equipment
