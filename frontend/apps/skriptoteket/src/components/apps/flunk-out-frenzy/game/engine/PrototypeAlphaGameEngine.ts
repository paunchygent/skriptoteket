/**
 * Prototype-alpha game engine for Flunk-Out Frenzy.
 *
 * This engine composes the Rapier-backed physics world with the pure scoring
 * rules so the runtime can treat the whole table slice as one simulation unit
 * without collapsing the physics/rules boundary.
 */

import type { RuntimeEngine, RuntimeEngineState } from "../core/runtimeEngineTypes";
import type { RuntimeCommand } from "../core/runtimeTypes";
import type { PhysicsSnapshot, MachineEvent } from "../physics/physicsTypes";
import type { GameEffectEvent } from "../presentation/gameEffectTypes";
import { PhysicsWorld } from "../physics/PhysicsWorld";
import {
  RuleEngine,
  type RuleSnapshot,
  type RuleStepResult,
} from "../rules/RuleEngine";
import { PROTOTYPE_ALPHA_TABLE } from "../table/prototypeAlphaTable";

export interface PrototypeAlphaPhysicsMachine {
  reset(): void;
  spawnBall(): void;
  removeBall(): void;
  applyCommand(command: RuntimeCommand): void;
  step(dtMs: number): MachineEvent[];
  currentSnapshot(): PhysicsSnapshot;
  dispose(): void;
}

export interface PrototypeAlphaRulesEngine {
  startGame(): RuleSnapshot;
  currentSnapshot(): RuleSnapshot;
  handleMachineEvents(events: MachineEvent[]): RuleStepResult;
}

export class PrototypeAlphaGameEngine implements RuntimeEngine {
  static async create(): Promise<PrototypeAlphaGameEngine> {
    const physics = await PhysicsWorld.create();
    return new PrototypeAlphaGameEngine(physics, new RuleEngine());
  }

  constructor(
    private readonly physics: PrototypeAlphaPhysicsMachine,
    private readonly rules: PrototypeAlphaRulesEngine,
  ) {}

  startGame(): RuntimeEngineState {
    this.rules.startGame();
    this.physics.reset();
    this.physics.spawnBall();
    return this.currentState([
      { type: "round-started" },
      { type: "ball-spawned" },
    ]);
  }

  restartGame(): RuntimeEngineState {
    return this.startGame();
  }

  applyCommand(command: RuntimeCommand): void {
    this.physics.applyCommand(command);
  }

  step(dtMs: number): RuntimeEngineState {
    const machineEvents = this.physics.step(dtMs);
    return this.applyMachineEvents(machineEvents);
  }

  injectMachineEventsForDebug(events: MachineEvent[]): RuntimeEngineState {
    return this.applyMachineEvents(events);
  }

  private applyMachineEvents(machineEvents: MachineEvent[]): RuntimeEngineState {
    const previousRuleSnapshot = this.rules.currentSnapshot();
    const ruleStep = this.rules.handleMachineEvents(machineEvents);
    const drainedBall = machineEvents.some((event) => event.type === "drain-enter");
    const effects = this.machineEventsToEffects(machineEvents, previousRuleSnapshot, ruleStep);

    if (drainedBall) {
      this.physics.removeBall();
    }

    if (ruleStep.shouldRespawnBall) {
      this.physics.spawnBall();
      effects.push({ type: "ball-spawned" });
    }

    if (ruleStep.snapshot.roundFinished) {
      effects.push({ type: "game-over", finalScore: ruleStep.snapshot.score });
    }

    return this.currentState(effects);
  }

  currentState(effects: GameEffectEvent[] = []): RuntimeEngineState {
    const physicsSnapshot = this.physics.currentSnapshot();
    const ruleSnapshot = this.rules.currentSnapshot();

    return {
      score: ruleSnapshot.score,
      ballsRemaining: ruleSnapshot.ballsRemaining,
      multiplier: ruleSnapshot.multiplier,
      roundFinished: ruleSnapshot.roundFinished,
      effects,
      view: {
        board: {
          width: PROTOTYPE_ALPHA_TABLE.board.width,
          height: PROTOTYPE_ALPHA_TABLE.board.height,
        },
        ball: physicsSnapshot.ball,
        flippers: physicsSnapshot.flippers,
        rollovers: PROTOTYPE_ALPHA_TABLE.rollovers.map((rollover) => ({
          tag: rollover.tag,
          label: rollover.label,
          x: rollover.x,
          y: rollover.y,
          lit: ruleSnapshot.litLaneTags.includes(rollover.tag),
        })),
      },
    };
  }

  dispose(): void {
    this.physics.dispose();
  }

  private machineEventsToEffects(
    machineEvents: MachineEvent[],
    previousRuleSnapshot: RuleSnapshot,
    ruleStep: RuleStepResult,
  ): GameEffectEvent[] {
    const effects: GameEffectEvent[] = [];

    for (const event of machineEvents) {
      switch (event.type) {
        case "bumper-fired":
          effects.push({ type: "bumper-hit", tag: event.tag });
          break;
        case "sling-fired":
          effects.push({ type: "sling-hit", tag: event.tag, side: event.side });
          break;
        case "rollover-enter": {
          const wasLit = previousRuleSnapshot.litLaneTags.includes(event.tag);
          if (!wasLit) {
            const rollover = PROTOTYPE_ALPHA_TABLE.rollovers.find((item) => item.tag === event.tag);
            effects.push({
              type: "rollover-lit",
              tag: event.tag,
              label: rollover?.label ?? "?",
            });
          }
          break;
        }
        case "drain-enter":
          effects.push({
            type: "ball-drained",
            ballsRemaining: ruleStep.snapshot.ballsRemaining,
          });
          break;
      }
    }

    if (ruleStep.snapshot.multiplier > previousRuleSnapshot.multiplier) {
      effects.push({
        type: "late-bank-complete",
        multiplier: ruleStep.snapshot.multiplier,
      });
    }

    return effects;
  }
}
