/**
 * Authenticated classroom planner Smart preference persistence lane.
 *
 * Purpose:
 *   Serializes profile-backed Smart preference writes so draft creation can
 *   wait for the teacher's latest explicit setting before asking the backend
 *   for a new draft seeded from profile state.
 *
 * Relationships:
 *   - consumed by `useClassroomState.ts`
 *   - writes through `classroomPlannerSmartPreferences.ts`
 *   - updates the auth profile snapshot after successful profile persistence
 */

import { computed, ref } from "vue";

import { useAuthStore } from "../../stores/auth";
import {
  type ClassroomPlannerSmartPreferenceKey,
  persistAuthenticatedClassroomPlannerSmartPreference,
} from "./classroomPlannerSmartPreferences";

type SmartPreferenceLaneResult =
  | { status: "saved" }
  | { status: "blocked"; reason: "error"; message: string };

const SMART_PREFERENCE_SAVE_ERROR_MESSAGE =
  "Kunde inte spara Smart-inställningen innan nytt utkast startades.";

export function useClassroomPlannerSmartPreferenceLane() {
  const auth = useAuthStore();
  const pendingWriteCount = ref(0);
  const lastErrorMessage = ref<string | null>(null);
  let writeTail: Promise<void> = Promise.resolve();

  function persistPreference(
    key: ClassroomPlannerSmartPreferenceKey,
    enabled: boolean,
  ): void {
    pendingWriteCount.value += 1;
    lastErrorMessage.value = null;

    const write = writeTail
      .catch(() => undefined)
      .then(async () => {
        const response = await persistAuthenticatedClassroomPlannerSmartPreference({
          [key]: enabled,
        });
        auth.user = response.user;
        auth.profile = response.profile;
      });

    writeTail = write;
    void write
      .catch((error: unknown) => {
        lastErrorMessage.value = error instanceof Error
          ? error.message
          : SMART_PREFERENCE_SAVE_ERROR_MESSAGE;
      })
      .finally(() => {
        pendingWriteCount.value = Math.max(0, pendingWriteCount.value - 1);
      });
  }

  async function flushPendingChanges(): Promise<SmartPreferenceLaneResult> {
    try {
      await writeTail;
      return { status: "saved" };
    } catch {
      return {
        status: "blocked",
        reason: "error",
        message: lastErrorMessage.value ?? SMART_PREFERENCE_SAVE_ERROR_MESSAGE,
      };
    }
  }

  return {
    isSaving: computed(() => pendingWriteCount.value > 0),
    persistPreference,
    flushPendingChanges,
  };
}
