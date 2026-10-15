/**
 * Seen-state for the Klassrumskartan tutorial first-use dialog.
 *
 * Purpose:
 *   Remember which planner sections already showed their first-use dialog.
 *   Guests keep the list in this browser; signed-in users keep it on their
 *   profile through the classroom-planner settings endpoint.
 *
 * Signed-in persistence lives in `stores/tutorialSeenSections.ts`: one write
 * chain per app load, so a gate that unmounts while its write is in flight
 * cannot race a gate mounted later. `persistence` reports the outcome.
 *
 * Relationships:
 *   - guest storage follows `views/apps/classroomPlannerSmartPreferences.ts`
 *   - signed-in state reads the auth store profile loaded by app continuation
 *     through `stores/tutorialSeenSections.ts`
 *   - read by `useTutorialFirstUse.ts`
 */

import { computed, ref, type ComputedRef } from "vue";

import type { TutorialSection } from "../../../api/tutorialClips";
import { useProfile } from "../../../composables/useProfile";
import { useAuthStore } from "../../../stores/auth";
import {
  unionOf,
  useTutorialSeenSectionsStore,
  type TutorialSeenPersistence,
} from "../../../stores/tutorialSeenSections";

export type TutorialHostMode = "authenticated" | "public";

export type { TutorialSeenPersistence };

export const GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY =
  "skriptoteket:classroom-planner:tutorial-seen-sections:v1";

export type TutorialSeenSections = {
  ready: ComputedRef<boolean>;
  isSeen: (section: string) => boolean;
  markSeen: (section: TutorialSection) => void;
  persistence: ComputedRef<TutorialSeenPersistence>;
  /** Sections dismissed in this page load that are not stored yet. */
  pendingSections: ComputedRef<readonly string[]>;
};

/** Reads a string list; anything else counts as an empty list. */
function parseSeenSections(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((entry): entry is string => typeof entry === "string");
}

function readGuestSeenSections(): string[] {
  try {
    const raw = window.localStorage.getItem(GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY);
    return raw ? parseSeenSections(JSON.parse(raw)) : [];
  } catch {
    return [];
  }
}

/** Returns whether the browser stored the list. */
function writeGuestSeenSections(sections: readonly string[]): boolean {
  try {
    window.localStorage.setItem(
      GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY,
      JSON.stringify(sections),
    );
    return true;
  } catch {
    return false;
  }
}

function useGuestSeenSections(): TutorialSeenSections {
  const seen = ref<string[]>(typeof window === "undefined" ? [] : readGuestSeenSections());
  const unsaved = ref<string[]>([]);
  return {
    ready: computed(() => true),
    isSeen: (section) => seen.value.includes(section),
    markSeen: (section) => {
      if (seen.value.includes(section)) {
        return;
      }
      seen.value = unionOf(seen.value, [section]);
      // Storage can be full or blocked; the in-memory list still holds this visit.
      unsaved.value = writeGuestSeenSections(seen.value) ? [] : unionOf(unsaved.value, [section]);
    },
    persistence: computed(() => (unsaved.value.length === 0 ? "confirmed" : "failed")),
    pendingSections: computed(() => unsaved.value),
  };
}

function useAuthenticatedSeenSections(): TutorialSeenSections {
  const auth = useAuthStore();
  const store = useTutorialSeenSectionsStore();

  if (auth.profile === null) {
    // The planner route normally has the profile from app continuation; load it
    // once when it is missing. A failed load leaves the seen-state not ready.
    void useProfile()
      .load()
      .catch(() => undefined);
  }

  return {
    ready: computed(() => store.ready),
    isSeen: (section) => store.isSeen(section),
    markSeen: (section) => store.markSeen(section),
    persistence: computed(() => store.persistence),
    pendingSections: computed(() => store.pending),
  };
}

export function useTutorialSeenSections(hostMode: TutorialHostMode): TutorialSeenSections {
  return hostMode === "authenticated" ? useAuthenticatedSeenSections() : useGuestSeenSections();
}
