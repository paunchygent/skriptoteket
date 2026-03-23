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
    return this.currentState();
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
    const ruleStep = this.rules.handleMachineEvents(machineEvents);
    const drainedBall = machineEvents.some((event) => event.type === "drain-enter");

    if (drainedBall) {
      this.physics.removeBall();
    }

    if (ruleStep.shouldRespawnBall) {
      this.physics.spawnBall();
    }

    return this.currentState();
  }

  currentState(): RuntimeEngineState {
    const physicsSnapshot = this.physics.currentSnapshot();
    const ruleSnapshot = this.rules.currentSnapshot();

    return {
      score: ruleSnapshot.score,
      ballsRemaining: ruleSnapshot.ballsRemaining,
      multiplier: ruleSnapshot.multiplier,
      roundFinished: ruleSnapshot.roundFinished,
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
}
