# Documentation

This repo uses a **Docs-as-Code** contract to keep documentation consistent and machine-checkable.

- Contract (source of truth): `docs/_meta/docs-contract.yaml`
- Templates: `docs/templates/`
- Validate locally: `pdm run docs-validate`

## Key documents

- PRD (MVP): `docs/prd/prd-script-hub-v0.1.md`
- PRD (Planned): `docs/prd/prd-script-hub-v0.2.md`
- Release notes: `docs/releases/`
- ADRs: `docs/adr/`
- Backlog: `docs/backlog/`

## Agent support

- Start-here: `.agent/readme-first.md`
- Session handoff: `.agent/handoff.md`
- Next-session prompt template: `.agent/next-session-instruction-prompt-template.md`
