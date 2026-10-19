# Backend Pytest

Use this reference for Skriptoteket backend unit, integration, API, domain, and
application tests.

## Read First

- `docs/runbooks/run-skript-runbook-testing-pytest-vitest-playwright-runbook-testing-pytest-vitest-playwright.md`
- `.codex/skills/skriptoteket-backend-dev/SKILL.md`

## Rules

- Domain and application unit tests should mock `typing.Protocol` boundaries
  with `AsyncMock(spec=...)`.
- Avoid `@patch` when constructor injection, Dishka DI, or an explicit protocol
  fixture can express the seam.
- API tests assert HTTP status, response contract, error code, correlation, and
  authorization behavior. Business rules belong below the router.
- Repository/UoW tests may use integration lanes; repositories never commit and
  UoW owns transaction behavior.
- Keep fixtures named by domain purpose. Shared fixtures live under
  `tests/fixtures/`, not as hidden behavior in `tests/conftest.py`.
- Use the shared staging-walk skill for staging and browser proof on Hemma.

## Marker Selection

- The default test selection excludes `docker`, `slow`, `financial`, and
  `simulation` (configured in `pyproject.toml`). Explicitly select the focused
  marked lane and override the default marker filter when needed.
- Use `simulation` for expensive statistical suites such as repeated classroom
  layout runs. Keep quick geometry/unit smoke checks unmarked so they remain
  in the normal test path.
- Named suite surfaces are `pdm run test` (changed-component routing),
  `pdm run pytest <target>` (focused runs), `pdm run test-docker` and
  `pdm run test-simulations`;
  iteration still uses the smallest focused target.

## Execution Mode

- Every pytest run is parallel and quiet by default: `addopts` in
  `pyproject.toml` carries `-n logical --dist worksteal`, no `-s`, `-v` or
  live log streaming. INFO logs and stdout are captured and printed only for
  failing tests, and the ten slowest tests are listed.
- `-n logical` is sized by `pytest_xdist_auto_num_workers` in
  `tests/conftest.py`: a run that selects one file runs in-process, and a run
  that selects N files uses `min(N, hardware threads)` workers (24 on Hemma).
  Pass an explicit `-n <count>` only when one large file needs workers.
- `pdm run pytest <target>` is the focused command. Pass `-q` or `-v` only
  when the run needs it; `-v` on 24 workers prints one line per test.
- A serial run (`-n 0`, `--pdb`, or overridden `addopts`) stops with a usage
  error unless it states why with `--serial-reason "<reason>"`. Valid reasons:
  stepping through a test with `--pdb`, or reading live log output of one
  failing test. `pdm run test-serial --serial-reason "<reason>" <target>` is
  the named route; it adds `-s -v --log-cli-level=INFO`. Keep the target small.
- The worker sizing and the serial-run check live in `tests/conftest.py` as
  run policy, not as fixtures.
- `pdm run test-docker` runs the Docker lane (`-m docker tests/integration`).
  Each worker starts one Postgres server on first use and migrates one
  template database; `migrated_db`, `database_url` and `db_session` give each
  module its own copy of the template, `empty_module_database` and
  `fresh_database` give empty databases. Never start a `PostgresContainer` in
  a test.

## Test Performance

Every xdist worker imports and collects every selected module, so collection
cost is paid once per worker (24 times on Hemma).

- Do no expensive work at import or collection time: no conversions, replays,
  renders or corpus parsing in module-level code or in `parametrize` lists.
  Parametrize over cheap identifiers (exam stems, file names) and compute the
  data inside the test through a cached helper.
- Parse or build an immutable input once per process: `tests/fixtures/docx_corpus.py`
  caches corpus DOCX bytes and chunks; cache other immutable fixtures the same
  way (`functools.cache` or a module/session fixture). Never share mutable
  state between tests.
- An expensive result that many tests read across workers goes through a
  run-scoped shared cache, as `docx_conversion_cache.py` does for default
  exam conversions (pickled into the run's temp directory under a file lock).
- Tests must be safe under xdist: write files under `tmp_path`, never fixed
  paths, ports or process-wide state that another worker shares.
- A unit test never depends on a build artifact (for example the built SPA);
  it writes its own input under `tmp_path`.
- Before adding a slow test, check `--durations` for the file; a test that
  needs more than a second should say why in its docstring.

## Commands

Use the command map in `docs/runbooks/run-skript-runbook-testing-pytest-vitest-playwright-runbook-testing-pytest-vitest-playwright.md` and `AGENTS.md`.
Prefer focused pytest targets while iterating, then the backend close-out gates
required for the touched layer.
