/**
 * Audio director tests for Flunk-Out Frenzy.
 *
 * These tests keep the Howler-backed adapter honest about lifecycle and mute
 * ownership so a disposed game session cannot leak global audio state into the
 * next runtime or other routes.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const { MockHowl, howlInstances, mockHowler, muteSpy } = vi.hoisted(() => {
  const instances: {
    unload: ReturnType<typeof vi.fn>;
    play: ReturnType<typeof vi.fn>;
    load: ReturnType<typeof vi.fn>;
    state: ReturnType<typeof vi.fn>;
  }[] = [];
  const howler = {
    autoUnlock: false,
    _muted: false,
    mute: vi.fn((muted: boolean) => {
      howler._muted = muted;
    }),
  };

  class HoistedMockHowl {
    public readonly unload = vi.fn();
    public readonly play = vi.fn(() => 1);
    public readonly load = vi.fn();
    public readonly state = vi.fn<() => "loaded">(() => "loaded");

    public constructor(_options: unknown) {
      instances.push(this);
    }
  }

  return {
    MockHowl: HoistedMockHowl,
    howlInstances: instances,
    mockHowler: howler,
    muteSpy: howler.mute,
  };
});

vi.mock("howler", () => ({
  Howl: MockHowl,
  Howler: mockHowler,
}));

import { AudioDirector } from "./AudioDirector";

describe("AudioDirector", () => {
  beforeEach(() => {
    howlInstances.length = 0;
    mockHowler.autoUnlock = false;
    mockHowler._muted = false;
    muteSpy.mockClear();
  });

  it("restores the incoming global mute state on dispose after muting a session", async () => {
    mockHowler._muted = false;

    const director = await AudioDirector.create();
    director.setMuted(true);
    director.dispose();

    expect(muteSpy).toHaveBeenNthCalledWith(1, true);
    expect(muteSpy).toHaveBeenNthCalledWith(2, false);
    expect(mockHowler._muted).toBe(false);
    expect(howlInstances.every((howl) => howl.unload.mock.calls.length === 1)).toBe(true);
  });

  it("preserves an already-muted global state when the session disposes", async () => {
    mockHowler._muted = true;

    const director = await AudioDirector.create();
    director.setMuted(false);
    director.dispose();

    expect(muteSpy).toHaveBeenNthCalledWith(1, false);
    expect(muteSpy).toHaveBeenNthCalledWith(2, true);
    expect(mockHowler._muted).toBe(true);
  });
});
