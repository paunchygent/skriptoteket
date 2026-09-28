---
type: runbook
id: RUN-SKRIPT-skriptoteket-staging-on-hemma
title: Skriptoteket staging on Hemma
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-09-28'
status: draft
system: hemma.hule.education
summary: Operate the skriptoteket-dev staging stack beside HuleEdu staging on Hemma and reach it from the Mac tunnel
---

## Trigger

Run this procedure when a Skriptoteket change needs the per-task Hemma staging
walk (EPIC-SKRIPT-40), after the change is merged to `main` and `main` is
pushed. The repository operator runs it on Hemma as `paunchygent` and on the
Mac as the tunnel owner. Staging proves `main`; a failed walk is fixed forward
on `main`, never patched in the staging checkout.

## Preconditions

- HuleEdu staging (project `huleedu-dev` on the rootless daemon
  `unix:///run/user/1000/docker.sock`) is running and includes
  TASK-HULE-REP-0087: its Gateway on `127.0.0.1:18080` accepts Skriptoteket
  returns to `http://127.0.0.1:15173/auth/callback` and routes `/api` to
  `http://skriptoteket-web:8000`.
- The external network `huleedu-dev_hule-network` exists on the rootless
  daemon.
- The HuleEdu staging Gateway public key exists at
  `/home/paunchygent/apps/huleedu-dev/secrets/local-runtime/internal-identity/gateway-internal-identity-public-key.pem`.
  Staging mounts only this public key file, read-only, never the key directory
  (it also holds the private key). Never print key material.
- The HuleEdu staging proof-subject export exists at
  `/home/paunchygent/apps/huleedu-dev/output/skriptoteket-proof-identities/subject-export.json`
  and maps `skriptoteket-proof-user`, `skriptoteket-proof-contributor`, and
  `skriptoteket-proof-admin` to `user`, `contributor`, and `admin`. Proof
  passwords live only in the untracked HuleEdu staging `.env`; never print or
  retain them.
- Hemma loopback ports `127.0.0.1:18000` and `127.0.0.1:5173` are free
  (`ss -ltn`).

## Topology

| Surface           | Address                                                                                        | Owner                                   |
| ----------------- | ---------------------------------------------------------------------------------------------- | --------------------------------------- |
| Staging checkout  | `/home/paunchygent/apps/skriptoteket-dev`                                                      | this runbook                            |
| Compose project   | `skriptoteket-dev`, file `compose.hemma-dev.yaml`, rootless daemon                             | `pdm run hemma-dev`                     |
| Web               | Hemma `127.0.0.1:18000`; alias `skriptoteket-web` on `huleedu-dev_hule-network`                | `web` service                           |
| Worker and runner | `worker` service; runner image `skriptoteket-dev-runner:latest` in the rootless image store    | `worker` service                        |
| Database          | Postgres 16 in project volume `db_data`; no host port                                          | `db` service                            |
| SPA               | Hemma `127.0.0.1:5173`, user unit `skriptoteket-vite-dev.service`                              | `systemd/skriptoteket-vite-dev.service` |
| Browser origin    | Mac `http://127.0.0.1:15173` (shared tunnel to Hemma `127.0.0.1:5173`)                         | Mac tunnel                              |
| Sign-in           | Mac `http://127.0.0.1:15174/api/auth/login` (HuleEdu staging Vite `/api` proxy to the Gateway) | HuleEdu staging                         |

Vite lanes in the unit: protected `/api` goes to the HuleEdu staging Gateway
`http://127.0.0.1:18080`; public API, share, and backend static routes go to
`http://127.0.0.1:18000`. The browser calls HuleEdu auth directly at
`http://127.0.0.1:15174/api` (`VITE_HULEEDU_AUTH_BASE_URL`) because the Mac
reaches the staging Gateway only through HuleEdu Vite on the tunnelled 15174
port. Only the login ceremony is supported; the register and password-reset
entry URLs drop the `/api` prefix and are outside this lane. The Sir Convert
route is outside this lane.

`web` and `worker` run as container root, mount the rootless socket, and set
`DOCKER_HOST=unix:///run/user/1000/docker.sock`; the rootless uid map makes
container root the socket owner. They share the project volumes
`artifacts_data` (`/app/.artifacts`) and `vault_data`
(`/var/lib/skriptoteket/vault`), the production paths.

## Steps

### One-time bootstrap on Hemma

1. Clone the staging checkout:

   ```bash
   git clone git@github.com:paunchygent/skriptoteket.git /home/paunchygent/apps/skriptoteket-dev
   ```

2. Create the untracked staging `.env` with one variable, a new random
   staging-only database password (never the production value):

   ```bash
   cd /home/paunchygent/apps/skriptoteket-dev
   umask 077
   printf 'SKRIPTOTEKET_DEV_DB_PASSWORD=%s\n' "$(openssl rand -hex 24)" > .env
   ```

3. Select the PDM interpreter for the lifecycle command (it uses only the
   standard library):

   ```bash
   pdm use -f /home/paunchygent/.local/share/pdm/python/cpython@3.14.2/bin/python3
   ```

