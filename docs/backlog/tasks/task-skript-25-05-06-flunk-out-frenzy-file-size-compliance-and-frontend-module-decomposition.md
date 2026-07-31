---
type: task
id: TASK-SKRIPT-25-05-06
title: 'Flunk-Out Frenzy: file size compliance and frontend module decomposition'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-25-05
task_kind: story
acceptance_criteria:
- All Flunk-Out Frenzy frontend files are under the 500 LoC hard limit per repo rules.
- FlunkOutFrenzyView.vue is decomposed from 1109 lines into focused sub-components
  and composables.
- The Flunk-Out Frenzy physics spec surface is split into domain-specific `game/physics/__tests__/PhysicsWorld.*.spec.ts`
  modules without losing coverage.
- compilePinballTable.ts is refactored into a compiler directory with single-responsibility
  modules.
- No behavioral regressions in existing game functionality (launch, flip, drain, scoring).
- All existing tests pass after decomposition (pdm run fe-test).
- Component communication follows the Props/Events pattern without circular dependencies.
- CSS styles are namespace-scoped under .fof-game-container to prevent global leakage.
- No memory leaks detected during 60fps stability check (Chrome DevTools Memory tab).
dependencies:
- TASK-SKRIPT-25-06-12
---

## Context
### Problem
Multiple Flunk-Out Frenzy frontend files violate the repo's hard file size limit
(<400-500 LoC per `.codex/rules/010-foundational-principles.md` and
`.codex/rules/050-python-standards.md`):

| File | Lines | Over Limit |
|------|-------|------------|
| `FlunkOutFrenzyView.vue` | 1109 | +609 |
| `Flunk-Out Frenzy physics spec surface` | 1206 | +706 |
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
### Risk assessment
| Risk | Mitigation |
|------|------------|
| Behavioral regression during file moves | Comprehensive test coverage before refactoring; no logic changes during moves |
| Import path breakage | Update all relative imports; verify with TypeScript compiler |
| Test coverage gaps | Ensure all original test cases are preserved across split files |
| Style leakage after CSS extraction | Verify visual parity with before/after screenshots; namespace all CSS |
| Prop-drilling in view decomposition | Props/events pattern enforced; max prop depth of 2; events bubble to parent |
| Physics performance degradation | Delegation pattern keeps direct references; benchmark 60fps before/after |
| Compiler contract drift | Strict TypeScript interfaces; runtime completeness assertion |
### Related documentation
- `.codex/rules/010-foundational-principles.md` - File size limits and "no vibe coding"
- `.codex/rules/050-python-standards.md` - Style and formatting rules
- `.codex/rules/025-curated-apps.md` - Curated app architecture
- `docs/backlog/stories/story-25-05-flunk-out-frenzy-mechanics-port-foundation.md` - Parent story
- `docs/backlog/epics/epic-25-competitive-games-and-flunk-out-frenzy.md` - Parent epic

## Decision And Assumption Ledger
The source record did not define a separate section for this package heading.

## Story Contract Slice
### Goal
Decompose all oversized Flunk-Out Frenzy modules into focused, single-responsibility
files that comply with the 500 LoC hard limit while preserving all existing
behavior and test coverage.
### Non-goals
- No new game mechanics or features (pure refactoring)
- No changes to the bootstrap contract or backend APIs
- No visual redesign of the game shell
- No changes to physics behavior or game balance

## Contract Inputs
The source record did not define a separate section for this package heading.

## Plan
### Implementation plan
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

#### Communication & State Pattern (Phase 1)

To prevent "prop-drilling hell" or fragmented reactive state:

- **Source of Truth**: `FlunkOutFrenzyView.vue` owns the authoritative game state
  (bootstrap data, HUD snapshot, runtime load state) via `ref()`/`computed()`.
- **Props Down**: Parent passes primitive props and callbacks to children:
  - `FofStatusCluster`: receives `hud: GameHudSnapshot` (read-only)
  - `FofServiceCluster`: receives `canStart`, `canPause`, `onStart`, `onPauseToggle`
  - `FofGameScene`: receives `runtimeFactory`, `audioEnabled`, emits `@hudChange`, `@bootError`
- **Events Up**: Child components emit events for user actions; parent handles state mutations.
- **No Pinia Store**: Local game state is ephemeral and scoped to the route; no global state needed.
- **No Provide/Inject**: Avoid implicit dependencies; explicit props/events maintain clarity.

Pattern enforced by: ESLint `vue/require-explicit-emits`, manual code review for prop depth.

#### CSS Scoping (Phase 1)

All extracted styles in `fof-shell.css` are namespace-scoped:

```css
/* fof-shell.css - All selectors prefixed */
.fof-game-container { /* root namespace */ }
.fof-game-container .fof-status-cluster { /* child elements */ }
.fof-game-container .fof-service-cluster { }
```

