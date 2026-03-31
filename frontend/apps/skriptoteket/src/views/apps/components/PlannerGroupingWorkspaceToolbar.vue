<script setup lang="ts">
/**
 * Detached grouping workspace toolbar.
 *
 * This component owns the grouping-only command row after ST-29-02 moved the
 * toolbar into the shared planner shell. It keeps first-row controls limited
 * to immediate actions plus the active class selector, while Smart tuning
 * lives in the adjacent settings drawer instead of in extra toolbar toggles.
 */

import { computed, ref } from "vue";

import {
  IconAdjustments,
  IconHistory,
  IconMinus,
  IconPlus,
  IconRedo,
  IconShuffle,
  IconUndo,
} from "../../../components/icons";
import {
  DENSE_FORM_INPUT_CLASS,
  UiDenseActionButton,
  UiDenseIconButton,
  UiDenseStatusPill,
  UiDenseToggle,
  denseActionValueClass,
  type DenseStatusTone,
} from "../../../components/ui";
import type { GroupingExportOption } from "../classroomPlannerExportApi";
import type { Roster } from "../classroomPlannerTypes";
import PlannerConfirmationDialog from "./PlannerConfirmationDialog.vue";
import PlannerExportActionGroup, {
  type PlannerExportOption,
  type PlannerExportOptionValue,
} from "./PlannerExportActionGroup.vue";
import PlannerToolbarIconButton from "./PlannerToolbarIconButton.vue";
import PlannerToolbarOverflowMenu from "./PlannerToolbarOverflowMenu.vue";
import PlannerWorkspaceActionBar from "./PlannerWorkspaceActionBar.vue";
import { useClassroomState } from "../useClassroomState";

const props = withDefaults(
  defineProps<{
    availableRosters?: Roster[];
    selectedRosterId?: string | null;
    smartSettingsOpen?: boolean;
    exportBusy?: boolean;
    exportStatusLabel?: string | null;
    exportErrorMessage?: string | null;
  }>(),
  {
    availableRosters: () => [],
    selectedRosterId: null,
    smartSettingsOpen: false,
    exportBusy: false,
    exportStatusLabel: null,
    exportErrorMessage: null,
  },
);

const emit = defineEmits<{
  (e: "change-grouping-roster", rosterId: string): void;
  (e: "new-grouping-draft"): void;
  (e: "open-settings"): void;
  (e: "open-history"): void;
  (e: "edit-roster"): void;
  (e: "export-default"): void;
  (e: "export-option", option: GroupingExportOption): void;
}>();

