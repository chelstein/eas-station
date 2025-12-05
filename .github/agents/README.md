# GitHub Copilot Agent Instructions

This directory contains instructions that are automatically loaded by GitHub Copilot agents at the start of each session.

## Files

- **AGENTS.md** - Complete coding standards, guidelines, and best practices for AI agents working on this codebase

## Maintenance

The canonical source for `AGENTS.md` is located at `docs/development/AGENTS.md`. When making updates:

1. Edit `docs/development/AGENTS.md` (the canonical source)
2. Copy to `.github/agents/AGENTS.md`:
   ```bash
   cp docs/development/AGENTS.md .github/agents/AGENTS.md
   ```
3. Commit both files together

## Why Two Copies?

- **`docs/development/AGENTS.md`** - Part of the main documentation tree, discoverable by developers
- **`.github/agents/AGENTS.md`** - Special location that GitHub Copilot agents read automatically at session start

This duplication ensures agents always have the latest guidelines while keeping the documentation properly organized.
