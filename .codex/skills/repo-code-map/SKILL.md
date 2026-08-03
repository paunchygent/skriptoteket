---
name: repo-code-map
description: "Skriptoteket repo-local entry point for platform discovery. Use when orienting in the repository: where the backend layers, curated apps, sandboxed runner, frontend workspace, docs surface, and deploy lanes live, which layer owns a change, and how the pieces call each other. Triggers on questions about how this repository is organized, where a concern lives, or which boundary a change crosses."
type: "skill"
created: "2026-08-03"
last_updated: "2026-08-03"
scope: "repo"
---

# Skriptoteket Code-Map Router

Read
`.codex/skills/repo-code-map/references/platform-discovery-overview.md` for the
repository's topology, layer boundaries, and delivery surfaces. It is the first
read for orientation and the only map in this lane.

| Surface                  | Map                                                                     |
| ------------------------ | ----------------------------------------------------------------------- |
| Whole-Platform Discovery | `.codex/skills/repo-code-map/references/platform-discovery-overview.md` |

The overview states topology and links onward. It does not restate routes,
commands, or engineering rules. For those, read the authority directly:

- Repository routes, invariants, and command policy: `AGENTS.md`.
- Backend architecture, DI, Unit of Work, runner contracts:
  `.codex/skills/skriptoteket-backend-dev/SKILL.md`.
- Test strategy, fixtures, and lane selection:
  `.codex/skills/skriptoteket-testing/SKILL.md`.
- Durable docs and generated indexes: `docs/index.md`.

After a structural change to `src/skriptoteket/`, `frontend/`, `runner/`, or the
docs topology, update the overview and refresh its as-of line. Run
`pdm run skills-validate`.
