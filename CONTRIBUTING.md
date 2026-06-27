# Contributing

Thanks for taking the time to contribute. All contributions — bug fixes, new features, documentation improvements — are welcome.

## Ground rules

- Every change that touches logic must include tests. PRs without tests for new behaviour will not be merged.
- All CI checks must pass before a PR is reviewed: **HACS**, **Hassfest**, and **Tests**.
- This integration is **read-only by design**. PRs that add order placement or any account mutation will be closed.
- Keep the minimum poll interval at 30 s (`MIN_POLL_INTERVAL` in `const.py`). Do not lower it.

## Getting started

```bash
git clone https://github.com/Smart-Home-Assistant-UK/homeassistant-trading212.git
cd homeassistant-trading212
pip install -r requirements_test.txt
```

Run the full test suite before making any changes to confirm everything is green:

```bash
pytest
```

## Making a change

1. **Fork** the repository and create a branch off `main`.
2. Write your tests first, then implement the change (or at minimum write tests alongside the change — not after).
3. Run `pytest` and confirm all tests pass.
4. Open a pull request against `main`. Describe what the change does and why.

Pull requests are reviewed by the maintainer (@sepehrs). There is no SLA on review time, but well-tested PRs with a clear description get looked at faster.

## Architecture

The integration follows a strict layered pattern — keep new code in the right layer:

```
api.py  →  coordinator.py  →  sensor.py
```

- **`api.py`** — HTTP only. One `_get()` helper, typed exceptions, no business logic.
- **`coordinator.py`** — All data normalisation, state tracking, and event firing lives here. Raises `UpdateFailed` on API errors.
- **`sensor.py`** — Entity classes only. No data fetching, no logic beyond formatting.
- **`config_flow.py`** — Validates the API key, nothing else.

See [`CLAUDE.md`](CLAUDE.md) for a detailed architecture reference.

## Writing tests

Tests live in `tests/` and use `pytest-homeassistant-custom-component` with `aioresponses` for HTTP mocking.

```bash
pytest                          # all tests
pytest tests/test_coordinator.py  # one file
pytest -k "test_dividend"       # by name pattern
pytest -v                       # verbose output
```

Fixtures in `conftest.py` (`mock_config_entry`, `mock_coordinator_data`) cover the common setup — reuse them rather than duplicating.

A test is not acceptable if it:
- Asserts nothing meaningful (e.g. only checks that a function does not raise)
- Mocks so much that it does not exercise any real code path
- Passes with the implementation deleted

## Commit style

Use conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`. One logical change per commit.

## Reporting a bug

Open an issue at https://github.com/Smart-Home-Assistant-UK/homeassistant-trading212/issues with:

- Home Assistant version
- Integration version (visible in Settings → Devices & Services → Trading212 → ⋮ → System information)
- What you expected to happen
- What actually happened, including any relevant log output (`Settings → System → Logs`)
