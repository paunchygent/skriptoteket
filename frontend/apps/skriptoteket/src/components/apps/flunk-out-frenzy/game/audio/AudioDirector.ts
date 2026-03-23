/**
 * Howler-backed audio director for Flunk-Out Frenzy.
 *
 * This adapter turns semantic game-effect events into lightweight synthesized
 * cues so the local prototype feels alive without committing to final assets.
 */

import { Howl, Howler } from "howler";

import type { GameEffectEvent } from "../presentation/gameEffectTypes";
import type { RuntimeAudioDirector } from "./audioTypes";

type CueName =
  | "round-started"
  | "flipper-fired"
  | "launch-released"
  | "bumper-hit"
  | "sling-hit"
  | "rollover-lit"
  | "late-bank-complete"
  | "ball-drained"
  | "game-over";

export class AudioDirector implements RuntimeAudioDirector {
  private readonly cues = new Map<CueName, Howl>();

  static async create(): Promise<AudioDirector> {
    return new AudioDirector();
  }

  private constructor() {
    Howler.autoUnlock = true;

    this.cues.set("round-started", this.createCue(520, 180, 0.12));
    this.cues.set("flipper-fired", this.createCue(220, 52, 0.08, "square"));
    this.cues.set("launch-released", this.createCue(310, 90, 0.09, "triangle"));
    this.cues.set("bumper-hit", this.createCue(660, 120, 0.16));
    this.cues.set("sling-hit", this.createCue(430, 96, 0.1, "triangle"));
    this.cues.set("rollover-lit", this.createCue(570, 76, 0.08, "triangle"));
    this.cues.set("late-bank-complete", this.createCue(880, 240, 0.18));
    this.cues.set("ball-drained", this.createCue(180, 240, 0.16, "triangle"));
    this.cues.set("game-over", this.createCue(120, 360, 0.18, "sawtooth"));
  }

  setMuted(muted: boolean): void {
    Howler.mute(muted);
  }

  consumeEffects(effects: GameEffectEvent[]): void {
    for (const effect of effects) {
      switch (effect.type) {
        case "round-started":
          this.playCue("round-started");
          break;
        case "flipper-fired":
          this.playCue("flipper-fired");
          break;
        case "launch-released":
          this.playCue("launch-released");
          break;
        case "bumper-hit":
          this.playCue("bumper-hit");
          break;
        case "sling-hit":
          this.playCue("sling-hit");
          break;
        case "rollover-lit":
          this.playCue("rollover-lit");
          break;
        case "late-bank-complete":
          this.playCue("late-bank-complete");
          break;
        case "ball-drained":
          this.playCue("ball-drained");
          break;
        case "game-over":
          this.playCue("game-over");
          break;
        case "ball-spawned":
          break;
      }
    }
  }

  dispose(): void {
    for (const cue of this.cues.values()) {
      cue.unload();
    }

    this.cues.clear();
  }

  private createCue(
    frequencyHz: number,
    durationMs: number,
    volume: number,
    wave: OscillatorType = "sine",
  ): Howl {
    return new Howl({
      src: [createToneDataUri(frequencyHz, durationMs, volume, wave)],
      volume,
      preload: true,
    });
  }

  private playCue(name: CueName): void {
    const cue = this.cues.get(name);
    if (!cue) {
      return;
    }

    if (cue.state() !== "loaded") {
      cue.load();
      return;
    }

    cue.play();
  }
}

function createToneDataUri(
  frequencyHz: number,
  durationMs: number,
  volume: number,
  wave: OscillatorType,
): string {
  const sampleRate = 22_050;
  const sampleCount = Math.max(1, Math.floor((sampleRate * durationMs) / 1000));
  const buffer = new ArrayBuffer(44 + sampleCount * 2);
  const view = new DataView(buffer);

  writeAscii(view, 0, "RIFF");
  view.setUint32(4, 36 + sampleCount * 2, true);
  writeAscii(view, 8, "WAVE");
  writeAscii(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeAscii(view, 36, "data");
  view.setUint32(40, sampleCount * 2, true);

  for (let index = 0; index < sampleCount; index += 1) {
    const t = index / sampleRate;
    const attack = Math.min(index / (sampleCount * 0.08), 1);
    const release = Math.min((sampleCount - index) / (sampleCount * 0.22), 1);
    const envelope = Math.min(attack, release, 1);
    const sample = waveformSample(2 * Math.PI * frequencyHz * t, wave) * envelope * volume;
    view.setInt16(44 + index * 2, sample * 0x7fff, true);
  }

  return `data:audio/wav;base64,${toBase64(new Uint8Array(buffer))}`;
}

function waveformSample(phase: number, wave: OscillatorType): number {
  switch (wave) {
    case "square":
      return Math.sign(Math.sin(phase)) || 1;
    case "triangle":
      return (2 / Math.PI) * Math.asin(Math.sin(phase));
    case "sawtooth":
      return 2 * (phase / (2 * Math.PI) - Math.floor(phase / (2 * Math.PI) + 0.5));
    case "sine":
    default:
      return Math.sin(phase);
  }
}

function writeAscii(view: DataView, offset: number, text: string): void {
  for (let index = 0; index < text.length; index += 1) {
    view.setUint8(offset + index, text.charCodeAt(index));
  }
}

function toBase64(bytes: Uint8Array): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  let output = "";

  for (let index = 0; index < bytes.length; index += 3) {
    const a = bytes[index] ?? 0;
    const b = bytes[index + 1] ?? 0;
    const c = bytes[index + 2] ?? 0;

    const chunk = (a << 16) | (b << 8) | c;

    output += alphabet[(chunk >> 18) & 63];
    output += alphabet[(chunk >> 12) & 63];
    output += index + 1 < bytes.length ? alphabet[(chunk >> 6) & 63] : "=";
    output += index + 2 < bytes.length ? alphabet[chunk & 63] : "=";
  }

  return output;
}