const state = useClassroomState();
const hasGroupingAssignments = computed(() => state.groupAssignments.length > 0);
const groupCount = computed(() => state.groups.length);
const selectedRosterValue = computed(() => {
  return props.selectedRosterId ?? props.availableRosters[0]?.id ?? "";
});
const removableGroupId = computed(() => {
  if (state.groups.length <= 1) {
    return null;
  }
  return [...state.groups].sort((left, right) => left.sort_order - right.sort_order).at(-1)?.id ?? null;
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
const exportOptions = computed<PlannerExportOption[]>(() => [
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
const secondaryActionItems = computed(() => [
  {
    id: "history",
    label: "Historik",
    icon: IconHistory,
    disabled: state.isWorkspaceBusy,
    testId: "grouping-history",
    onSelect: () => emit("open-history"),
  },
  {
    id: "edit-roster",
    label: "Redigera klass",
    icon: IconAdjustments,
    disabled: state.isWorkspaceBusy,
    testId: "edit-grouping-roster",
    onSelect: () => emit("edit-roster"),
  },
]);
const isResetGroupingDialogOpen = ref(false);

function isGroupingExportOption(option: PlannerExportOptionValue): option is GroupingExportOption {
  return option === "xlsx" || option === "pdf_a4_portrait";
}

function changeGroupingRoster(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement) || !target.value) {
    return;
  }
  emit("change-grouping-roster", target.value);
}

function openResetGroupingDialog(): void {
  if (state.isWorkspaceBusy || !hasGroupingAssignments.value) {
    return;
  }
  isResetGroupingDialogOpen.value = true;
}

function closeResetGroupingDialog(): void {
  isResetGroupingDialogOpen.value = false;
}

function confirmResetGroupingDraft(): void {
  state.clearGroupingAssignments();
  closeResetGroupingDialog();
}

function handleExportOption(option: PlannerExportOptionValue): void {
  if (!isGroupingExportOption(option)) {
    return;
  }
  emit("export-option", option);
}

function decrementGroupCount(): void {
  if (state.isWorkspaceBusy || removableGroupId.value === null) {
    return;
  }
  state.removeGroup(removableGroupId.value);
}

function incrementGroupCount(): void {
  if (state.isWorkspaceBusy) {
    return;
  }
  state.addGroup();
}
</script>

<template>
  <div class="space-y-3">
    <PlannerWorkspaceActionBar>
      <template #leading>
        <div
          class="flex items-center [&>*+*]:-ml-px"
          data-test="grouping-history-cluster"
        >
          <PlannerToolbarIconButton
            label="Ångra"
            size="utility"
            group-position="start"
            data-test="undo-grouping"
            :disabled="!state.canUndo"
            @mousedown.prevent
            @click="void state.undoGroupingDraft()"
          >
            <IconUndo :size="16" />
          </PlannerToolbarIconButton>
          <PlannerToolbarIconButton
            label="Gör om"
            size="utility"
            group-position="end"
            data-test="redo-grouping"
            :disabled="!state.canRedo"
            @mousedown.prevent
            @click="void state.redoGroupingDraft()"
          >
            <IconRedo :size="16" />
          </PlannerToolbarIconButton>
        </div>
        <UiDenseActionButton
          label="Nytt utkast"
          title="Nytt grupputkast"
          data-test="new-grouping-draft"
          :disabled="state.isWorkspaceBusy"
          @click="emit('new-grouping-draft')"
        />
        <UiDenseActionButton
          label="Slumpa"
          data-test="randomize-groups"
          :disabled="state.isWorkspaceBusy"
          @click="void state.runGroupingShuffle()"
        >
          <template #leading>
            <IconShuffle :size="16" />
          </template>
        </UiDenseActionButton>
        <div
          class="flex items-center [&>*+*]:-ml-px"
          data-test="grouping-smart-cluster"
        >
          <UiDenseToggle
            data-test="grouping-smart-toggle"
            label="Smart"
            group-position="start"
            :model-value="state.draft?.smart_enabled ?? false"
            :disabled="state.isWorkspaceBusy"
            @update:model-value="state.setDraftSmartEnabled($event)"
          />
          <UiDenseIconButton
            data-test="grouping-open-settings"
            label="Smart-inställningar"
            aria-label="Smart-inställningar"
            title="Öppna Smart-inställningar"
            size="utility"
            group-position="end"
            :active="smartSettingsOpen"
            :expanded="smartSettingsOpen"
            has-popup="dialog"
            :disabled="state.isWorkspaceBusy"
            @click="emit('open-settings')"
          >
            <IconAdjustments :size="14" />
          </UiDenseIconButton>
        </div>
        <UiDenseActionButton
          label="Börja om"
          data-test="reset-grouping-draft"
          :disabled="state.isWorkspaceBusy || !hasGroupingAssignments"
          tone="danger"
          @click="openResetGroupingDialog"
        >
          Börja om
        </UiDenseActionButton>
        <div
          class="flex items-center"
          data-test="grouping-group-count-control"
        >
          <div class="flex items-center [&>*+*]:-ml-px">
            <PlannerToolbarIconButton
              label="Minska antal grupper"
              title="Ta bort sista gruppen"
              size="utility"
              group-position="start"
              data-test="decrement-group-count"
              :disabled="state.isWorkspaceBusy || removableGroupId === null"
              @click="decrementGroupCount"
            >
              <IconMinus :size="16" />
            </PlannerToolbarIconButton>
            <span
              :class="denseActionValueClass({ groupPosition: 'middle' })"
              data-test="group-count-value"
              title="Antal grupper"
            >
              {{ groupCount }}
            </span>
            <PlannerToolbarIconButton
              label="Öka antal grupper"
              title="Lägg till grupp"
              size="utility"
              group-position="end"
              data-test="increment-group-count"
              :disabled="state.isWorkspaceBusy"
              @click="incrementGroupCount"
            >
              <IconPlus :size="16" />
            </PlannerToolbarIconButton>
          </div>
        </div>
      </template>

      <label
        v-if="availableRosters.length > 0"
        class="block w-[8rem]"
        data-test="grouping-roster-control"
      >
        <select
          aria-label="Klass"
          :class="[DENSE_FORM_INPUT_CLASS, 'pr-8']"
          :value="selectedRosterValue"
          data-test="grouping-roster-select"
          @change="changeGroupingRoster"
        >
          <option
            v-for="roster in availableRosters"
            :key="roster.id"
            :value="roster.id"
          >
            {{ roster.name }}
          </option>
        </select>
      </label>
      <PlannerExportActionGroup
        :busy="exportBusy"
        :options="exportOptions"
        group-test-id="grouping-export-group"
        default-button-test-id="grouping-export-default"
        menu-trigger-test-id="grouping-export-menu-trigger"
        option-test-id-prefix="grouping-export-option"
        @export-default="emit('export-default')"
        @export-option="handleExportOption"
      />
      <UiDenseStatusPill
        v-if="exportStatus"
        :label="exportStatus.label"
        :tone="exportStatus.tone"
        :title="exportStatus.title"
        data-test="grouping-export-status-pill"
      />
      <PlannerToolbarOverflowMenu
        label="Fler gruppåtgärder"
        :items="secondaryActionItems"
        test-id="grouping-actions-menu"
      />
    </PlannerWorkspaceActionBar>

    <PlannerConfirmationDialog
      v-if="isResetGroupingDialogOpen"
      eyebrow="Börja om grupper"
      title="Töm gruppindelningen?"
      message="Det här rensar gruppplaceringarna i det aktuella grupputkastet och flyttar tillbaka alla elever till Ej grupperade. Själva utkastet finns kvar."
      confirm-label="Börja om"
      @cancel="closeResetGroupingDialog"
      @confirm="confirmResetGroupingDraft"
    />
  </div>
</template>
