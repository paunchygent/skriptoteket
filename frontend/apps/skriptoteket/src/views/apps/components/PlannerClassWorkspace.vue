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
import { IconEdit, IconPlus, IconTrash } from "../../../components/icons";
import PlannerPhoneOverviewShareExportRow from "./PlannerPhoneOverviewShareExportRow.vue";
import PlannerRosterOverviewPanel from "./PlannerRosterOverviewPanel.vue";
import PlannerTemplateOverviewPanel from "./PlannerTemplateOverviewPanel.vue";
import PlannerTopPanel from "./PlannerTopPanel.vue";

const CLASS_PREVIEW_NAME_LIMIT = 33;
const PHONE_CLASS_PREVIEW_NAME_LIMIT = 10;
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
const selectedRosterSortedNames = computed(() => {
  const roster = selectedRoster.value;
  if (!roster) {
    return [];
  }

  const sortedNames = [...roster.students]
    .map((student) => student.display_name.trim())
    .filter((displayName) => displayName.length > 0)
    .sort((left, right) => {
      const leftFirstName = left.split(/\s+/)[0] ?? left;
      const rightFirstName = right.split(/\s+/)[0] ?? right;
      const firstNameComparison = leftFirstName.localeCompare(rightFirstName, "sv");
      if (firstNameComparison !== 0) {
        return firstNameComparison;
      }
      return left.localeCompare(right, "sv");
    });

  return sortedNames;
});
const selectedRosterPreviewNames = computed(() => {
  if (selectedRosterSortedNames.value.length <= CLASS_PREVIEW_NAME_LIMIT) {
    return selectedRosterSortedNames.value;
  }

  return [...selectedRosterSortedNames.value.slice(0, CLASS_PREVIEW_NAME_LIMIT), "..."];
});
const phoneRosterPreviewNames = computed(() => {
  return selectedRosterSortedNames.value.slice(0, PHONE_CLASS_PREVIEW_NAME_LIMIT);
});
const phoneRosterPreviewRemainingCount = computed(() => {
  return Math.max(0, selectedRosterSortedNames.value.length - PHONE_CLASS_PREVIEW_NAME_LIMIT);
});
const workspaceContextLabel = computed(() => {
  if (!selectedTemplate.value) {
    return "Inget klassrum valt";
  }
  return `Klassrum: ${selectedTemplate.value.name}`;
});
const workspaceHomeTitle = computed(() => {
  return selectedRoster.value?.name ?? activeRosterSummary.value?.name ?? "Planering";
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
    hasRoster: props.selectedRosterId !== null,
    hasTemplate: props.selectedTemplateId !== null,
  });

  return {
    grouping: baseReasons.grouping,
    seating: baseReasons.seating,
    rules: baseReasons.rules,
  };
});
const overviewPrerequisiteCopy = computed(() => {
  const baseCopy = resolvePlannerOverviewPrerequisiteCopy({
    hasRoster: props.selectedRosterId !== null,
    hasTemplate: props.selectedTemplateId !== null,
  });

  return {
    guidance: props.overviewCapabilities?.status_message ?? baseCopy.guidance,
    help: props.overviewCapabilities?.supporting_text ?? baseCopy.help,
  };
});
function selectWorkspaceMode(value: string): void {
  if (value === "overview") {
    workspaceMode.value = value;
    return;
  }

  if (value === "grouping") {
    emit("open-grouping", { templateId: null });
    return;
  }

  if (value === "seating") {
    emit("open-seating", { templateId: props.selectedTemplateId });
    return;
  }

  if (value === "rules") {
    emit("open-rules");
  }
}

function selectPhoneRoster(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement) || !target.value) {
    return;
  }
  emit("select-roster", target.value);
}

