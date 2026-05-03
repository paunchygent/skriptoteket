<script setup lang="ts">
/**
 * Compact export action cluster for planner exports.
 *
 * Relationships:
 * - planner-facing wrapper over the shared `UiDenseSplitButton` primitive
 * - keeps planner export semantics local while freezing the shared split-button contract
 */

import { computed } from "vue";

import { UiDenseSplitButton, type UiDenseSplitButtonItem } from "../../../components/ui";
import type {
  PlannerExportOption,
  PlannerExportOptionValue,
} from "./plannerShareExportActions";

const props = withDefaults(
  defineProps<{
    options?: PlannerExportOption[];
    defaultLabel?: string;
    busyLabel?: string;
    menuAriaLabel?: string;
    groupTestId?: string;
    defaultButtonTestId?: string;
    menuTriggerTestId?: string;
    optionTestIdPrefix?: string;
    disabled?: boolean;
    busy?: boolean;
  }>(),
  {
    options: () => [
      {
        id: "a3",
        label: "Affisch (A3)",
        option: "a3_landscape",
        isDefault: true,
      },
      {
        id: "a4",
        label: "Affisch (A4)",
        option: "a4_landscape",
      },
      {
        id: "xlsx",
        label: "Excel (.xlsx)",
        option: "xlsx",
      },
    ],
    defaultLabel: "Exportera",
    busyLabel: "Exporterar…",
    menuAriaLabel: "Fler exportval",
    groupTestId: "seating-export-group",
    defaultButtonTestId: "seating-export-default",
    menuTriggerTestId: "seating-export-menu-trigger",
    optionTestIdPrefix: "seating-export-option",
    disabled: false,
    busy: false,
  },
);

const emit = defineEmits<{
  (e: "export-default"): void;
  (e: "export-option", option: PlannerExportOptionValue): void;
  (e: "share-link"): void;
}>();

const exportOptions = computed<PlannerExportOption[]>(() => props.options);
const splitItems = computed<UiDenseSplitButtonItem[]>(() => {
  return exportOptions.value.map((option) => ({
    id: option.id,
    label: option.label,
    metaLabel: option.isDefault ? "Standard" : null,
  }));
});

function selectOption(optionId: string): void {
  const option = exportOptions.value.find((item) => item.id === optionId);
  if (!option) {
    return;
  }
  if ("action" in option) {
    emit("share-link");
    return;
  }
  emit("export-option", option.option);
}
</script>

<template>
  <div
    class="relative flex items-stretch border-l border-navy/15 pl-3"
    :data-test="groupTestId"
  >
    <UiDenseSplitButton
      :label="defaultLabel"
      :busy-label="busyLabel"
      :menu-label="menuAriaLabel"
      :items="splitItems"
      :disabled="disabled"
      :busy="busy"
      :root-test-id="groupTestId"
      :main-button-test-id="defaultButtonTestId"
      :menu-trigger-test-id="menuTriggerTestId"
      :item-test-id-prefix="optionTestIdPrefix"
      @trigger="emit('export-default')"
      @select="selectOption"
    />
  </div>
</template>
