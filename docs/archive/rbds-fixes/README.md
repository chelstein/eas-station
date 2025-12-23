# RBDS Fix Archive

This directory contains documentation from 35+ pull requests attempting to fix RBDS synchronization issues.

**These files are archived for historical reference only.**

## What Went Wrong

The repository root was cluttered with fix documentation from each failed attempt:
- 16 RBDS fix documentation files
- Multiple deployment guides
- Redundant test scripts
- Broken promises of "final" fixes

Each PR tried to fix symptoms without identifying root causes:
- DSP processing order
- Differential decoding formula
- Bit buffer management
- Register reset handling
- Polarity checking
- Presync spacing logic

## The Real Solution

Instead of more documentation, we needed **ONE diagnostic tool** that automatically detects all these issues.

See: `/tools/rbds_auto_diagnostic.py`

This tool checks the implementation for all known issues from the 35+ failed PRs and can analyze runtime logs to identify problems.

## Lessons Learned

1. **Create diagnostic tools FIRST** - Don't accumulate 35 PRs before creating automated detection
2. **Don't clutter the repository root** - Keep fix docs in proper directories
3. **Focus on root causes** - Stop fixing symptoms and find the actual bugs
4. **Test before claiming "final"** - Many "final fix" docs here weren't actually final

## Files in This Archive

All RBDS_*.md files represent different attempts to fix the same issues from different angles, without proper diagnostics to identify what was actually wrong.

## Moving Forward

- Use `/tools/rbds_auto_diagnostic.py` to check code before merging
- Analyze logs with the same tool to identify runtime issues
- Keep documentation in proper directories
- Create tests that verify fixes, not just document attempts
