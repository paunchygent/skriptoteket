import { ref, watch } from "vue";

import type { useClassroomState } from "./useClassroomState";

type PlannerView = "groups" | "seats" | "rules";

/** Coordinates mode changes with transient settings, rule selection and template inputs. */
export function usePlannerWorkspaceNavigation(options: {
  plannerState: ReturnType<typeof useClassroomState>;
  initialView: () => PlannerView;
  initialTemplateId: () => string;
  identityKey: (view: PlannerView) => string;
  resetTemplateId: (view: PlannerView) => string;
  onReset?: () => void;
}) {
  const { plannerState } = options;
  function resolvePlannerView(requestedView: PlannerView): PlannerView {
    if (requestedView === "rules") return "rules";
    if (plannerState.draft?.draft_kind === "grouping") return "groups";
    if (plannerState.draft?.draft_kind === "seating") return "seats";
    return requestedView;
  }

  const currentView = ref<PlannerView>(resolvePlannerView(options.initialView()));
  const selectedStudentId = ref<string | null>(null);
  const isGroupingSettingsDrawerOpen = ref(false);
  const isSeatingSettingsDrawerOpen = ref(false);
  const pendingGroupingTemplateId = ref(options.initialTemplateId());
  const pendingSeatingTemplateId = ref(options.initialTemplateId());

  function resetTransientState(): void {
    isGroupingSettingsDrawerOpen.value = false;
    isSeatingSettingsDrawerOpen.value = false;
    selectedStudentId.value = null;
    options.onReset?.();
  }

  watch(options.initialView, (view) => {
    currentView.value = resolvePlannerView(view);
    resetTransientState();
  });

  watch(() => options.identityKey(resolvePlannerView(currentView.value)), () => {
    currentView.value = resolvePlannerView(currentView.value);
    resetTransientState();
    const templateId = options.resetTemplateId(currentView.value);
    pendingGroupingTemplateId.value = templateId;
    pendingSeatingTemplateId.value = templateId;
  });

  function selectStudent(studentId: string): void {
    if (currentView.value === "rules" && plannerState.activeSeatingSmartTool) {
      if (plannerState.isStudentInPendingRuleCandidates(studentId)) {
        plannerState.removePendingRuleCandidate(studentId);
      } else {
        plannerState.handleSeatingSmartToolStudentSelection(studentId);
      }
    }
    selectedStudentId.value = null;
  }

  return {
    currentView,
    selectedStudentId,
    isGroupingSettingsDrawerOpen,
    isSeatingSettingsDrawerOpen,
    pendingGroupingTemplateId,
    pendingSeatingTemplateId,
    selectStudent,
    openGroupingSettingsDrawer: () => { isGroupingSettingsDrawerOpen.value = true; },
    closeGroupingSettingsDrawer: () => { isGroupingSettingsDrawerOpen.value = false; },
    openSeatingSettingsDrawer: () => { isSeatingSettingsDrawerOpen.value = true; },
    closeSeatingSettingsDrawer: () => { isSeatingSettingsDrawerOpen.value = false; },
  };
}
