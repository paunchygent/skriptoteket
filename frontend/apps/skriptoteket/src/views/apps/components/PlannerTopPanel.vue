<script setup lang="ts">
/**
 * Shared top panel for the classroom planner workspace.
 *
 * This component keeps the class/workspace header stable across overview,
 * grouping, and seating so the segmented toggle, exit action, and compact
 * supporting information do not shift size or position when teachers move
 * between modes.
 */

import { computed, ref, type Component } from "vue";

import {
  IconCheck,
  IconGroupsWorkspace,
  IconMoreVertical,
  IconOverview,
  IconRules,
  IconSeatingPlan,
  IconX,
} from "../../../components/icons";
import UiSegmentedToggle, {
  type UiSegmentedToggleOption,
} from "../../../components/ui/UiSegmentedToggle.vue";

type WorkspaceMode = "overview" | "grouping" | "seating" | "rules";
type StatusTone = "neutral" | "success" | "warning" | "danger";

const props = withDefaults(
  defineProps<{
    title: string;
    contextLabel?: string | null;
    modeValue: WorkspaceMode;
    showGroupingOption?: boolean;
    showSeatingOption?: boolean;
    showRulesOption?: boolean;
    groupingDisabledReason?: string | null;
    seatingDisabledReason?: string | null;
    rulesDisabledReason?: string | null;
    supportingText?: string | null;
    compactStatusMessage?: string | null;
    statusLabel?: string | null;
    statusMessage?: string | null;
    statusTone?: StatusTone;
    exitLabel?: string;
  }>(),
  {
    contextLabel: null,
    showGroupingOption: true,
    showSeatingOption: true,
    showRulesOption: true,
    groupingDisabledReason: null,
    seatingDisabledReason: null,
    rulesDisabledReason: null,
    supportingText: null,
    compactStatusMessage: null,
    statusLabel: null,
    statusMessage: null,
    statusTone: "neutral",
    exitLabel: "Avsluta",
  },
);

const emit = defineEmits<{
  (e: "update:modeValue", value: WorkspaceMode): void;
  (e: "exit"): void;
}>();

const modeSheetOpen = ref(false);

const workspaceOptions = computed<UiSegmentedToggleOption[]>(() => {
  const options: UiSegmentedToggleOption[] = [
    { value: "overview", label: "Översikt", dataTest: "planner-mode-overview" },
  ];

  if (props.showGroupingOption) {
    options.push({
      value: "grouping",
      label: "Grupper",
      disabled: Boolean(props.groupingDisabledReason),
      title: props.groupingDisabledReason ?? undefined,
      dataTest: "planner-mode-grouping",
    });
  }

  if (props.showSeatingOption) {
    options.push({
      value: "seating",
      label: "Sittplatser",
      disabled: Boolean(props.seatingDisabledReason),
      title: props.seatingDisabledReason ?? undefined,
      dataTest: "planner-mode-seating",
    });
  }

  if (props.showRulesOption) {
    options.push({
      value: "rules",
      label: "Regler",
      disabled: Boolean(props.rulesDisabledReason),
      title: props.rulesDisabledReason ?? undefined,
      dataTest: "planner-mode-rules",
    });
  }

  return options;
});

const modeMetadata: Record<WorkspaceMode, {
  label: string;
  subtitle: string;
  icon: Component;
}> = {
  overview: {
    label: "Översikt",
    subtitle: "Snabböversikt",
    icon: IconOverview,
  },
  grouping: {
    label: "Grupper",
    subtitle: "Gruppindelning",
    icon: IconGroupsWorkspace,
  },
  seating: {
    label: "Sittplatser",
    subtitle: "Klassrumskarta",
    icon: IconSeatingPlan,
  },
  rules: {
    label: "Regler",
    subtitle: "Regler och relationer",
    icon: IconRules,
  },
};
const activeModeOption = computed(() => {
  return workspaceOptions.value.find((option) => option.value === props.modeValue)
    ?? workspaceOptions.value[0];
});
const activeModeLabel = computed(() => {
  const value = activeModeOption.value?.value;
  if (value === "overview" || value === "grouping" || value === "seating" || value === "rules") {
    return modeMetadata[value].label;
  }
  return activeModeOption.value?.label ?? "Översikt";
});

const statusToneClass = computed(() => {
  switch (props.statusTone) {
    case "success":
      return "border-success/45 bg-success/10 text-success";
    case "warning":
      return "border-warning/50 bg-warning/15 text-navy";
    case "danger":
      return "border-error/40 bg-error/10 text-error";
    default:
      return "border-navy/15 bg-canvas text-navy/70";
  }
});

const statusDotClass = computed(() => {
  switch (props.statusTone) {
    case "success":
      return "bg-success";
    case "warning":
      return "bg-warning";
    case "danger":
      return "bg-error";
    default:
      return "bg-navy/35";
  }
});

function selectWorkspaceMode(value: string): void {
  if (value === "overview" || value === "grouping" || value === "seating" || value === "rules") {
    modeSheetOpen.value = false;
    emit("update:modeValue", value);
  }
}

function openModeSheet(): void {
  modeSheetOpen.value = true;
}

function closeModeSheet(): void {
  modeSheetOpen.value = false;
}

function modeOptionMetadata(option: UiSegmentedToggleOption) {
  const value = option.value;
  if (value === "overview" || value === "grouping" || value === "seating" || value === "rules") {
    return modeMetadata[value];
  }
  return {
    label: option.label,
    subtitle: option.title ?? "",
    icon: IconOverview,
  };
}
</script>

