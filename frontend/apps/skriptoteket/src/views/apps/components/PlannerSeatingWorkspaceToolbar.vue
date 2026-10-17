<script setup lang="ts">
/**
 * Detached seating workspace toolbar.
 *
 * This component owns the seating-only command row after ST-29-02 moved the
 * toolbar into the shared planner shell. It keeps the first row focused on
 * immediate actions plus the active classroom selector, while Smart tuning
 * lives in the adjacent settings drawer instead of in extra toolbar toggles.
 */

import { computed, nextTick, ref } from "vue";

import { UiGlyph } from "../../../components/ui/shared";
import {
  DENSE_FORM_INPUT_CLASS,
  UiDenseActionButton,
} from "../../../components/ui";
import type { SeatingExportOption } from "../classroomPlannerExportApi";
import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";
import type { RoomTemplate } from "../classroomPlannerTypes";
import PlannerConfirmationDialog from "./PlannerConfirmationDialog.vue";
import PlannerShareExportPanel from "./PlannerShareExportPanel.vue";
import PlannerToolbarOverflowMenu from "./PlannerToolbarOverflowMenu.vue";
import PlannerWorkspaceActionBar from "./PlannerWorkspaceActionBar.vue";
import { useSeatingToolbarOverflow } from "./useSeatingToolbarOverflow";
import { useSeatingToolbarReset } from "./useSeatingToolbarReset";
import { useSeatingToolbarShareExport } from "./useSeatingToolbarShareExport";
import { useClassroomState } from "../useClassroomState";

const props = withDefaults(
  defineProps<{
    availableTemplates?: RoomTemplate[];
    selectedTemplateId?: string | null;
    smartSettingsOpen?: boolean;
    seatingLifecycleBusy?: boolean;
    exportBusy?: boolean;
    exportStatusLabel?: string | null;
    exportErrorMessage?: string | null;
    shareBusy?: boolean;
    shareLoading?: boolean;
    shareStatusLabel?: string | null;
    shareErrorMessage?: string | null;
    revokingShareId?: string | null;
    shares?: ClassroomPlannerShareArtifact[];
    showHistoryAction?: boolean;
    showSmartControls?: boolean;
    showExportActions?: boolean;
    showShareLinkAction?: boolean;
    showShareRevokeAction?: boolean;
  }>(),
  {
    availableTemplates: () => [],
    selectedTemplateId: null,
    smartSettingsOpen: false,
    seatingLifecycleBusy: false,
    exportBusy: false,
    exportStatusLabel: null,
    exportErrorMessage: null,
    shareBusy: false,
    shareLoading: false,
    shareStatusLabel: null,
    shareErrorMessage: null,
    revokingShareId: null,
    shares: () => [],
    showHistoryAction: true,
    showSmartControls: true,
    showExportActions: true,
    showShareLinkAction: false,
    showShareRevokeAction: true,
  },
);

const emit = defineEmits<{
  (e: "change-seating-template", templateId: string | null): void;
  (e: "new-seating-draft", templateId: string): void;
  (e: "edit-roster"): void;
  (e: "edit-current-template", template: RoomTemplate): void;
  (e: "open-history"): void;
  (e: "open-settings"): void;
  (e: "export-default"): void;
  (e: "export-option", option: SeatingExportOption): void;
  (e: "share-link"): void;
  (e: "copy-share", share: ClassroomPlannerShareArtifact): void;
  (e: "revoke-share", share: ClassroomPlannerShareArtifact): void;
}>();

