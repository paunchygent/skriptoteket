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

import { UiGlyph } from "../../../components/ui/shared";
import {
  DENSE_FORM_INPUT_CLASS,
  UiDenseActionButton,
  denseActionValueClass,
} from "../../../components/ui";
import type { GroupingExportOption } from "../classroomPlannerExportApi";
import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";
import type { Roster } from "../classroomPlannerTypes";
import PlannerConfirmationDialog from "./PlannerConfirmationDialog.vue";
import PlannerShareExportPanel from "./PlannerShareExportPanel.vue";
import PlannerToolbarOverflowMenu from "./PlannerToolbarOverflowMenu.vue";
import PlannerWorkspaceActionBar from "./PlannerWorkspaceActionBar.vue";
import { useGroupingToolbarOverflow } from "./useGroupingToolbarOverflow";
import { useGroupingToolbarReset } from "./useGroupingToolbarReset";
import { useGroupingToolbarShareExport } from "./useGroupingToolbarShareExport";
import { useClassroomState } from "../useClassroomState";

const props = withDefaults(
  defineProps<{
    availableRosters?: Roster[];
    selectedRosterId?: string | null;
    smartSettingsOpen?: boolean;
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
    availableRosters: () => [],
    selectedRosterId: null,
    smartSettingsOpen: false,
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
  (e: "change-grouping-roster", rosterId: string): void;
  (e: "new-grouping-draft"): void;
  (e: "open-settings"): void;
  (e: "open-history"): void;
  (e: "edit-roster"): void;
  (e: "export-default"): void;
  (e: "export-option", option: GroupingExportOption): void;
  (e: "share-link"): void;
  (e: "copy-share", share: ClassroomPlannerShareArtifact): void;
  (e: "revoke-share", share: ClassroomPlannerShareArtifact): void;
}>();

const state = useClassroomState();
const actionBarRef = ref<{
  getRootElement: () => HTMLDivElement | null;
} | null>(null);
const {
  hasGroupingAssignments,
  isResetGroupingDialogOpen,
  openResetGroupingDialog,
  closeResetGroupingDialog,
  confirmResetGroupingDraft,
} = useGroupingToolbarReset(state);
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
} = useGroupingToolbarOverflow({
  getRootElement: () => actionBarRef.value?.getRootElement() ?? null,
  props,
  state,
  hasGroupingAssignments,
  openResetGroupingDialog,
  openHistory: () => emit("open-history"),
  editRoster: () => emit("edit-roster"),
  openSettings: () => emit("open-settings"),
});
const {
  shareExportPanelProps,
  shareExportPanelListeners,
  showDistributionAction,
} = useGroupingToolbarShareExport(props, {
  createShare: () => emit("share-link"),
  copyShare: (share) => emit("copy-share", share),
  revokeShare: (share) => emit("revoke-share", share),
  exportDefault: () => emit("export-default"),
  exportOption: (option) => emit("export-option", option),
});

function changeGroupingRoster(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement) || !target.value) {
    return;
  }
  emit("change-grouping-roster", target.value);
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
          data-test="grouping-undo-redo-cluster"
        >
          <UiDenseActionButton
            icon-only
            label="Ångra"
            size="utility"
            group-position="start"
            data-test="undo-grouping"
            :disabled="!state.canUndo"
            @mousedown.prevent
            @click="void state.undoGroupingDraft()"
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
            data-test="redo-grouping"
            :disabled="!state.canRedo"
            @mousedown.prevent
            @click="void state.redoGroupingDraft()"
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
            title="Nytt grupputkast"
            data-test="new-grouping-draft"
            :disabled="state.isWorkspaceBusy"
            @click="emit('new-grouping-draft')"
          />
        </div>
        <div
          data-test="grouping-randomize-control"
        >
          <UiDenseActionButton
            label="Slumpa"
            data-test="randomize-groups"
            :disabled="state.isWorkspaceBusy"
            @click="void state.runGroupingShuffle()"
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
            data-test="reset-grouping-draft"
            :disabled="state.isWorkspaceBusy || !hasGroupingAssignments"
            tone="danger"
            @click="openResetGroupingDialog"
          >
            Börja om
          </UiDenseActionButton>
        </div>
        <div
          class="flex items-center"
          data-test="grouping-group-count-control"
        >
          <div class="flex items-center [&>*+*]:-ml-px">
            <UiDenseActionButton
              icon-only
              label="Minska antal grupper"
              title="Ta bort sista gruppen"
              size="utility"
              group-position="start"
              data-test="decrement-group-count"
              :disabled="state.isWorkspaceBusy || removableGroupId === null"
              @click="decrementGroupCount"
            >
              <template #leading>
                <UiGlyph
                  meaning="decrement"
                  :size="16"
                  :stroke-width="2.5"
                />
              </template>
            </UiDenseActionButton>
            <span
              :class="denseActionValueClass({ groupPosition: 'middle' })"
              data-test="group-count-value"
              title="Antal grupper"
            >
              {{ groupCount }}
            </span>
            <UiDenseActionButton
              icon-only
              label="Öka antal grupper"
              title="Lägg till grupp"
              size="utility"
              group-position="end"
              data-test="increment-group-count"
              :disabled="state.isWorkspaceBusy"
              @click="incrementGroupCount"
            >
              <template #leading>
                <UiGlyph
                  meaning="increment"
                  :size="16"
                  :stroke-width="2.5"
                />
              </template>
            </UiDenseActionButton>
          </div>
        </div>
      </template>

      <template
        v-if="availableRosters.length > 0"
        #context
      >
        <label
          :class="[
            'block w-[8rem]',
            !isContextInline ? 'planner-toolbar-inline-overflowed' : null,
          ]"
          data-overflow-contribution="context"
          :data-overflow-inline-hidden="!isContextInline ? 'true' : undefined"
          data-test="grouping-roster-control"
          :aria-hidden="!isContextInline"
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
            v-bind="shareExportPanelProps"
            trigger-test-id="grouping-share-trigger"
            v-on="shareExportPanelListeners"
          />
        </div>
        <PlannerToolbarOverflowMenu
          label="Fler gruppåtgärder"
          :items="secondaryActionItems"
          test-id="grouping-actions-menu"
        >
          <template
            v-if="showOverflowPanel"
            #panel
          >
            <label
              v-if="hasContextOverflowPanel"
              class="block space-y-1"
              data-test="grouping-overflow-roster-control"
            >
              <span class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/55">
                Klass
              </span>
              <select
                aria-label="Klass"
                :class="[DENSE_FORM_INPUT_CLASS, 'pr-8']"
                :value="selectedRosterValue"
                data-test="grouping-overflow-roster-select"
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
          </template>
          <template
            v-if="showDistributionAction && !isDistributionInline"
            #footer
          >
            <PlannerShareExportPanel
              v-bind="shareExportPanelProps"
              trigger-variant="menu-item"
              trigger-test-id="grouping-overflow-share-trigger"
              trigger-meta=""
              v-on="shareExportPanelListeners"
            />
          </template>
        </PlannerToolbarOverflowMenu>
      </template>
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
