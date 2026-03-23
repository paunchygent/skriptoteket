/**
 * No-op audio adapter for Flunk-Out Frenzy.
 *
 * This adapter preserves the runtime/audio contract when bootstrap or future
 * shell policy disables audio entirely. It lets `GameRuntime` keep honest HUD
 * state without instantiating Howler-backed behavior.
 */

import type { GameEffectEvent } from "../presentation/gameEffectTypes";
import type { RuntimeAudioDirector } from "./audioTypes";

export class NoopAudioDirector implements RuntimeAudioDirector {
  readonly enabled = false;

  static async create(): Promise<NoopAudioDirector> {
    return new NoopAudioDirector();
  }

  setMuted(_muted: boolean): void {}

  consumeEffects(_effects: GameEffectEvent[]): void {}

  dispose(): void {}
}
