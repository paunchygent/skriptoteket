---
type: reference
id: REF-curated-app-pinball-teacher-architecture-and-foundational-code
title: "Reference: Curated app - Pinball Teacher architecture and foundational code"
status: active
owners: "agents"
created: 2026-03-22
topic: "curated-apps"
links:
  - ADR-0022
  - ADR-0023
  - ADR-0024
  - ADR-0027
  - ADR-0036
---

## Purpose

This document is the architecture and implementation reference for the
**Pinball Teacher** curated app. It records the app's product shape, the
boundary between curated-app logic and platform services, and the foundational
code layout expected for a Skriptoteket curated app.

The reference is descriptive, not a change request. It exists to keep the app
easy to discover, easy to implement, and aligned with the platform contracts.

## Search terms

Use these canonical terms when searching the codebase or linking future docs:

- `Pinball Teacher`
- `curated app`
- `bespoke app UX`
- `tool sessions`
- `ui_payload`
- `Tool UI contract v2`
- `curated app registry`

## Product intent

- Teacher-first guidance for a pinball-themed learning activity.
- Curated app behavior, not a generic tool runner flow.
- Bespoke app UX with platform-owned persistence, auth, and routing.
- Deterministic outcomes with explicit validation and no hidden heuristics.

## Architectural position

Pinball Teacher should follow the standard curated-app seam:

- The SPA renders a dedicated app surface.
- The backend owns validation, state, and persistence.
- Curated-app logic stays behind protocols and small, testable modules.
- Shared platform concerns remain internal to Skriptoteket.

### Contract boundaries

- UI transport: Tool UI contract v2 / v2.x
- App registration: curated app registry
- Runtime state: tool sessions and ui_payload persistence
- Error handling: domain errors mapped to HTTP in the web layer

## Recommended code map

Use a small, modular layout with explicit responsibilities:

```text
src/skriptoteket/
  domain/
    curated_apps/
      pinball_teacher/
        models.py
        rules.py
        service.py
  application/
    curated_apps/
      pinball_teacher/
        execute_action.py
  infrastructure/
    curated_apps/
      pinball_teacher/
        registry_entry.py
        repository.py
        renderer_adapter.py
  web/
    api/v1/
      curated_apps/
        pinball_teacher.py
frontend/apps/skriptoteket/src/
  views/apps/
    PinballTeacherView.vue
  components/apps/pinball-teacher/
```

## Foundational code principles

### Domain

- Keep game rules and teacher-facing logic pure.
- Use `typing.Protocol` for seams that touch persistence, clocks, or external
  services.
- Prefer small value objects over loosely typed dicts when the shape is stable.

### Application

- Orchestrate a single action per use case.
- Let the application layer own transaction boundaries through the unit of work.
- Convert domain outcomes into curated-app UI payloads without leaking HTTP
  details.

### Infrastructure

- Implement the registry, persistence, and renderer adapters here.
- Keep DB-specific code out of the domain.
- Avoid service-locator style wiring; prefer Dishka-backed dependency injection
  where it reduces coupling.

### Web and SPA

- Keep web handlers thin.
- The SPA should render a bespoke Pinball Teacher experience instead of a
  generic app shell when the app is curated.
- Treat platform-provided forms and outputs as transport primitives, not UI
  design constraints.

## Suggested runtime flow

1. User opens the Pinball Teacher curated app.
2. The SPA requests the app boot payload.
3. The backend resolves the curated-app registry entry and current session state.
4. The app validates input and computes the next state deterministically.
5. The backend persists the result and returns the updated UI payload.
6. The SPA re-renders the bespoke app view from the returned contract data.

## Testing shape

- Unit tests for pure rules and validation.
- Protocol-mock tests for application orchestration.
- Integration tests for API-to-persistence boundaries.
- Live functional UI checks whenever the app view or route changes.

## Notes

- This reference does not define product fiction or gameplay details.
- If Pinball Teacher gains a dedicated ADR or epic, link it here and keep the
  implementation map current.

## Implementation Plan: Pinball Teacher

Vue 3 + Vite + TypeScript
PixiJS v8
Rapier 2D
Howler.js
FastAPI
PostgreSQL + Redis if you need user accounts, leaderboards, sessions, tournaments
Good alternative if you want faster framework-level onboarding
Vue for shell
Phaser for game
FastAPI backend

That is easier to get moving with, but slightly less elegant for a “physics-first custom pinball machine.”

What I would do first, in order
Build a single-table vertical slice.
Implement only:
one ball,
two flippers,
slingshots,
3 bumper types,
rollover lanes,
drain,
score + multiplier,
juicy audio/particles.
Tune that until it feels excellent.
Only then add missions, multiball, backend accounts, cosmetics, and tournaments.

This order matters. In pinball, feel first, systems second.

Final recommendation

If you want the best modern setup today, I would build it as:

Frontend: Vue 3 + Vite + TypeScript + PixiJS v8 + Rapier 2D + Howler
Backend: FastAPI + PostgreSQL + Redis
Testing: Vitest + Playwright

That is the stack I would trust for a browser pinball game that aims to feel premium rather than merely functional.

I’d structure it as one repo, two deployables, one shared contracts layer.
That shape fits your stack well: Vue has first-class TypeScript support, Vue recommends the Composition API for stronger TS inference, PixiJS v8 explicitly recommends a Vite-based setup, Rapier’s JS bindings are WebAssembly and load asynchronously, FastAPI supports WebSockets, Vitest is Vite-native, and Playwright is built for browser testing with automatic waiting. (Vue.js)
Repository shape
frontend/apps/skriptoteket/
├─ src/
│  ├─ views/apps/PinballTeacherView.vue
│  └─ components/apps/pinball-teacher/
│     ├─ GameHost.vue
│     ├─ gameBridge.ts
│     ├─ game/
│     │  ├─ bootstrap/createRuntime.ts
│     │  ├─ bootstrap/loadAssets.ts
│     │  ├─ core/GameRuntime.ts
│     │  ├─ core/FixedStepRunner.ts
│     │  ├─ core/CommandQueue.ts
│     │  ├─ physics/PhysicsWorld.ts
│     │  ├─ render/PixiRenderer.ts
│     │  ├─ audio/AudioDirector.ts
│     │  ├─ rules/RuleEngine.ts
│     │  ├─ table/TableDefinition.ts
│     │  ├─ replay/ReplayRecorder.ts
│     │  └─ debug/TuningPanel.ts
│     └─ content/tables/prototype-alpha/
│        ├─ manifest.ts
│        ├─ layout.json
│        ├─ physics.json
│        ├─ rules.ts
│        ├─ art/
│        └─ audio/
│  └─ tests/e2e/
src/skriptoteket/
├─ application/
│  └─ curated_apps/
│     └─ pinball_teacher.py
├─ domain/
│  └─ curated_apps/
│     └─ pinball_teacher/
├─ infrastructure/
│  └─ curated_apps/
│     └─ apps/
│        └─ pinball_teacher/
└─ web/
   └─ api/v1/
      └─ apps_pinball_teacher.py
The hard boundaries

1. app/ is the shell. game/ is the machine.
frontend/apps/skriptoteket/src/views/apps/PinballTeacherView.vue owns:

* router
- auth/session UI
- settings
- leaderboards
- profile pages
- the play page wrapper
frontend/apps/skriptoteket/src/components/apps/pinball-teacher/game/ owns:
- the simulation loop
- physics
- rendering
- audio
- scoring rules
- replay capture
Rule: Vue must never own the simulation state.
Weak:
- ball position in a Vue store
- flipper angle in a composable
- collision events handled by watchers
Strong:
- GameRuntime owns the machine
- Vue receives a read-only HUD projection such as score, balls left, multiplier, paused state
That boundary will save you months.

2. table/ is declarative. physics/ and render/ instantiate it.
Do not bury table geometry inside handwritten code.
Use:

* layout.json for visual layer placement, anchors, insert positions
- physics.json for colliders, sensors, materials, flipper pivots, bumper strengths
- rules.ts for table-specific rule logic
- manifest.ts for asset imports and bundle registration
This gives you a real engine/content split.

3. Share contracts, not code
Do not invent a fake cross-language “shared package” for Python and TypeScript.
Share:

* JSON Schema for table definitions
- JSON Schema for replay files
- OpenAPI output for the HTTP client
- event format docs
FastAPI’s OpenAPI output makes this especially practical for frontend client generation and API contract checks. (fastapi.tiangolo.com)
Frontend module boundaries
game/core/
This is the spine.
FixedStepRunner.ts
- fixed timestep update
- accumulator
- pause/resume
- slow-frame handling
GameRuntime.ts
- wires input, physics, rules, render, audio, replay
- exposes start(), stop(), mount(canvas), unmount()
CommandQueue.ts
- stores timestamped input commands per frame
Why this matters: pinball feel depends on deterministic stepping, not ad hoc animation timing.
game/input/
This layer converts browser input into commands, not direct state mutation.
Example commands:
- LEFT_FLIP_DOWN
- LEFT_FLIP_UP
- RIGHT_FLIP_DOWN
- RIGHT_FLIP_UP
- LAUNCH_PULL
- LAUNCH_RELEASE
- NUDGE_LEFT
The rule is simple: input produces commands; only the runtime mutates the machine.
game/physics/
This module owns Rapier completely.
It should expose:
- world creation
- rigid body creation
- collider creation
- stepping
- low-level contact/sensor events
- world queries
It should not know:
- score
- multiplier
- mission logic
- leaderboard rules
Also: do not leak Rapier handles across the whole codebase. Keep them inside PhysicsWorld and expose stable IDs or tags.
Because Rapier’s JS bindings are WASM-based and load asynchronously, keep physics startup behind a bootstrap layer rather than importing it casually from UI code. (Rapier)
game/render/
This module owns Pixi.
It reads:
- a render snapshot
- semantic game events
- table render definitions
It does not decide rules.
Good responsibility:
- sprites
- lights
- particle bursts
- screen shake
- score popups
- animation polish
Bad responsibility:
- “award 500 points”
- “advance multiplier”
- “drain the ball”
game/audio/
This module owns Howler.
It subscribes to semantic events such as:
- BUMPER_HIT
- SLINGSHOT_FIRED
- ROLLOVER_COMPLETED
- BALL_DRAINED
- MULTIPLIER_CHANGED
It should not inspect physics objects directly.
game/rules/
This is your game design layer.
It consumes:
- sensor entries/exits
- important contact events
- timed ticks
- input-derived actions that matter to rules
It produces:
- score changes
- multiplier changes
- ball lifecycle events
- audio/FX cues
- HUD updates
For the first vertical slice, I would keep it brutally small:
// conceptual shape
type PhysicsEvent =
  | { type: 'sensor-enter'; tag: string; ballId: string }
  | { type: 'contact'; tagA: string; tagB: string; impulse: number };

type GameEvent =
  | { type: 'score-awarded'; points: number; reason: string }
  | { type: 'multiplier-changed'; value: number }
  | { type: 'play-sfx'; cue: string }
  | { type: 'spawn-fx'; cue: string }
  | { type: 'ball-drained' };
That split is the key boundary:
- physics emits machine facts
- rules emit game meaning
game/replay/
Build this on day one.
Store:
- seed
- table version
- input stream by frame
- major state checkpoints if needed
Do not wait until “later.” Replays are how you debug pinball feel.
frontend/apps/skriptoteket/src/components/apps/pinball-teacher/gameBridge.ts
This file is more important than it looks.
Its job:
  - mount the runtime into `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/GameHost.vue`
- subscribe to runtime HUD events
- push score/multiplier/ball count into the shell store
- forward UI actions like pause, mute, restart
It is the seam between “app” and “machine.”
Table content structure
For one table, I’d use this exact pattern:
frontend/apps/skriptoteket/src/components/apps/pinball-teacher/content/tables/prototype-alpha/
├─ manifest.ts
├─ layout.json
├─ physics.json
├─ rules.ts
├─ art/
│  ├─ playfield.webp
│  ├─ lights.json
│  └─ atlas/
└─ audio/
   ├─ flipper-up.mp3
   ├─ flipper-down.mp3
   ├─ bumper-1.mp3
   └─ drain.mp3
manifest.ts should export the bundle entry:
- id
- display name
- asset imports
- schema version
- references to layout.json, physics.json, and rules.ts
Use string tags everywhere in the table data:
- bumper/pop-left
- bumper/pop-center
- lane/top-a
- drain/main
- sling/left
That is stronger than numeric IDs because rules remain readable.
Backend module boundaries
FastAPI belongs on the service side, not in the game loop. It is a good fit for HTTP APIs and WebSockets. (fastapi.tiangolo.com)
I would keep the backend layered like this:
api/routes/
Thin transport layer only.
- parse request
- auth/deps
- call service
- return response
domain/
Actual business rules.
- how scores become official
- replay ownership
- leaderboard scope
- tournament eligibility
repos/
Database access only.
- read/write models
- no scoring logic
services/
Cross-cutting workflows.
- replay validation
- anti-cheat heuristics
- leaderboard recompute
- session finalization
workers/
Background jobs.
- validate replay after submission
- recalculate daily/weekly leaderboards
- tournament rollups
Redis and Postgres responsibilities
Use Postgres as source of truth.Use Redis as transient speed.
Postgres:
- users
- tables
- score submissions
- official scores
- replay metadata
- tournaments
Redis:
- session cache
- top leaderboard cache
- rate limiting
- live scoreboard fan-out
Add Redis Streams only when you genuinely need append-only live event distribution to multiple consumers; Streams are designed for recording and syndicating real-time events and support consumer groups. (Redis)
Testing layout
Keep tests at the layer they verify.
frontend/apps/skriptoteket/src/components/apps/pinball-teacher/game/**/*.spec.ts
- score rules
- multiplier logic
- drain behavior
- replay serialization
- command queue behavior
frontend/apps/skriptoteket/tests/e2e/
- launch app
- start table
- flip left/right
- drain ball
- submit score
- open leaderboard
Vitest is the natural unit/integration test fit in a Vite app, and Playwright is the natural browser-flow fit because of its browser coverage and auto-wait behavior. (Vitest)

### What I would create first
In this order:

1. frontend/apps/skriptoteket/src/components/apps/pinball-teacher/GameHost.vue
2. GameRuntime.ts
3. FixedStepRunner.ts
4. PhysicsWorld.ts
5. PixiRenderer.ts
6. prototype-alpha/physics.json
7. prototype-alpha/layout.json
8. RuleEngine.ts
9. bumper / sling / rollover / drain rule files
10. AudioDirector.ts
11. ReplayRecorder.ts
12. gameBridge.ts
That sequence forces the right dependency graph.
### Three rules I would enforce strictly
13. Vue never owns live ball physics. Vue owns shell state only.
14. Pixi objects are never the source of truth. Render from state; do not store gameplay truth in sprites.
15. Physics events are not game rules. Translate machine events into semantic game events through the rule engine.
That is the architecture I would actually build.

## File-by-file vertical-slice starter plan

Good. For the first implementation pass, keep the slice aggressively small: one table, one active ball, keyboard input only, no backend calls from the runtime, and no ECS. In the Vue shell, use <script setup> with Composition API and TypeScript. Load the table JSON, textures, and audio before constructing the runtime with Pixi’s promise-based asset loader. Initialize Rapier in an async factory because its JS binding is WebAssembly-based, and let PhysicsWorld normalize Rapier events into your own tagged machine events because Rapier’s event queue reports collider handles, not game semantics. (Vue.js)
The data flow should be this:
input commands
  -> GameRuntime
  -> PhysicsWorld.step()
  -> machine events
  -> RuleEngine.step()
  -> game events + physics requests + HUD
  -> GameRuntime fans out to PhysicsWorld / Renderer / Audio / HUD
The important boundary is simple:
- PhysicsWorld knows what physically happened.
- RuleEngine knows what it means for score and progression.
- prototype-alpha/rules.ts knows the specific table rules.
- GameRuntime only wires the machine together.
GameRuntime.ts
This file is the orchestrator. It should contain zero table rules and zero Rapier details.
Put these things in it now:
- the RuntimeCommand union
- the GameRuntime class
- the fixed-step tick
- HUD subscription methods
- the glue code that applies rule outputs
Do not put score logic, bumper values, tag names, or direct Rapier code here.
A first-pass shape:
import { FixedStepRunner } from './FixedStepRunner'
import { CommandQueue } from './CommandQueue'
import type { PhysicsWorld, PhysicsCommand, PhysicsSnapshot } from '../physics/PhysicsWorld'
import type {
  RuleEngine,
  RuleStepOutput,
  GameEvent,
  HudSnapshot,
  PhysicsRequest,
} from '../rules/RuleEngine'
import type { PixiRenderer } from '../render/PixiRenderer'
import type { AudioDirector } from '../audio/AudioDirector'

export type RuntimeCommand =
  | { type: 'start-game' }
  | { type: 'pause' }
  | { type: 'resume' }
  | { type: 'restart' }
  | { type: 'left-flip'; pressed: boolean }
  | { type: 'right-flip'; pressed: boolean }
  | { type: 'launch'; pressed: boolean }

type RuntimeStatus = 'idle' | 'running' | 'paused' | 'gameover'

export class GameRuntime {
  private readonly runner: FixedStepRunner
  private readonly commands = new CommandQueue<RuntimeCommand>()
  private readonly hudListeners = new Set<(hud: HudSnapshot) => void>()
  private status: RuntimeStatus = 'idle'
  private frame = 0

  constructor(
    private readonly physics: PhysicsWorld,
    private readonly rules: RuleEngine,
    private readonly renderer: PixiRenderer,
    private readonly audio: AudioDirector,
    hz = 120,
  ) {
    this.runner = new FixedStepRunner(1000 / hz, this.tick)
  }

  mount(canvas: HTMLCanvasElement): void {
    this.renderer.attach(canvas)
  }

