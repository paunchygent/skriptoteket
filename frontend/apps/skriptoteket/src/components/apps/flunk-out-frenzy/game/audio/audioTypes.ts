/**
 * Audio adapter contracts for Flunk-Out Frenzy.
 *
 * The runtime owns lifecycle and mute state, while concrete audio adapters
 * consume semantic game-effect events to play lightweight cues. The adapter
 * also reports whether audio is actually enabled so the runtime can keep HUD
 * state aligned with the true subsystem state.
 */

import type { GameEffectEvent } from "../presentation/gameEffectTypes";

export interface RuntimeAudioDirector {
  readonly enabled: boolean;
  setMuted(muted: boolean): void;
  consumeEffects(effects: GameEffectEvent[]): void;
  dispose(): void;
}
