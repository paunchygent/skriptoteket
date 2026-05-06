<script setup lang="ts">
/**
 * Detached grouping workspace toolbar.
 *
 * This component owns the grouping-only command row after ST-29-02 moved the
 * toolbar into the shared planner shell. It keeps first-row controls limited
 * to immediate actions plus the active class selector, while Smart tuning
 * lives in the adjacent settings drawer instead of in extra toolbar toggles.
 */

import { computed, ref, type Component } from "vue";

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
  UiDenseToggle,
  denseActionValueClass,
} from "../../../components/ui";
import { useToast } from "../../../composables/useToast";
import type { GroupingExportOption } from "../classroomPlannerExportApi";
import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";
import {
  SMART_DISABLED_NOTICE,
  isSmartEnabledByDefault,
} from "../classroomPlannerSmartDefaults";
import type { Roster } from "../classroomPlannerTypes";
import PlannerConfirmationDialog from "./PlannerConfirmationDialog.vue";
import PlannerShareExportPanel from "./PlannerShareExportPanel.vue";
import type {
  PlannerExportFileOption,
  PlannerExportOptionValue,
} from "./plannerShareExportActions";
import PlannerToolbarIconButton from "./PlannerToolbarIconButton.vue";
import PlannerToolbarOverflowMenu from "./PlannerToolbarOverflowMenu.vue";
import PlannerWorkspaceActionBar from "./PlannerWorkspaceActionBar.vue";
import { usePlannerToolbarOverflow } from "./usePlannerToolbarOverflow";
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

const PHONE_TOOLBAR_MEDIA_QUERY = "(max-width: 767px)";
const PHONE_CONTEXT_OVERFLOW_MAX_WIDTH_PX = 540;
const PHONE_RESET_OVERFLOW_MAX_WIDTH_PX = 400;
const OVERFLOW_PRIORITY_ORDER = ["context", "reset"];

function resolvePhoneHiddenContributionIds(rootElement: HTMLElement): string[] | null {
  if (typeof window === "undefined" || !window.matchMedia(PHONE_TOOLBAR_MEDIA_QUERY).matches) {
    return null;
  }
  if (rootElement.clientWidth > PHONE_CONTEXT_OVERFLOW_MAX_WIDTH_PX) {
    return null;
  }
  if (rootElement.clientWidth > PHONE_RESET_OVERFLOW_MAX_WIDTH_PX) {
    return OVERFLOW_PRIORITY_ORDER.slice(0, 1);
  }
  return OVERFLOW_PRIORITY_ORDER;
}

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

type OverflowActionItem = {
  id: string;
  label: string;
  icon?: Component;
  disabled: boolean;
  group?: "primary" | "secondary";
  responsiveVisibility?: "all" | "phone";
  tone?: "danger";
  testId: string;
  onSelect: () => void;
};