- No global element selectors (e.g., `button`, `div`)
- No CSS custom properties at `:root` that could leak
- Scoped under `.fof-game-container` to isolate from Skriptoteket shell

### Phase 2: Test File Decomposition

Split the former monolithic Flunk-Out Frenzy physics spec surface (1206 lines):

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

Each test file:
- Imports shared helpers from `physicsTestHelpers.ts`
- Sets up its own isolated Rapier world instance
- Runs independently (no test interdependencies)

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

#### Compiler Orchestration Contract (Phase 3)

To prevent "Contract Drift" between orchestrator and sub-compilers:

Strict interfaces in `compilerTypes.ts`:

```typescript
// Each sub-compiler implements this interface
interface TableElementCompiler<T extends TableDeviceDefinition> {
  compile(device: T, world: Rapier.World, context: CompilerContext): CompiledElement;
}

// Orchestrator validates output completeness
interface CompiledTable {
  walls: CompiledWall[];
  bumpers: CompiledBumper[];
  sensors: CompiledSensor[];
  rails: CompiledRail[];
  captureDevices: CompiledCaptureDevice[];
  // Mandatory: must have all keys, no partial returns
}
```

- Each `compile*.ts` module exports a pure function matching `TableElementCompiler`
- `compilePinballTable.ts` orchestrator aggregates results and validates completeness
- TypeScript enforces: missing return properties cause compile-time errors
- Runtime assertion: `assertCompleteTable(compiled)` throws if any category is missing

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
- `prototypeAlphaTableSpec.ts` → Extract device-specific spec modules

#### PhysicsWorld Delegation Architecture (Phase 5)

For `PhysicsWorld.ts` extraction, use a **Delegation Pattern** (not mixins):

```typescript
// PhysicsWorld.ts - remains owner of Rapier world
class PhysicsWorld {
  private readonly world: Rapier.World;
  private readonly flipperHandler: FlipperHandler;  // delegated
  private readonly sensorHandler: SensorHandler;    // delegated

  constructor(config: WorldConfig) {
    this.world = new Rapier.World(config.gravity);
    // Delegates initialized with direct world reference
    this.flipperHandler = new FlipperHandler(this.world, config.flippers);
    this.sensorHandler = new SensorHandler(this.world, config.sensors);
  }

  step(dtMs: number): WorldSnapshot {
    // Delegates handle specific logic; PhysicsWorld orchestrates
    this.flipperHandler.update(dtMs);
    const sensorEvents = this.sensorHandler.poll();
    this.world.step();
    return this.buildSnapshot(sensorEvents);
  }
}
```

- `PhysicsWorld` retains sole ownership of `Rapier.World` instance
- Handlers receive world reference in constructor; no runtime lookup
- Handlers are stateless logic wrappers (no internal world state duplication)
- Direct method calls (not event emitters) for 60fps performance
- Handlers are testable in isolation by injecting mock world

Performance requirement: No `requestAnimationFrame` jitter; maintain 60fps stable.
### Test plan
Automated:

```bash
### Frontend unit tests
pdm run fe-test -- --run src/components/apps/flunk-out-frenzy

### Type checking (enforces compiler contracts)
pdm run fe-type-check

### Build verification
pdm run fe-build

### Docs validation
pdm run docs-validate
```

Manual/live:

- Play one complete local run at `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`
- Verify: launch, flipper response, drain detection, scoring, game over, restart
- Verify: pause/resume, mute toggle, settings panel
- Verify: No console errors or runtime warnings

### Performance & Memory Verification

**60fps Stability Check:**
- Open Chrome DevTools > Performance tab
- Record 30 seconds of gameplay
- Verify: No dropped frames, consistent 60fps, no long task warnings

**Memory Leak Check:**
- Open Chrome DevTools > Memory tab
- Take heap snapshot before starting game
- Play 3 complete games (launch, play, drain x3)
- Take heap snapshot after games complete
- Verify: Memory delta < 10MB, no retained `GameRuntime` instances in heap
- Force GC (`performance.memory` if available) and confirm cleanup

**CSS Leakage Check:**
- Load game, then navigate to Skriptoteket home/catalog
- Verify: No layout shifts, color overrides, or broken button styles
- Check computed styles on main navigation buttons remain unchanged
### Rollback plan
- Git revert the decomposition commits
- Restore original oversized files from git history
- Re-run tests to verify baseline behavior

## Implementation Steps
The source record did not define a separate section for this package heading.

## Proof
The source record did not define a separate section for this package heading.

## Validation
The source record did not define a separate section for this package heading.

## Stop Conditions
The source record did not define a separate section for this package heading.

## Lessons Learned
The source record did not define a separate section for this package heading.

## Notes
The source record did not define a separate section for this package heading.

## Plan Document Review
The source record did not define a separate section for this package heading.

## Implementation Review
The source record did not define a separate section for this package heading.
