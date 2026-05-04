<script setup lang="ts">
/**
 * Class-first planner workspace.
 *
 * This component is now the only home surface for Klassrumskartan. It keeps
 * overview as the default entry state, folds the no-class empty state into the
 * same surface, relies on the segmented toggle as the only way to enter
 * task work, and composes overview-specific subcomponents instead of mixing
 * resumable cards, roster controls, and classroom controls in one file.
 */

import { computed, onUnmounted, ref } from "vue";

import type { GroupingExportOption, SeatingExportOption } from "../classroomPlannerExportApi";
import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";
import type {
  ClassWorkspaceSummary,
  PlanDraftSummary,
  RoomTemplate,
  Roster,
} from "../classroomPlannerTypes";
import type { ClassroomPlannerOverviewCapabilities } from "../classroomPlannerOverviewCapabilities";
import {
  resolvePlannerOverviewPrerequisiteCopy,
  resolvePlannerWorkspaceDisabledReasons,
} from "../plannerWorkspacePrerequisites";
import { useHelp } from "../../../components/help/useHelp";
import PlannerOverviewSetupPanel from "./PlannerOverviewSetupPanel.vue";
import PlannerPhoneOverviewShareExportRow from "./PlannerPhoneOverviewShareExportRow.vue";
import PlannerTopPanel from "./PlannerTopPanel.vue";

type OverviewDistributionScope = "grouping" | "seating";

const props = defineProps<{
  workspaceSummary: ClassWorkspaceSummary | null;
  availableRosters: Roster[];
  availableTemplates: RoomTemplate[];
  selectedRosterId: string | null;
  selectedTemplateId: string | null;
  isLoadingWorkspace: boolean;
  transitionLabel?: string | null;
  visibleGroupingDraft: PlanDraftSummary | null;
  visibleSeatingDraft: PlanDraftSummary | null;
  overviewCapabilities?: ClassroomPlannerOverviewCapabilities | null;
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
  (e: "exit-app"): void;
  (e: "create-roster"): void;
  (e: "edit-roster"): void;
  (e: "delete-current-roster"): void;
  (e: "select-roster", rosterId: string): void;
  (e: "create-template"): void;
  (e: "select-template", templateId: string | null): void;
  (e: "edit-current-template", template?: RoomTemplate): void;
  (e: "delete-current-template"): void;
  (e: "open-grouping", payload: { templateId: string | null }): void;
  (e: "open-seating", payload: { templateId: string | null }): void;
  (e: "open-rules"): void;
  (e: "dismiss-grouping-draft"): void;
  (e: "dismiss-seating-draft"): void;
  (e: "prepare-overview-distribution", scope: OverviewDistributionScope): void;
  (e: "export-overview-grouping-default"): void;
  (e: "export-overview-grouping-option", option: GroupingExportOption): void;
  (e: "share-overview-grouping-link"): void;
  (e: "copy-overview-grouping-share", share: ClassroomPlannerShareArtifact): void;
  (e: "revoke-overview-grouping-share", share: ClassroomPlannerShareArtifact): void;
  (e: "export-overview-seating-default"): void;
  (e: "export-overview-seating-option", option: SeatingExportOption): void;
  (e: "share-overview-seating-link"): void;
  (e: "copy-overview-seating-share", share: ClassroomPlannerShareArtifact): void;
  (e: "revoke-overview-seating-share", share: ClassroomPlannerShareArtifact): void;
}>();

const workspaceMode = ref<"overview" | "grouping" | "seating" | "rules">("overview");

// Keep the global help panel aware that we are in overview mode.
const { setHelpContext, clearHelpContext } = useHelp();
setHelpContext("planner_overview");
onUnmounted(() => clearHelpContext("planner_overview"));

