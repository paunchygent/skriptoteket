/**
 * Klassrumskartan public guest snapshot status controller.
 *
 * This composable keeps the public shell focused on one small responsibility:
 * reporting whether the browser-owned guest workspace foundation is missing,
 * ready, expired, or broken, while the richer guest planner experience lands
 * in later EPIC-32 slices.
 */

import { onMounted, ref } from "vue";

import {
  createClassroomPlannerGuestStorage,
} from "./classroomPlannerGuestStorage";
import type { ClassroomPlannerGuestSnapshotSummary } from "./classroomPlannerGuestSnapshot";

export type ClassroomPlannerGuestSnapshotShellStatus =
  | "idle"
  | "loading"
  | "missing"
  | "ready"
  | "expired"
  | "error";

type ClassroomPlannerGuestStorageAdapter = ReturnType<typeof createClassroomPlannerGuestStorage>;

export function useClassroomPlannerGuestSnapshotStatus(options?: {
  enabled?: boolean;
  guestStorage?: ClassroomPlannerGuestStorageAdapter;
  guestStorageFactory?: () => ClassroomPlannerGuestStorageAdapter;
}) {
  const enabled = options?.enabled ?? true;
  let guestStorage: ClassroomPlannerGuestStorageAdapter | null = options?.guestStorage ?? null;

  const status = ref<ClassroomPlannerGuestSnapshotShellStatus>(enabled ? "loading" : "idle");
  const summary = ref<ClassroomPlannerGuestSnapshotSummary | null>(null);
  const errorMessage = ref<string | null>(null);
  const isWorking = ref(false);

  function resolveGuestStorage(): ClassroomPlannerGuestStorageAdapter {
    if (!guestStorage) {
      guestStorage = options?.guestStorageFactory?.() ?? createClassroomPlannerGuestStorage();
    }
    return guestStorage;
  }

  async function refresh(): Promise<void> {
    if (!enabled) {
      status.value = "idle";
      summary.value = null;
      errorMessage.value = null;
      return;
    }

    status.value = "loading";
    errorMessage.value = null;
    try {
      const result = await resolveGuestStorage().loadCurrentSnapshot();
      status.value = result.status;
      summary.value = result.summary;
    } catch (error: unknown) {
      status.value = "error";
      summary.value = null;
      errorMessage.value = error instanceof Error
        ? error.message
        : "Det gick inte att läsa den lokala gästarbetsytan.";
    }
  }

  async function initializeGuestWorkspace(): Promise<void> {
    if (!enabled || isWorking.value) {
      return;
    }

    isWorking.value = true;
    errorMessage.value = null;
    try {
      const result = await resolveGuestStorage().initializeEmptySnapshot();
      status.value = result.status;
      summary.value = result.summary;
    } catch (error: unknown) {
      status.value = "error";
      errorMessage.value = error instanceof Error
        ? error.message
        : "Det gick inte att initiera den lokala gästarbetsytan.";
    } finally {
      isWorking.value = false;
    }
  }

  async function clearGuestWorkspace(): Promise<void> {
    if (!enabled || isWorking.value) {
      return;
    }

    isWorking.value = true;
    errorMessage.value = null;
    try {
      await resolveGuestStorage().clearCurrentSnapshot();
      status.value = "missing";
      summary.value = null;
    } catch (error: unknown) {
      status.value = "error";
      errorMessage.value = error instanceof Error
        ? error.message
        : "Det gick inte att rensa den lokala gästarbetsytan.";
    } finally {
      isWorking.value = false;
    }
  }

  onMounted(() => {
    void refresh();
  });

  return {
    status,
    summary,
    errorMessage,
    isWorking,
    refresh,
    initializeGuestWorkspace,
    clearGuestWorkspace,
  };
}
