import { computed, ref } from "vue";

import type { ClassWorkspaceSummary } from "../classroomPlannerTypes";

type HistoryKind = "grouping" | "seating";

/** Owns the account-only history drawer selection, labels and lifecycle guards. */
export function usePlannerWorkspaceHistory(options: {
  summary: () => ClassWorkspaceSummary | null;
  seatingBusy: () => boolean;
  openDraft: (kind: HistoryKind, draftId: string) => void;
  deleteDraft: (kind: HistoryKind, draftId: string) => void;
}) {
  const openHistoryDrawerKind = ref<HistoryKind | null>(null);
  const isSeating = computed(() => openHistoryDrawerKind.value === "seating");
  const isHistoryDrawerOpen = computed(() => openHistoryDrawerKind.value !== null);
  const historyDrawerTitle = computed(() => isSeating.value ? "Sittplatser" : "Grupper");
  const historyDrawerActiveSummary = computed(() => isSeating.value
    ? options.summary()?.active_seating_draft ?? null
    : options.summary()?.active_grouping_draft ?? null);
  const historyDrawerSummaries = computed(() => isSeating.value
    ? options.summary()?.seating_history ?? []
    : options.summary()?.grouping_history ?? []);
  const historyDrawerEmptyLabel = computed(() => isSeating.value
    ? "Ingen sitthistorik ännu." : "Ingen grupphistorik ännu.");
  const historyDrawerActiveLabel = computed(() => isSeating.value
    ? "Aktuellt sittschema" : "Aktuellt grupputkast");
  const historyDrawerLabel = computed(() => isSeating.value
    ? "Tidigare sittscheman" : "Tidigare grupputkast");

  function openGroupingHistoryDrawer(): void {
    openHistoryDrawerKind.value = "grouping";
  }

  function openSeatingHistoryDrawer(): void {
    if (!options.seatingBusy()) {
      openHistoryDrawerKind.value = "seating";
    }
  }

  function closeHistoryDrawer(): void {
    openHistoryDrawerKind.value = null;
  }

  function openHistoryDraft(kind: HistoryKind, draftId: string): void {
    if (kind === "seating" && options.seatingBusy()) {
      return;
    }
    closeHistoryDrawer();
    options.openDraft(kind, draftId);
  }

  function deleteHistoryDraft(kind: HistoryKind, draftId: string): void {
    if (kind === "seating" && options.seatingBusy()) {
      return;
    }
    closeHistoryDrawer();
    options.deleteDraft(kind, draftId);
  }

  return {
    openHistoryDrawerKind,
    isHistoryDrawerOpen,
    historyDrawerTitle,
    historyDrawerActiveSummary,
    historyDrawerSummaries,
    historyDrawerEmptyLabel,
    historyDrawerActiveLabel,
    historyDrawerLabel,
    openGroupingHistoryDrawer,
    openSeatingHistoryDrawer,
    closeHistoryDrawer,
    openGroupingHistoryDraft: (draftId: string) => openHistoryDraft("grouping", draftId),
    openSeatingHistoryDraft: (draftId: string) => openHistoryDraft("seating", draftId),
    deleteGroupingHistoryDraft: (draftId: string) => deleteHistoryDraft("grouping", draftId),
    deleteSeatingHistoryDraft: (draftId: string) => deleteHistoryDraft("seating", draftId),
  };
}
