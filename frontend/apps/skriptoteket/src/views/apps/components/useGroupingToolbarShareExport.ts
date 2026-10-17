/**
 * Grouping-specific adaptation of the shared share/export panel.
 *
 * Both toolbar placements keep their own trigger presentation while sharing
 * file choices, option validation, reactive panel inputs and emitted intents.
 */

import { computed } from "vue";

import type { GroupingExportOption } from "../classroomPlannerExportApi";
import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";
import type {
  PlannerExportFileOption,
  PlannerExportOptionValue,
} from "./plannerShareExportActions";

type GroupingToolbarShareExportProps = {
  shares: ClassroomPlannerShareArtifact[];
  shareLoading: boolean;
  shareBusy: boolean;
  shareStatusLabel: string | null;
  shareErrorMessage: string | null;
  exportBusy: boolean;
  exportErrorMessage: string | null;
  revokingShareId: string | null;
  showExportActions: boolean;
  showShareLinkAction: boolean;
  showShareRevokeAction: boolean;
};

type GroupingToolbarShareExportActions = {
  createShare: () => void;
  copyShare: (share: ClassroomPlannerShareArtifact) => void;
  revokeShare: (share: ClassroomPlannerShareArtifact) => void;
  exportDefault: () => void;
  exportOption: (option: GroupingExportOption) => void;
};

function isGroupingExportOption(option: PlannerExportOptionValue): option is GroupingExportOption {
  return option === "xlsx" || option === "pdf_a4_portrait";
}

export function useGroupingToolbarShareExport(
  props: GroupingToolbarShareExportProps,
  actions: GroupingToolbarShareExportActions,
) {
  const exportOptions = computed<PlannerExportFileOption[]>(() => [
    {
      id: "xlsx",
      label: "Excel (.xlsx)",
      option: "xlsx",
      isDefault: true,
    },
    {
      id: "pdf",
      label: "PDF (A4 stående)",
      option: "pdf_a4_portrait",
    },
  ]);
  const shareExportPanelProps = computed(() => ({
    fileOptions: exportOptions.value,
    shares: props.shares,
    shareLoading: props.shareLoading,
    shareBusy: props.shareBusy,
    shareStatusLabel: props.shareStatusLabel,
    shareErrorMessage: props.shareErrorMessage,
    exportBusy: props.exportBusy,
    exportErrorMessage: props.exportErrorMessage,
    revokingShareId: props.revokingShareId,
    showFileActions: props.showExportActions,
    showShareActions: props.showShareLinkAction,
    showRevokeAction: props.showShareRevokeAction,
    panelTestId: "grouping-share-management",
    createShareTestId: "grouping-share-create",
    createShareMobileTestId: "grouping-share-create-mobile",
    fileOptionTestIdPrefix: "grouping-export-option",
  }));

  function handleExportOption(option: PlannerExportOptionValue): void {
    if (!isGroupingExportOption(option)) {
      return;
    }
    actions.exportOption(option);
  }

  const shareExportPanelListeners = {
    "create-share": actions.createShare,
    "copy-share": actions.copyShare,
    "revoke-share": actions.revokeShare,
    "export-default": actions.exportDefault,
    "export-option": handleExportOption,
  };
  const showDistributionAction = computed(() => props.showExportActions || props.showShareLinkAction);

  return {
    shareExportPanelProps,
    shareExportPanelListeners,
    showDistributionAction,
  };
}
