---
type: pr
id: PR-0265
title: "Docs mockup bundle contract and existing preview indexes"
status: done
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
stories:
  - "ST-32-07"
tags: ["docs", "mockup", "ux", "docs-as-code"]
acceptance_criteria:
  - "Given mockups are a canonical design-before-code surface, when docs validation runs, then `docs/mockups/` is an allowed docs top-level lane with typed bundle README support."
  - "Given multiple designers may submit competing layouts, when a mockup bundle is created, then the structure supports `submissions/` and `winner/` subfolders without moving existing preview resources."
  - "Given mockups are a creative design and proofing ground, when non-Markdown files live under `docs/mockups/`, then HTML/CSS/JS/SVG/images/fonts/fixtures and similar resources are explicitly allowed without frontmatter validation."
  - "Given existing backlog docs link to mockup preview files, when this slice lands, then existing `index.html`, designer HTML, and SVG asset paths remain stable."
---

## Problem

`docs/mockups/` exists and is already used by live planning slices, but the docs-as-code contract
does not treat it as a typed canonical lane. Existing mockup folders also lack the explicit bundle
shape now used in HuleEdu for competitive designer submissions and winner iterations.

## Goal

Port the HuleEdu mockup-bundle system into Skriptoteket:

- `docs/mockups/INDEX.md` is the lane doorway.
- each page/component/bundle has its own folder,
- each bundle has a typed `README.md`,
- designer submissions can live under `submissions/`,
- promoted/winning iterations can live under `winner/`,
- non-Markdown design/proofing resources are explicitly allowed without
  frontmatter validation,
- existing direct preview assets remain stable.

## Non-goals

- Do not redesign any mockup.
- Do not move existing HTML/SVG preview assets or break current backlog links.
- Do not implement production frontend changes.

## Implementation plan

1. Add `mockups` to `docs/_meta/docs-contract.yaml`.
2. Add typed `mockup` frontmatter rules for bundle README docs.
3. Add `docs/mockups/INDEX.md` as the mockup lane doorway.
4. Add `README.md` entry docs plus `submissions/` and `winner/` placeholders to existing bundles.
5. Update `docs/index.md` and `.agents/handoff.md` with the new contract.

## Test plan

- `pdm run docs-validate`
- `git diff --check`

## Rollback plan

Remove the mockup type from `docs/_meta/docs-contract.yaml`, delete the added bundle README/index
docs and placeholder folders, and restore `docs/index.md` / `.agents/handoff.md` references.
