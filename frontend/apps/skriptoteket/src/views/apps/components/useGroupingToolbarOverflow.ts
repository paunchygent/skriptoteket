/**
 * Grouping toolbar overflow policy and secondary command construction.
 *
 * Keeps grouping's phone cutovers and menu actions beside its toolbar while
 * delegating measurement and lifecycle to the shared planner overflow ladder.
 */

import { computed, type Component, type Ref } from "vue";

import { IconAdjustments, IconHistory } from "../../../components/icons";
import type { Roster } from "../classroomPlannerTypes";
import { usePlannerToolbarOverflow } from "./usePlannerToolbarOverflow";

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

type UseGroupingToolbarOverflowOptions = {
  getRootElement: () => HTMLElement | null;
  props: {
    availableRosters: Roster[];
    showHistoryAction: boolean;
    showSmartControls: boolean;
    smartSettingsOpen: boolean;
  };
  state: { isWorkspaceBusy: boolean };
  hasGroupingAssignments: Readonly<Ref<boolean>>;
  openResetGroupingDialog: () => void;
  openHistory: () => void;
  editRoster: () => void;
  openSettings: () => void;
};

const PHONE_TOOLBAR_MEDIA_QUERY = "(max-width: 767px)";
const PHONE_CONTEXT_OVERFLOW_MAX_WIDTH_PX = 540;
const PHONE_RESET_OVERFLOW_MAX_WIDTH_PX = 405;
const PHONE_DISTRIBUTION_OVERFLOW_MAX_WIDTH_PX = 380;
const OVERFLOW_PRIORITY_ORDER = ["context", "reset", "distribution"];

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

export function useGroupingToolbarOverflow(options: UseGroupingToolbarOverflowOptions) {
  const { props, state } = options;
  const {
    hiddenContributionIds,
    stageLabel,
    thresholds,
  } = usePlannerToolbarOverflow({
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
      id: "reset-grouping",
      label: "Börja om",
      disabled: state.isWorkspaceBusy || !options.hasGroupingAssignments.value,
      group: "primary" as const,
      tone: "danger" as const,
      testId: "grouping-overflow-reset",
      responsiveVisibility: "all" as const,
      onSelect: options.openResetGroupingDialog,
    }];
  });
  const secondaryActionItems = computed(() => {
    const items: OverflowActionItem[] = [...overflowActionItems.value];
    if (props.showHistoryAction) {
      items.push({
        id: "history",
        label: "Historik",
        icon: IconHistory,
        disabled: state.isWorkspaceBusy,
        testId: "grouping-history",
        onSelect: options.openHistory,
      });
    }
    items.push({
      id: "edit-roster",
      label: "Redigera klass",
      icon: IconAdjustments,
      disabled: state.isWorkspaceBusy,
      testId: "edit-grouping-roster",
      onSelect: options.editRoster,
    });
    if (props.showSmartControls) {
      items.push({
        id: "advanced-settings",
        label: "Avancerade inställningar",
        icon: IconAdjustments,
        disabled: state.isWorkspaceBusy,
        hasPopup: "dialog",
        expanded: props.smartSettingsOpen,
        testId: "grouping-overflow-open-settings",
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
  const hasContextOverflowPanel = computed(() => props.availableRosters.length > 0 && !isContextInline.value);
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
