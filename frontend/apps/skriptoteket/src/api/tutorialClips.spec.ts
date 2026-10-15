import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchTutorialClipManifest, resolveTutorialMediaUrl } from "./tutorialClips";

const MANIFEST_URL = "/static/media/klassrumskartan/clips.json";

const validManifest = {
  schema_version: 1,
  app: "classroom.group-seating-studio",
  clips: [
    {
      id: "klass",
      section: "planner_overview",
      order: 1,
      title: "Klass",
      duration_seconds: 8.5,
      video: "klass.mp4",
      poster: "posters/klass.jpg",
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

function withClip(override: Record<string, unknown>): unknown {
  return { ...validManifest, clips: [{ ...validManifest.clips[1], ...override }] };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Serves `body` as the manifest and returns what the boundary admits. */
async function admit(body: unknown) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body)));
  return await fetchTutorialClipManifest();
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchTutorialClipManifest", () => {
  it("fetches the manifest URL without the HTTP cache and admits the contract", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(validManifest));
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchTutorialClipManifest();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      MANIFEST_URL,
      expect.objectContaining({ cache: "no-cache", credentials: "same-origin" }),
    );
    expect(result.app).toBe("classroom.group-seating-studio");
    expect(result.clips.map((clip) => clip.id)).toEqual(["klass", "regler"]);
    expect(result.clips[0]).not.toHaveProperty("published_at");
  });

  it.each([
    ["a 404", () => Promise.resolve(new Response("Not found", { status: 404 }))],
    ["invalid JSON", () => Promise.resolve(new Response("{not json", { status: 200 }))],
    ["a network failure", () => Promise.reject(new TypeError("offline"))],
  ])("resolves %s to an empty manifest", async (_label, respond) => {
    vi.stubGlobal("fetch", vi.fn(respond));

    expect((await fetchTutorialClipManifest()).clips).toEqual([]);
  });

  it.each([
    ["another app", { app: "other-app" }],
    ["a missing app", { app: undefined }],
    ["another schema version", { schema_version: 2 }],
    ["a string schema version", { schema_version: "1" }],
    ["a non-list clips field", { clips: {} }],
  ])("resolves a manifest with %s to an empty manifest", async (_label, override) => {
    expect((await admit({ ...validManifest, ...override })).clips).toEqual([]);
  });

  it.each([null, [validManifest], "manifest"])(
    "resolves the non-object document %j to an empty manifest",
    async (body) => {
      expect((await admit(body)).clips).toEqual([]);
    },
  );

  it.each([
    ["an unknown section", { section: "planner_share" }],
    ["an empty id", { id: "" }],
    ["an empty title", { title: "" }],
    ["a fractional order", { order: 1.5 }],
    ["a string order", { order: "1" }],
    ["a string duration", { duration_seconds: "8" }],
    ["a missing poster", { poster: undefined }],
    ["an empty video path", { video: "" }],
    ["a malformed absolute video URL", { video: "http://[" }],
    ["an absolute https video URL", { video: "https://cdn.example/klass.mp4" }],
    ["a javascript: poster", { poster: "javascript:alert(1)" }],
    ["a data: poster", { poster: "data:image/png;base64,AAAA" }],
    ["a root-absolute video path", { video: "/static/other.mp4" }],
    ["a protocol-relative poster", { poster: "//cdn.example/klass.jpg" }],
    ["a backslash path", { poster: "\\\\cdn.example\\klass.jpg" }],
    ["a parent-directory video path", { video: "../klass.mp4" }],
    ["an inner parent-directory segment", { video: "clips/../../klass.mp4" }],
  ])("rejects the whole manifest for %s", async (_label, override) => {
    expect((await admit(withClip(override))).clips).toEqual([]);
  });

  it("rejects non-finite durations, which JSON cannot carry but a parsed document can", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => withClip({ duration_seconds: Number.POSITIVE_INFINITY }),
      }),
    );
    expect((await fetchTutorialClipManifest()).clips).toEqual([]);
  });

  it("rejects the whole manifest when one of several clips is invalid", async () => {
    const broken = {
      ...validManifest,
      clips: [...validManifest.clips, { ...validManifest.clips[1], id: "x", video: "/x.mp4" }],
    };
    expect((await admit(broken)).clips).toEqual([]);
  });
});

describe("resolveTutorialMediaUrl", () => {
  it.each(["klass.mp4", "posters/klass.jpg", "./klass.mp4", "klass..v2.mp4", "a b/klass.mp4"])(
    "admits %s and resolves it under the manifest directory without throwing",
    async (path) => {
      const [clip] = (await admit(withClip({ video: path, poster: path }))).clips;

      expect(clip?.video).toBe(path);
      expect(() => resolveTutorialMediaUrl(path)).not.toThrow();
      expect(resolveTutorialMediaUrl(path)).toBe(`/static/media/klassrumskartan/${path}`);
    },
  );
});
