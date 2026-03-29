<script setup lang="ts">
/**
 * Detached seating workspace toolbar.
 *
 * This component owns the seating-only command row after ST-29-02 moved the
 * toolbar into the shared planner shell. It keeps export, history, smart-rule,
 * and classroom actions adjacent to the live canvas while removing the old
 * full-width interstitial status bands.
 */

import { computed, nextTick, ref } from "vue";

import { IconAdjustments, IconHistory, IconRedo, IconShuffle, IconUndo } from "../../../components/icons";
import {
  DENSE_FORM_INPUT_CLASS,
  UiDenseActionButton,
  UiDenseCompoundToggle,
  UiDenseStatusPill,
  UiDenseToggle,
  type DenseStatusTone,
} from "../../../components/ui";
import type { SeatingExportOption } from "../classroomPlannerExportApi";
import type { RoomTemplate } from "../classroomPlannerTypes";
import PlannerConfirmationDialog from "./PlannerConfirmationDialog.vue";
import PlannerExportActionGroup, { type PlannerExportOptionValue } from "./PlannerExportActionGroup.vue";
import PlannerToolbarIconButton from "./PlannerToolbarIconButton.vue";
import PlannerToolbarOverflowMenu from "./PlannerToolbarOverflowMenu.vue";
import PlannerWorkspaceActionBar from "./PlannerWorkspaceActionBar.vue";
import { useClassroomState } from "../useClassroomState";

const props = withDefaults(
  defineProps<{
    availableTemplates?: RoomTemplate[];
    selectedTemplateId?: string | null;
    seatingLifecycleBusy?: boolean;
    exportBusy?: boolean;
    exportStatusLabel?: string | null;
    exportErrorMessage?: string | null;
  }>(),
  {
    availableTemplates: () => [],
    selectedTemplateId: null,
    seatingLifecycleBusy: false,
    exportBusy: false,
    exportStatusLabel: null,
    exportErrorMessage: null,
  },
);

const emit = defineEmits<{
  (e: "change-seating-template", templateId: string | null): void;
  (e: "new-seating-draft", templateId: string): void;
  (e: "edit-roster"): void;
  (e: "edit-current-template", template: RoomTemplate): void;
  (e: "open-history"): void;
  (e: "open-rules"): void;
  (e: "export-default"): void;
  (e: "export-option", option: SeatingExportOption): void;
}>();

const plannerState = useClassroomState();
const seatingTemplateSelect = ref<HTMLSelectElement | null>(null);
const showSeatingTemplateRequiredHint = ref(false);
const isResetSeatingDialogOpen = ref(false);

const canEditCurrentTemplate = computed(() => plannerState.template !== null);
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
const hasSeatingAssignments = computed(() => plannerState.seatAssignments.length > 0);
const activeRuleCount = computed(() => {
  const nearTeacherRuleCount = plannerState.seatingPreferences.some((preference) => preference.near_teacher)
    ? 1
    : 0;
  return nearTeacherRuleCount + plannerState.relationshipRules.length;
});
const activeRuleLabel = computed(() => {
  if (activeRuleCount.value === 1) {
    return "1 regel";
  }
  return `${activeRuleCount.value} regler`;
});
const exportStatus = computed<{
  label: string;
  tone: DenseStatusTone;
  title?: string;
} | null>(() => {
  if (props.exportBusy) {
    if (props.exportStatusLabel?.includes("längre tid än väntat")) {
      return {
        label: "Kontrollerar export…",
        tone: "warning",
        title: props.exportStatusLabel,
      };
    }
    return {
      label: props.exportStatusLabel ?? "Exporterar…",
      tone: "neutral",
      title: props.exportStatusLabel ?? undefined,
    };
  }
  if (props.exportErrorMessage) {
    return {
      label: "Exportproblem",
      tone: "error",
      title: props.exportErrorMessage,
    };
  }
  return null;
});
const secondaryActionItems = computed(() => [
  {
    id: "history",
    label: "Historik",
    icon: IconHistory,
    disabled: props.seatingLifecycleBusy,
    testId: "seating-history",
    onSelect: () => emit("open-history"),
  },
  {
    id: "edit-roster",
    label: "Redigera klass",
    icon: IconAdjustments,
    disabled: plannerState.isWorkspaceBusy || props.seatingLifecycleBusy,
    testId: "edit-seating-roster",
    onSelect: () => emit("edit-roster"),
  },
  {
    id: "edit-classroom",
    label: "Redigera klassrum",
    icon: IconAdjustments,
    disabled: !canEditCurrentTemplate.value || plannerState.isWorkspaceBusy || props.seatingLifecycleBusy,
    testId: "edit-current-template",
    onSelect: editCurrentTemplate,
  },
]);

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

