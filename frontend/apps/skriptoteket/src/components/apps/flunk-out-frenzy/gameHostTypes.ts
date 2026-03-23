/**
 * Flunk-Out Frenzy shell-to-host contracts.
 *
 * These types keep the bespoke route shell decoupled from the browser-owned
 * runtime. The route consumes read-only HUD projections while `GameHost.vue`
 * forwards imperative lifecycle controls into the runtime core.
 */

export type {
  GameHudSnapshot,
  GameSessionStatus,
  GameViewSnapshot,
} from "./game/core/runtimeTypes";

export interface GameHostApi {
  startGame(): void;
  pauseGame(): void;
  resumeGame(): void;
  restartGame(): void;
  setMuted(muted: boolean): void;
}
