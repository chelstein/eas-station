# GitHub Copilot Agent Instructions

This directory contains instructions that are automatically loaded by GitHub Copilot agents at the start of each session.

## Files

- **AGENTS.md** — Coding standards, guidelines, and best practices for AI agents working on this codebase.
  This file is a **symbolic link** to `docs/development/AGENTS.md` — there is only one copy.

## Maintenance

Edit `docs/development/AGENTS.md` directly. Because `.github/agents/AGENTS.md` is a symlink,
the change is immediately visible here with no copy step required.

```bash
# Edit the canonical source
$EDITOR docs/development/AGENTS.md

# Commit — only one file changes
git add docs/development/AGENTS.md
git commit -m "docs: update agent guidelines"
```
