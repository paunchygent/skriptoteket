import { beforeEach, describe, expect, it, vi } from "vitest";

const manifest = {
  schema_version: 1,
  app: "classroom.group-seating-studio",
  clips: [
    {
      id: "klass-2",
      section: "planner_overview",
      order: 2,
      title: "Klassrum",
      duration_seconds: 40,
      video: "klassrum.mp4",
      poster: "klassrum.jpg",
    },
    {
      id: "klass",
      section: "planner_overview",
      order: 1,
      title: "Klass",
      duration_seconds: 8,
      video: "klass.mp4",
      poster: "klass.jpg",
    },
    {
      id: "regler",
      section: "planner_rules",
      order: 1,
      title: "Regler",
      duration_seconds: 30,
      video: "regler.mp4",
      poster: "regler.jpg",
    },
  ],
};

// The manifest cache is module state that lives for one app load; each test
// starts from a fresh module graph, as a new app load would.
async function freshModule() {
  vi.resetModules();
  return await import("./useTutorialClipManifest");
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe("useTutorialClipManifest", () => {
  it("fetches once per app load and lists a section's clips in manifest order", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json(manifest));
    vi.stubGlobal("fetch", fetchMock);
    const { clipsForSection, loadTutorialClipManifest, useTutorialClipManifest } =
      await freshModule();

    const state = useTutorialClipManifest();
    expect(state.loaded.value).toBe(false);
    await loadTutorialClipManifest();
    await loadTutorialClipManifest();
    useTutorialClipManifest();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(state.loaded.value).toBe(true);
    expect(clipsForSection("planner_overview").map((clip) => clip.id)).toEqual([
      "klass",
      "klass-2",
    ]);
    expect(clipsForSection("planner_seating")).toEqual([]);
  });

  it("is loaded with no clips when the manifest is missing", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Not found", { status: 404 })));
    const { clipsForSection, loadTutorialClipManifest, useTutorialClipManifest } =
      await freshModule();

    const state = useTutorialClipManifest();
    await loadTutorialClipManifest();

    expect(state.loaded.value).toBe(true);
    expect(clipsForSection("planner_overview")).toEqual([]);
  });
});
