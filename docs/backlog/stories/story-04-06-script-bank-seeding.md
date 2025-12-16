---
type: story
id: ST-04-06
title: "Repo script bank + seeding till DB"
status: done
owners: "agents"
created: 2025-12-16
epic: EPIC-04
acceptance_criteria:
  - "Det finns en repo-nivå script bank med svensk, lärarfokuserad exempeltool."
  - "Det finns ett CLI-kommando som kan seed:a script bank till databasen på ett idempotent sätt (per slug)."
  - "Default-beteende skriver inte över existerande metadata/kod utan explicit opt-in (`--sync-*`)."
  - "Det finns en generisk runbook för hur seed körs i prod (Docker) och lokalt."
---

## Bakgrund

Vi vill kunna fylla tjänsten med realistiska exempelverktyg utan att manuellt klicka i UI efter varje deploy.
Detta hjälper även att identifiera framtida backend-behov för mer avancerade scripts (t.ex. fler inputtyper,
rapportmallar, cache/lagring, etc).

## Leverans (implementation)

- Script bank:
  - `src/skriptoteket/script_bank/`
- CLI seed:
  - `pdm run seed-script-bank`
  - `src/skriptoteket/cli/main.py`
- Runbook:
  - `docs/runbooks/runbook-script-bank-seeding.md`
- Test:
  - `tests/unit/test_script_bank.py`

