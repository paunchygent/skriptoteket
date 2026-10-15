/**
 * Klassrumskartan tutorial clip manifest.
 *
 * Purpose:
 *   Load the clip manifest published to the media directory once per app load,
 *   validate it at the boundary, and expose the clips of one planner section.
 *   A missing or invalid manifest resolves to an empty manifest, so the planner
 *   shows no pop-up and no thumbnails and the written help stays.
 *
 * Relationships:
 *   - read by `TutorialClipThumbnails.vue` and `useTutorialFirstUse.ts`
 *   - the manifest contract is story ST-SKRIPT-08-36 D15
 */

import { computed, shallowRef, type ComputedRef } from "vue";

export const TUTORIAL_CLIP_MANIFEST_URL = "/static/media/klassrumskartan/clips.json";

export const TUTORIAL_SECTIONS = [
  "planner_overview",
  "planner_seating",
  "planner_grouping",
  "planner_rules",
] as const;

export type TutorialSection = (typeof TUTORIAL_SECTIONS)[number];

export type TutorialClip = {
  id: string;
  section: TutorialSection;
  order: number;
  title: string;
  duration_seconds: number;
  video: string;
  poster: string;
};

export type TutorialClipManifest = {
  schema_version: 1;
  app: string;
  clips: TutorialClip[];
};

const EMPTY_MANIFEST: TutorialClipManifest = Object.freeze({
  schema_version: 1,
  app: "",
  clips: [],
}) as TutorialClipManifest;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function isTutorialSection(value: unknown): value is TutorialSection {
  return typeof value === "string" && (TUTORIAL_SECTIONS as readonly string[]).includes(value);
}

function parseClip(value: unknown): TutorialClip | null {
  if (!isRecord(value)) {
    return null;
  }
  const { id, section, order, title, duration_seconds, video, poster } = value;
  if (
    !isNonEmptyString(id) ||
    !isTutorialSection(section) ||
    !isFiniteNumber(order) ||
    !isNonEmptyString(title) ||
    !isFiniteNumber(duration_seconds) ||
    !isNonEmptyString(video) ||
    !isNonEmptyString(poster)
  ) {
    return null;
  }
  // Extra fields such as `published_at` are tolerated and dropped.
  return { id, section, order, title, duration_seconds, video, poster };
}

/**
 * Validates a manifest document. Returns null when the document breaks the
 * contract; one invalid clip invalidates the whole manifest.
 */
export function parseTutorialClipManifest(value: unknown): TutorialClipManifest | null {
  if (!isRecord(value) || value.schema_version !== 1 || typeof value.app !== "string") {
    return null;
  }
  if (!Array.isArray(value.clips)) {
    return null;
  }
  const clips: TutorialClip[] = [];
  for (const rawClip of value.clips) {
    const clip = parseClip(rawClip);
    if (!clip) {
      return null;
    }
    clips.push(clip);
  }
  return { schema_version: 1, app: value.app, clips };
}

/** Resolves a manifest-relative media path against the manifest's directory. */
export function resolveMediaUrl(relative: string): string {
  const base = new URL(TUTORIAL_CLIP_MANIFEST_URL, "https://media.invalid");
  const resolved = new URL(relative, base);
  return resolved.origin === base.origin
    ? `${resolved.pathname}${resolved.search}`
    : resolved.href;
}

const manifest = shallowRef<TutorialClipManifest>(EMPTY_MANIFEST);
const loaded = shallowRef(false);
let loadPromise: Promise<TutorialClipManifest> | null = null;

async function fetchManifest(): Promise<TutorialClipManifest> {
  try {
    const response = await fetch(TUTORIAL_CLIP_MANIFEST_URL, {
      cache: "no-cache",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      return EMPTY_MANIFEST;
    }
    return parseTutorialClipManifest(await response.json()) ?? EMPTY_MANIFEST;
  } catch {
    return EMPTY_MANIFEST;
  }
}

/** Starts the single manifest fetch for this app load and returns it. */
export function loadTutorialClipManifest(): Promise<TutorialClipManifest> {
  if (!loadPromise) {
    loadPromise = fetchManifest().then((result) => {
      manifest.value = result;
      loaded.value = true;
      return result;
    });
  }
  return loadPromise;
}

function sortClips(clips: TutorialClip[]): TutorialClip[] {
  return [...clips].sort((left, right) => left.order - right.order);
}

/** Returns the clips of one section in manifest order. */
export function clipsForSection(section: string): TutorialClip[] {
  return sortClips(manifest.value.clips.filter((clip) => clip.section === section));
}

export function useTutorialClipManifest(): {
  loaded: ComputedRef<boolean>;
  manifest: ComputedRef<TutorialClipManifest>;
  clipsForSection: (section: string) => TutorialClip[];
} {
  void loadTutorialClipManifest();
  return {
    loaded: computed(() => loaded.value),
    manifest: computed(() => manifest.value),
    clipsForSection,
  };
}

/** Test-only reset of the module-level manifest cache. */
export function resetTutorialClipManifestCacheForTests(): void {
  manifest.value = EMPTY_MANIFEST;
  loaded.value = false;
  loadPromise = null;
}
