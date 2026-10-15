/**
 * Seen-state for the Klassrumskartan tutorial first-use dialog.
 *
 * Purpose:
 *   Remember which planner sections already showed their first-use dialog.
 *   Guests keep the list in this browser; signed-in users keep it on their
 *   profile through the classroom-planner settings endpoint.
 *
 * Signed-in persistence:
 *   - The endpoint replaces the stored list with the list a request carries,
 *     so this host sends one write at a time. A dismissal made while a write
 *     is in flight queues one more write, which carries the full union of the
 *     confirmed and pending sections when it starts.
 *   - A section is confirmed only when an acknowledged response's profile list
 *     includes it. Until then it is pending: the dialog stays closed for this
 *     page load, but the auth profile only ever holds acknowledged server
 *     state.
 *   - A failed write shows a toast, keeps its sections pending and sends them
 *     again with the next write. `persistence` reports the outcome.
 *
 * Relationships:
 *   - guest storage follows `views/apps/classroomPlannerSmartPreferences.ts`
 *   - signed-in state reads the auth store profile loaded by app continuation
 *     and writes through `api/classroomPlannerSettings.ts`
 *   - read by `useTutorialFirstUse.ts`
 */

import { computed, ref, type ComputedRef } from "vue";

import { updateClassroomPlannerSettings } from "../../../api/classroomPlannerSettings";
import type { TutorialSection } from "../../../api/tutorialClips";
import { useProfile } from "../../../composables/useProfile";
import { useToast } from "../../../composables/useToast";
import { useAuthStore } from "../../../stores/auth";
import { TUTORIAL_COPY } from "./tutorialCopy";

export type TutorialHostMode = "authenticated" | "public";

/** Whether every dismissed section is stored, is still being stored, or failed to store. */
export type TutorialSeenPersistence = "confirmed" | "pending" | "failed";

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

function unionOf(...lists: ReadonlyArray<readonly string[]>): string[] {
  const merged: string[] = [];
  for (const list of lists) {
    for (const section of list) {
      if (!merged.includes(section)) {
        merged.push(section);
      }
    }
  }
  return merged;
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
  const toast = useToast();

  if (auth.profile === null) {
    // The planner route normally has the profile from app continuation; load it
    // once when it is missing. A failed load leaves the seen-state not ready.
    void useProfile()
      .load()
      .catch(() => undefined);
  }

  const profileSeen = computed<readonly string[]>(
    () => auth.profile?.classroom_planner_tutorial_seen_sections ?? [],
  );
  // Sections this host's acknowledged writes returned. Another profile write,
  // such as a Smart preference save, can replace `auth.profile` with a response
  // read before this host's write committed; these stay confirmed regardless.
  const acknowledged = ref<string[]>([]);
  const pending = ref<string[]>([]);
  const lastWriteFailed = ref(false);
  let writing = false;
  let writeQueued = false;

  function isConfirmed(section: string): boolean {
    return profileSeen.value.includes(section) || acknowledged.value.includes(section);
  }

  async function drainWrites(): Promise<void> {
    writing = true;
    try {
      while (writeQueued) {
        writeQueued = false;
        lastWriteFailed.value = false;
        const sections = unionOf(profileSeen.value, acknowledged.value, pending.value);
        try {
          const response = await updateClassroomPlannerSettings({
            tutorial_seen_sections: sections,
          });
          auth.user = response.user;
          auth.profile = response.profile;
          const stored = response.profile.classroom_planner_tutorial_seen_sections ?? [];
          acknowledged.value = unionOf(acknowledged.value, stored);
          pending.value = pending.value.filter((section) => !stored.includes(section));
        } catch {
          lastWriteFailed.value = true;
          toast.failure(TUTORIAL_COPY.seenSaveFailed);
        }
      }
    } finally {
      writing = false;
    }
  }

  function queueWrite(): void {
    writeQueued = true;
    if (!writing) {
      void drainWrites();
    }
  }

  return {
    ready: computed(() => auth.profile !== null),
    isSeen: (section) => isConfirmed(section) || pending.value.includes(section),
    markSeen: (section) => {
      if (isConfirmed(section) || pending.value.includes(section)) {
        return;
      }
      pending.value = [...pending.value, section];
      queueWrite();
    },
    persistence: computed(() => {
      if (pending.value.length === 0) {
        return "confirmed";
      }
      return lastWriteFailed.value ? "failed" : "pending";
    }),
    pendingSections: computed(() => pending.value),
  };
}

export function useTutorialSeenSections(hostMode: TutorialHostMode): TutorialSeenSections {
  return hostMode === "authenticated" ? useAuthenticatedSeenSections() : useGuestSeenSections();
}
