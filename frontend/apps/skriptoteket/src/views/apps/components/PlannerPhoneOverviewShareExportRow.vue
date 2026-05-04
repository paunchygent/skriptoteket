<script setup lang="ts">
/**
 * Phone overview distribution row.
 *
 * Relationships:
 * - adapts the shared share/export panel to the small-screen overview
 * - keeps Grupper and Sittplatser selection inside the Dela affordance
 * - emits scope-specific actions while the route shell prepares drafts in place
 */

import { computed, ref } from "vue";

import type { GroupingExportOption, SeatingExportOption } from "../classroomPlannerExportApi";
import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";
import PlannerShareExportPanel from "./PlannerShareExportPanel.vue";
import type {
  PlannerExportFileOption,
  PlannerExportOptionValue,
  PlannerShareExportScopeOption,
} from "./plannerShareExportActions";

type OverviewDistributionScope = "grouping" | "seating";

const props = defineProps<{
  hasRoster: boolean;
  hasTemplate: boolean;
  showGroupingOption?: boolean;
  showSeatingOption?: boolean;
  groupingExportBusy?: boolean;
  groupingExportErrorMessage?: string | null;
  groupingShareBusy?: boolean;
  groupingShareLoading?: boolean;
  groupingShareStatusLabel?: string | null;
  groupingShareErrorMessage?: string | null;
  groupingShareRevokingId?: string | null;
  groupingShares?: ClassroomPlannerShareArtifact[];
  seatingExportBusy?: boolean;
  seatingExportErrorMessage?: string | null;
  seatingShareBusy?: boolean;
  seatingShareLoading?: boolean;
  seatingShareStatusLabel?: string | null;
  seatingShareErrorMessage?: string | null;
  seatingShareRevokingId?: string | null;
  seatingShares?: ClassroomPlannerShareArtifact[];
}>();

const emit = defineEmits<{
  (e: "prepare", scope: OverviewDistributionScope): void;
  (e: "export-grouping-default"): void;
  (e: "export-grouping-option", option: GroupingExportOption): void;
  (e: "share-grouping-link"): void;
  (e: "copy-grouping-share", share: ClassroomPlannerShareArtifact): void;
  (e: "revoke-grouping-share", share: ClassroomPlannerShareArtifact): void;
  (e: "export-seating-default"): void;
  (e: "export-seating-option", option: SeatingExportOption): void;
  (e: "share-seating-link"): void;
  (e: "copy-seating-share", share: ClassroomPlannerShareArtifact): void;
  (e: "revoke-seating-share", share: ClassroomPlannerShareArtifact): void;
}>();

const selectedScope = ref<OverviewDistributionScope | null>(null);

