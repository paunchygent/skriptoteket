import { afterEach, describe, expect, it, vi } from "vitest";

import {
  clipsForSection,
  loadTutorialClipManifest,
  parseTutorialClipManifest,
  resetTutorialClipManifestCacheForTests,
  resolveMediaUrl,
  TUTORIAL_CLIP_MANIFEST_URL,
  useTutorialClipManifest,
} from "./tutorialClipManifest";

const validManifest = {
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
      published_at: "2026-10-15T05:49:48Z",
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

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  resetTutorialClipManifestCacheForTests();
  vi.unstubAllGlobals();
});

describe("parseTutorialClipManifest", () => {
  it("accepts the contract and drops extra fields such as published_at", () => {
    const parsed = parseTutorialClipManifest(validManifest);
    expect(parsed?.clips).toHaveLength(3);
    expect(parsed?.clips[1]).not.toHaveProperty("published_at");
  });

  it.each([
    ["an unknown section", { section: "planner_share" }],
    ["a missing poster", { poster: undefined }],
    ["a string duration", { duration_seconds: "8" }],
    ["an empty video path", { video: "" }],
  ])("rejects the whole manifest for %s", (_label, override) => {
    const broken = {
      ...validManifest,
      clips: [{ ...validManifest.clips[0], ...override }],
    };
    expect(parseTutorialClipManifest(broken)).toBeNull();
  });

  it("rejects another schema version and a non-list clips field", () => {
    expect(parseTutorialClipManifest({ ...validManifest, schema_version: 2 })).toBeNull();
    expect(parseTutorialClipManifest({ ...validManifest, clips: {} })).toBeNull();
    expect(parseTutorialClipManifest(null)).toBeNull();
  });
});

describe("resolveMediaUrl", () => {
  it("resolves paths relative to the manifest directory", () => {
    expect(resolveMediaUrl("klass.mp4")).toBe("/static/media/klassrumskartan/klass.mp4");
    expect(resolveMediaUrl("posters/klass.jpg")).toBe(
      "/static/media/klassrumskartan/posters/klass.jpg",
    );
    expect(resolveMediaUrl("/static/other.jpg")).toBe("/static/other.jpg");
  });
});

describe("loadTutorialClipManifest", () => {
  it("fetches once per app load without the HTTP cache and sorts section clips by order", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(validManifest));
    vi.stubGlobal("fetch", fetchMock);

    const state = useTutorialClipManifest();
    await loadTutorialClipManifest();
    await loadTutorialClipManifest();
    useTutorialClipManifest();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      TUTORIAL_CLIP_MANIFEST_URL,
      expect.objectContaining({ cache: "no-cache" }),
    );
    expect(state.loaded.value).toBe(true);
    expect(clipsForSection("planner_overview").map((clip) => clip.id)).toEqual([
      "klass",
      "klass-2",
    ]);
    expect(clipsForSection("planner_seating")).toEqual([]);
  });

  it("resolves a 404 to an empty, loaded manifest", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Not found", { status: 404 })));
    const state = useTutorialClipManifest();

    const result = await loadTutorialClipManifest();

    expect(result.clips).toEqual([]);
    expect(state.loaded.value).toBe(true);
  });

  it("resolves invalid JSON and network failures to an empty manifest", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{not json", { status: 200 })));
    expect((await loadTutorialClipManifest()).clips).toEqual([]);

    resetTutorialClipManifestCacheForTests();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    expect((await loadTutorialClipManifest()).clips).toEqual([]);
  });

  it("resolves a manifest that breaks the contract to an empty manifest", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ ...validManifest, schema_version: 2 })),
    );
    expect((await loadTutorialClipManifest()).clips).toEqual([]);
  });
});
