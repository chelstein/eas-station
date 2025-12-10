# Fix Scripts

This directory contains one-time fix scripts that resolve specific issues.

## Files

- `fix_airspy_audio_monitor.py` - Fixes Airspy audio monitor issues
- `fix_audio_source_sync.py` - Resolves audio source synchronization issues
- `fix_audio_squeal.py` - Corrects audio squeal/feedback problems
- `fix_sdr_pipeline.py` - Repairs SDR pipeline configuration

## Usage

These scripts are typically run once to fix a specific issue. Most users will not need these unless troubleshooting a known problem.

**Note:** Some of these scripts may be deprecated if the underlying issues have been resolved in the main codebase.

Run from the project root:
```bash
python scripts/fixes/fix_audio_source_sync.py
```
