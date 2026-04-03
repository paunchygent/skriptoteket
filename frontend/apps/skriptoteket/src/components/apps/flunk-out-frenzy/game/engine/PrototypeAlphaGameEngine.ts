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
import { RuleEngine } from "../rules/RuleEngine";
import { PROTOTYPE_ALPHA_TABLE } from "../table/prototypeAlphaTable";
import type { RuleEvent, RuleSnapshot, RuleStepResult } from "../rules/ruleTypes";

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

    if (ruleStep.snapshot.ballLifecycle.roundFinished) {
      effects.push({ type: "game-over", finalScore: ruleStep.snapshot.score });
    }

    return this.currentState(effects);
  }

  currentState(effects: GameEffectEvent[] = []): RuntimeEngineState {
    const physicsSnapshot = this.physics.currentSnapshot();
    const ruleSnapshot = this.rules.currentSnapshot();

    return {
      score: ruleSnapshot.score,
      ballsRemaining: ruleSnapshot.ballLifecycle.ballsRemaining,
      multiplier: ruleSnapshot.multiplier,
      bonus: ruleSnapshot.bonus,
      jackpot: ruleSnapshot.jackpot,
      ballLifecycle: {
        shootAgainLit: ruleSnapshot.ballLifecycle.shootAgainLit,
      },
      roundFinished: ruleSnapshot.ballLifecycle.roundFinished,
      effects,
      view: {
        board: {
          width: PROTOTYPE_ALPHA_TABLE.board.width,
          height: PROTOTYPE_ALPHA_TABLE.board.height,
        },
        ball: physicsSnapshot.ball,
        plunger: physicsSnapshot.plunger,
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
        case "tripwire-crossed":
          effects.push({ type: "tripwire-crossed", tag: event.tag });
          break;
        case "standup-target-hit":
          effects.push({ type: "standup-target-hit", tag: event.tag });
          break;
        case "popup-target-hit":
          effects.push({ type: "popup-target-hit", tag: event.tag });
          break;
        case "gate-passed":
          effects.push({ type: "gate-passed", tag: event.tag });
          break;
        case "ball-captured":
          effects.push({
            type: "ball-captured",
            tag: event.tag,
            deviceKind: event.deviceKind,
          });
          break;
        case "ball-ejected":
          effects.push({
            type: "ball-ejected",
            tag: event.tag,
            deviceKind: event.deviceKind,
          });
          break;
        case "ball-saved":
          effects.push({
            type: "ball-saved",
            tag: event.tag,
            deviceKind: event.deviceKind,
          });
          break;
        case "launcher-released":
          effects.push({ type: "launch-released", chargeActive: true });
          break;
        case "drain-enter":
          effects.push({
            type: "ball-drained",
            ballsRemaining: ruleStep.snapshot.ballLifecycle.ballsRemaining,
          });
          break;
        case "launch-lane-enter":
        case "launcher-fed":
        case "launcher-charged":
          break;
      }
    }

    effects.push(...ruleStep.ruleEvents.map(mapRuleEventToGameEffect));

    return effects;
  }
}

function mapRuleEventToGameEffect(ruleEvent: RuleEvent): GameEffectEvent {
  switch (ruleEvent.type) {
    case "late-bank-complete":
      return {
        type: "late-bank-complete",
        multiplier: ruleEvent.multiplier,
      };
    case "bonus-awarded":
      return {
        type: "bonus-awarded",
        points: ruleEvent.points,
      };
    case "jackpot-lit":
      return {
        type: "jackpot-lit",
        points: ruleEvent.points,
      };
    case "jackpot-awarded":
      return {
        type: "jackpot-awarded",
        points: ruleEvent.points,
      };
    case "capture-awarded":
      return {
        type: "capture-awarded",
        tag: ruleEvent.tag,
        deviceKind: ruleEvent.deviceKind,
        points: ruleEvent.points,
      };
    case "eject-awarded":
      return {
        type: "eject-awarded",
        tag: ruleEvent.tag,
        deviceKind: ruleEvent.deviceKind,
        points: ruleEvent.points,
      };
    case "save-awarded":
      return {
        type: "save-awarded",
        tag: ruleEvent.tag,
        deviceKind: ruleEvent.deviceKind,
        points: ruleEvent.points,
      };
    case "shoot-again-lit":
      return {
        type: "shoot-again-lit",
      };
  }
}