<template>
  <article class="planner-top-panel space-y-3 border border-navy bg-white p-4 shadow-brutal-sm">
    <div class="planner-top-panel-heading flex items-start justify-between gap-3 border-b border-navy/20 pb-3">
      <div class="min-w-0 space-y-1">
        <h2 class="planner-shell-title">
          {{ title }}
        </h2>
        <p
          v-if="contextLabel"
          class="planner-top-panel-context text-sm text-navy/70"
        >
          {{ contextLabel }}
        </p>
      </div>

      <button
        type="button"
        class="btn-ghost planner-btn-ghost-canvas planner-btn-icon-md planner-top-panel-exit shrink-0"
        :aria-label="exitLabel"
        :title="exitLabel"
        data-test="planner-exit"
        @click="emit('exit')"
      >
        <IconX :size="16" />
      </button>
    </div>

    <div class="planner-desktop-mode-switch">
      <UiSegmentedToggle
        :model-value="modeValue"
        :options="workspaceOptions"
        aria-label="Välj arbetsyta i planeringen"
        data-test="planner-workspace-switch"
        density="default"
        variant="workspace"
        :columns="workspaceOptions.length"
        width="full"
        @update:model-value="selectWorkspaceMode"
      />
    </div>

    <div
      class="planner-phone-mode-switch"
      data-test="planner-phone-mode-switch"
    >
      <button
        type="button"
        class="planner-phone-mode-active"
        data-test="planner-phone-active-mode"
        @click="openModeSheet"
      >
        {{ activeModeLabel }}
      </button>
      <button
        type="button"
        class="planner-phone-mode-sheet-trigger"
        data-test="planner-phone-mode-sheet-trigger"
        :aria-expanded="modeSheetOpen"
        aria-haspopup="dialog"
        @click="openModeSheet"
      >
        Lägen
      </button>
    </div>

    <Teleport to="body">
      <div
        v-if="modeSheetOpen"
        class="planner-phone-sheet-backdrop"
        data-test="planner-phone-mode-sheet-backdrop"
        @click="closeModeSheet"
      />
      <section
        v-if="modeSheetOpen"
        class="planner-phone-mode-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="planner-phone-mode-sheet-title"
        data-test="planner-phone-mode-sheet"
        tabindex="-1"
        @keydown.esc="closeModeSheet"
      >
        <div class="planner-phone-sheet-handle" />
        <div class="flex items-center justify-between gap-3 border-b border-navy/20 pb-3">
          <h2
            id="planner-phone-mode-sheet-title"
            class="font-serif text-lg text-navy"
          >
            Byt läge
          </h2>
          <button
            type="button"
            class="btn-ghost planner-btn-ghost-canvas planner-btn-icon-md"
            aria-label="Stäng lägesväljaren"
            data-test="planner-phone-mode-sheet-close"
            @click="closeModeSheet"
          >
            <IconX :size="16" />
          </button>
        </div>

        <div class="mt-3 grid gap-2">
          <button
            v-for="option in workspaceOptions"
            :key="option.value"
            type="button"
            class="planner-phone-mode-sheet-row"
            :class="modeValue === option.value ? 'planner-phone-mode-sheet-row-active' : ''"
            :disabled="option.disabled"
            :title="option.disabled ? option.title : undefined"
            :data-test="`planner-phone-mode-sheet-${option.value}`"
            @click="selectWorkspaceMode(option.value)"
          >
            <component
              :is="modeOptionMetadata(option).icon"
              :size="18"
              class="shrink-0"
            />
            <span class="min-w-0 flex-1">
              <span class="block text-sm font-semibold leading-tight">
                {{ modeOptionMetadata(option).label }}
              </span>
              <span class="block text-xs leading-tight text-navy/60">
                {{ option.disabled ? option.title : modeOptionMetadata(option).subtitle }}
              </span>
            </span>
            <IconCheck
              v-if="modeValue === option.value"
              :size="16"
              aria-hidden="true"
            />
            <IconMoreVertical
              v-else
              :size="14"
              class="text-navy/35"
              aria-hidden="true"
            />
          </button>
        </div>
      </section>
    </Teleport>

    <div class="planner-top-panel-status flex min-h-[2rem] flex-wrap items-center gap-2 text-xs text-navy/65">
      <span
        v-if="statusLabel"
        class="planner-top-panel-status-pill inline-flex items-center gap-2 rounded-full border px-2.5 py-1 font-semibold uppercase tracking-[var(--huleedu-tracking-label)]"
        :class="statusToneClass"
        :title="statusLabel"
        data-test="planner-top-panel-status-label"
      >
        <span
          class="h-2 w-2 rounded-full"
          :class="statusDotClass"
        />
        <span class="planner-top-panel-status-label-text">
          {{ statusLabel }}
        </span>
      </span>
      <span
        v-if="statusMessage"
        data-test="planner-top-panel-status-message"
        class="planner-top-panel-status-copy text-[11px] text-navy/55"
      >
        {{ statusMessage }}
      </span>
      <span
        v-if="supportingText"
        data-test="planner-top-panel-supporting-text"
        class="planner-top-panel-status-copy text-[11px] text-navy/55"
      >
        {{ supportingText }}
      </span>
      <span
        v-if="compactStatusMessage"
        data-test="planner-top-panel-compact-status-message"
        class="planner-top-panel-compact-status-message text-[11px] text-navy/55"
      >
        {{ compactStatusMessage }}
      </span>
    </div>
  </article>
</template>
