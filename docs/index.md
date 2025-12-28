# Documentation

This repo uses a **Docs-as-Code** contract to keep documentation consistent and machine-checkable.

- Contract (source of truth): `docs/_meta/docs-contract.yaml`
- Templates: `docs/templates/`
- Validate locally: `pdm run docs-validate`

## Key documents

- PRD (MVP): `docs/prd/prd-script-hub-v0.1.md`
- PRD (Planned): `docs/prd/prd-script-hub-v0.2.md`
- PRD (Frontend): `docs/prd/prd-spa-frontend-v0.1.md`
- PRD (Editor Sandbox): `docs/prd/prd-editor-sandbox-v0.1.md`
- Implementation map (v0.2): `docs/reference/ref-implementation-map-script-hub-v0-2.md`
- Editor sandbox preview plan: `docs/reference/ref-editor-sandbox-preview-plan.md`
- Migration roadmap (SPA): `docs/reference/reports/ref-vue-spa-migration-roadmap.md`
- Toasts + system messages (SPA): `docs/reference/ref-toast-system-messages.md`
- Active sprint: `docs/backlog/sprints/sprint-2026-01-05-tool-editor-vertical-slice.md`
- Release notes: `docs/releases/`
- ADRs: `docs/adr/`
- Backlog: `docs/backlog/`

## Agent support

- Start-here: `.agent/readme-first.md`
- Session handoff: `.agent/handoff.md`
- Next-session prompt template: `.agent/next-session-instruction-prompt-template.md`
