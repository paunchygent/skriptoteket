/**
 * Flunk-Out Frenzy shell-to-host contracts.
 *
 * These types keep the bespoke route shell decoupled from the browser-owned
 * runtime. The route consumes read-only HUD projections while `GameHost.vue`
 * forwards imperative lifecycle controls into the runtime core.
 */

import type {
  GameHudSnapshot,
  GameSessionStatus,
  RuntimeCommand,
} from "./game/core/runtimeTypes";
import type { MachineEvent } from "./game/physics/physicsTypes";

export type {
  GameHudSnapshot,
  GameSessionStatus,
  GameViewSnapshot,
} from "./game/core/runtimeTypes";

export type GameRuntimeLoadState = "idle" | "loading" | "ready" | "error";

export interface GameHostApi {
  startGame(): Promise<void>;
  pauseGame(): void;
  resumeGame(): void;
  restartGame(): Promise<void>;
  setMuted(muted: boolean): void;
}

export interface GameRuntimeLike {
  mount(hostElement: HTMLElement): void;
  start(): void;
  pause(): void;
  resume(): void;
  restart(): void;
  setMuted(muted: boolean): void;
  enqueueCommand(command: RuntimeCommand): void;
  subscribeHud(listener: (hud: GameHudSnapshot) => void): () => void;
  dispose(): void;
  injectMachineEventsForDebug?(events: MachineEvent[]): void;
}

export interface GameRuntimeFactoryOptions {
  audioEnabled: boolean;
}

export type GameRuntimeFactory = (
  options: GameRuntimeFactoryOptions,
) => Promise<GameRuntimeLike>;

export function labelGameSessionStatus(
  status: GameSessionStatus,
): "Pågående runda" | "Pausad" | "Game over" | "Redo att starta" {
  switch (status) {
    case "running":
      return "Pågående runda";
    case "paused":
      return "Pausad";
    case "game-over":
      return "Game over";
    case "ready":
      return "Redo att starta";
  }
}
