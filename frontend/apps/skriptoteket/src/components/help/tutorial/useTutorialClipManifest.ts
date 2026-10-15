/**
 * Klassrumskartan tutorial clip manifest state.
 *
 * Purpose:
 *   Load the clip manifest once per app load through the API layer and expose
 *   whether it has loaded and the clips of one planner section in manifest
 *   order. A missing or invalid manifest arrives as an empty manifest, so the
 *   planner shows no pop-up and no thumbnails.
 *
 * Relationships:
 *   - fetch and validation live in `api/tutorialClips.ts`
 *   - read by `TutorialClipThumbnails.vue` and `useTutorialFirstUse.ts`
 */

import { computed, shallowRef, type ComputedRef } from "vue";

import {
  EMPTY_TUTORIAL_CLIP_MANIFEST,
  fetchTutorialClipManifest,
  type TutorialClip,
  type TutorialClipManifest,
} from "../../../api/tutorialClips";

const manifest = shallowRef<TutorialClipManifest>(EMPTY_TUTORIAL_CLIP_MANIFEST);
const loaded = shallowRef(false);
let loadPromise: Promise<TutorialClipManifest> | null = null;

/** Starts the single manifest fetch for this app load and returns it. */
export function loadTutorialClipManifest(): Promise<TutorialClipManifest> {
  if (!loadPromise) {
    loadPromise = fetchTutorialClipManifest().then((result) => {
      manifest.value = result;
      loaded.value = true;
      return result;
    });
  }
  return loadPromise;
}

/** Returns the clips of one section sorted by their manifest order. */
export function clipsForSection(section: string): TutorialClip[] {
  return manifest.value.clips
    .filter((clip) => clip.section === section)
    .sort((left, right) => left.order - right.order);
}

export function useTutorialClipManifest(): {
  loaded: ComputedRef<boolean>;
  clipsForSection: (section: string) => TutorialClip[];
} {
  void loadTutorialClipManifest();
  return {
    loaded: computed(() => loaded.value),
    clipsForSection,
  };
}
