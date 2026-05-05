<script setup lang="ts">
/**
 * Overview distribution panel.
 *
 * Relationships:
 * - adapts the shared share/export panel to overview-only distribution
 * - rendered in separate phone/tablet and desktop containers by the parent
 * - emits scope-specific actions while the route shell prepares drafts in place
 */

import { computed, onMounted, ref, watch } from "vue";

import type { GroupingExportOption, SeatingExportOption } from "../classroomPlannerExportApi";
import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";
import PlannerShareExportPanel from "./PlannerShareExportPanel.vue";
import type {
  PlannerExportFileOption,
  PlannerExportOptionValue,
  PlannerShareExportScopeOption,
} from "./plannerShareExportActions";

type OverviewDistributionScope = "grouping" | "seating";

const props = withDefaults(
  defineProps<{
    testPrefix: "phone-overview" | "desktop-overview";
    autoPrepare?: boolean;
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
  }>(),
  {
    autoPrepare: true,
    showGroupingOption: true,
    showSeatingOption: true,
    groupingExportBusy: false,
    groupingExportErrorMessage: null,
    groupingShareBusy: false,
    groupingShareLoading: false,
    groupingShareStatusLabel: null,
    groupingShareErrorMessage: null,
    groupingShareRevokingId: null,
    groupingShares: () => [],
    seatingExportBusy: false,
    seatingExportErrorMessage: null,
    seatingShareBusy: false,
    seatingShareLoading: false,
    seatingShareStatusLabel: null,
    seatingShareErrorMessage: null,
    seatingShareRevokingId: null,
    seatingShares: () => [],
  },
);

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
const preparedScope = ref<OverviewDistributionScope | null>(null);

const canDistribute = computed(() => props.hasRoster);
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
        disabled: !canDistribute.value,
        disabledReason: canDistribute.value ? null : "Skapa en klasslista först.",
      }]
  ),
  ...(
    props.showSeatingOption === false
      ? []
      : [{
        value: "seating",
        label: "Sittschema",
        disabled: !canDistribute.value || !props.hasTemplate,
        disabledReason: !canDistribute.value
          ? "Skapa en klasslista först."
          : props.hasTemplate
            ? null
            : "Välj ett klassrum först.",
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

function prepare(scope = resolvedScope.value): void {
  if (props.hasRoster) {
    preparedScope.value = scope;
    emit("prepare", scope);
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
  prepare(value);
}

onMounted(() => {
  if (props.autoPrepare !== false) {
    prepare();
  }
});

watch(resolvedScope, (scope) => {
  if (props.autoPrepare === false) {
    return;
  }
  if (preparedScope.value === scope) {
    return;
  }
  prepare(scope);
});

watch(() => props.hasRoster, (hasRoster) => {
  if (props.autoPrepare === false) {
    return;
  }
  if (!hasRoster || preparedScope.value === resolvedScope.value) {
    return;
  }
  prepare();
});

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
    :scope-value="canDistribute ? resolvedScope : null"
    :scope-options="scopeOptions"
    :class="testPrefix === 'desktop-overview' ? 'planner-share-export-overview-desktop' : undefined"
    :visual-variant="testPrefix === 'desktop-overview' ? 'desktop-overview' : 'default'"
    trigger-variant="inline"
    :trigger-test-id="`${testPrefix}-share-export-row`"
    :panel-test-id="`${testPrefix}-share-export-panel`"
    :create-share-test-id="`${testPrefix}-share-create`"
    :create-share-mobile-test-id="`${testPrefix}-share-create-mobile`"
    :file-option-test-id-prefix="`${testPrefix}-export-option`"
    @select-scope="selectScope"
    @create-share="createShare"
    @copy-share="copyShare"
    @revoke-share="revokeShare"
    @export-default="exportDefault"
    @export-option="exportOption"
  />
</template>
