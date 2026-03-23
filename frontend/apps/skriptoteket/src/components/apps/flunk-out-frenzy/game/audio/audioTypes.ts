/**
 * Audio adapter contracts for Flunk-Out Frenzy.
 *
 * The runtime owns lifecycle and mute state, while concrete audio adapters
 * consume semantic game-effect events to play lightweight cues.
 */

import type { GameEffectEvent } from "../presentation/gameEffectTypes";

export interface RuntimeAudioDirector {
  setMuted(muted: boolean): void;
  consumeEffects(effects: GameEffectEvent[]): void;
  dispose(): void;
}
