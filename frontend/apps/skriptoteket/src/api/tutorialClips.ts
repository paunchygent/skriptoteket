/**
 * Klassrumskartan tutorial clip manifest API client.
 *
 * Purpose:
 *   Fetch the clip manifest published to the media directory and validate it
 *   at the boundary with a Zod schema. A missing manifest, a
 *   non-OK response, invalid JSON or a manifest that breaks the contract
 *   resolves to an empty manifest, so the planner shows no pop-up and no
 *   thumbnails and the written help stays.
 *
 * Contract (story ST-SKRIPT-08-36 D15):
 *   `schema_version` 1, `app` `classroom.group-seating-studio`, and `clips[]`
 *   with `id`, `section` (one of the four planner sections), integer `order`,
 *   `title`, finite `duration_seconds`, and `video` and `poster` as paths
 *   relative to the manifest. Extra fields are dropped; one invalid clip
 *   invalidates the whole manifest.
 *
 * Relationships:
 *   - the once-per-app-load cache lives in
 *     `components/help/tutorial/useTutorialClipManifest.ts`
 *   - `resolveTutorialMediaUrl` is used by the tutorial dialog and thumbnails
 */

import { z } from "zod";

const TUTORIAL_CLIP_MANIFEST_URL = "/static/media/klassrumskartan/clips.json";

const TUTORIAL_MEDIA_DIRECTORY = TUTORIAL_CLIP_MANIFEST_URL.slice(
  0,
  TUTORIAL_CLIP_MANIFEST_URL.lastIndexOf("/") + 1,
);

const TUTORIAL_CLIP_APP = "classroom.group-seating-studio";

const TUTORIAL_SECTIONS = [
  "planner_overview",
  "planner_seating",
  "planner_grouping",
  "planner_rules",
] as const;

const URL_SCHEME_PATTERN = /^[A-Za-z][A-Za-z0-9+.-]*:/;

/**
 * Accepts a non-empty path relative to the manifest directory. Rejects
 * absolute URLs and any scheme, root-absolute and protocol-relative paths,
 * backslashes (URL parsers read them as slashes) and `..` segments.
 */
function isManifestRelativeMediaPath(value: string): boolean {
  return (
    value.length > 0
    && !URL_SCHEME_PATTERN.test(value)
    && !value.startsWith("/")
    && !value.includes("\\")
    && !value.split("/").includes("..")
  );
}

const tutorialSectionSchema = z.enum(TUTORIAL_SECTIONS);

const manifestRelativeMediaPathSchema = z
  .string()
  .refine(isManifestRelativeMediaPath, { error: "Expected a path relative to the manifest." });

const tutorialClipSchema = z.object({
  id: z.string().min(1),
  section: tutorialSectionSchema,
  order: z.int(),
  title: z.string().min(1),
  // z.number() admits finite numbers only.
  duration_seconds: z.number(),
  video: manifestRelativeMediaPathSchema,
  poster: manifestRelativeMediaPathSchema,
});

/** The manifest contract; unknown keys such as `published_at` are stripped. */
const tutorialClipManifestSchema = z.object({
  schema_version: z.literal(1),
  app: z.literal(TUTORIAL_CLIP_APP),
  clips: z.array(tutorialClipSchema),
});

export type TutorialSection = z.infer<typeof tutorialSectionSchema>;
export type TutorialClipManifest = z.infer<typeof tutorialClipManifestSchema>;
export type TutorialClip = TutorialClipManifest["clips"][number];

export const EMPTY_TUTORIAL_CLIP_MANIFEST: TutorialClipManifest = Object.freeze({
  schema_version: 1,
  app: TUTORIAL_CLIP_APP,
  clips: [],
}) as TutorialClipManifest;

export function isTutorialSection(value: unknown): value is TutorialSection {
  return tutorialSectionSchema.safeParse(value).success;
}

/** Validates a manifest document; returns null when it breaks the contract. */
function parseTutorialClipManifest(value: unknown): TutorialClipManifest | null {
  const result = tutorialClipManifestSchema.safeParse(value);
  return result.success ? result.data : null;
}

/** Returns the same-origin URL of a manifest-relative media path. */
export function resolveTutorialMediaUrl(path: string): string {
  return `${TUTORIAL_MEDIA_DIRECTORY}${path}`;
}

/** Fetches and validates the manifest; every failure yields the empty manifest. */
export async function fetchTutorialClipManifest(): Promise<TutorialClipManifest> {
  try {
    const response = await fetch(TUTORIAL_CLIP_MANIFEST_URL, {
      cache: "no-cache",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      return EMPTY_TUTORIAL_CLIP_MANIFEST;
    }
    return parseTutorialClipManifest(await response.json()) ?? EMPTY_TUTORIAL_CLIP_MANIFEST;
  } catch {
    return EMPTY_TUTORIAL_CLIP_MANIFEST;
  }
}