const activeRosterSummary = computed(() => props.workspaceSummary?.roster ?? null);
const selectedRoster = computed(() => {
  return props.availableRosters.find((roster) => roster.id === props.selectedRosterId) ?? null;
});
const selectedTemplate = computed(() => {
  return props.availableTemplates.find((template) => template.id === props.selectedTemplateId) ?? null;
});
const hasSelectedRoster = computed(() => Boolean(selectedRoster.value));
const hasSelectedTemplate = computed(() => Boolean(selectedTemplate.value));
const workspaceContextLabel = computed(() => {
  if (!selectedTemplate.value) {
    return "Klassrum saknas";
  }
  return `Klassrum: ${selectedTemplate.value.name}`;
});
const workspaceHomeTitle = computed(() => {
  return selectedRoster.value?.name ?? activeRosterSummary.value?.name ?? "Klass saknas";
});
const selectedRosterCountLabel = computed(() => {
  if (activeRosterSummary.value) {
    return `${activeRosterSummary.value.student_count} elever`;
  }
  if (selectedRoster.value) {
    return `${selectedRoster.value.students.length} elever`;
  }
  return null;
});
const workspaceDisabledReasons = computed(() => {
  const baseReasons = resolvePlannerWorkspaceDisabledReasons({
    hasRoster: hasSelectedRoster.value,
    hasTemplate: hasSelectedTemplate.value,
  });

  return {
    grouping: baseReasons.grouping,
    seating: baseReasons.seating,
    rules: baseReasons.rules,
  };
});
const overviewPrerequisiteCopy = computed(() => {
  const baseCopy = resolvePlannerOverviewPrerequisiteCopy({
    hasRoster: hasSelectedRoster.value,
    hasTemplate: hasSelectedTemplate.value,
  });

  return {
    guidance: props.overviewCapabilities?.status_message ?? baseCopy.guidance,
    help: props.overviewCapabilities?.supporting_text ?? baseCopy.help,
  };
});
const compactOverviewStatusMessage = computed(() => {
  if (hasSelectedRoster.value) {
    return null;
  }
  return "Börja med att skapa en klasslista. Tryck på hjälp för vägledning.";
});
function selectWorkspaceMode(value: string): void {
  if (value === "overview") {
    workspaceMode.value = value;
    return;
  }

  if (value === "grouping") {
    if (workspaceDisabledReasons.value.grouping) {
      return;
    }
    emit("open-grouping", { templateId: null });
    return;
  }

  if (value === "seating") {
    if (workspaceDisabledReasons.value.seating) {
      return;
    }
    emit("open-seating", { templateId: props.selectedTemplateId });
    return;
  }

  if (value === "rules") {
    if (workspaceDisabledReasons.value.rules) {
      return;
    }
    emit("open-rules");
  }
}

</script>

