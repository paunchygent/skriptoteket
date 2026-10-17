import { computed } from "vue";

import type { SeatingExportOption } from "../classroomPlannerExportApi";
import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";
import type {
  PlannerExportFileOption,
  PlannerExportOptionValue,
} from "./plannerShareExportActions";

type SeatingShareExportProps = {
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

function isSeatingExportOption(option: PlannerExportOptionValue): option is SeatingExportOption {
  return option === "a3_landscape" || option === "a4_landscape" || option === "xlsx";
}

/** Adapts both seating distribution panels to the shared share/export surface. */
export function useSeatingToolbarShareExport(props: SeatingShareExportProps, actions: {
  createShare: () => void;
  copyShare: (share: ClassroomPlannerShareArtifact) => void;
  revokeShare: (share: ClassroomPlannerShareArtifact) => void;
  exportDefault: () => void;
  exportOption: (option: SeatingExportOption) => void;
}) {
  const exportOptions = computed<PlannerExportFileOption[]>(() => [
    {
      id: "a3",
      label: "Affisch (A3)",
      option: "a3_landscape",
      isDefault: true,
    },
    {
      id: "a4",
      label: "Affisch (A4)",
      option: "a4_landscape",
    },
    {
      id: "xlsx",
      label: "Excel (.xlsx)",
      option: "xlsx",
    },
  ]);

  function handleExportOption(option: PlannerExportOptionValue): void {
    if (!isSeatingExportOption(option)) {
      return;
    }
    actions.exportOption(option);
  }

  const showDistributionAction = computed(() => props.showExportActions || props.showShareLinkAction);
  const shareExportPanelBindings = computed(() => ({
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
    panelTestId: "seating-share-management",
    createShareTestId: "seating-share-create",
    createShareMobileTestId: "seating-share-create-mobile",
    fileOptionTestIdPrefix: "seating-export-option",
    onCreateShare: actions.createShare,
    onCopyShare: actions.copyShare,
    onRevokeShare: actions.revokeShare,
    onExportDefault: actions.exportDefault,
    onExportOption: handleExportOption,
  }));

  return { showDistributionAction, shareExportPanelBindings };
}
