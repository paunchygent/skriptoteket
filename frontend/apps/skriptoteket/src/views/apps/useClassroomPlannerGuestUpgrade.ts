/**
 * Klassrumskartan authenticated guest-upgrade gate.
 *
 * This composable blocks authenticated planner bootstrap when a local guest
 * snapshot exists, previews the import boundary, and then lets the user
 * import, postpone, or discard without leaking storage and API concerns into
 * the entry view.
 */

import { computed, onMounted, ref } from "vue";

import { createClassroomPlannerGuestStorage } from "./classroomPlannerGuestStorage";
import {
  runClassroomPlannerGuestUpgrade,
  type ClassroomPlannerGuestUpgradeReceipt,
} from "./classroomPlannerGuestUpgradeApi";
import type {
  ClassroomPlannerGuestSnapshot,
  ClassroomPlannerGuestSnapshotSummary,
} from "./classroomPlannerGuestSnapshot";

type ClassroomPlannerGuestStorageAdapter = ReturnType<typeof createClassroomPlannerGuestStorage>;
type GuestUpgradeGateState = "allowed" | "checking" | "previewing" | "prompt" | "committing";

function buildConflictErrorMessage(receipt: ClassroomPlannerGuestUpgradeReceipt): string {
  if (receipt.conflicted.length === 0) {
    return "Allt gick inte att spara.";
  }
  return "Allt gick inte att spara. Det som blev kvar finns fortfarande i den här webbläsaren.";
}

export function useClassroomPlannerGuestUpgrade(options?: {
  enabled?: boolean;
  guestStorage?: ClassroomPlannerGuestStorageAdapter;
  guestStorageFactory?: () => ClassroomPlannerGuestStorageAdapter;
}) {
  const enabled = options?.enabled ?? true;
  let guestStorage: ClassroomPlannerGuestStorageAdapter | null = options?.guestStorage ?? null;

  const gateState = ref<GuestUpgradeGateState>(enabled ? "checking" : "allowed");
  const snapshot = ref<ClassroomPlannerGuestSnapshot | null>(null);
  const summary = ref<ClassroomPlannerGuestSnapshotSummary | null>(null);
  const previewReceipt = ref<ClassroomPlannerGuestUpgradeReceipt | null>(null);
  const lastReceipt = ref<ClassroomPlannerGuestUpgradeReceipt | null>(null);
  const errorMessage = ref<string | null>(null);
  const plannerRefreshKey = ref(0);

  function resolveGuestStorage(): ClassroomPlannerGuestStorageAdapter {
    if (!guestStorage) {
      guestStorage = options?.guestStorageFactory?.() ?? createClassroomPlannerGuestStorage();
    }
    return guestStorage;
  }

  async function initialize(): Promise<void> {
    if (!enabled) {
      gateState.value = "allowed";
      return;
    }

    gateState.value = "checking";
    errorMessage.value = null;
    try {
      const result = await resolveGuestStorage().loadCurrentSnapshot();
      if (result.status !== "ready" || !result.snapshot) {
        snapshot.value = null;
        summary.value = result.summary;
        gateState.value = "allowed";
        return;
      }

      snapshot.value = result.snapshot;
      summary.value = result.summary;
      await previewCurrentSnapshot();
    } catch (error: unknown) {
      snapshot.value = null;
      summary.value = null;
      gateState.value = "allowed";
      errorMessage.value = error instanceof Error
        ? error.message
        : "Det gick inte att läsa lokal gästarbetsyta.";
    }
  }

  async function previewCurrentSnapshot(): Promise<void> {
    if (!snapshot.value) {
      gateState.value = "allowed";
      return;
    }

    gateState.value = "previewing";
    errorMessage.value = null;
    try {
      previewReceipt.value = await runClassroomPlannerGuestUpgrade({
        mode: "preview",
        snapshot: snapshot.value,
      });
      gateState.value = "prompt";
    } catch (error: unknown) {
      previewReceipt.value = null;
      gateState.value = "prompt";
      errorMessage.value = error instanceof Error
        ? error.message
        : "Det gick inte att förhandsgranska importen av gästarbetsytan.";
    }
  }

  async function importGuestWorkspace(): Promise<void> {
    if (!snapshot.value) {
      gateState.value = "allowed";
      return;
    }

    gateState.value = "committing";
    errorMessage.value = null;
    try {
      const commitReceipt = await runClassroomPlannerGuestUpgrade({
        mode: "commit",
        snapshot: snapshot.value,
      });
      if (commitReceipt.conflicted.length > 0) {
        lastReceipt.value = null;
        previewReceipt.value = commitReceipt;
        gateState.value = "prompt";
        errorMessage.value = buildConflictErrorMessage(commitReceipt);
        return;
      }

      lastReceipt.value = commitReceipt;
      await resolveGuestStorage().clearCurrentSnapshot();
      snapshot.value = null;
      summary.value = null;
      previewReceipt.value = null;
      plannerRefreshKey.value += 1;
      gateState.value = "allowed";
    } catch (error: unknown) {
      gateState.value = "prompt";
      errorMessage.value = error instanceof Error
        ? error.message
        : "Det gick inte att importera gästarbetsytan.";
    }
  }

  function postponeGuestWorkspace(): void {
    gateState.value = "allowed";
  }

  function dismissLastReceiptSummary(): void {
    lastReceipt.value = null;
  }

  async function discardGuestWorkspace(): Promise<void> {
    errorMessage.value = null;
    await resolveGuestStorage().clearCurrentSnapshot();
    snapshot.value = null;
    summary.value = null;
    previewReceipt.value = null;
    gateState.value = "allowed";
  }

  onMounted(() => {
    void initialize();
  });

  return {
    gateState,
    snapshot,
    summary,
    previewReceipt,
    lastReceipt,
    errorMessage,
    plannerRefreshKey,
    isBlocking: computed(
      () =>
        enabled &&
        (gateState.value === "checking"
          || gateState.value === "previewing"
          || gateState.value === "committing"),
    ),
    shouldShowPrompt: computed(
      () => enabled && snapshot.value !== null && gateState.value === "prompt",
    ),
    importGuestWorkspace,
    postponeGuestWorkspace,
    dismissLastReceiptSummary,
    discardGuestWorkspace,
  };
}
