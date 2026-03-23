/**
 * Runtime engine contracts for Flunk-Out Frenzy.
 *
 * The runtime spine orchestrates lifecycle, scheduling, and HUD publication,
 * while a narrower engine implementation owns table simulation and rules. This
 * keeps `GameRuntime` testable without forcing every test through Rapier.
 */

import type { GameViewSnapshot, RuntimeCommand } from "./runtimeTypes";
import type { MachineEvent } from "../physics/physicsTypes";

export interface RuntimeEngineState {
  score: number;
  ballsRemaining: number;
  multiplier: number;
  roundFinished: boolean;
  view: GameViewSnapshot;
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
