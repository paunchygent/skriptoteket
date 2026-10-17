import { ref, watch } from "vue";

import type { useClassroomState } from "../useClassroomState";

/** Keeps the last settled workspace header visible while its replacement loads. */
export function usePlannerTransitionPresentation(options: {
  title: () => string;
  contextLabel: () => string;
  supportingText: () => string;
  transitionLabel: () => string | null;
  plannerState: ReturnType<typeof useClassroomState>;
}) {
  const { plannerState } = options;
  const displayedPlannerTitle = ref(options.title());
  const displayedContextLabel = ref(options.contextLabel());
  const displayedSupportingText = ref(options.supportingText());
  const displayedStatusLabel = ref<string | null>(plannerState.plannerStatusLabel ?? null);
  const displayedStatusMessage = ref<string | null>(plannerState.plannerStatusMessage ?? null);
  const displayedStatusTone = ref(plannerState.plannerStatusTone);

  watch(
    [
      options.title,
      options.contextLabel,
      options.supportingText,
      () => plannerState.plannerStatusLabel,
      () => plannerState.plannerStatusMessage,
      () => plannerState.plannerStatusTone,
      options.transitionLabel,
    ],
    ([title, contextLabel, supportingText, statusLabel, statusMessage, statusTone, transitionLabel]) => {
      if (transitionLabel) {
        return;
      }
      displayedPlannerTitle.value = title;
      displayedContextLabel.value = contextLabel;
      displayedSupportingText.value = supportingText;
      displayedStatusLabel.value = statusLabel;
      displayedStatusMessage.value = statusMessage;
      displayedStatusTone.value = statusTone;
    },
    { immediate: true },
  );

  return {
    displayedPlannerTitle,
    displayedContextLabel,
    displayedSupportingText,
    displayedStatusLabel,
    displayedStatusMessage,
    displayedStatusTone,
  };
}
