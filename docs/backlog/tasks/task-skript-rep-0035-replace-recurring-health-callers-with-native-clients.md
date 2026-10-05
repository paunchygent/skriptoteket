---
type: task
id: TASK-SKRIPT-REP-0035
title: Replace recurring health callers with native clients
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-05'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- Native callers preserve web readiness and worker dependency predicates in production and staging.
- Focused failure proof and actual image tools, runtime configuration and client cost are recorded.
backlog_document_profile: contract-derived
---

## Implementation Contract

Replace recurring Python callers with native clients under the user-accepted
minimal health architecture. The parent admitted implementation on 2026-10-05.
Preserve health claims, detection cadence, startup grace and bounded failures.

## Contract Inputs

- User-accepted architecture: skill-repository retained session
  `01a10378-68fe-78bc-b530-f9268d075ccf`,
  `evidence/architecture/minimal-health-probes-20261005.md`.
- Current source/image/runtime proof:
  `evidence/post-repair-exact-cause-20261005/` in that session.
- Parent owns lane lifecycle, integration, publication and final observation.
  Source edits, proof, builds and rollout occur on Hemma.

## Core Vertical And Performance

Web uses curl while preserving HTTP failure, redirects, proxy behavior and
existing Compose timeout. The readiness handler retains pooled SQL and
configured SMTP checks.

One named worker script authenticates to PostgreSQL and executes `SELECT 1`,
validates Docker's actual `/_ping` response and creates, writes and removes
a unique artifact file under the runtime user and artifact directory. Preserve
asyncpg URI-prefix conversion, deployed URI authentication, the two-second
database connection bound, three-second Docker bound and safe diagnostics.

Add PostgreSQL client to the shared web/worker image; curl already exists.
Operator and fast entrypoints delegate to the canonical script. Preserve
production's default Docker socket, staging's rootless socket, environment,
mounts and all health timing. Report image size and process CPU separately from
wall latency.

## Validation

Focused HTTP success, failure, redirect and timeout; database authentication
and query failures; Docker response failure; artifact write failure and cleanup.
Verify real image tools, runtime user, mounts, nonsecret environment, health argv
and unchanged timing. Run affected shell/Python lint, type, tests and docs gates.
Long jobs run detached with terminal receipts. Parent coordinates one final
natural observation after both repository lanes settle.

Focused delivery proof on 2026-10-05: 19 tests passed, including real curl
success/failure/redirect/304/timeout/proxy cases, SQL exit failure, Docker
response failure and actual failed write with cleanup. ShellCheck, focused
Ruff/mypy, docs validation, handoff validation and diff checks passed.

Candidate `skriptoteket-native-health:rep0035` is
`sha256:7bf298db6d9bc158378bc68eb75803eafccd3241311b132599ba8e4dff0d86d0`.
Its 2,122,191,651 bytes add 7,387,326 bytes versus the prior production image.
Actual-image proof passed authenticated SQL, bad authentication, query failure,
bad Docker response, unwritable directory and failed-write cleanup. The image
contains curl 8.14.1 and psql 17.11. Production runtime user is UID 0 and the
artifact root is `/app/.artifacts`; Docker uses its default Unix socket.

On the same image/dependencies, 10 worker samples averaged 0.01994 CPU seconds
and 0.02169 wall seconds with native clients, versus 0.39829 CPU and 0.40516
wall seconds for the previous Python checker. Three web samples averaged
0.00606 caller CPU and 1.97386 wall seconds, versus 0.11450 caller CPU and
2.01738 wall seconds for Python. HTTP cost preserves the localhost Host header;
readiness handler and dependency CPU are outside these caller measurements.

Rootless staging actual-image proof also passed all six success/failure cases,
using UID 0, `/app/.artifacts` and
`unix:///run/user/1000/docker.sock`. Its 10 worker samples averaged
0.01943 CPU/0.02096 wall seconds native versus 0.39615 CPU/0.41747 wall
seconds Python. Three web samples averaged 0.00407 CPU/0.00554 wall native
versus 0.08840 CPU/0.09020 wall Python. The staging proof uses its existing
default-network `web` alias with the localhost Host header.

Raw logs, terminal job receipts, failure fixtures and measurements are in
`.artifacts/native-health/` in the admitted Hemma task worktree. Parent-owned
publication, targeted rollout and final natural observation remain pending.

## Stop Conditions

Return material scope conflicts, genuine tool refusal or foreign-owned blockers
to the parent. Preserve foreign changes. No caching, heartbeat publisher,
monitoring service, service algorithm, fan/GPU or scheduling change.

## Decided Contract Terms

| ID | Decided contract term |
| --- | --- |
| D1 | Preserve pooled SQL and configured SMTP web readiness. |
| D2 | Native web caller preserves failure, redirects, proxy and timeout semantics. |
| D3 | One native worker script keeps authenticated SQL, Docker response and actual artifact write. |
| D4 | Preserve DSN prefix conversion, authentication, bounds and deployed sockets. |
| D5 | Add PostgreSQL client to the actual image and measure its tradeoff. |
| D6 | Operator/fast entrypoints delegate and duplicate dependency checks are removed. |
| D7 | Source, build, proof and rollout run on Hemma in the admitted lane. |
| D8 | User waived additional implementation agents and review loops. |
| D9 | Parent integrates/publishes main and coordinates final natural observation. |