const plannerState = useClassroomState();
const actionBarRef = ref<{
  getRootElement: () => HTMLDivElement | null;
} | null>(null);
const seatingTemplateSelect = ref<HTMLSelectElement | null>(null);
const showSeatingTemplateRequiredHint = ref(false);
const {
  hasSeatingAssignments,
  isResetSeatingDialogOpen,
  openResetSeatingDialog,
  closeResetSeatingDialog,
  confirmResetSeatingDraft,
} = useSeatingToolbarReset({
  seatingLifecycleBusy: () => props.seatingLifecycleBusy,
  workspaceBusy: () => plannerState.isWorkspaceBusy,
  assignmentCount: () => plannerState.seatAssignments.length,
  clearSeatingAssignments: () => plannerState.clearSeatingAssignments(),
});
const canRandomizeSeating = computed(() => {
  return (
    plannerState.template !== null
    && plannerState.students.length > 0
    && plannerState.seats.length > 0
    && !plannerState.isWorkspaceBusy
    && !plannerState.isRunningSmartSeating
    && !props.seatingLifecycleBusy
  );
});
const {
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
} = useSeatingToolbarOverflow({
  getRootElement: () => actionBarRef.value?.getRootElement() ?? null,
  seatingLifecycleBusy: () => props.seatingLifecycleBusy,
  workspaceBusy: () => plannerState.isWorkspaceBusy,
  hasSeatingAssignments: () => hasSeatingAssignments.value,
  canEditCurrentTemplate: () => plannerState.template !== null,
  availableTemplateCount: () => props.availableTemplates.length,
  showHistoryAction: () => props.showHistoryAction,
  showSmartControls: () => props.showSmartControls,
  smartSettingsOpen: () => props.smartSettingsOpen,
  openResetSeatingDialog,
  openHistory: () => emit("open-history"),
  editRoster: () => emit("edit-roster"),
  editCurrentTemplate,
  openSettings: () => emit("open-settings"),
});
const { showDistributionAction, shareExportPanelBindings } = useSeatingToolbarShareExport(props, {
  createShare: () => emit("share-link"),
  copyShare: (share) => emit("copy-share", share),
  revokeShare: (share) => emit("revoke-share", share),
  exportDefault: () => emit("export-default"),
  exportOption: (option) => emit("export-option", option),
});

async function startNewSeatingDraft(): Promise<void> {
  if (props.seatingLifecycleBusy) {
    return;
  }
  if (!props.selectedTemplateId) {
    showSeatingTemplateRequiredHint.value = true;
    await nextTick();
    seatingTemplateSelect.value?.focus();
    return;
  }

  showSeatingTemplateRequiredHint.value = false;
  emit("new-seating-draft", props.selectedTemplateId);
}

async function undoSeatingDraft(): Promise<void> {
  if (props.seatingLifecycleBusy) {
    return;
  }
  await plannerState.undoSeatingDraft();
}

async function redoSeatingDraft(): Promise<void> {
  if (props.seatingLifecycleBusy) {
    return;
  }
  await plannerState.redoSeatingDraft();
}

async function randomizeCurrentSeatingDraft(): Promise<void> {
  if (!canRandomizeSeating.value) {
    return;
  }
  await plannerState.runSeatingShuffle();
}

function changeSeatingTemplateFromEvent(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) {
    return;
  }

  showSeatingTemplateRequiredHint.value = false;
  emit("change-seating-template", target.value || null);
}

function editCurrentTemplate(): void {
  if (plannerState.template) {
    emit("edit-current-template", plannerState.template);
  }
}

</script>