<template>
  <section class="space-y-4">
    <PlannerTopPanel
      :title="workspaceHomeTitle"
      :context-label="workspaceContextLabel"
      :mode-value="workspaceMode"
      :show-grouping-option="overviewCapabilities?.show_grouping_option !== false"
      :show-seating-option="overviewCapabilities?.show_seating_option !== false"
      :show-rules-option="overviewCapabilities?.show_rules_option !== false"
      :grouping-disabled-reason="workspaceDisabledReasons.grouping"
      :seating-disabled-reason="workspaceDisabledReasons.seating"
      :rules-disabled-reason="workspaceDisabledReasons.rules"
      :status-message="overviewPrerequisiteCopy.guidance"
      :supporting-text="overviewPrerequisiteCopy.help"
      :compact-status-message="compactOverviewStatusMessage"
      status-tone="neutral"
      @update:mode-value="selectWorkspaceMode"
      @exit="emit('exit-app')"
    />

    <div
      v-if="transitionLabel || isLoadingWorkspace"
      class="border border-navy bg-white px-4 py-12 text-center text-sm font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy shadow-brutal-sm"
    >
      {{ transitionLabel ?? "Laddar planeringen..." }}
    </div>

    <template v-else>
      <div
        class="planner-phone-overview-dashboard"
        data-test="planner-phone-overview-dashboard"
      >
        <PlannerOverviewSetupPanel
          variant="phone"
          :selected-roster="selectedRoster"
          :selected-roster-id="selectedRosterId"
          :selected-roster-count-label="selectedRosterCountLabel"
          :available-rosters="availableRosters"
          :selected-template="selectedTemplate"
          :selected-template-id="selectedTemplateId"
          :available-templates="availableTemplates"
          :is-loading-workspace="isLoadingWorkspace"
          :show-roster-actions="overviewCapabilities?.show_roster_actions !== false"
          :show-template-actions="overviewCapabilities?.show_template_actions !== false"
          :roster-create-disabled-reason="overviewCapabilities?.roster_actions?.create_disabled_reason"
          :roster-edit-disabled-reason="overviewCapabilities?.roster_actions?.edit_disabled_reason"
          :roster-delete-disabled-reason="overviewCapabilities?.roster_actions?.delete_disabled_reason"
          :template-create-disabled-reason="overviewCapabilities?.template_actions?.create_disabled_reason"
          :template-edit-disabled-reason="overviewCapabilities?.template_actions?.edit_disabled_reason"
          :template-delete-disabled-reason="overviewCapabilities?.template_actions?.delete_disabled_reason"
          @select-roster="emit('select-roster', $event)"
          @create-roster="emit('create-roster')"
          @edit-roster="emit('edit-roster')"
          @delete-current-roster="emit('delete-current-roster')"
          @select-template="emit('select-template', $event)"
          @create-template="emit('create-template')"
          @edit-current-template="emit('edit-current-template', $event)"
          @delete-current-template="emit('delete-current-template')"
        />

        <PlannerPhoneOverviewShareExportRow
          :has-roster="Boolean(selectedRoster)"
          :has-template="Boolean(selectedTemplate)"
          :show-grouping-option="overviewCapabilities?.show_grouping_option !== false"
          :show-seating-option="overviewCapabilities?.show_seating_option !== false"
          :grouping-export-busy="groupingExportBusy"
          :grouping-export-error-message="groupingExportErrorMessage"
          :grouping-share-busy="groupingShareBusy"
          :grouping-share-loading="groupingShareLoading"
          :grouping-share-status-label="groupingShareStatusLabel"
          :grouping-share-error-message="groupingShareErrorMessage"
          :grouping-share-revoking-id="groupingShareRevokingId"
          :grouping-shares="groupingShares"
          :seating-export-busy="seatingExportBusy"
          :seating-export-error-message="seatingExportErrorMessage"
          :seating-share-busy="seatingShareBusy"
          :seating-share-loading="seatingShareLoading"
          :seating-share-status-label="seatingShareStatusLabel"
          :seating-share-error-message="seatingShareErrorMessage"
          :seating-share-revoking-id="seatingShareRevokingId"
          :seating-shares="seatingShares"
          @prepare="emit('prepare-overview-distribution', $event)"
          @export-grouping-default="emit('export-overview-grouping-default')"
          @export-grouping-option="emit('export-overview-grouping-option', $event)"
          @share-grouping-link="emit('share-overview-grouping-link')"
          @copy-grouping-share="emit('copy-overview-grouping-share', $event)"
          @revoke-grouping-share="emit('revoke-overview-grouping-share', $event)"
          @export-seating-default="emit('export-overview-seating-default')"
          @export-seating-option="emit('export-overview-seating-option', $event)"
          @share-seating-link="emit('share-overview-seating-link')"
          @copy-seating-share="emit('copy-overview-seating-share', $event)"
          @revoke-seating-share="emit('revoke-overview-seating-share', $event)"
        />
      </div>

      <div class="planner-desktop-overview-grid">
        <PlannerOverviewSetupPanel
          :selected-roster="selectedRoster"
          :selected-roster-id="selectedRosterId"
          :available-rosters="availableRosters"
          :selected-roster-count-label="selectedRosterCountLabel"
          :selected-template="selectedTemplate"
          :selected-template-id="selectedTemplateId"
          :available-templates="availableTemplates"
          :is-loading-workspace="isLoadingWorkspace"
          :show-roster-actions="overviewCapabilities?.show_roster_actions !== false"
          :show-template-actions="overviewCapabilities?.show_template_actions !== false"
          :roster-create-disabled-reason="overviewCapabilities?.roster_actions?.create_disabled_reason"
          :roster-edit-disabled-reason="overviewCapabilities?.roster_actions?.edit_disabled_reason"
          :roster-delete-disabled-reason="overviewCapabilities?.roster_actions?.delete_disabled_reason"
          :template-create-disabled-reason="overviewCapabilities?.template_actions?.create_disabled_reason"
          :template-edit-disabled-reason="overviewCapabilities?.template_actions?.edit_disabled_reason"
          :template-delete-disabled-reason="overviewCapabilities?.template_actions?.delete_disabled_reason"
          @select-roster="emit('select-roster', $event)"
          @create-roster="emit('create-roster')"
          @edit-roster="emit('edit-roster')"
          @delete-current-roster="emit('delete-current-roster')"
          @select-template="emit('select-template', $event)"
          @create-template="emit('create-template')"
          @edit-current-template="emit('edit-current-template', $event)"
          @delete-current-template="emit('delete-current-template')"
        />
      </div>
    </template>
  </section>
</template>