function openResetSeatingDialog(): void {
  if (props.seatingLifecycleBusy || plannerState.isWorkspaceBusy || !hasSeatingAssignments.value) {
    return;
  }
  isResetSeatingDialogOpen.value = true;
}

function closeResetSeatingDialog(): void {
  isResetSeatingDialogOpen.value = false;
}

function confirmResetSeatingDraft(): void {
  plannerState.clearSeatingAssignments();
  closeResetSeatingDialog();
}

function editCurrentTemplate(): void {
  if (plannerState.template) {
    emit("edit-current-template", plannerState.template);
  }
}

function handleExportOption(option: PlannerExportOptionValue): void {
  emit("export-option", option as SeatingExportOption);
}
</script>

<template>
  <div class="space-y-3">
    <PlannerWorkspaceActionBar>
      <template #leading>
        <label
          class="block w-[12rem]"
          data-test="seating-workspace-setup"
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
            class="mt-1 text-xs font-semibold text-burgundy"
          >
            Välj klassrum innan du startar ett nytt sittschema.
          </p>
        </label>
      </template>

      <div
        class="flex items-center [&>*+*]:-ml-px"
        data-test="seating-history-cluster"
      >
        <PlannerToolbarIconButton
          label="Ångra"
          size="utility"
          group-position="start"
          data-test="undo-seating-draft"
          :disabled="!plannerState.canUndo || seatingLifecycleBusy"
          @click="void undoSeatingDraft()"
        >
          <IconUndo :size="16" />
        </PlannerToolbarIconButton>
        <PlannerToolbarIconButton
          label="Gör om"
          size="utility"
          group-position="end"
          data-test="redo-seating-draft"
          :disabled="!plannerState.canRedo || seatingLifecycleBusy"
          @click="void redoSeatingDraft()"
        >
          <IconRedo :size="16" />
        </PlannerToolbarIconButton>
      </div>
      <UiDenseActionButton
        label="Slumpa"
        data-test="randomize-seating"
        :disabled="!canRandomizeSeating"
        @click="void randomizeCurrentSeatingDraft()"
      >
        <template #leading>
          <IconShuffle :size="16" />
        </template>
      </UiDenseActionButton>
      <UiDenseCompoundToggle
        root-test-id="seating-smart-toggle"
        label="Smart"
        :model-value="plannerState.draft?.smart_enabled ?? false"
        :disabled="plannerState.isWorkspaceBusy || seatingLifecycleBusy"
        action-label="Regler"
        action-title="Öppna regler"
        :action-disabled="plannerState.isWorkspaceBusy || seatingLifecycleBusy"
        action-test-id="seating-open-rules"
        @update:model-value="plannerState.setDraftSmartEnabled($event)"
        @action="emit('open-rules')"
      />
      <UiDenseToggle
        data-test="seating-use-history-toggle"
        label="Använd historik"
        :model-value="plannerState.draft?.use_history ?? false"
        :disabled="plannerState.isWorkspaceBusy || seatingLifecycleBusy"
        @update:model-value="plannerState.setDraftUseHistoryEnabled($event)"
      />
      <UiDenseStatusPill
        v-if="activeRuleCount > 0"
        :label="activeRuleLabel"
        :title="`${activeRuleLabel} aktiva i Regler`"
        data-test="seating-active-rule-count"
      />
      <UiDenseActionButton
        label="Börja om"
        data-test="reset-seating-draft"
        :disabled="seatingLifecycleBusy || plannerState.isWorkspaceBusy || !hasSeatingAssignments"
        tone="danger"
        @click="openResetSeatingDialog"
      >
        Börja om
      </UiDenseActionButton>
      <UiDenseActionButton
        label="Nytt sittschema"
        data-test="new-seating-draft"
        :disabled="seatingLifecycleBusy"
        @click="void startNewSeatingDraft()"
      />
      <PlannerExportActionGroup
        :busy="exportBusy"
        @export-default="emit('export-default')"
        @export-option="handleExportOption"
      />
      <UiDenseStatusPill
        v-if="exportStatus"
        :label="exportStatus.label"
        :tone="exportStatus.tone"
        :title="exportStatus.title"
        data-test="seating-export-status-pill"
      />
      <PlannerToolbarOverflowMenu
        label="Fler sittplatsåtgärder"
        :items="secondaryActionItems"
        test-id="seating-actions-menu"
      />
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
