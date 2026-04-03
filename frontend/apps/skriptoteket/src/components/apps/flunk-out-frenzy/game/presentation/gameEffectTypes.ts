/**
 * Semantic game-effect events for Flunk-Out Frenzy.
 *
 * These events sit above physics and below presentation. The runtime can feed
 * them to rendering and audio adapters without leaking Rapier details or Vue
 * concerns into either side.
 */

import type {
  CaptureMachineEventKind,
  SaveMachineEventKind,
} from "../physics/physicsTypes";

export type GameEffectEvent =
  | { type: "round-started" }
  | { type: "ball-spawned" }
  | { type: "flipper-fired"; side: "left" | "right" }
  | { type: "launch-released"; chargeActive: boolean }
  | { type: "bumper-hit"; tag: string }
  | { type: "sling-hit"; tag: string; side: "left" | "right" }
  | { type: "rollover-lit"; tag: string; label: string }
  | { type: "tripwire-crossed"; tag: string }
  | { type: "standup-target-hit"; tag: string }
  | { type: "popup-target-hit"; tag: string }
  | { type: "gate-passed"; tag: string }
  | { type: "ball-captured"; tag: string; deviceKind: CaptureMachineEventKind }
  | { type: "ball-ejected"; tag: string; deviceKind: CaptureMachineEventKind }
  | { type: "ball-saved"; tag: string; deviceKind: SaveMachineEventKind }
  | { type: "late-bank-complete"; multiplier: number }
  | { type: "bonus-awarded"; points: number }
  | { type: "jackpot-lit"; points: number }
  | { type: "jackpot-awarded"; points: number }
  | { type: "capture-awarded"; tag: string; deviceKind: CaptureMachineEventKind; points: number }
  | { type: "eject-awarded"; tag: string; deviceKind: CaptureMachineEventKind; points: number }
  | { type: "save-awarded"; tag: string; deviceKind: SaveMachineEventKind; points: number }
  | { type: "shoot-again-lit" }
  | { type: "ball-drained"; ballsRemaining: number }
  | { type: "game-over"; finalScore: number };