const resolvedScope = computed<OverviewDistributionScope>(() => {
  if (selectedScope.value === "seating" && props.hasTemplate) {
    return "seating";
  }
  if (selectedScope.value === "grouping") {
    return "grouping";
  }
  return props.hasTemplate && props.showSeatingOption !== false ? "seating" : "grouping";
});
const scopeOptions = computed<PlannerShareExportScopeOption[]>(() => [
  ...(
    props.showGroupingOption === false
      ? []
      : [{
        value: "grouping",
        label: "Gruppindelning",
        meta: "Länk, PDF, Excel",
      }]
  ),
  ...(
    props.showSeatingOption === false
      ? []
      : [{
        value: "seating",
        label: "Sittschema",
        meta: "Länk, PDF, Excel",
        disabled: !props.hasTemplate,
        disabledReason: props.hasTemplate ? null : "Välj ett klassrum först.",
      }]
  ),
]);
const groupingExportOptions = computed<PlannerExportFileOption[]>(() => [
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
const seatingExportOptions = computed<PlannerExportFileOption[]>(() => [
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
const fileOptions = computed(() => {
  return resolvedScope.value === "seating" ? seatingExportOptions.value : groupingExportOptions.value;
});
const shares = computed(() => {
  return resolvedScope.value === "seating" ? (props.seatingShares ?? []) : (props.groupingShares ?? []);
});
const shareBusy = computed(() => {
  return resolvedScope.value === "seating" ? (props.seatingShareBusy ?? false) : (props.groupingShareBusy ?? false);
});
const shareLoading = computed(() => {
  return resolvedScope.value === "seating"
    ? (props.seatingShareLoading ?? false)
    : (props.groupingShareLoading ?? false);
});
const shareStatusLabel = computed(() => {
  return resolvedScope.value === "seating"
    ? (props.seatingShareStatusLabel ?? null)
    : (props.groupingShareStatusLabel ?? null);
});
const shareErrorMessage = computed(() => {
  return resolvedScope.value === "seating"
    ? (props.seatingShareErrorMessage ?? null)
    : (props.groupingShareErrorMessage ?? null);
});
const exportBusy = computed(() => {
  return resolvedScope.value === "seating" ? (props.seatingExportBusy ?? false) : (props.groupingExportBusy ?? false);
});
const exportErrorMessage = computed(() => {
  return resolvedScope.value === "seating"
    ? (props.seatingExportErrorMessage ?? null)
    : (props.groupingExportErrorMessage ?? null);
});
const revokingShareId = computed(() => {
  return resolvedScope.value === "seating"
    ? (props.seatingShareRevokingId ?? null)
    : (props.groupingShareRevokingId ?? null);
});

function isGroupingExportOption(option: PlannerExportOptionValue): option is GroupingExportOption {
  return option === "xlsx" || option === "pdf_a4_portrait";
}

function isSeatingExportOption(option: PlannerExportOptionValue): option is SeatingExportOption {
  return option === "a3_landscape" || option === "a4_landscape" || option === "xlsx";
}

function prepare(): void {
  if (props.hasRoster) {
    emit("prepare", resolvedScope.value);
  }
}

function selectScope(value: string): void {
  if (value !== "grouping" && value !== "seating") {
    return;
  }
  if (value === "seating" && !props.hasTemplate) {
    return;
  }
  selectedScope.value = value;
  prepare();
}

function exportDefault(): void {
  if (resolvedScope.value === "seating") {
    emit("export-seating-default");
    return;
  }
  emit("export-grouping-default");
}

function exportOption(option: PlannerExportOptionValue): void {
  if (resolvedScope.value === "seating") {
    if (isSeatingExportOption(option)) {
      emit("export-seating-option", option);
    }
    return;
  }
  if (isGroupingExportOption(option)) {
    emit("export-grouping-option", option);
  }
}

function createShare(): void {
  if (resolvedScope.value === "seating") {
    emit("share-seating-link");
    return;
  }
  emit("share-grouping-link");
}

function copyShare(share: ClassroomPlannerShareArtifact): void {
  if (resolvedScope.value === "seating") {
    emit("copy-seating-share", share);
    return;
  }
  emit("copy-grouping-share", share);
}

function revokeShare(share: ClassroomPlannerShareArtifact): void {
  if (resolvedScope.value === "seating") {
    emit("revoke-seating-share", share);
    return;
  }
  emit("revoke-grouping-share", share);
}
</script>

<template>
  <PlannerShareExportPanel
    :file-options="fileOptions"
    :shares="shares"
    :share-loading="shareLoading"
    :share-busy="shareBusy"
    :share-status-label="shareStatusLabel"
    :share-error-message="shareErrorMessage"
    :export-busy="exportBusy"
    :export-error-message="exportErrorMessage"
    :revoking-share-id="revokingShareId"
    :show-file-actions="hasRoster"
    :show-share-actions="hasRoster"
    :scope-value="resolvedScope"
    :scope-options="scopeOptions"
    trigger-variant="phone-row"
    trigger-test-id="phone-overview-share-export-row"
    trigger-meta="Länk + filer"
    panel-test-id="phone-overview-share-export-panel"
    create-share-test-id="phone-overview-share-create"
    create-share-mobile-test-id="phone-overview-share-create-mobile"
    file-option-test-id-prefix="phone-overview-export-option"
    @open="prepare"
    @select-scope="selectScope"
    @create-share="createShare"
    @copy-share="copyShare"
    @revoke-share="revokeShare"
    @export-default="exportDefault"
    @export-option="exportOption"
  />
</template>
