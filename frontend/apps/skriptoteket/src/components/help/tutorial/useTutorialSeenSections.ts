/**
 * Seen-state for the Klassrumskartan tutorial first-use dialog.
 *
 * Purpose:
 *   Remember which planner sections already showed their first-use dialog.
 *   Guests keep the list in this browser; signed-in users keep it on their
 *   profile through the classroom-planner settings endpoint.
 *
 * Relationships:
 *   - guest storage follows `classroomPlannerSmartPreferences.ts`
 *   - signed-in state reads the auth store profile loaded by app continuation
 *     and writes `PATCH /api/v1/profile/classroom-planner-settings`
 *   - read by `useTutorialFirstUse.ts`
 */

import { computed, ref, type ComputedRef } from "vue";

import { apiPatch } from "../../../api/client";
import type { components } from "../../../api/openapi";
import { useProfile } from "../../../composables/useProfile";
import { useAuthStore } from "../../../stores/auth";

export type TutorialHostMode = "authenticated" | "public";

export const GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY =
  "skriptoteket:classroom-planner:tutorial-seen-sections:v1";

export const CLASSROOM_PLANNER_SETTINGS_PATH = "/api/v1/profile/classroom-planner-settings";

type ProfileResponse = components["schemas"]["ProfileResponse"];
type UpdateClassroomPlannerSettingsRequest =
  components["schemas"]["UpdateClassroomPlannerSettingsRequest"];

export type TutorialSeenSections = {
  ready: ComputedRef<boolean>;
  isSeen: (section: string) => boolean;
  markSeen: (section: string) => void;
};

/** Reads a string list; anything else counts as an empty list. */
export function parseSeenSections(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((entry): entry is string => typeof entry === "string");
}

function union(current: readonly string[], section: string): string[] {
  return current.includes(section) ? [...current] : [...current, section];
}

function readGuestSeenSections(): string[] {
  try {
    const raw = window.localStorage.getItem(GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY);
    return raw ? parseSeenSections(JSON.parse(raw)) : [];
  } catch {
    return [];
  }
}

function writeGuestSeenSections(sections: readonly string[]): void {
  try {
    window.localStorage.setItem(
      GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY,
      JSON.stringify(sections),
    );
  } catch {
    // Storage can be full or blocked; the in-memory list still holds this visit.
  }
}

function useGuestSeenSections(): TutorialSeenSections {
  const seen = ref<string[]>(typeof window === "undefined" ? [] : readGuestSeenSections());
  return {
    ready: computed(() => true),
    isSeen: (section) => seen.value.includes(section),
    markSeen: (section) => {
      if (seen.value.includes(section)) {
        return;
      }
      seen.value = union(seen.value, section);
      writeGuestSeenSections(seen.value);
    },
  };
}

function useAuthenticatedSeenSections(): TutorialSeenSections {
  const auth = useAuthStore();
  const profileSeen = computed(() =>
    parseSeenSections(auth.profile?.classroom_planner_tutorial_seen_sections),
  );

  if (auth.profile === null) {
    // The planner route normally has the profile from app continuation; load it
    // once when it is missing. A failed load leaves the seen-state not ready.
    void useProfile()
      .load()
      .catch(() => undefined);
  }

  function writeProfileSeenSections(sections: string[]): void {
    if (auth.profile) {
      auth.profile = { ...auth.profile, classroom_planner_tutorial_seen_sections: sections };
    }
  }

  async function persist(sections: string[]): Promise<void> {
    try {
      const body = { tutorial_seen_sections: sections } satisfies UpdateClassroomPlannerSettingsRequest;
      const response = await apiPatch<ProfileResponse>(CLASSROOM_PLANNER_SETTINGS_PATH, body);
      const persisted = parseSeenSections(
        response?.profile?.classroom_planner_tutorial_seen_sections,
      );
      // Keep any section marked while the request was in flight.
      writeProfileSeenSections(
        profileSeen.value.reduce((merged, section) => union(merged, section), persisted),
      );
    } catch {
      // The optimistic local value stays for this visit; no retry.
    }
  }

  return {
    ready: computed(() => auth.profile !== null),
    isSeen: (section) => profileSeen.value.includes(section),
    markSeen: (section) => {
      if (profileSeen.value.includes(section)) {
        return;
      }
      const next = union(profileSeen.value, section);
      writeProfileSeenSections(next);
      void persist(next);
    },
  };
}

export function useTutorialSeenSections(hostMode: TutorialHostMode): TutorialSeenSections {
  return hostMode === "authenticated" ? useAuthenticatedSeenSections() : useGuestSeenSections();
}
