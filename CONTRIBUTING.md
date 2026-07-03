# Contributing to Agent Assets Control Plane

Thanks for your interest. This project is intentionally small and macOS-specific. Before opening a PR, please read the guidelines below.

## Scope

Agent Assets Control Plane is a **local runtime observatory** for macOS. We want to keep it:

- macOS-first (Linux/Windows collectors belong in separate, optional modules)
- standard-library-only for runtime dependencies
- read-first and safe-by-default

## Getting Started

```bash
git clone https://github.com/yang1996202-cpu/agent-assets-control-plane.git
cd agent-assets-control-plane
python3 -m unittest discover -s tests -v
```

No `pip install` or virtualenv is required.

## How to Contribute

1. **Open an issue first** for non-trivial changes (new collectors, new UI sections, breaking CLI changes).
2. **One change per PR.** Keep diffs small and reviewable.
3. **Add or update tests** in `tests/` for any new pure function or collector output shape.
4. **Update docs**: `docs/CHANGELOG.md` for bug fixes/features, `docs/FEATURES.md` for new capabilities, `README.md` if user-facing behavior changes.
5. **Run the full test suite** before pushing:

   ```bash
   python3 -m unittest discover -s tests -v
   ```

## Code Style

- Python 3.9+ compatibility.
- Use type hints where they clarify intent.
- Keep modules focused: `lib/agent_assets_dashboard_*.py` each have a single responsibility.
- Avoid adding third-party dependencies. If you absolutely need one, open an issue first.

## macOS-Specific Rules

- Any command that calls `launchctl`, `lsof`, or reads plists must handle missing/timeout gracefully.
- Do not hardcode personal paths or vendor names in core code. User-specific mappings belong in `~/.config/agent-assets/product-map.json`.
- Kill / launchctl actions must be behind whitelist/path checks.

## Reporting Bugs

Include:

- macOS version
- Python version (`python3 --version`)
- The command you ran
- The output or error message
- Whether the dashboard was running with `--serve`

## Questions

Open a discussion or issue. For local setup questions, read `README.md` and `docs/architecture.md` first.
