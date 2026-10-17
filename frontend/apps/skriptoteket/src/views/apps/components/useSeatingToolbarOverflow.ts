import { computed, type Component } from "vue";

import { IconAdjustments, IconHistory } from "../../../components/icons";
import { usePlannerToolbarOverflow } from "./usePlannerToolbarOverflow";

const PHONE_TOOLBAR_MEDIA_QUERY = "(max-width: 767px)";
const PHONE_CONTEXT_OVERFLOW_MAX_WIDTH_PX = 540;
const PHONE_RESET_OVERFLOW_MAX_WIDTH_PX = 400;
const PHONE_DISTRIBUTION_OVERFLOW_MAX_WIDTH_PX = 340;
const OVERFLOW_PRIORITY_ORDER = ["context", "reset", "distribution"];

type OverflowActionItem = {
  id: string;
  label: string;
  icon?: Component;
  disabled: boolean;
  group?: "primary" | "secondary";
  hasPopup?: "dialog" | "menu";
  expanded?: boolean;
  responsiveVisibility?: "all" | "phone";
  tone?: "danger";
  testId: string;
  onSelect: () => void;
};

function resolvePhoneHiddenContributionIds(rootElement: HTMLElement): string[] | null {
  if (typeof window === "undefined" || !window.matchMedia(PHONE_TOOLBAR_MEDIA_QUERY).matches) {
    return null;
  }
  if (rootElement.clientWidth > PHONE_CONTEXT_OVERFLOW_MAX_WIDTH_PX) {
    return null;
  }
  if (rootElement.clientWidth > PHONE_RESET_OVERFLOW_MAX_WIDTH_PX) {
    return OVERFLOW_PRIORITY_ORDER.slice(0, 1);
  }
  if (rootElement.clientWidth > PHONE_DISTRIBUTION_OVERFLOW_MAX_WIDTH_PX) {
    return OVERFLOW_PRIORITY_ORDER.slice(0, 2);
  }
  return OVERFLOW_PRIORITY_ORDER;
}

/** Owns the seating overflow ladder, responsive visibility and secondary menu actions. */
export function useSeatingToolbarOverflow(options: {
  getRootElement: () => HTMLDivElement | null;
  seatingLifecycleBusy: () => boolean;
  workspaceBusy: () => boolean;
  hasSeatingAssignments: () => boolean;
  canEditCurrentTemplate: () => boolean;
  availableTemplateCount: () => number;
  showHistoryAction: () => boolean;
  showSmartControls: () => boolean;
  smartSettingsOpen: () => boolean;
  openResetSeatingDialog: () => void;
  openHistory: () => void;
  editRoster: () => void;
  editCurrentTemplate: () => void;
  openSettings: () => void;
}) {
  const { hiddenContributionIds, stageLabel, thresholds } = usePlannerToolbarOverflow({
    getRootElement: options.getRootElement,
    forcedHiddenContributionIds: resolvePhoneHiddenContributionIds,
    contributions: [
      {
        id: "context",
        selector: '[data-overflow-contribution="context"]',
      },
      {
        id: "reset",
        selector: '[data-overflow-contribution="reset"]',
      },
      {
        id: "distribution",
        selector: '[data-overflow-contribution="distribution"]',
      },
    ],
  });
  const overflowActionItems = computed(() => {
    const isResetOverflowed = hiddenContributionIds.value.includes("reset");
    if (!isResetOverflowed) {
      return [];
    }
    return [{
      id: "reset-seating",
      label: "Börja om",
      disabled: options.seatingLifecycleBusy() || options.workspaceBusy() || !options.hasSeatingAssignments(),
      group: "primary" as const,
      tone: "danger" as const,
      testId: "seating-overflow-reset",
      responsiveVisibility: "all" as const,
      onSelect: options.openResetSeatingDialog,
    }];
  });
  const secondaryActionItems = computed(() => {
    const items: OverflowActionItem[] = [...overflowActionItems.value];
    if (options.showHistoryAction()) {
      items.push({
        id: "history",
        label: "Historik",
        icon: IconHistory,
        disabled: options.seatingLifecycleBusy(),
        testId: "seating-history",
        onSelect: options.openHistory,
      });
    }
    items.push({
      id: "edit-roster",
      label: "Redigera klass",
      icon: IconAdjustments,
      disabled: options.workspaceBusy() || options.seatingLifecycleBusy(),
      testId: "edit-seating-roster",
      onSelect: options.editRoster,
    });
    items.push({
      id: "edit-classroom",
      label: "Redigera klassrum",
      icon: IconAdjustments,
      disabled: !options.canEditCurrentTemplate() || options.workspaceBusy() || options.seatingLifecycleBusy(),
      testId: "edit-current-template",
      onSelect: options.editCurrentTemplate,
    });
    if (options.showSmartControls()) {
      items.push({
        id: "advanced-settings",
        label: "Avancerade inställningar",
        icon: IconAdjustments,
        disabled: options.workspaceBusy() || options.seatingLifecycleBusy(),
        hasPopup: "dialog",
        expanded: options.smartSettingsOpen(),
        testId: "seating-overflow-open-settings",
        onSelect: options.openSettings,
      });
    }
    return items;
  });

  const isUndoRedoInline = computed(() => true);
  const isResetInline = computed(() => !hiddenContributionIds.value.includes("reset"));
  const isNewDraftInline = computed(() => true);
  const isContextInline = computed(() => !hiddenContributionIds.value.includes("context"));
  const isDistributionInline = computed(() => !hiddenContributionIds.value.includes("distribution"));
  const hasContextOverflowPanel = computed(() => options.availableTemplateCount() > 0 && !isContextInline.value);
  const showOverflowPanel = computed(() => (
    hasContextOverflowPanel.value
  ));

  return {
    hiddenContributionIds,
    stageLabel,
    thresholds,
    secondaryActionItems,
    isUndoRedoInline,
    isResetInline,
    isNewDraftInline,
    isContextInline,
    isDistributionInline,
    hasContextOverflowPanel,
    showOverflowPanel,
  };
}