4. Build, install the Vite unit, and start:

   ```bash
   pdm run hemma-dev build
   pdm run hemma-dev install-vite-unit
   pdm run hemma-dev start
   pdm run hemma-dev status
   ```

### One-time tunnel line on the Mac

1. Add this line to `~/.local/bin/hemma-shared-tunnel`, directly after the
   `-L 127.0.0.1:13001:127.0.0.1:13001 \` line:

   ```text
     -L 127.0.0.1:15173:127.0.0.1:5173 \
   ```

2. Restart the LaunchAgent and confirm the listener:

   ```bash
   launchctl kickstart -k gui/$(id -u)/com.paunchygent.hemma-shared-tunnel
   lsof -nP -iTCP:15173 -sTCP:LISTEN
   ```

The tunnel script has no source control; this runbook is the record of the
line.

### Per-task walk update

1. On Hemma, fast-forward to the pushed `main`:

   ```bash
   cd /home/paunchygent/apps/skriptoteket-dev
   git fetch origin main
   git merge --ff-only origin/main
   git rev-parse HEAD
   git status --porcelain
   ```

2. Rebuild images and frontend dependencies when the change touches the
   backend, the runner, or frontend dependencies, then start:

   ```bash
   pdm run hemma-dev build
   pdm run hemma-dev start
   pdm run hemma-dev status
   ```

   `start` runs, in order: database up and healthy, `db-upgrade` to the
   checked-out revision, `web` and `worker` up and healthy, `web` `/healthz`,
   `consume-huleedu-subject-export --export-json /run/huleedu/proof-identities/subject-export.json --apply`,
   `setup-staging-proof-fixture`, then the Vite unit and `127.0.0.1:5173`.

3. On the Mac, open exactly `http://127.0.0.1:15173` (not `localhost`; the
   tunnel binds `127.0.0.1`).

### Staging proof fixture

`setup-staging-proof-fixture` ensures one harmless tool through the existing
catalog and scripting handlers:

- slug `staging-provverktyg`, title `Staging-provverktyg`, created by
  `skriptoteket-proof-admin`;
- `skriptoteket-proof-contributor` assigned as maintainer;
- one draft created by the contributor whose `run_tool` returns the notice
  `Staging-provkörningen är klar.`

The step is idempotent: a repeat run reuses the tool, the maintainer, and the
contributor's draft. It reuses an existing `staging-provverktyg` tool only when
`skriptoteket-proof-admin` owns it, and stops without writes if another user
owns a tool with that slug or created its draft head.
It never acquires the draft lock; the walk locks the draft in the editor.

Rerun only the fixture (for example after the contributor's draft was
published or replaced):

```bash
cd /home/paunchygent/apps/skriptoteket-dev
pdm run hemma-dev fixture
```

`setup-staging-proof-fixture` also guards itself: it exits with status 1
before opening a database session unless `ENVIRONMENT=staging` and
`DATABASE_URL` points at database `skriptoteket` on host `db` (the
`skriptoteket-dev` database service). It never writes to production, which
uses `shared-postgres`.

For a clean fixture, run `pdm run hemma-dev reset`.

### Other lifecycle commands

- `pdm run hemma-dev stop` stops the Vite unit and the containers; volumes
  stay.
- `pdm run hemma-dev reset` stops the Vite unit, runs `docker compose down --volumes --remove-orphans` for `skriptoteket-dev` only, then the complete
  start. It never touches HuleEdu identities, containers, or the external
  HuleEdu network.

## Expected Results

- `pdm run hemma-dev status` prints `db: healthy`, `web: healthy`,
  `worker: healthy`, `web /healthz ... : 200`, `frontend (...): healthy`, and
  `skriptoteket-dev staging: healthy`, and exits 0.
- `start` prints `HuleEdu subject export apply ok: ...` and
  `Staging proof fixture ok: tool_slug=staging-provverktyg, ...`.
- In the browser at `http://127.0.0.1:15173` the proof contributor signs in
  through HuleEdu staging, returns to `/auth/callback`, opens the
  `staging-provverktyg` draft in the editor, locks it, runs it in the sandbox,
  and sees `Staging-provkörningen är klar.`

## Stop Conditions

- The proof-subject export, the staging public key, or
  `huleedu-dev_hule-network` is missing: `hemma-dev start` exits 2 before any
  container change. Restore HuleEdu staging first.
- `hemma-dev` refuses the production checkout
  `/home/paunchygent/apps/skriptoteket` and any `DOCKER_HOST` other than the
  rootless socket. Never run staging against the system Docker socket or
  production data.
- A sandbox run fails a runner limit on the rootless daemon: stop and report;
  never weaken runner limits.
- Never produce the failure toast by stopping a staging service; use the
  named reversible action recorded before the walk.

## Rollback

Staging holds no production data. `pdm run hemma-dev stop` removes it from
service; `pdm run hemma-dev reset` rebuilds its data from the HuleEdu export
and the fixture. To remove the tunnel line, delete it from
`~/.local/bin/hemma-shared-tunnel` and restart the LaunchAgent with the same
`launchctl kickstart -k` command.
