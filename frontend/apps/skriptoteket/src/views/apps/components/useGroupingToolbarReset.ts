/**
 * Confirmation state and destructive actions for resetting grouping placements.
 * The toolbar keeps the dialog markup and both inline and overflow triggers.
 */

import { computed, ref } from "vue";

import type { GroupAssignment } from "../classroomPlannerTypes";

type GroupingToolbarResetState = {
  groupAssignments: GroupAssignment[];
  isWorkspaceBusy: boolean;
  clearGroupingAssignments: () => void;
};

export function useGroupingToolbarReset(state: GroupingToolbarResetState) {
  const hasGroupingAssignments = computed(() => state.groupAssignments.length > 0);
  const isResetGroupingDialogOpen = ref(false);

  function openResetGroupingDialog(): void {
    if (state.isWorkspaceBusy || !hasGroupingAssignments.value) {
      return;
    }
    isResetGroupingDialogOpen.value = true;
  }

  function closeResetGroupingDialog(): void {
    isResetGroupingDialogOpen.value = false;
  }

  function confirmResetGroupingDraft(): void {
    state.clearGroupingAssignments();
    closeResetGroupingDialog();
  }

  return {
    hasGroupingAssignments,
    isResetGroupingDialogOpen,
    openResetGroupingDialog,
    closeResetGroupingDialog,
    confirmResetGroupingDraft,
  };
}