  startNewGame(): void {
    this.physics.reset()
    this.renderer.reset()
    this.audio.reset()

    const init = this.rules.startNewGame()
    this.applyRuleOutput(init)

    this.status = 'running'
    this.frame = 0
    this.runner.start()

    this.renderer.render(this.physics.getSnapshot(), init.gameEvents)
    this.publishHud(init.hud)
  }

  enqueue(command: RuntimeCommand): void {
    this.commands.push(command)
  }

  pause(): void {
    if (this.status !== 'running') return
    this.status = 'paused'
    this.runner.stop()
  }

  resume(): void {
    if (this.status !== 'paused') return
    this.status = 'running'
    this.runner.start()
  }

  dispose(): void {
    this.runner.stop()
    this.renderer.dispose()
    this.audio.dispose()
    this.physics.dispose()
  }

  subscribeHud(listener: (hud: HudSnapshot) => void): () => void {
    this.hudListeners.add(listener)
    listener(this.rules.getHud())
    return () => this.hudListeners.delete(listener)
  }

  private tick = (dtMs: number): void => {
    if (this.status !== 'running') return

    const pending = this.commands.drain()

    for (const command of pending) {
      if (command.type === 'pause') this.pause()
      else if (command.type === 'resume') this.resume()
      else if (command.type === 'restart') this.startNewGame()
      else if (command.type !== 'start-game') {
        this.physics.applyCommand(command as PhysicsCommand)
      }
    }

    const machineEvents = this.physics.step(dtMs / 1000)
    const output = this.rules.step({
      frame: this.frame++,
      dtMs,
      machineEvents,
    })

    this.applyRuleOutput(output)

    const snapshot = this.physics.getSnapshot()
    this.audio.consume(output.gameEvents)
    this.renderer.render(snapshot, output.gameEvents)
    this.publishHud(output.hud)

    if (output.hud.status === 'gameover') {
      this.status = 'gameover'
      this.runner.stop()
    }
  }

  private applyRuleOutput(output: RuleStepOutput): void {
    for (const req of output.physicsRequests) {
      if (req.type === 'spawn-ball') this.physics.spawnBall()
      if (req.type === 'remove-ball') this.physics.removeBall()
    }
  }

  private publishHud(hud: HudSnapshot): void {
    for (const listener of this.hudListeners) listener(hud)
  }
}
What this file should do in pass one:
- translate shell commands into runtime actions
- step physics at fixed rate
- hand machine events to rules
- apply rule-driven physics requests
- push semantic game events to audio and renderer
- publish HUD snapshots
What it should not do yet:
- replay recording
- network calls
- tournament/session logic
- nudge/tilt
- multiball orchestration
- async asset loading
Keep async loading outside this file.
PhysicsWorld.ts
This file owns Rapier completely. No other file should touch Rapier handles or collider metadata. Rapier can emit collision/contact/sensor events through an EventQueue, and those events identify colliders by handle. That is why this file must own the handle-to-tag map and convert raw events into your own MachineEvent union. (Rapier)
Put these things in it now:
- PhysicsCommand
- MachineEvent
- PhysicsSnapshot
- PhysicsWorld class
- handle/tag registries
- flipper actuator state
- ball spawn/remove/reset logic
- bumper and slingshot impulse helpers
- cooldown handling
Do not put points, multipliers, audio cue names, or HUD logic here.
A first-pass shape:
import type { TablePhysicsDefinition } from '../table/TableDefinition'

export type PhysicsCommand =
  | { type: 'left-flip'; pressed: boolean }
  | { type: 'right-flip'; pressed: boolean }
  | { type: 'launch'; pressed: boolean }

export type MachineEvent =
  | { type: 'bumper-fired'; tag: string }
  | { type: 'sling-fired'; tag: string; side: 'left' | 'right' }
  | { type: 'rollover-enter'; tag: string }
  | { type: 'drain-enter'; tag: string }

export interface PhysicsSnapshot {
  ball: null | {
    x: number
    y: number
    angle: number
    vx: number
    vy: number
  }
  flippers: {
    left: { x: number; y: number; angle: number }
    right: { x: number; y: number; angle: number }
  }
}

type ColliderKind =
  | 'wall'
  | 'ball'
  | 'bumper'
  | 'sling'
  | 'rollover'
  | 'drain'
  | 'flipper'

type ColliderMeta = {
  tag: string
  kind: ColliderKind
  side?: 'left' | 'right'
  impulse?: number
  cooldownMs?: number
}

export class PhysicsWorld {
  private colliderMetaByHandle = new Map<number, ColliderMeta>()
  private cooldowns = new Map<string, number>()

  private leftPressed = false
  private rightPressed = false
  private launchPressed = false
  private launchChargeMs = 0

  private ballPresent = false
  private ballState: 'absent' | 'in-play' | 'draining' = 'absent'

  static async create(def: TablePhysicsDefinition): Promise<PhysicsWorld> {
    // await Rapier init here or receive initialized Rapier module from bootstrap
    // build static bodies, flippers, colliders, sensors, registries
    return new PhysicsWorld(def)
  }

  private constructor(private readonly def: TablePhysicsDefinition) {
    // create world, event queue, static table, flippers, launch lane
  }

  reset(): void {
    this.clearDynamicState()
    this.leftPressed = false
    this.rightPressed = false
    this.launchPressed = false
    this.launchChargeMs = 0
    this.cooldowns.clear()
  }

  dispose(): void {
    // free world/resources if needed
  }

  applyCommand(command: PhysicsCommand): void {
    if (command.type === 'left-flip') this.leftPressed = command.pressed
    if (command.type === 'right-flip') this.rightPressed = command.pressed
    if (command.type === 'launch') this.launchPressed = command.pressed
  }

  spawnBall(): void {
    // remove any old ball
    // create new dynamic ball at launch position
    // set ballPresent / ballState
  }

  removeBall(): void {
    // destroy active ball if present
    this.ballPresent = false
    this.ballState = 'absent'
  }

  step(dtSec: number): MachineEvent[] {
    this.tickCooldowns(dtSec)
    this.applyFlipperActuators(dtSec)
    this.applyLauncher(dtSec)

    // world.step(eventQueue)

    const events: MachineEvent[] = []

    // drain queue:
    // - find ball vs sensor/trigger pairs
    // - map handles -> ColliderMeta
    // - emit normalized MachineEvents
    // - for bumpers/slings: apply impulses immediately
    // - for drain: set ballState = 'draining' so it cannot double-fire

    return events
  }

  getSnapshot(): PhysicsSnapshot {
    return {
      ball: this.ballPresent ? this.readBallSnapshot() : null,
      flippers: {
        left: this.readFlipperSnapshot('left'),
        right: this.readFlipperSnapshot('right'),
      },
    }
  }

  private applyFlipperActuators(dtSec: number): void {
    // first pass: kinematic flippers driven toward target angles
    // left/right each have restAngle, upAngle, angularSpeed
  }

  private applyLauncher(dtSec: number): void {
    // while launchPressed: charge up to max
    // on release: apply impulse to active ball in launch lane
  }

  private fireBumper(meta: ColliderMeta): MachineEvent | null {
    if (this.isCoolingDown(meta.tag)) return null
    this.setCooldown(meta.tag, meta.cooldownMs ?? 80)
    // apply impulse away from bumper center
    return { type: 'bumper-fired', tag: meta.tag }
  }

  private fireSling(meta: ColliderMeta): MachineEvent | null {
    if (this.isCoolingDown(meta.tag)) return null
    this.setCooldown(meta.tag, meta.cooldownMs ?? 120)
    // apply sling impulse
    return {
      type: 'sling-fired',
      tag: meta.tag,
      side: meta.side ?? 'left',
    }
  }

  private clearDynamicState(): void {}
  private tickCooldowns(dtSec: number): void {}
  private isCoolingDown(tag: string): boolean { return false }
  private setCooldown(tag: string, ms: number): void {}
  private readBallSnapshot(): PhysicsSnapshot['ball'] { return null }
  private readFlipperSnapshot(side: 'left' | 'right') {
    return { x: 0, y: 0, angle: 0 }
  }
}
First-pass implementation choices I would make here:
- Use static colliders for walls and guides.
- Use kinematic flippers first. Later, if you want subtler transfer, upgrade to motorized revolute joints.
- For bumpers and slingshots, use solid geometry plus an inner sensor trigger. The solid collider gives contact shape; the sensor adds the authored kick.
- Use sensor-enter only for rollovers and drain.
- Add per-tag cooldowns for bumpers and slings so one overlap does not machine-gun score.
Important constraint: this file should emit stable tags like bumper/pop-left or lane/top-a, never raw handles.
Keep this file strict. Weak vs. strong:
- Weak: PhysicsWorld awards 100 points for a bumper.
- Strong: PhysicsWorld emits { type: 'bumper-fired', tag: 'bumper/pop-left' }.
RuleEngine.ts
This file is the semantic layer. It receives machine events and turns them into score, multiplier, lamp, ball-lifecycle, audio, and FX outputs.
Put these things in it now:
- HudSnapshot
- GameEvent
- PhysicsRequest
- RuleContext
- TableScript
- TableScriptFactory
- RuleEngine
Do not put Rapier handles, Pixi objects, or Howler instances here.
A first-pass shape:
import type { MachineEvent } from '../physics/PhysicsWorld'