const state = useClassroomState();
const toast = useToast();
const actionBarRef = ref<{
  getRootElement: () => HTMLDivElement | null;
} | null>(null);
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
const exportOptions = computed<PlannerExportFileOption[]>(() => [
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
const {
  hiddenContributionIds,
  stageLabel,
  thresholds,
} = usePlannerToolbarOverflow({
  getRootElement: () => actionBarRef.value?.getRootElement() ?? null,
  forcedHiddenContributionIds: resolvePhoneHiddenContributionIds,
  contributions: [
    {
      id: "context",
      selector: '[data-overflow-contribution="context"]',
    },
    {
      id: "reset",
      selector: '[data-overflow-contribution="reset"]',
    },
  ],
});
const overflowActionItems = computed(() => {
  const isResetOverflowed = hiddenContributionIds.value.includes("reset");
  if (!isResetOverflowed) {
    return [];
  }
  return [{
    id: "reset-grouping",
    label: "Börja om",
    disabled: state.isWorkspaceBusy || !hasGroupingAssignments.value,
    group: "primary" as const,
    tone: "danger" as const,
    testId: "grouping-overflow-reset",
    responsiveVisibility: "all" as const,
    onSelect: openResetGroupingDialog,
  }];
});
const secondaryActionItems = computed(() => {
  const items: OverflowActionItem[] = [...overflowActionItems.value];
  if (props.showHistoryAction) {
    items.push({
      id: "history",
      label: "Historik",
      icon: IconHistory,
      disabled: state.isWorkspaceBusy,
      testId: "grouping-history",
      onSelect: () => emit("open-history"),
    });
  }
  items.push({
    id: "edit-roster",
    label: "Redigera klass",
    icon: IconAdjustments,
    disabled: state.isWorkspaceBusy,
    testId: "edit-grouping-roster",
    onSelect: () => emit("edit-roster"),
  });
  return items;
});
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

const isUndoRedoInline = computed(() => true);
const isResetInline = computed(() => !hiddenContributionIds.value.includes("reset"));
const isNewDraftInline = computed(() => true);
const isContextInline = computed(() => !hiddenContributionIds.value.includes("context"));
const isSmartInline = computed(() => false);
const showDistributionAction = computed(() => props.showExportActions || props.showShareLinkAction);
const hasContextOverflowPanel = computed(() => props.availableRosters.length > 0 && !isContextInline.value);
const hasSmartOverflowPanel = computed(() => props.showSmartControls);
const showOverflowPanel = computed(() => (
  hasContextOverflowPanel.value
  || hasSmartOverflowPanel.value
));

function setSmartEnabled(enabled: boolean): void {
  state.setDraftSmartEnabled(enabled);
  if (!enabled) {
    toast.warning(SMART_DISABLED_NOTICE);
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
    >
      <template #primary>
        <div
          v-if="isUndoRedoInline"
          class="flex items-center [&>*+*]:-ml-px"
          data-overflow-contribution="undo-redo"
          data-test="grouping-undo-redo-cluster"
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
              <IconShuffle :size="16" />
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
        <div
          :class="[
            'flex items-center [&>*+*]:-ml-px',
            !isSmartInline ? 'planner-toolbar-inline-overflowed' : null,
          ]"
          data-overflow-contribution="smart"
          :data-overflow-inline-hidden="!isSmartInline ? 'true' : undefined"
          data-test="grouping-smart-cluster"
          :aria-hidden="!isSmartInline"
        >
          <UiDenseToggle
            data-test="grouping-smart-toggle"
            label="Smart"
            group-position="start"
            :model-value="isSmartEnabledByDefault(state.draft)"
            :disabled="state.isWorkspaceBusy"
            @update:model-value="setSmartEnabled"
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
        <PlannerShareExportPanel
          v-if="showDistributionAction"
          :file-options="exportOptions"
          :shares="shares"
          :share-loading="shareLoading"
          :share-busy="shareBusy"
          :share-status-label="shareStatusLabel"
          :share-error-message="shareErrorMessage"
          :export-busy="exportBusy"
          :export-error-message="exportErrorMessage"
          :revoking-share-id="revokingShareId"
          :show-file-actions="showExportActions"
          :show-share-actions="showShareLinkAction"
          :show-revoke-action="showShareRevokeAction"
          trigger-test-id="grouping-share-trigger"
          panel-test-id="grouping-share-management"
          create-share-test-id="grouping-share-create"
          create-share-mobile-test-id="grouping-share-create-mobile"
          file-option-test-id-prefix="grouping-export-option"
          @create-share="emit('share-link')"
          @copy-share="emit('copy-share', $event)"
          @revoke-share="emit('revoke-share', $event)"
          @export-default="emit('export-default')"
          @export-option="handleExportOption"
        />
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
            <div
              v-if="hasSmartOverflowPanel"
              :class="[
                'space-y-2',
                hasContextOverflowPanel ? 'border-t border-navy/10 pt-3' : null,
              ]"
              data-test="grouping-overflow-smart-control"
            >
              <span class="block text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/55">
                Smart
              </span>
              <div class="flex items-center [&>*+*]:-ml-px">
                <UiDenseToggle
                  data-test="grouping-overflow-smart-toggle"
                  label="Smart"
                  group-position="start"
                  :model-value="isSmartEnabledByDefault(state.draft)"
                  :disabled="state.isWorkspaceBusy"
                  @update:model-value="setSmartEnabled"
                />
                <UiDenseIconButton
                  data-test="grouping-overflow-open-settings"
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
            </div>
          </template>
          <template
            v-if="showDistributionAction"
            #footer
          >
            <PlannerShareExportPanel
              :file-options="exportOptions"
              :shares="shares"
              :share-loading="shareLoading"
              :share-busy="shareBusy"
              :share-status-label="shareStatusLabel"
              :share-error-message="shareErrorMessage"
              :export-busy="exportBusy"
              :export-error-message="exportErrorMessage"
              :revoking-share-id="revokingShareId"
              :show-file-actions="showExportActions"
              :show-share-actions="showShareLinkAction"
              :show-revoke-action="showShareRevokeAction"
              trigger-variant="menu-item"
              trigger-test-id="grouping-overflow-share-trigger"
              trigger-meta=""
              panel-test-id="grouping-share-management"
              create-share-test-id="grouping-share-create"
              create-share-mobile-test-id="grouping-share-create-mobile"
              file-option-test-id-prefix="grouping-export-option"
              @create-share="emit('share-link')"
              @copy-share="emit('copy-share', $event)"
              @revoke-share="emit('revoke-share', $event)"
              @export-default="emit('export-default')"
              @export-option="handleExportOption"
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
