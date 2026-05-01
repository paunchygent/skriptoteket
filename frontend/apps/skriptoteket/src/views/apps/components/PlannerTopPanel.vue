<script setup lang="ts">
/**
 * Shared top panel for the classroom planner workspace.
 *
 * This component keeps the class/workspace header stable across overview,
 * grouping, and seating so the segmented toggle, exit action, and compact
 * supporting information do not shift size or position when teachers move
 * between modes.
 */

import { computed } from "vue";

import { IconX } from "../../../components/icons";
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

const statusToneClass = computed(() => {
  switch (props.statusTone) {
    case "success":
      return "border-emerald-300/80 bg-emerald-50 text-emerald-800";
    case "warning":
      return "border-amber-300/80 bg-amber-50 text-amber-800";
    case "danger":
      return "border-rose-300/80 bg-rose-50 text-rose-800";
    default:
      return "border-navy/15 bg-canvas text-navy/70";
  }
});

const statusDotClass = computed(() => {
  switch (props.statusTone) {
    case "success":
      return "bg-emerald-600";
    case "warning":
      return "bg-amber-500";
    case "danger":
      return "bg-rose-600";
    default:
      return "bg-navy/35";
  }
});

function selectWorkspaceMode(value: string): void {
  if (value === "overview" || value === "grouping" || value === "seating" || value === "rules") {
    emit("update:modeValue", value);
  }
}
</script>

<template>
  <article class="space-y-3 border border-navy bg-white p-4 shadow-brutal-sm">
    <div class="flex flex-col gap-3 border-b border-navy/20 pb-3 lg:flex-row lg:items-center lg:justify-between">
      <div class="min-w-0 space-y-1">
        <h2 class="planner-shell-title">
          {{ title }}
        </h2>
        <p
          v-if="contextLabel"
          class="text-sm text-navy/70"
        >
          {{ contextLabel }}
        </p>
      </div>

      <button
        type="button"
        class="btn-ghost planner-btn-ghost-canvas planner-btn-icon-md self-start lg:self-auto"
        :aria-label="exitLabel"
        :title="exitLabel"
        data-test="planner-exit"
        @click="emit('exit')"
      >
        <IconX :size="16" />
      </button>
    </div>

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

    <div class="flex min-h-[2rem] flex-wrap items-center gap-2 text-xs text-navy/65">
      <span
        v-if="statusLabel"
        class="inline-flex items-center gap-2 rounded-full border px-2.5 py-1 font-semibold uppercase tracking-[var(--huleedu-tracking-label)]"
        :class="statusToneClass"
      >
        <span
          class="h-2 w-2 rounded-full"
          :class="statusDotClass"
        />
        {{ statusLabel }}
      </span>
      <span
        v-if="statusMessage"
        data-test="planner-top-panel-status-message"
        class="text-[11px] text-navy/55"
      >
        {{ statusMessage }}
      </span>
      <span
        v-if="supportingText"
        data-test="planner-top-panel-supporting-text"
        class="text-[11px] text-navy/55"
      >
        {{ supportingText }}
      </span>
    </div>
  </article>
</template>
