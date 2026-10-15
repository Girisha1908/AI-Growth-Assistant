# Claude Code: Phase 3, tests in containers (2026-10-13)

## First run
* Frontend `docker compose exec frontend npm test`: 14/14 passed (vitest 2.1.9).
* Backend `pytest`: 75 passed, **1 skipped**. `tests/test_providers.py::test_ollama_unreachable_maps_to_connection_error` (the AC-7 resilience check) was skipped with "async def functions are not natively supported". `pytest.ini` set `asyncio_mode = auto` and the test used `@pytest.mark.asyncio`, but `pytest-asyncio` is not in `requirements-dev.txt`. The test had never actually run.

## Fix
It is the only async test, so the fix uses the stdlib instead of a new dependency:
* The test is now sync and wraps the calls in `asyncio.run(...)`.
* Removed the dead `asyncio_mode = auto` line from `backend/pytest.ini`.

## Result
* Backend: **76 passed, 0 skipped**.
* One leftover warning ("Unknown config option: asyncio_mode") comes from the old `pytest.ini` baked into the running image. Only `app/` and `tests/` are bind-mounted. It clears when the api container is next recreated from the new build.