export interface HudSnapshot {
  score: number
  multiplier: number
  ballsRemaining: number
  status: 'idle' | 'running' | 'paused' | 'gameover'
}

export type GameEvent =
  | { type: 'score-awarded'; delta: number; total: number; reason: string }
  | { type: 'multiplier-changed'; value: number }
  | { type: 'lamp-changed'; tag: string; lit: boolean }
  | { type: 'play-sfx'; cue: string }
  | { type: 'spawn-fx'; cue: string; tag?: string }
  | { type: 'ball-drained'; ballsRemaining: number }
  | { type: 'ball-spawned'; ballsRemaining: number }
  | { type: 'game-over'; finalScore: number }

export type PhysicsRequest =
  | { type: 'spawn-ball' }
  | { type: 'remove-ball' }

export interface RuleStepInput {
  frame: number
  dtMs: number
  machineEvents: MachineEvent[]
}

export interface RuleStepOutput {
  gameEvents: GameEvent[]
  physicsRequests: PhysicsRequest[]
  hud: HudSnapshot
}

type EngineState = {
  score: number
  multiplier: number
  ballsRemaining: number
  status: 'idle' | 'running' | 'paused' | 'gameover'
}

export interface RuleContext {
  readonly state: Readonly<EngineState>

  award(points: number, reason: string, opts?: { multiplied?: boolean }): void
  setMultiplier(value: number): void
  incrementMultiplier(step?: number, max?: number): void

  setLamp(tag: string, lit: boolean): void
  playSfx(cue: string): void
  spawnFx(cue: string, tag?: string): void

  drainBall(): void
  requestBallSpawn(): void
}

export interface TableScript {
  onGameStart?(ctx: RuleContext): void
  onBallStart?(ctx: RuleContext): void
  onMachineEvent?(event: MachineEvent, ctx: RuleContext): void
  onTick?(dtMs: number, ctx: RuleContext): void
}

export type TableScriptFactory = () => TableScript

export class RuleEngine {
  private state: EngineState = {
    score: 0,
    multiplier: 1,
    ballsRemaining: 0,
    status: 'idle',
  }

  private script: TableScript
  private gameEvents: GameEvent[] = []
  private physicsRequests: PhysicsRequest[] = []

  constructor(
    private readonly createScript: TableScriptFactory,
    private readonly ballsPerGame = 3,
  ) {
    this.script = createScript()
  }

  startNewGame(): RuleStepOutput {
    this.script = this.createScript()
    this.state = {
      score: 0,
      multiplier: 1,
      ballsRemaining: this.ballsPerGame,
      status: 'running',
    }

    this.beginStep()

    const ctx = this.createContext()
    this.script.onGameStart?.(ctx)
    this.requestBallSpawnInternal()

    return this.endStep()
  }

  step(input: RuleStepInput): RuleStepOutput {
    if (this.state.status !== 'running') return this.emptyOutput()

    this.beginStep()

    const ctx = this.createContext()

    for (const event of input.machineEvents) {
      this.script.onMachineEvent?.(event, ctx)
    }

    this.script.onTick?.(input.dtMs, ctx)

    return this.endStep()
  }

  getHud(): HudSnapshot {
    return {
      score: this.state.score,
      multiplier: this.state.multiplier,
      ballsRemaining: this.state.ballsRemaining,
      status: this.state.status,
    }
  }

  private beginStep(): void {
    this.gameEvents = []
    this.physicsRequests = []
  }

  private endStep(): RuleStepOutput {
    return {
      gameEvents: [...this.gameEvents],
      physicsRequests: [...this.physicsRequests],
      hud: this.getHud(),
    }
  }

  private emptyOutput(): RuleStepOutput {
    return {
      gameEvents: [],
      physicsRequests: [],
      hud: this.getHud(),
    }
  }

  private createContext(): RuleContext {
    return {
      state: this.state,

      award: (points, reason, opts) => {
        const multiplied = opts?.multiplied ?? true
        const delta = multiplied ? points * this.state.multiplier : points
        this.state.score += delta
        this.gameEvents.push({
          type: 'score-awarded',
          delta,
          total: this.state.score,
          reason,
        })
      },

      setMultiplier: (value) => {
        const next = Math.max(1, value)
        if (next === this.state.multiplier) return
        this.state.multiplier = next
        this.gameEvents.push({ type: 'multiplier-changed', value: next })
      },

      incrementMultiplier: (step = 1, max = 5) => {
        const next = Math.min(max, this.state.multiplier + step)
        if (next === this.state.multiplier) return
        this.state.multiplier = next
        this.gameEvents.push({ type: 'multiplier-changed', value: next })
      },

      setLamp: (tag, lit) => {
        this.gameEvents.push({ type: 'lamp-changed', tag, lit })
      },

      playSfx: (cue) => {
        this.gameEvents.push({ type: 'play-sfx', cue })
      },

      spawnFx: (cue, tag) => {
        this.gameEvents.push({ type: 'spawn-fx', cue, tag })
      },

      drainBall: () => {
        this.state.ballsRemaining -= 1
        this.gameEvents.push({
          type: 'ball-drained',
          ballsRemaining: this.state.ballsRemaining,
        })

        if (this.state.ballsRemaining > 0) {
          this.requestBallSpawnInternal()
        } else {
          this.state.status = 'gameover'
          this.physicsRequests.push({ type: 'remove-ball' })
          this.gameEvents.push({
            type: 'game-over',
            finalScore: this.state.score,
          })
        }
      },

      requestBallSpawn: () => {
        this.requestBallSpawnInternal()
      },
    }
  }

  private requestBallSpawnInternal(): void {
    this.physicsRequests.push({ type: 'spawn-ball' })
    this.gameEvents.push({
      type: 'ball-spawned',
      ballsRemaining: this.state.ballsRemaining,
    })
    const ctx = this.createContext()
    this.script.onBallStart?.(ctx)
  }
}
Why this structure is strong:
- RuleEngine owns universal game state.
- the table script owns local table logic
- all mutations go through RuleContext
- restart creates a fresh script instance, so no stale lane state leaks across games
That last point matters. Export a factory from prototype-alpha/rules.ts, not a singleton object.
frontend/apps/skriptoteket/src/components/apps/pinball-teacher/content/tables/prototype-alpha/rules.ts
This file should be small, specific, and opinionated. It should import only the rule types. It should not import Rapier, Pixi, or Howler.
Its job is simple:
- define point values
- define which rollover tags form the lane bank
- react to machine events
- use ctx helpers to change score, multiplier, lamps, and ball state
A first-pass shape:
import type { TableScript, RuleContext } from '../../../game/rules/RuleEngine'
import type { MachineEvent } from '../../../game/physics/PhysicsWorld'

const ROLLOVERS = [
  'lane/top-a',
  'lane/top-b',
  'lane/top-c',
] as const

const POINTS = {
  sling: 10,
  rollover: 50,
  bumperPop: 100,
  bumperRing: 250,
  bumperSuper: 500,
  laneCompleteBonus: 1000,
} as const

export function createPrototypeAlphaRules(): TableScript {
  const litRollovers = new Set<string>()

  const clearRollovers = (ctx: RuleContext) => {
    litRollovers.clear()
    for (const tag of ROLLOVERS) ctx.setLamp(tag, false)
  }

  const allRolloversLit = () =>
    ROLLOVERS.every((tag) => litRollovers.has(tag))

  return {
    onGameStart(ctx) {
      ctx.setMultiplier(1)
      clearRollovers(ctx)
    },

    onBallStart(ctx) {
      clearRollovers(ctx)
      ctx.playSfx('ball-ready')
    },

    onMachineEvent(event: MachineEvent, ctx: RuleContext) {
      switch (event.type) {
        case 'bumper-fired': {
          if (event.tag.startsWith('bumper/pop')) {
            ctx.award(POINTS.bumperPop, 'pop bumper')
            ctx.playSfx('bumper-pop')
            ctx.spawnFx('bumper-pop', event.tag)
            return
          }

          if (event.tag.startsWith('bumper/ring')) {
            ctx.award(POINTS.bumperRing, 'ring bumper')
            ctx.playSfx('bumper-ring')
            ctx.spawnFx('bumper-ring', event.tag)
            return
          }

          if (event.tag.startsWith('bumper/super')) {
            ctx.award(POINTS.bumperSuper, 'super bumper')
            ctx.playSfx('bumper-super')
            ctx.spawnFx('bumper-super', event.tag)
            return
          }

          return
        }

        case 'sling-fired': {
          ctx.award(POINTS.sling, 'slingshot')
          ctx.playSfx(event.side === 'left' ? 'sling-left' : 'sling-right')
          ctx.spawnFx('sling', event.tag)
          return
        }

        case 'rollover-enter': {
          if (litRollovers.has(event.tag)) return

          litRollovers.add(event.tag)
          ctx.setLamp(event.tag, true)
          ctx.award(POINTS.rollover, 'rollover')
          ctx.playSfx('rollover')

          if (allRolloversLit()) {
            ctx.incrementMultiplier(1, 5)
            ctx.award(POINTS.laneCompleteBonus, 'lane bank complete', {
              multiplied: false,
            })
            ctx.playSfx('multiplier-up')
            ctx.spawnFx('lane-complete')
            clearRollovers(ctx)
          }

          return
        }

        case 'drain-enter': {
          ctx.playSfx('drain')
          ctx.spawnFx('drain')
          ctx.drainBall()
          return
        }
      }
    },
  }
}
That file should stay brutally table-specific. Good examples:
- lane/top-a
- bumper/pop-left
- bumper/super-center
- drain/main
Bad examples:
- generic if event.kind === 'target'
- dynamic score lookup via a huge config object on day one
- importing the renderer to flash a light directly
Weak vs. strong:
- Weak: table script mutates sprites or bodies.
- Strong: table script emits meaning through ctx.
What to leave out of pass one
Be strict here.
Leave these out:
- nudge / tilt
- save/load
- live backend session
- replay persistence
- multiball
- missions
- combo timers
- dynamic table loading
- editor features
- analytics
- generic content DSL for everything
Build the narrow slice first.
The exact contract between the four files
This is the part to protect.
PhysicsWorld.ts exports:
- PhysicsCommand
- MachineEvent
- PhysicsSnapshot
- PhysicsWorld
RuleEngine.ts exports:
- GameEvent
- PhysicsRequest
- HudSnapshot
- RuleContext
- TableScript
- TableScriptFactory
- RuleEngine
prototype-alpha/rules.ts exports:
- createPrototypeAlphaRules(): TableScript
GameRuntime.ts imports both systems and wires them.
Nothing else should cross that boundary.
### The first tests I would write
Before adding more gameplay, write these:

1. Starting a new game sets score=0, multiplier=1, ballsRemaining=3, and requests one ball spawn.
2. A bumper-fired machine event awards the correct multiplied score.
3. A rollover only scores once until the lane bank is cleared.
4. Completing all three rollovers increments multiplier and clears the lamps.
5. A drain decrements balls and requests a new spawn when balls remain.
6. The final drain emits game-over and requests remove-ball.
7. PhysicsWorld fires one bumper event per cooldown window, not every frame of overlap.
8. Restarting the game clears prototype-alpha local rollover state.

That gives you a real vertical slice, not just a pile of files.

## Runtime bootstrap and `createRuntime.ts`

This bootstrap split matches Rapier’s async initialization model and Pixi’s promise-based asset loading. (Rapier):

Change one detail first: make the runtime mount into a host element, not a pre-existing <canvas>. In Pixi v8, the Application is created and then asynchronously initialized with await app.init(...), and the canvas you append is app.canvas. Vue’s onMounted() / onUnmounted() lifecycle hooks are the correct seam for that DOM-bound setup and teardown. (PixiJS)
For the first vertical slice, centralize all async bootstrapping in createRuntime.ts. Do not import Rapier inside PhysicsWorld; load it once in bootstrap and pass the loaded module in. With the NPM package, Rapier’s JS/WASM binding is loaded asynchronously via dynamic import. For Pixi, initialize the Application first, then register and load the table bundle. Pixi documents runtime bundle registration with Assets.addBundle() and bundle loading with Assets.loadBundle(), and it also documents that repeated loads are safe because the Assets singleton caches by URL or alias. (Rapier)
Make AudioDirector.create() async as well. Howler preloads by default, exposes load / loaderror events, and supports sound sprites, so wrapping those events in a Promise gives bootstrap a clean “audio bank is ready” signal. (GitHub)
createRuntime.ts
// frontend/apps/skriptoteket/src/components/apps/pinball-teacher/game/bootstrap/createRuntime.ts
import { Application, Assets, type ApplicationOptions } from 'pixi.js'

import { GameRuntime } from '../core/GameRuntime'
import { PhysicsWorld } from '../physics/PhysicsWorld'
import { RuleEngine } from '../rules/RuleEngine'
import { PixiRenderer } from '../render/PixiRenderer'
import { AudioDirector } from '../audio/AudioDirector'

import {
  PROTOTYPE_ALPHA_BUNDLE,
  prototypeAlphaPixiAssets,
  prototypeAlphaLayout,
  prototypeAlphaPhysics,
  prototypeAlphaAudioBank,
} from '../../content/tables/prototype-alpha/manifest'
import { createPrototypeAlphaRules } from '../../content/tables/prototype-alpha/rules'

type RapierModule = typeof import('@dimforge/rapier2d')

export interface CreateRuntimeOptions {
  hz?: number
  signal?: AbortSignal
  pixi?: Partial<ApplicationOptions>
}

const registeredBundles = new Set<string>()
let prototypeAlphaBundlePromise: Promise<Record<string, unknown>> | null = null
let rapierPromise: Promise<RapierModule> | null = null

export async function createRuntime(
  options: CreateRuntimeOptions = {},
): Promise<GameRuntime> {
  const {
    hz = 120,
    signal,
    pixi,
  } = options

  let app: Application | null = null
  let renderer: PixiRenderer | null = null
  let physics: PhysicsWorld | null = null
  let audio: AudioDirector | null = null

  try {
    assertNotAborted(signal)

    // Start Rapier loading immediately. It is async/WASM-backed.
    const rapierLoad = loadRapier()

    // Pixi v8 application init is also async.
    app = new Application()
    await app.init({
      antialias: true,
      autoDensity: true,
      backgroundAlpha: 0,
      preference: 'webgl',
      powerPreference: 'high-performance',
      resolution: getResolution(),
      ...pixi,
    })
    assertNotAborted(signal)

    // Register + load the table's Pixi bundle after app init.
    const pixiAssets = await loadPrototypeAlphaBundle()
    assertNotAborted(signal)

    renderer = await PixiRenderer.create({
      app,
      layout: prototypeAlphaLayout,
      assets: pixiAssets,
    })
    assertNotAborted(signal)

    const RAPIER = await rapierLoad
    physics = await PhysicsWorld.create({
      RAPIER,
      def: prototypeAlphaPhysics,
    })
    assertNotAborted(signal)

    const rules = new RuleEngine(createPrototypeAlphaRules, 3)

    audio = await AudioDirector.create({
      bank: prototypeAlphaAudioBank,
    })
    assertNotAborted(signal)

    return new GameRuntime(physics, rules, renderer, audio, hz)
  } catch (error) {
    audio?.dispose()
    renderer?.dispose()
    physics?.dispose()

    // If renderer never took ownership of the Pixi Application, destroy it here.
    if (!renderer) {
      app?.destroy()
    }

    throw error
  }
}

function loadRapier(): Promise<RapierModule> {
  rapierPromise ??= import('@dimforge/rapier2d')
  return rapierPromise
}

function loadPrototypeAlphaBundle(): Promise<Record<string, unknown>> {
  if (!registeredBundles.has(PROTOTYPE_ALPHA_BUNDLE)) {
    Assets.addBundle(PROTOTYPE_ALPHA_BUNDLE, prototypeAlphaPixiAssets)
    registeredBundles.add(PROTOTYPE_ALPHA_BUNDLE)
  }

  prototypeAlphaBundlePromise ??=
    Assets.loadBundle(PROTOTYPE_ALPHA_BUNDLE) as Promise<Record<string, unknown>>

  return prototypeAlphaBundlePromise
}

function getResolution(): number {
  if (typeof window === 'undefined') return 1
  return Math.min(window.devicePixelRatio || 1, 2)
}

function assertNotAborted(signal?: AbortSignal): void {
  if (!signal?.aborted) return
  throw new DOMException('Runtime bootstrap aborted', 'AbortError')
}
Expected manifest.ts shape
Keep the first pass literal and table-specific. Do not abstract too early.
// frontend/apps/skriptoteket/src/components/apps/pinball-teacher/content/tables/prototype-alpha/manifest.ts
import layout from './layout.json'
import physics from './physics.json'

export const PROTOTYPE_ALPHA_BUNDLE = 'prototype-alpha'

export const prototypeAlphaPixiAssets = [
  {
    alias: 'playfield',
    src: new URL('./art/playfield.webp', import.meta.url).href,
  },
  {
    alias: 'table-atlas',
    src: new URL('./art/atlas/table-atlas.json', import.meta.url).href,
  },
  {
    alias: 'lights',
    src: new URL('./art/lights.json', import.meta.url).href,
  },
] as const

export const prototypeAlphaLayout = layout
export const prototypeAlphaPhysics = physics

