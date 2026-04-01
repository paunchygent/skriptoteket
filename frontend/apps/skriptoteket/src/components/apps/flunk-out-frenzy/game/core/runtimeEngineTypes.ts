/**
 * Runtime engine contracts for Flunk-Out Frenzy.
 *
 * The runtime spine orchestrates lifecycle, scheduling, and HUD publication,
 * while a narrower engine implementation owns table simulation and rules. This
 * keeps `GameRuntime` testable without forcing every test through Rapier.
 */

import type { GameViewSnapshot, RuntimeCommand } from "./runtimeTypes";
import type { MachineEvent } from "../physics/physicsTypes";
import type { GameEffectEvent } from "../presentation/gameEffectTypes";

export interface RuntimeEngineState {
  score: number;
  ballsRemaining: number;
  multiplier: number;
  bonus: {
    points: number;
    collectReady: boolean;
  };
  jackpot: {
    points: number;
    lit: boolean;
  };
  ballLifecycle: {
    shootAgainLit: boolean;
  };
  roundFinished: boolean;
  view: GameViewSnapshot;
  effects: GameEffectEvent[];
}

export interface RuntimeEngine {
  startGame(): RuntimeEngineState;
  restartGame(): RuntimeEngineState;
  applyCommand(command: RuntimeCommand): void;
  step(dtMs: number): RuntimeEngineState;
  currentState(): RuntimeEngineState;
  dispose(): void;
  injectMachineEventsForDebug?(events: MachineEvent[]): RuntimeEngineState;
}
