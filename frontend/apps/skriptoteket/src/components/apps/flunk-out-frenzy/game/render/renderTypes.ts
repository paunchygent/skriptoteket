/**
 * Rendering adapter contracts for Flunk-Out Frenzy.
 *
 * The runtime owns when rendering happens. Concrete renderers such as Pixi
 * attach to the host surface and consume immutable view snapshots plus
 * semantic game-effect events.
 */

import type { GameHudSnapshot, GameViewSnapshot } from "../core/runtimeTypes";
import type { GameEffectEvent } from "../presentation/gameEffectTypes";

export interface RuntimeRenderer {
  attach(hostElement: HTMLElement): void;
  render(view: GameViewSnapshot, hud: GameHudSnapshot, effects: GameEffectEvent[]): void;
  dispose(): void;
}
