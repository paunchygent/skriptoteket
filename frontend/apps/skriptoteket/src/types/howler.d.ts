/**
 * Minimal howler typings for the Flunk-Out Frenzy audio director.
 *
 * The project only uses a narrow subset of Howler in this slice, so a local
 * declaration keeps the frontend self-contained without broad ambient types.
 */

declare module "howler" {
  export interface HowlOptions {
    src: string[];
    volume?: number;
    preload?: boolean;
  }

  export class Howl {
    public constructor(options: HowlOptions);
    public load(): void;
    public play(): number;
    public state(): "unloaded" | "loading" | "loaded";
    public unload(): void;
  }

  export const Howler: {
    autoUnlock: boolean;
    mute(muted: boolean): void;
  };
}