export const prototypeAlphaAudioBank = {
  masterVolume: 0.9,
  sprites: {
    sfx: {
      src: [new URL('./audio/sfx-sprite.mp3', import.meta.url).href],
      sprite: {
        'ball-ready': [0, 600],
        'bumper-pop': [1000, 250],
        'bumper-ring': [2000, 300],
        'bumper-super': [3000, 400],
        'sling-left': [4500, 180],
        'sling-right': [5000, 180],
        'rollover': [5500, 120],
        'multiplier-up': [6000, 500],
        'drain': [7000, 900],
      },
    },
  },
} as const
This is deliberately narrow. One table. One bundle. One audio bank.
frontend/apps/skriptoteket/src/components/apps/pinball-teacher/GameHost.vue
This is the clean handoff point: `createRuntime()` constructs the runtime, and
`frontend/apps/skriptoteket/src/components/apps/pinball-teacher/GameHost.vue`
mounts, starts, subscribes, and disposes.
<script setup lang="ts">
import { onMounted, onUnmounted, ref, shallowRef } from 'vue'

import { createRuntime } from '@/components/apps/pinball-teacher/game/bootstrap/createRuntime'
import type { GameRuntime } from '@/components/apps/pinball-teacher/game/core/GameRuntime'

const hostEl = ref<HTMLDivElement | null>(null)
const runtime = shallowRef<GameRuntime | null>(null)

const loading = ref(true)
const error = ref<string | null>(null)

let controller: AbortController | null = null
let unsubscribeHud: (() => void) | null = null

