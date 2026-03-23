/**
 * Semantic game-effect events for Flunk-Out Frenzy.
 *
 * These events sit above physics and below presentation. The runtime can feed
 * them to rendering and audio adapters without leaking Rapier details or Vue
 * concerns into either side.
 */

export type GameEffectEvent =
  | { type: "round-started" }
  | { type: "ball-spawned" }
  | { type: "flipper-fired"; side: "left" | "right" }
  | { type: "launch-released"; chargeActive: boolean }
  | { type: "bumper-hit"; tag: string }
  | { type: "sling-hit"; tag: string; side: "left" | "right" }
  | { type: "rollover-lit"; tag: string; label: string }
  | { type: "late-bank-complete"; multiplier: number }
  | { type: "ball-drained"; ballsRemaining: number }
  | { type: "game-over"; finalScore: number };
