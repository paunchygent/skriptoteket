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

import { IconAdjustments, IconHistory, IconRedo, IconShuffle, IconUndo } from "../../../components/icons";
import {
  DENSE_FORM_INPUT_CLASS,
  UiDenseActionButton,
  UiDenseIconButton,
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
import { usePlannerToolbarOverflow } from "./usePlannerToolbarOverflow";
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
    showHistoryAction?: boolean;
    showSmartControls?: boolean;
    showExportActions?: boolean;
  }>(),
  {
    availableTemplates: () => [],
    selectedTemplateId: null,
    smartSettingsOpen: false,
    seatingLifecycleBusy: false,
    exportBusy: false,
    exportStatusLabel: null,
    exportErrorMessage: null,
    showHistoryAction: true,
    showSmartControls: true,
    showExportActions: true,
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
}>();

const plannerState = useClassroomState();
const actionBarRef = ref<{
  getRootElement: () => HTMLDivElement | null;
} | null>(null);
const seatingTemplateSelect = ref<HTMLSelectElement | null>(null);
const showSeatingTemplateRequiredHint = ref(false);
const isResetSeatingDialogOpen = ref(false);

function isSeatingExportOption(option: PlannerExportOptionValue): option is SeatingExportOption {
  return option === "a3_landscape" || option === "a4_landscape" || option === "xlsx";
}

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
const {
  hiddenContributionIds,
  stageLabel,
  thresholds,
} = usePlannerToolbarOverflow({
  getRootElement: () => actionBarRef.value?.getRootElement() ?? null,
  contributions: [
    {
      id: "undo-redo",
      selector: '[data-overflow-contribution="undo-redo"]',
    },
    {
      id: "reset",
      selector: '[data-overflow-contribution="reset"]',
    },
    {
      id: "new-draft",
      selector: '[data-overflow-contribution="new-draft"]',
    },
    {
      id: "context",
      selector: '[data-overflow-contribution="context"]',
    },
    {
      id: "smart",
      selector: '[data-overflow-contribution="smart"]',
    },
  ],
});
const overflowActionItems = computed(() => {
  const items = [];
  if (hiddenContributionIds.value.includes("undo-redo")) {
    items.push({
      id: "undo-seating",
      label: "Ångra",
      icon: IconUndo,
      disabled: !plannerState.canUndo || props.seatingLifecycleBusy,
      testId: "seating-overflow-undo",
      onSelect: () => {
        void undoSeatingDraft();
      },
    });
    items.push({
      id: "redo-seating",
      label: "Gör om",
      icon: IconRedo,
      disabled: !plannerState.canRedo || props.seatingLifecycleBusy,
      testId: "seating-overflow-redo",
      onSelect: () => {
        void redoSeatingDraft();
      },
    });
  }
  if (hiddenContributionIds.value.includes("reset")) {
    items.push({
      id: "reset-seating",
      label: "Börja om",
      disabled: props.seatingLifecycleBusy || plannerState.isWorkspaceBusy || !hasSeatingAssignments.value,
      tone: "danger" as const,
      testId: "seating-overflow-reset",
      onSelect: openResetSeatingDialog,
    });
  }
  if (hiddenContributionIds.value.includes("new-draft")) {
    items.push({
      id: "new-seating-draft",
      label: "Nytt sittschema",
      disabled: props.seatingLifecycleBusy,
      testId: "seating-overflow-new-draft",
      onSelect: () => {
        void startNewSeatingDraft();
      },
    });
  }
  return items;
});
const secondaryActionItems = computed(() => {
  const items = [...overflowActionItems.value];
  if (props.showHistoryAction) {
    items.push({
      id: "history",
      label: "Historik",
      icon: IconHistory,
      disabled: props.seatingLifecycleBusy,
      testId: "seating-history",
      onSelect: () => emit("open-history"),
    });
  }
  items.push({
    id: "edit-roster",
    label: "Redigera klass",
    icon: IconAdjustments,
    disabled: plannerState.isWorkspaceBusy || props.seatingLifecycleBusy,
    testId: "edit-seating-roster",
    onSelect: () => emit("edit-roster"),
  });
  items.push({
    id: "edit-classroom",
    label: "Redigera klassrum",
    icon: IconAdjustments,
    disabled: !canEditCurrentTemplate.value || plannerState.isWorkspaceBusy || props.seatingLifecycleBusy,
    testId: "edit-current-template",
    onSelect: editCurrentTemplate,
  });
  return items;
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
  if (!isSeatingExportOption(option)) {
    return;
  }
  emit("export-option", option);
}

const isUndoRedoInline = computed(() => !hiddenContributionIds.value.includes("undo-redo"));
const isResetInline = computed(() => !hiddenContributionIds.value.includes("reset"));
const isNewDraftInline = computed(() => !hiddenContributionIds.value.includes("new-draft"));
const isContextInline = computed(() => !hiddenContributionIds.value.includes("context"));
const isSmartInline = computed(() => !hiddenContributionIds.value.includes("smart"));
const showOverflowPanel = computed(() => !isContextInline.value || !isSmartInline.value);
</script>

<template>
  <div class="space-y-3">
    <PlannerWorkspaceActionBar
      ref="actionBarRef"
      :data-overflow-stage="stageLabel"
      :data-overflow-hidden-actions="hiddenContributionIds.join(',')"
      :data-overflow-undo-redo-inline-min-width="thresholds['undo-redo']"
      :data-overflow-reset-inline-min-width="thresholds.reset"
      :data-overflow-new-draft-inline-min-width="thresholds['new-draft']"
      :data-overflow-context-inline-min-width="thresholds.context"
      :data-overflow-smart-inline-min-width="thresholds.smart"
    >
      <template #primary>
        <div
          v-if="isUndoRedoInline"
          class="flex items-center [&>*+*]:-ml-px"
          data-overflow-contribution="undo-redo"
          data-test="seating-undo-redo-cluster"
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
        <div
          v-if="isNewDraftInline"
          data-overflow-contribution="new-draft"
        >
          <UiDenseActionButton
            label="Nytt sittschema"
            data-test="new-seating-draft"
            :disabled="seatingLifecycleBusy"
            @click="void startNewSeatingDraft()"
          />
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
        <div
          v-if="showSmartControls && isSmartInline"
          class="flex items-center [&>*+*]:-ml-px"
          data-overflow-contribution="smart"
          data-test="seating-smart-cluster"
        >
          <UiDenseToggle
            data-test="seating-smart-toggle"
            label="Smart"
            group-position="start"
            :model-value="plannerState.draft?.smart_enabled ?? false"
            :disabled="plannerState.isWorkspaceBusy || seatingLifecycleBusy"
            @update:model-value="plannerState.setDraftSmartEnabled($event)"
          />
          <UiDenseIconButton
            data-test="seating-open-settings"
            label="Smart-inställningar"
            aria-label="Smart-inställningar"
            title="Öppna Smart-inställningar"
            size="utility"
            group-position="end"
            :active="smartSettingsOpen"
            :expanded="smartSettingsOpen"
            has-popup="dialog"
            :disabled="plannerState.isWorkspaceBusy || seatingLifecycleBusy"
            @click="emit('open-settings')"
          >
            <IconAdjustments :size="14" />
          </UiDenseIconButton>
        </div>
        <div
          v-if="isResetInline"
          data-overflow-contribution="reset"
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
        v-if="isContextInline"
        #context
      >
        <label
          class="block w-[11rem] shrink-0"
          data-overflow-contribution="context"
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

      <template #secondary>
        <PlannerExportActionGroup
          v-if="showExportActions"
          :busy="exportBusy"
          @export-default="emit('export-default')"
          @export-option="handleExportOption"
        />
        <UiDenseStatusPill
          v-if="showExportActions && exportStatus"
          :label="exportStatus.label"
          :tone="exportStatus.tone"
          :title="exportStatus.title"
          data-test="seating-export-status-pill"
        />
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
              v-if="!isContextInline"
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
            <div
              v-if="showSmartControls && !isSmartInline"
              class="space-y-2"
              data-test="seating-overflow-smart-control"
            >
              <span class="block text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/55">
                Smart
              </span>
              <div class="flex items-center [&>*+*]:-ml-px">
                <UiDenseToggle
                  data-test="seating-overflow-smart-toggle"
                  label="Smart"
                  group-position="start"
                  :model-value="plannerState.draft?.smart_enabled ?? false"
                  :disabled="plannerState.isWorkspaceBusy || seatingLifecycleBusy"
                  @update:model-value="plannerState.setDraftSmartEnabled($event)"
                />
                <UiDenseIconButton
                  data-test="seating-overflow-open-settings"
                  label="Smart-inställningar"
                  aria-label="Smart-inställningar"
                  title="Öppna Smart-inställningar"
                  size="utility"
                  group-position="end"
                  :active="smartSettingsOpen"
                  :expanded="smartSettingsOpen"
                  has-popup="dialog"
                  :disabled="plannerState.isWorkspaceBusy || seatingLifecycleBusy"
                  @click="emit('open-settings')"
                >
                  <IconAdjustments :size="14" />
                </UiDenseIconButton>
              </div>
            </div>
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