onMounted(async () => {
  if (!hostEl.value) return

  controller = new AbortController()

  try {
    const created = await createRuntime({
      signal: controller.signal,
    })

    if (controller.signal.aborted) {
      created.dispose()
      return
    }

    runtime.value = created
    created.mount(hostEl.value)

    unsubscribeHud = created.subscribeHud((hud) => {
      // Replace with your store or emit bridge.
      console.log('HUD update:', hud)
    })

    created.startNewGame()
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') return

    error.value =
      cause instanceof Error
        ? cause.message
        : 'Failed to create game runtime.'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  controller?.abort()
  unsubscribeHud?.()
  runtime.value?.dispose()
  runtime.value = null
})
</script>

<template>
  <section class="game-host">
    <div ref="hostEl" class="game-canvas-host" />

    <div v-if="loading" class="game-overlay">
      Loading table…
    </div>

    <div v-else-if="error" class="game-overlay game-overlay--error">
      {{ error }}
    </div>
  </section>
</template>

<style scoped>
.game-host {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.game-canvas-host {
  width: 100%;
  height: 100%;
}

.game-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
}
</style>
Vue’s lifecycle API is exactly what you want here: create on mount, destroy on unmount, and keep the async bootstrap outside the template layer. (Vue.js)
Two small interface adjustments
Do these now.
GameRuntime.ts
mount(host: HTMLElement): void {
  this.renderer.attach(host)
}
PhysicsWorld.ts
static async create(args: {
  RAPIER: typeof import('@dimforge/rapier2d')
  def: TablePhysicsDefinition
}): Promise<PhysicsWorld> {
  return new PhysicsWorld(args.RAPIER, args.def)
}
AudioDirector.ts
static async create(args: {
  bank: AudioBankDefinition
}): Promise<AudioDirector> {
  const director = new AudioDirector(args.bank)
  await director.ready()
  return director
}
That last method is the right place to wrap Howler’s load / loaderror event model. Howler preloads by default, lets you listen once for load, and supports sprite definitions in milliseconds, which fits a pinball SFX bank cleanly. (GitHub)
One strategic note
For this slice, use Assets.addBundle() in bootstrap exactly as shown. It is simpler and valid. When you add a second table, move bundle registration to a global app-level manifest with Assets.init({ manifest }), because Pixi explicitly recommends manifests and bundles for larger projects. (PixiJS)
Now; here are PixiRenderer.attach(host) and AudioDirector.ready(), because those are the two seams that make this bootstrap compile and actually run.
Use attach(host) to make the renderer own Pixi’s canvas and resize target. Use ready() to mean only one thing: all Howler assets are loaded. Do not let it mean “browser audio is unlocked,” because that is a separate browser-policy problem. In Pixi v8, Application is created first, then asynchronously initialized with await app.init(...), and the DOM canvas is app.canvas; the built-in resize plugin exposes resizeTo and resize(), and its docs explicitly show changing resizeTo at runtime to a specific element. Howler preloads by default, exposes state(), once('load'), and loaderror, but its own docs also note that some browsers gate playback until a user interaction. Vue’s onMounted / onUnmounted hooks are the right seam for mounting and tearing down DOM-bound runtime code. (PixiJS)
PixiRenderer.ts
Drop this in as a minimal first-pass renderer. It gives you a real attach(host) seam, scales the table into the host, and renders a fallback vector playfield if your textured art is not ready yet.
// frontend/apps/skriptoteket/src/components/apps/pinball-teacher/game/render/PixiRenderer.ts
import {
  Application,
  Container,
  Graphics,
  Sprite,
  Texture,
} from 'pixi.js'

import type { PhysicsSnapshot } from '../physics/PhysicsWorld'
import type { GameEvent } from '../rules/RuleEngine'

type AssetRecord = Record<string, unknown>

export interface FlipperLayout {
  pivot: { x: number; y: number }
  length: number
  thickness: number
  restAngleDeg: number
  color?: number
}

export interface TableLayoutDefinition {
  table: {
    width: number
    height: number
    background?: number
  }
  playfield?: {
    alias: string
  }
  ball: {
    radius: number
    color?: number
  }
  flippers: {
    left: FlipperLayout
    right: FlipperLayout
  }
}

export interface PixiRendererCreateArgs {
  app: Application
  layout: TableLayoutDefinition
  assets: AssetRecord
}

export class PixiRenderer {
  private host: HTMLElement | null = null

  private readonly root = new Container()
  private readonly playfieldLayer = new Container()
  private readonly actorLayer = new Container()
  private readonly fxLayer = new Container()

  private readonly ballGraphic: Graphics
  private readonly leftFlipperGraphic: Graphics
  private readonly rightFlipperGraphic: Graphics

  private readonly playfieldSprite: Sprite | null

  static async create(args: PixiRendererCreateArgs): Promise<PixiRenderer> {
    return new PixiRenderer(args.app, args.layout, args.assets)
  }

  private constructor(
    private readonly app: Application,
    private readonly layout: TableLayoutDefinition,
    private readonly assets: AssetRecord,
  ) {
    this.root.addChild(this.playfieldLayer, this.actorLayer, this.fxLayer)
    this.app.stage.addChild(this.root)

    this.playfieldSprite = this.buildPlayfieldSprite()

    if (this.playfieldSprite) {
      this.playfieldLayer.addChild(this.playfieldSprite)
    } else {
      this.playfieldLayer.addChild(this.buildFallbackPlayfield())
    }

    this.leftFlipperGraphic = this.buildFlipper(this.layout.flippers.left)
    this.rightFlipperGraphic = this.buildFlipper(this.layout.flippers.right)

    this.ballGraphic = new Graphics()
      .circle(0, 0, this.layout.ball.radius)
      .fill(this.layout.ball.color ?? 0xffffff)
    this.ballGraphic.visible = false

    this.actorLayer.addChild(
      this.leftFlipperGraphic,
      this.rightFlipperGraphic,
      this.ballGraphic,
    )

    this.reset()
  }

  attach(host: HTMLElement): void {
    if (this.host === host && this.app.canvas.parentElement === host) {
      this.syncViewport()
      return
    }

    const currentParent = this.app.canvas.parentElement
    if (currentParent && currentParent !== host) {
      currentParent.removeChild(this.app.canvas)
    }

    this.host = host

    this.app.canvas.style.display = 'block'
    this.app.canvas.style.touchAction = 'none'
    this.app.canvas.setAttribute('data-game-canvas', 'true')

    if (this.app.canvas.parentElement !== host) {
      host.appendChild(this.app.canvas)
    }

    // Pixi ResizePlugin can target an HTMLElement at runtime.
    this.app.resizeTo = host
    this.app.resize()

    this.syncViewport()
  }

  reset(): void {
    this.clearFx()

    this.ballGraphic.visible = false

    this.leftFlipperGraphic.x = this.layout.flippers.left.pivot.x
    this.leftFlipperGraphic.y = this.layout.flippers.left.pivot.y
    this.leftFlipperGraphic.rotation = degToRad(
      this.layout.flippers.left.restAngleDeg,
    )

    this.rightFlipperGraphic.x = this.layout.flippers.right.pivot.x
    this.rightFlipperGraphic.y = this.layout.flippers.right.pivot.y
    this.rightFlipperGraphic.rotation = degToRad(
      this.layout.flippers.right.restAngleDeg,
    )
  }

  render(snapshot: PhysicsSnapshot, events: GameEvent[]): void {
    this.syncViewport()
    this.consumeEvents(events)
    this.syncBall(snapshot.ball)
    this.syncFlippers(snapshot.flippers)
  }

  dispose(): void {
    this.app.resizeTo = null
    this.app.stage.removeChild(this.root)
    this.app.destroy({ removeView: true }, { children: true })
  }

  private buildPlayfieldSprite(): Sprite | null {
    const alias = this.layout.playfield?.alias
    if (!alias) return null

    const texture = this.assets[alias] as Texture | undefined
    if (!texture) return null

    const sprite = new Sprite(texture)
    sprite.width = this.layout.table.width
    sprite.height = this.layout.table.height
    return sprite
  }

  private buildFallbackPlayfield(): Graphics {
    return new Graphics()
      .rect(0, 0, this.layout.table.width, this.layout.table.height)
      .fill(this.layout.table.background ?? 0x101828)
  }

  private buildFlipper(flipper: FlipperLayout): Graphics {
    // Draw with local origin at the pivot so rotation feels correct.
    const g = new Graphics()
      .rect(
        -flipper.length * 0.12,
        -flipper.thickness / 2,
        flipper.length,
        flipper.thickness,
      )
      .fill(flipper.color ?? 0xff7a59)

    g.x = flipper.pivot.x
    g.y = flipper.pivot.y
    g.rotation = degToRad(flipper.restAngleDeg)

    return g
  }

  private syncViewport(): void {
    const viewportWidth =
      this.app.canvas.clientWidth || this.layout.table.width
    const viewportHeight =
      this.app.canvas.clientHeight || this.layout.table.height

    const scale = Math.min(
      viewportWidth / this.layout.table.width,
      viewportHeight / this.layout.table.height,
    )

    this.root.scale.set(scale)
    this.root.x = Math.round(
      (viewportWidth - this.layout.table.width * scale) / 2,
    )
    this.root.y = Math.round(
      (viewportHeight - this.layout.table.height * scale) / 2,
    )
  }

  private syncBall(ball: PhysicsSnapshot['ball']): void {
    if (!ball) {
      this.ballGraphic.visible = false
      return
    }

    this.ballGraphic.visible = true
    this.ballGraphic.x = ball.x
    this.ballGraphic.y = ball.y
    this.ballGraphic.rotation = ball.angle
  }

  private syncFlippers(flippers: PhysicsSnapshot['flippers']): void {
    this.leftFlipperGraphic.x = flippers.left.x
    this.leftFlipperGraphic.y = flippers.left.y
    this.leftFlipperGraphic.rotation = flippers.left.angle

    this.rightFlipperGraphic.x = flippers.right.x
    this.rightFlipperGraphic.y = flippers.right.y
    this.rightFlipperGraphic.rotation = flippers.right.angle
  }

  private consumeEvents(events: GameEvent[]): void {
    for (const event of events) {
      switch (event.type) {
        case 'spawn-fx':
          // Keep first pass simple. Add real particles in Sprint 2.
          this.spawnPulse()
          break
        case 'lamp-changed':
        case 'score-awarded':
        case 'multiplier-changed':
        case 'play-sfx':
        case 'ball-drained':
        case 'ball-spawned':
        case 'game-over':
          break
      }
    }
  }

  private spawnPulse(): void {
    if (!this.ballGraphic.visible) return

    const pulse = new Graphics()
      .circle(0, 0, this.layout.ball.radius * 1.8)
      .fill({ color: 0xfff08a, alpha: 0.18 })

    pulse.x = this.ballGraphic.x
    pulse.y = this.ballGraphic.y
    this.fxLayer.addChild(pulse)

    let elapsedMs = 0
    const durationMs = 140

    const tick = () => {
      elapsedMs += this.app.ticker.deltaMS

      const t = Math.min(elapsedMs / durationMs, 1)
      pulse.alpha = 0.18 * (1 - t)
      pulse.scale.set(1 + t * 1.6)

      if (t >= 1) {
        this.app.ticker.remove(tick)
        this.fxLayer.removeChild(pulse)
        pulse.destroy()
      }
    }

    this.app.ticker.add(tick)
  }

  private clearFx(): void {
    for (const child of [...this.fxLayer.children]) {
      this.fxLayer.removeChild(child)
      child.destroy()
    }
  }
}

function degToRad(deg: number): number {
  return (deg * Math.PI) / 180
}
AudioDirector.ts
This implementation makes ready() honest. It resolves when every Howl is loaded or rejects on loaderror. It does not pretend to solve browser interaction gating.
// frontend/apps/skriptoteket/src/components/apps/pinball-teacher/game/audio/AudioDirector.ts
import { Howl, Howler } from 'howler'

import type { GameEvent } from '../rules/RuleEngine'

export type AudioSpriteTuple = [number, number] | [number, number, boolean]

export interface AudioSpriteFileDefinition {
  src: string[]
  sprite?: Record<string, AudioSpriteTuple>
  volume?: number
  preload?: boolean
  loop?: boolean
}

export interface AudioBankDefinition {
  masterVolume?: number
  sprites: Record<string, AudioSpriteFileDefinition>
}

interface CueTarget {
  howl: Howl
  sprite?: string
}

export class AudioDirector {
  private readonly howls = new Map<string, Howl>()
  private readonly cues = new Map<string, CueTarget>()

  static async create(args: {
    bank: AudioBankDefinition
  }): Promise<AudioDirector> {
    const director = new AudioDirector(args.bank)
    await director.ready()
    return director
  }

  private constructor(private readonly bank: AudioBankDefinition) {
    if (typeof bank.masterVolume === 'number') {
      Howler.volume(bank.masterVolume)
    }

    // Be explicit even though this is the default.
    Howler.autoUnlock = true

    for (const [name, definition] of Object.entries(bank.sprites)) {
      const howl = new Howl({
        src: definition.src,
        sprite: definition.sprite,
        volume: definition.volume ?? 1,
        preload: definition.preload ?? true,
        loop: definition.loop ?? false,
      })

      this.howls.set(name, howl)

      if (definition.sprite && Object.keys(definition.sprite).length > 0) {
        for (const cue of Object.keys(definition.sprite)) {
          this.cues.set(cue, { howl, sprite: cue })
        }
      } else {
        this.cues.set(name, { howl })
      }
    }
  }

  async ready(): Promise<void> {
    if (Howler.noAudio) return

    await Promise.all(
      [...this.howls.values()].map((howl) => waitForHowlLoaded(howl)),
    )
  }

  reset(): void {
    for (const howl of this.howls.values()) {
      howl.stop()
    }
  }

  consume(events: GameEvent[]): void {
    for (const event of events) {
      if (event.type === 'play-sfx') {
        this.playCue(event.cue)
      }
    }
  }

  setMuted(muted: boolean): void {
    Howler.mute(muted)
  }

  setMasterVolume(volume: number): void {
    Howler.volume(clamp(volume, 0, 1))
  }

  dispose(): void {
    for (const howl of this.howls.values()) {
      howl.unload()
    }

    this.howls.clear()
    this.cues.clear()
  }

  private playCue(cue: string): void {
    const target = this.cues.get(cue)
    if (!target) return

    if (target.howl.state() !== 'loaded') return

    if (target.sprite) {
      target.howl.play(target.sprite)
    } else {
      target.howl.play()
    }
  }
}

function waitForHowlLoaded(howl: Howl): Promise<void> {
  const state = howl.state()

  if (state === 'loaded') {
    return Promise.resolve()
  }

  if (state === 'unloaded') {
    howl.load()
  }

  return new Promise<void>((resolve, reject) => {
    const onLoad = () => {
      cleanup()
      resolve()
    }

    const onLoadError = (_id?: number, error?: unknown) => {
      cleanup()
      reject(
        new Error(`Failed to load audio: ${String(error ?? 'unknown error')}`),
      )
    }

    const cleanup = () => {
      howl.off('load', onLoad)
      howl.off('loaderror', onLoadError)
    }

    howl.once('load', onLoad)
    howl.once('loaderror', onLoadError)
  })
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}
A small but important `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/GameHost.vue` adjustment
Do not auto-start the game in onMounted() if you care about reliable first-run audio. Load the runtime on mount, but start the first ball from a click/tap button. Howler’s docs explicitly describe first-user-interaction unlocking on mobile and Chrome/Safari-class environments; that is why ready() and “audio may now play” are not the same concept. (GitHub)
<script setup lang="ts">
import { onMounted, onUnmounted, ref, shallowRef } from 'vue'
import { createRuntime } from '@/components/apps/pinball-teacher/game/bootstrap/createRuntime'
import type { GameRuntime } from '@/components/apps/pinball-teacher/game/core/GameRuntime'

const hostEl = ref<HTMLDivElement | null>(null)
const runtime = shallowRef<GameRuntime | null>(null)

const loading = ref(true)
const error = ref<string | null>(null)
const booted = ref(false)
const started = ref(false)

let controller: AbortController | null = null
let unsubscribeHud: (() => void) | null = null

onMounted(async () => {
  if (!hostEl.value) return

  controller = new AbortController()

  try {
    const created = await createRuntime({ signal: controller.signal })

    if (controller.signal.aborted) {
      created.dispose()
      return
    }

    runtime.value = created
    created.mount(hostEl.value)

    unsubscribeHud = created.subscribeHud((hud) => {
      console.log('HUD', hud)
    })

    booted.value = true
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') return
    error.value =
      cause instanceof Error ? cause.message : 'Failed to create runtime.'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  controller?.abort()
  unsubscribeHud?.()
  runtime.value?.dispose()
  runtime.value = null
})

function startGame(): void {
  runtime.value?.startNewGame()
  started.value = true
}
</script>

<template>
  <section class="game-host">
    <div ref="hostEl" class="game-canvas-host" />

    <button
      v-if="booted && !started && !loading && !error"
      class="game-overlay start-button"
      @click="startGame"
    >
      Press Start
    </button>

    <div v-else-if="loading" class="game-overlay">
      Loading table…
    </div>

    <div v-else-if="error" class="game-overlay game-overlay--error">
      {{ error }}
    </div>
  </section>
</template>

<style scoped>
.game-host {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.game-canvas-host {
  width: 100%;
  height: 100%;
}

.game-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
}

.start-button {
  font: inherit;
  padding: 1rem 1.5rem;
  cursor: pointer;
}
</style>
Create and destroy the runtime in onMounted() / onUnmounted(). That is exactly what Vue documents those hooks for: DOM-bound side effects on mount, and cleanup of listeners/timers/connections on unmount. (Vue.js)
### Developer instruction: assemble this into a runnable program

Use the latest Vite scaffold, and respect its current Node floor. Vite’s official quick start uses npm create vite@latest, and Vite 8 requires Node 20.19+ or 22.12+. For the backend, install FastAPI with pip install "fastapi[standard]"; the official docs use fastapi dev for local development. (vitejs)

### Scaffold the repo

```bash
mkdir pinball && cd pinball

npm create vite@latest frontend/apps/skriptoteket
```

#### Scaffold choice: Vue + TypeScript

```bash
python -m venv .venv
source .venv/bin/activate
pip install "fastapi[standard]"
```

### Install the game runtime packages in `frontend/apps/skriptoteket`

```bash
cd frontend/apps/skriptoteket
npm install pixi.js @dimforge/rapier2d howler
npm install -D @types/node
```

### Set the minimum app shell

Create these files first:

- `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/game/bootstrap/createRuntime.ts`
- `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/game/render/PixiRenderer.ts`
- `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/game/audio/AudioDirector.ts`
- `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/game/core/GameRuntime.ts`
- `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/game/physics/PhysicsWorld.ts`
- `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/game/rules/RuleEngine.ts`
- `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/content/tables/prototype-alpha/manifest.ts`
- `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/content/tables/prototype-alpha/rules.ts`
- `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/content/tables/prototype-alpha/layout.json`
- `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/content/tables/prototype-alpha/physics.json`
- `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/GameHost.vue`

### Wire the shell so the game actually appears

Put `frontend/apps/skriptoteket/src/components/apps/pinball-teacher/GameHost.vue` directly in `App.vue`
for now. Do not add router, auth, or profile pages yet.

```vue
<template>

  <GameHost />
</template>

<script setup lang="ts">
import GameHost from '@/components/apps/pinball-teacher/GameHost.vue'
</script>
```

### Give the DOM a real height

If you skip this, the host element will have zero height and the canvas will look broken.

```css
/* src/style.css */
html,
body,
#app {
  margin: 0;
  width: 100%;
  height: 100%;
}

body {
  background: #0b1020;
}
```

### Add the alias in `vite.config.ts`

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

### Keep the backend minimal on day one

Do not block the vertical slice on auth, sessions, or Redis.

#### FastAPI entrypoint example

```py
from fastapi import FastAPI

app = FastAPI(title="Pinball API")

@app.get("/health")
async def health():
    return {"ok": True}
```
Run it with:
```bash
fastapi dev src/skriptoteket/web/api/v1/apps_pinball_teacher.py
```
The official FastAPI docs show fastapi dev as the development command and note that it auto-detects and runs your app locally. (FastAPI)

### Use dynamic Pixi bundles

For one table, your current Assets.addBundle() / Assets.loadBundle() approach is fine. When you add more tables, switch to Assets.init({ manifest }), because Pixi’s own docs recommend manifests and bundles as the scalable asset-management pattern for larger applications. (PixiJS)

### First smoke-test checklist

Verify these in order:

- app boots with no red console errors
- the canvas is appended into GameHost
- the fallback playfield appears even if art is missing
- pressing Start spawns a ball
- flipper keys move the flippers
- bumpers/rollovers/drain affect score and multiplier
- audio files load before gameplay begins
- backend /health responds

### Build target for “runnable”

You are done with the first runnable milestone when:

- one full 3-ball game can be played locally
- restart works
- pause works
- mute works
- no frame hitch permanently breaks the ball state
- no reload is needed between games

### PRD: polished browser pinball product

#### Product
A premium-feeling browser pinball game with one deeply polished table, excellent flipper response, readable scoring logic, strong audiovisual feedback, and an optional connected layer for profiles, scores, and tournaments.

#### Problem
Most browser pinball projects are technically playable but physically weak. They look acceptable and feel wrong. This product solves that by making ball feel, flipper response, authored collision behavior, and audiovisual feedback the first-order requirements.

#### Target users
- Desktop-first arcade players
- Score-chasers and leaderboard competitors
- Players who want short, replayable sessions
- Streamers or teachers who want a polished browser game that launches instantly

#### Product promise
“Open a browser, press start, and get a pinball table that feels deliberate rather than floaty.”

#### MVP scope
- One table only
- One ball in play at a time
- Two flippers
- Launcher
- Slingshots
- Three bumper types
- Rollover lane bank
- Drain
- Score + multiplier
- Pause, restart, mute
- Keyboard controls
- Basic particles, lamps, and SFX
- Local play first
- Online leaderboard second

#### Non-goals for MVP
- Multiple tables
- Full mobile-first controls
- User-generated tables
- Tournament administration UI
- Cosmetics store
- Social graph
- Mission-heavy progression systems

#### Core gameplay requirements
- Physics runs at a fixed step
- Rendering stays smooth and decoupled from physics
- Flippers feel immediate
- Ball drains and respawns reliably
- Rules are deterministic within a build
- Replay data can be recorded for score validation
- Table logic stays outside the physics layer

#### Connected-product requirements
- FastAPI service for health, scores, leaderboards, replay upload
- PostgreSQL as source of truth
- Redis for cache/session/leaderboard fan-out
- Replay-backed score validation before a score becomes “official”

#### Non-functional requirements
- Desktop-first, modern Chromium/Firefox/Safari support
- 60 FPS render target on ordinary laptops
- 120 Hz physics step target
- Clean restart without full page reload
- No network dependency during live play
- Crash-safe score submission after game end
- Asset loading failures show a clean error state

#### Success metrics
- 95%+ successful local boots
- 90%+ completed game sessions without hard reset
- Median first session greater than 4 minutes
- Strong restart rate, because replayability matters
- Low divergence between local score and validated official score

#### Release criteria
- One table feels “good enough to show strangers”
- No blocker bugs in launch, drain, respawn, or scoring
- Leaderboard submission works end-to-end
- Replays are stored and re-openable
- First-load UX is clean
- Audio, particles, and lamps materially improve feel

### Roadmap to polished product

#### Phase 1
Runnable local vertical slice.

#### Phase 2
Feel pass: tune flippers, materials, bumper kick behavior, light timing, and audio layering until the table feels intentional.

#### Phase 3
Connected beta: backend, score submission, leaderboards, replay validation, player profile.

#### Phase 4
Release candidate: QA sweep, balancing, onboarding, accessibility/key remapping, analytics, deployment hardening.

### Next 3 major sprints

#### Sprint 1 — Playable local vertical slice
Goal: one complete 3-ball game runs locally with reliable boot, controls, scoring, drain, restart.
Deliver:
- createRuntime.ts finalized
- PixiRenderer, AudioDirector, PhysicsWorld, RuleEngine
- one table manifest + layout + physics + rules
- frontend/apps/skriptoteket/src/components/apps/pinball-teacher/GameHost.vue
- keyboard controls
- score + multiplier HUD bridge
- pause/restart/mute
Exit criteria:
- one full local game playable end-to-end
- no console errors during a normal session
- runtime mounts/unmounts cleanly
- audio loads before gameplay
- fallback visuals work even if final art is missing

#### Sprint 2 — Feel and polish alpha
Goal: make the game feel good, not merely functional.
Deliver:
- flipper timing and angle tuning
- bumper/slingshot impulse tuning
- lamp states rendered in Pixi
- better particles and hit flashes
- launch lane polish
- replay recorder
- deterministic rules tests
- physics cooldown and collision regression tests
- settings panel for sound and controls
Exit criteria:
- internal testers say the table feels responsive
- no obvious double-hit scoring bugs
- no “stuck ball” soft-locks in ordinary play
- replay file can reproduce a run on the same build

#### Sprint 3 — Connected beta
Goal: ship the first real product layer around the game.
Deliver:
- FastAPI health, score submit, leaderboard read, replay upload
- PostgreSQL models and migrations
- Redis cache for top scores / live board
- end-of-game submission flow
- leaderboard page in Vue shell
- profile stub
- anti-cheat/replay validation worker
- deployment config for web + api
Exit criteria:
- official score flow works end-to-end
- leaderboard updates after a validated run
- failed submissions do not corrupt local session state
- core gameplay remains fully local even if backend is down
The correct build order is still the same: feel first, systems second. Do not let Sprint 3 start until Sprint 2 has already made the table fun.
