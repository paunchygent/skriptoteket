---
type: pr
id: PR-0210
title: "Flunk-Out Frenzy: file size compliance and frontend module decomposition"
status: ready
owners: "agents"
created: 2026-04-03
updated: 2026-04-03
stories:
  - "ST-25-05"
tags: ["frontend", "games", "refactoring", "architecture", "code-quality"]
dependencies:
  - "PR-0209"
acceptance_criteria:
  - "All Flunk-Out Frenzy frontend files are under the 500 LoC hard limit per repo rules."
  - "FlunkOutFrenzyView.vue is decomposed from 1109 lines into focused sub-components and composables."
  - "PhysicsWorld.spec.ts is split into domain-specific test modules without losing coverage."
  - "compilePinballTable.ts is refactored into a compiler directory with single-responsibility modules."
  - "No behavioral regressions in existing game functionality (launch, flip, drain, scoring)."
  - "All existing tests pass after decomposition (pdm run fe-test)."
---

## Problem

Multiple Flunk-Out Frenzy frontend files violate the repo's hard file size limit
(<400-500 LoC per `.agents/rules/010-foundational-principles.md` and
`.agents/rules/050-python-standards.md`):

| File | Lines | Over Limit |
|------|-------|------------|
| `FlunkOutFrenzyView.vue` | 1109 | +609 |
| `PhysicsWorld.spec.ts` | 1206 | +706 |
| `compilePinballTable.ts` | 1019 | +519 |
| `launcherChain3d.ts` | 856 | +356 |
| `prototypeAlphaVpwDonorMap.ts` | 845 | +345 |
| `PhysicsWorld.ts` | 743 | +243 |
| `prototypeAlphaTableSpec.ts` | 739 | +239 |

These oversized files:
- Violate the "Zero Tolerance for Vibe Coding" rule (no undocumented shortcuts)
- Risk becoming monolithic "god modules" that hinder testability
- Complicate future mechanics work (ST-25-05, ST-25-06)
- Make code review and maintenance more difficult

## Goal

Decompose all oversized Flunk-Out Frenzy modules into focused, single-responsibility
files that comply with the 500 LoC hard limit while preserving all existing
behavior and test coverage.

## Non-goals

- No new game mechanics or features (pure refactoring)
- No changes to the bootstrap contract or backend APIs
- No visual redesign of the game shell
- No changes to physics behavior or game balance

## Implementation plan

### Phase 1: View Layer Decomposition

Refactor `FlunkOutFrenzyView.vue` (1109 lines):

```
views/apps/flunkOutFrenzy/
├── FlunkOutFrenzyView.vue                 (~200 lines - shell orchestration)
├── components/
│   ├── FofGameScene.vue                   (~150 lines - playfield host)
│   ├── FofStatusCluster.vue               (~100 lines - HUD plaques)
│   ├── FofServiceCluster.vue              (~120 lines - controls panel)
│   ├── FofSettingsPanel.vue               (~150 lines - settings drawer)
│   └── FofKeyGuide.vue                    (~80 lines - keyboard help)
├── composables/
│   └── useCabinetFrameSizing.ts           (~100 lines - resize observer logic)
└── styles/
    └── fof-shell.css                      (~250 lines - extracted styles)
```

### Phase 2: Test File Decomposition

Split `PhysicsWorld.spec.ts` (1206 lines):

```
physics/
├── __tests__/
│   ├── PhysicsWorld.collisions.spec.ts    (~250 lines)
│   ├── PhysicsWorld.flippers.spec.ts      (~200 lines)
│   ├── PhysicsWorld.launcher.spec.ts      (~250 lines)
│   ├── PhysicsWorld.captureDevices.spec.ts (~200 lines)
│   └── helpers/
│       └── physicsTestHelpers.ts          (~150 lines)
```

### Phase 3: Table Compiler Decomposition

Refactor `compilePinballTable.ts` (1019 lines):

```
table/
├── compiler/
│   ├── compilePinballTable.ts             (~200 lines - orchestrator)
│   ├── compileWalls.ts                    (~150 lines)
│   ├── compileBumpers.ts                  (~150 lines)
│   ├── compileSensors.ts                  (~150 lines)
│   ├── compileRails.ts                    (~150 lines)
│   └── compileCaptureDevices.ts           (~150 lines)
└── types/
    └── compilerTypes.ts                   (~80 lines)
```

### Phase 4: Launcher Chain Decomposition

Split `launcherChain3d.ts` (856 lines):

```
physics/
├── launcher/
│   ├── LauncherChain3D.ts                 (~350 lines - core class)
│   ├── LauncherContactTelemetry.ts        (~150 lines - contact tracking)
│   ├── LauncherTravelRoute.ts             (~200 lines - route management)
│   └── LauncherReleaseIntegration.ts      (~180 lines - release logic)
└── utils/
    └── rapier3dHelpers.ts                 (~100 lines)
```

### Phase 5: Supporting Module Cleanup

- `prototypeAlphaVpwDonorMap.ts` → Split into `donorWalls.ts`, `donorBumpers.ts`, `donorSensors.ts`
- `PhysicsWorld.ts` → Extract `PhysicsWorldFlippers.ts`, `PhysicsWorldSensors.ts`
- `prototypeAlphaTableSpec.ts` → Extract device-specific spec modules

## Test plan

Automated:

```bash
# Frontend unit tests
pdm run fe-test -- --run src/components/apps/flunk-out-frenzy

# Type checking
pdm run fe-type-check

# Build verification
pdm run fe-build

# Docs validation
pdm run docs-validate
```

Manual/live:

- Play one complete local run at `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
- Verify: launch, flipper response, drain detection, scoring, game over, restart
- Verify: pause/resume, mute toggle, settings panel
- Verify: No console errors or runtime warnings

## Rollback plan

- Git revert the decomposition commits
- Restore original oversized files from git history
- Re-run tests to verify baseline behavior

## Risk assessment

| Risk | Mitigation |
|------|------------|
| Behavioral regression during file moves | Comprehensive test coverage before refactoring; no logic changes during moves |
| Import path breakage | Update all relative imports; verify with TypeScript compiler |
| Test coverage gaps | Ensure all original test cases are preserved across split files |
| Style leakage after CSS extraction | Verify visual parity with before/after screenshots |

## Related documentation

- `.agents/rules/010-foundational-principles.md` - File size limits and "no vibe coding"
- `.agents/rules/050-python-standards.md` - Style and formatting rules
- `.agents/rules/025-curated-apps.md` - Curated app architecture
- `docs/backlog/stories/story-25-05-flunk-out-frenzy-mechanics-port-foundation.md` - Parent story
- `docs/backlog/epics/epic-25-competitive-games-and-flunk-out-frenzy.md` - Parent epic
