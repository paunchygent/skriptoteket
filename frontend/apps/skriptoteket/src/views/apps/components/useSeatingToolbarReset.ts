import { computed, ref } from "vue";

/** Owns confirmation state and assignment guards for resetting the active seating draft. */
export function useSeatingToolbarReset(options: {
  seatingLifecycleBusy: () => boolean;
  workspaceBusy: () => boolean;
  assignmentCount: () => number;
  clearSeatingAssignments: () => void;
}) {
  const isResetSeatingDialogOpen = ref(false);
  const hasSeatingAssignments = computed(() => options.assignmentCount() > 0);

  function openResetSeatingDialog(): void {
    if (options.seatingLifecycleBusy() || options.workspaceBusy() || !hasSeatingAssignments.value) {
      return;
    }
    isResetSeatingDialogOpen.value = true;
  }

  function closeResetSeatingDialog(): void {
    isResetSeatingDialogOpen.value = false;
  }

  function confirmResetSeatingDraft(): void {
    options.clearSeatingAssignments();
    closeResetSeatingDialog();
  }

  return {
    hasSeatingAssignments,
    isResetSeatingDialogOpen,
    openResetSeatingDialog,
    closeResetSeatingDialog,
    confirmResetSeatingDraft,
  };
}
