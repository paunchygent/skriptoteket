/**
 * Signed-in seen-state for the Klassrumskartan tutorial first-use dialog.
 *
 * Purpose:
 *   Hold the one write chain per app load that stores which planner sections
 *   already showed their first-use dialog on the user's profile. The chain
 *   lives in a store, not in a component, because the planner gate mounts and
 *   unmounts per section while an earlier write may still be in flight.
 *
 * Persistence rules:
 *   - The settings endpoint replaces the stored list with the list a request
 *     carries, so this app sends one write at a time. A dismissal made while a
 *     write is in flight queues one more write, which carries the full union of
 *     the confirmed and pending sections when it starts.
 *   - A section is confirmed only when an acknowledged response's profile list
 *     includes it. Until then it is pending: the dialog stays closed for this
 *     page load, but the auth profile only ever holds acknowledged server state.
 *   - A failed write shows a toast, keeps its sections pending and sends them
 *     again with the next write.
 *   - The chain belongs to the signed-in user it started for. A response that
 *     arrives after logout or after another user signed in is discarded, so
 *     it can never put a cleared session back into the auth store, and the
 *     chain state resets whenever the signed-in user changes.
 *
 * Relationships:
 *   - writes through `api/classroomPlannerSettings.ts`
 *   - reads and updates the auth store profile loaded by app continuation
 *   - consumed by `components/help/tutorial/useTutorialSeenSections.ts`
 */

import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";

import { updateClassroomPlannerSettings } from "../api/classroomPlannerSettings";
import type { TutorialSection } from "../api/tutorialClips";
import { TUTORIAL_COPY } from "../components/help/tutorial/tutorialCopy";
import { useToast } from "../composables/useToast";
import { useAuthStore } from "./auth";

/** Whether every dismissed section is stored, is still being stored, or failed to store. */
export type TutorialSeenPersistence = "confirmed" | "pending" | "failed";

export function unionOf(...lists: ReadonlyArray<readonly string[]>): string[] {
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

export const useTutorialSeenSectionsStore = defineStore("tutorialSeenSections", () => {
  const auth = useAuthStore();
  const toast = useToast();

  const profileSeen = computed<readonly string[]>(
    () => auth.profile?.classroom_planner_tutorial_seen_sections ?? [],
  );
  // Sections this app's acknowledged writes returned. Another profile write,
  // such as a Smart preference save, can replace `auth.profile` with a response
  // read before this write committed; these stay confirmed regardless.
  const acknowledged = ref<string[]>([]);
  const pending = ref<string[]>([]);
  const lastWriteFailed = ref(false);
  let writing = false;
  let writeQueued = false;

  const ready = computed(() => auth.profile !== null);
  // The profile is the signed-in identity this chain writes for; `clear()` nulls it.
  const currentUserId = computed(() => auth.profile?.user_id ?? null);

  function resetChain(): void {
    acknowledged.value = [];
    pending.value = [];
    lastWriteFailed.value = false;
    writeQueued = false;
  }

  // Logout, a 401 clear or a different user signing in ends this chain.
  watch(currentUserId, (next, previous) => {
    if (next !== previous) {
      resetChain();
    }
  });

  function isConfirmed(section: string): boolean {
    return profileSeen.value.includes(section) || acknowledged.value.includes(section);
  }

  function isSeen(section: string): boolean {
    return isConfirmed(section) || pending.value.includes(section);
  }

  async function drainWrites(): Promise<void> {
    writing = true;
    try {
      while (writeQueued) {
        writeQueued = false;
        lastWriteFailed.value = false;
        const writerId = currentUserId.value;
        if (writerId === null) {
          // Nothing to write without a session; the identity watch already
          // cleared the chain.
          continue;
        }
        const sections = unionOf(profileSeen.value, acknowledged.value, pending.value);
        try {
          const response = await updateClassroomPlannerSettings({
            tutorial_seen_sections: sections,
          });
          if (currentUserId.value !== writerId) {
            // The session ended or changed while this write was in flight. The
            // response belongs to the old session and must not revive it; the
            // identity watch already reset the chain, and any write the new
            // session queued meanwhile runs on the next loop pass.
            continue;
          }
          auth.user = response.user;
          auth.profile = response.profile;
          const stored = response.profile.classroom_planner_tutorial_seen_sections ?? [];
          acknowledged.value = unionOf(acknowledged.value, stored);
          pending.value = pending.value.filter((section) => !stored.includes(section));
        } catch {
          if (currentUserId.value !== writerId) {
            continue;
          }
          lastWriteFailed.value = true;
          toast.failure(TUTORIAL_COPY.seenSaveFailed);
        }
      }
    } finally {
      writing = false;
    }
  }

  function markSeen(section: TutorialSection): void {
    if (isSeen(section)) {
      return;
    }
    pending.value = [...pending.value, section];
    writeQueued = true;
    if (!writing) {
      void drainWrites();
    }
  }

  const persistence = computed<TutorialSeenPersistence>(() => {
    if (pending.value.length === 0) {
      return "confirmed";
    }
    return lastWriteFailed.value ? "failed" : "pending";
  });

  return { ready, pending, persistence, isSeen, markSeen };
});
