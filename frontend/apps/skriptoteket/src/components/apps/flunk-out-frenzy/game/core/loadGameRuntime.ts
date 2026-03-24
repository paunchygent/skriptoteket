/**
 * Lazy runtime loader for Flunk-Out Frenzy.
 *
 * This module keeps the route shell and host free from eagerly importing the
 * full game runtime graph. `GameHost.vue` uses this seam to fetch the runtime
 * only when the player actually starts the game, while the runtime module
 * itself continues to own engine, renderer, and audio composition.
 */

import type { GameRuntimeFactory, GameRuntimeFactoryOptions } from "../../gameHostTypes";

export const loadGameRuntime: GameRuntimeFactory = async (
  options: GameRuntimeFactoryOptions,
) => {
  const { GameRuntime } = await import("./GameRuntime");
  return GameRuntime.create(options);
};