<template>
  <div class="space-y-3">
    <PlannerWorkspaceActionBar
      ref="actionBarRef"
      :data-overflow-stage="stageLabel"
      :data-overflow-hidden-actions="hiddenContributionIds.join(',')"
      :data-overflow-context-inline-min-width="thresholds.context"
      :data-overflow-reset-inline-min-width="thresholds.reset"
      :data-overflow-distribution-inline-min-width="thresholds.distribution"
    >
      <template #primary>
        <div
          v-if="isUndoRedoInline"
          class="flex items-center [&>*+*]:-ml-px"
          data-overflow-contribution="undo-redo"
          data-test="seating-undo-redo-cluster"
        >
          <UiDenseActionButton
            icon-only
            label="Ångra"
            size="utility"
            group-position="start"
            data-test="undo-seating-draft"
            :disabled="!plannerState.canUndo || seatingLifecycleBusy"
            @click="void undoSeatingDraft()"
          >
            <template #leading>
              <UiGlyph
                meaning="undo"
                :size="16"
                :stroke-width="2.5"
              />
            </template>
          </UiDenseActionButton>
          <UiDenseActionButton
            icon-only
            label="Gör om"
            size="utility"
            group-position="end"
            data-test="redo-seating-draft"
            :disabled="!plannerState.canRedo || seatingLifecycleBusy"
            @click="void redoSeatingDraft()"
          >
            <template #leading>
              <UiGlyph
                meaning="redo"
                :size="16"
                :stroke-width="2.5"
              />
            </template>
          </UiDenseActionButton>
        </div>
        <div
          v-if="isNewDraftInline"
          data-overflow-contribution="new-draft"
        >
          <UiDenseActionButton
            label="Nytt utkast"
            data-test="new-seating-draft"
            :disabled="seatingLifecycleBusy"
            @click="void startNewSeatingDraft()"
          >
            <template #leading>
              <UiGlyph
                meaning="add"
                :size="14"
                :stroke-width="2.5"
              />
            </template>
          </UiDenseActionButton>
        </div>
        <div
          data-test="seating-randomize-control"
        >
          <UiDenseActionButton
            label="Slumpa"
            data-test="randomize-seating"
            :disabled="!canRandomizeSeating"
            @click="void randomizeCurrentSeatingDraft()"
          >
            <template #leading>
              <UiGlyph
                meaning="shuffle"
                :size="16"
                :stroke-width="2.5"
              />
            </template>
          </UiDenseActionButton>
        </div>
        <div
          :class="{ 'planner-toolbar-inline-overflowed': !isResetInline }"
          data-overflow-contribution="reset"
          :data-overflow-inline-hidden="!isResetInline ? 'true' : undefined"
          :aria-hidden="!isResetInline"
        >
          <UiDenseActionButton
            label="Börja om"
            data-test="reset-seating-draft"
            :disabled="seatingLifecycleBusy || plannerState.isWorkspaceBusy || !hasSeatingAssignments"
            tone="danger"
            @click="openResetSeatingDialog"
          >
            Börja om
          </UiDenseActionButton>
        </div>
      </template>

      <template
        v-if="availableTemplates.length > 0"
        #context
      >
        <label
          :class="[
            'block w-[11rem] shrink-0',
            !isContextInline ? 'planner-toolbar-inline-overflowed' : null,
          ]"
          data-overflow-contribution="context"
          :data-overflow-inline-hidden="!isContextInline ? 'true' : undefined"
          data-test="seating-workspace-setup"
          :aria-hidden="!isContextInline"
        >
          <select
            ref="seatingTemplateSelect"
            data-test="seating-template-select"
            aria-label="Klassrum"
            :class="[DENSE_FORM_INPUT_CLASS, 'pr-8']"
            :value="selectedTemplateId ?? ''"
            @change="changeSeatingTemplateFromEvent"
          >
            <option value="">
              Välj klassrum
            </option>
            <option
              v-for="template in availableTemplates"
              :key="template.id"
              :value="template.id"
            >
              {{ template.name }} · {{ template.seats.length }} platser
            </option>
          </select>
          <p
            v-if="showSeatingTemplateRequiredHint"
            class="mt-1 text-xs font-semibold text-critical"
          >
            Välj klassrum innan du startar ett nytt sittschema.
          </p>
        </label>
      </template>

      <template #secondary>
        <div
          v-if="showDistributionAction"
          :class="{ 'planner-toolbar-inline-overflowed': !isDistributionInline }"
          data-overflow-contribution="distribution"
          :data-overflow-inline-hidden="!isDistributionInline ? 'true' : undefined"
          :aria-hidden="!isDistributionInline"
        >
          <PlannerShareExportPanel
            v-bind="shareExportPanelBindings"
            trigger-test-id="seating-share-trigger"
          />
        </div>
        <PlannerToolbarOverflowMenu
          label="Fler sittplatsåtgärder"
          :items="secondaryActionItems"
          test-id="seating-actions-menu"
        >
          <template
            v-if="showOverflowPanel"
            #panel
          >
            <label
              v-if="hasContextOverflowPanel"
              class="block space-y-1"
              data-test="seating-overflow-template-control"
            >
              <span class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/55">
                Klassrum
              </span>
              <select
                ref="seatingTemplateSelect"
                data-test="seating-overflow-template-select"
                aria-label="Klassrum"
                :class="[DENSE_FORM_INPUT_CLASS, 'pr-8']"
                :value="selectedTemplateId ?? ''"
                @change="changeSeatingTemplateFromEvent"
              >
                <option value="">
                  Välj klassrum
                </option>
                <option
                  v-for="template in availableTemplates"
                  :key="template.id"
                  :value="template.id"
                >
                  {{ template.name }} · {{ template.seats.length }} platser
                </option>
              </select>
            </label>
          </template>
          <template
            v-if="showDistributionAction && !isDistributionInline"
            #footer
          >
            <PlannerShareExportPanel
              v-bind="shareExportPanelBindings"
              trigger-variant="menu-item"
              trigger-test-id="seating-overflow-share-trigger"
              trigger-meta=""
            />
          </template>
        </PlannerToolbarOverflowMenu>
      </template>
    </PlannerWorkspaceActionBar>

    <PlannerConfirmationDialog
      v-if="isResetSeatingDialogOpen"
      eyebrow="Börja om sittschema"
      title="Töm sittplaceringarna?"
      message="Det här rensar sittplaceringarna i det aktuella sittschemat och flyttar tillbaka alla elever till Ej placerade. Själva utkastet och klassrummet finns kvar."
      confirm-label="Börja om"
      @cancel="closeResetSeatingDialog"
      @confirm="confirmResetSeatingDraft"
    />
  </div>
</template>