function selectPhoneTemplate(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) {
    return;
  }
  emit("select-template", target.value || null);
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
        <section class="planner-phone-overview-section">
          <div class="flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold text-navy">
              Klasslista
            </h3>
            <span class="text-xs text-navy/65">
              {{ selectedRosterCountLabel ?? "0 elever" }}
            </span>
          </div>
          <label class="mt-2 block">
            <select
              aria-label="Klasslista"
              class="planner-phone-select"
              :value="selectedRosterId ?? ''"
              data-test="phone-overview-roster-select"
              :disabled="isLoadingWorkspace || availableRosters.length === 0"
              @change="selectPhoneRoster"
            >
              <option value="">
                Välj klass
              </option>
              <option
                v-for="roster in availableRosters"
                :key="roster.id"
                :value="roster.id"
              >
                {{ roster.name }}
              </option>
            </select>
          </label>
          <div
            class="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs leading-snug text-navy/75"
            data-test="phone-overview-roster-preview"
          >
            <span
              v-for="name in phoneRosterPreviewNames"
              :key="name"
              class="truncate"
            >
              {{ name }}
            </span>
            <span
              v-if="phoneRosterPreviewRemainingCount > 0"
              class="col-span-2 font-semibold text-navy/55"
              data-test="phone-overview-roster-preview-more"
            >
              ... {{ phoneRosterPreviewRemainingCount }} till
            </span>
          </div>
          <div
            v-if="overviewCapabilities?.show_roster_actions !== false"
            class="mt-2 flex items-center gap-1.5"
          >
            <button
              type="button"
              class="planner-phone-link-button"
              data-test="phone-overview-edit-roster"
              :disabled="Boolean(overviewCapabilities?.roster_actions?.edit_disabled_reason)"
              @click="emit('edit-roster')"
            >
              <IconEdit :size="14" />
              Ändra
            </button>
            <button
              type="button"
              class="planner-phone-link-button"
              data-test="phone-overview-create-roster"
              :disabled="Boolean(overviewCapabilities?.roster_actions?.create_disabled_reason)"
              @click="emit('create-roster')"
            >
              <IconPlus :size="14" />
              Ny
            </button>
            <button
              type="button"
              class="planner-phone-link-button planner-phone-link-button-danger"
              data-test="phone-overview-delete-roster"
              :disabled="Boolean(overviewCapabilities?.roster_actions?.delete_disabled_reason)"
              @click="emit('delete-current-roster')"
            >
              <IconTrash :size="14" />
              Radera
            </button>
          </div>
        </section>

        <section class="planner-phone-overview-section">
          <div class="flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold text-navy">
              Klassrum
            </h3>
            <span class="text-xs text-navy/65">
              {{ selectedTemplate ? `${selectedTemplate.seats.length} platser` : "Inget valt" }}
            </span>
          </div>
          <label class="mt-2 block">
            <select
              aria-label="Klassrum"
              class="planner-phone-select"
              :value="selectedTemplateId ?? ''"
              data-test="phone-overview-template-select"
              :disabled="isLoadingWorkspace || availableTemplates.length === 0"
              @change="selectPhoneTemplate"
            >
              <option value="">
                Välj klassrum
              </option>
              <option
                v-for="template in availableTemplates"
                :key="template.id"
                :value="template.id"
              >
                {{ template.name }}
              </option>
            </select>
          </label>
          <div
            v-if="overviewCapabilities?.show_template_actions !== false"
            class="mt-2 flex items-center gap-1.5"
          >
            <button
              v-if="selectedTemplate"
              type="button"
              class="planner-phone-link-button"
              data-test="phone-overview-edit-template"
              :disabled="Boolean(overviewCapabilities?.template_actions?.edit_disabled_reason)"
              @click="emit('edit-current-template', selectedTemplate)"
            >
              <IconEdit :size="14" />
              Ändra
            </button>
            <button
              type="button"
              class="planner-phone-link-button"
              data-test="phone-overview-create-template"
              :disabled="Boolean(overviewCapabilities?.template_actions?.create_disabled_reason)"
              @click="emit('create-template')"
            >
              <IconPlus :size="14" />
              Ny
            </button>
            <button
              v-if="selectedTemplate"
              type="button"
              class="planner-phone-link-button planner-phone-link-button-danger"
              data-test="phone-overview-delete-template"
              :disabled="Boolean(overviewCapabilities?.template_actions?.delete_disabled_reason)"
              @click="emit('delete-current-template')"
            >
              <IconTrash :size="14" />
              Radera
            </button>
          </div>
          <div
            v-if="!selectedTemplate"
            class="mt-2 border border-dashed border-navy/25 bg-canvas px-3 py-2 text-xs text-navy/60"
            data-test="phone-overview-classroom-empty"
          >
            Välj ett klassrum.
          </div>
        </section>

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

      <div class="planner-desktop-overview-grid grid gap-3 xl:grid-cols-2">
        <PlannerRosterOverviewPanel
          :title="selectedRoster?.name ?? activeRosterSummary?.name ?? 'Ingen klass vald'"
          :count-label="selectedRosterCountLabel"
          :selected-roster="selectedRoster"
          :selected-roster-id="selectedRosterId"
          :available-rosters="availableRosters"
          :selected-roster-preview-names="selectedRosterPreviewNames"
          :is-loading-workspace="isLoadingWorkspace"
          :show-actions="overviewCapabilities?.show_roster_actions !== false"
          :create-disabled-reason="overviewCapabilities?.roster_actions?.create_disabled_reason"
          :edit-disabled-reason="overviewCapabilities?.roster_actions?.edit_disabled_reason"
          :delete-disabled-reason="overviewCapabilities?.roster_actions?.delete_disabled_reason"
          @select-roster="emit('select-roster', $event)"
          @create-roster="emit('create-roster')"
          @edit-roster="emit('edit-roster')"
          @delete-current-roster="emit('delete-current-roster')"
        />

        <PlannerTemplateOverviewPanel
          :selected-template="selectedTemplate"
          :selected-template-id="selectedTemplateId"
          :available-templates="availableTemplates"
          :is-loading-workspace="isLoadingWorkspace"
          :show-actions="overviewCapabilities?.show_template_actions !== false"
          :create-disabled-reason="overviewCapabilities?.template_actions?.create_disabled_reason"
          :edit-disabled-reason="overviewCapabilities?.template_actions?.edit_disabled_reason"
          :delete-disabled-reason="overviewCapabilities?.template_actions?.delete_disabled_reason"
          @select-template="emit('select-template', $event)"
          @create-template="emit('create-template')"
          @edit-current-template="emit('edit-current-template', $event)"
          @delete-current-template="emit('delete-current-template')"
        />
      </div>
    </template>
  </section>
</template>
