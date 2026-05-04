<script setup lang="ts">
/**
 * File export section for Klassrumskartan share/export surfaces.
 *
 * Relationships:
 * - rendered by `PlannerShareExportPanel` beside link management
 * - translates selected visual file options into export intents for the parent
 */

import { computed } from "vue";

import { IconDownload } from "../../../components/icons";
import { UiDenseSpinner } from "../../../components/ui";
import type {
  PlannerExportFileOption,
  PlannerExportOptionValue,
} from "./plannerShareExportActions";

const props = defineProps<{
  fileOptions: PlannerExportFileOption[];
  exportBusy?: boolean;
  exportErrorMessage?: string | null;
  fileOptionTestIdPrefix: string;
}>();

const emit = defineEmits<{
  (e: "export-default"): void;
  (e: "export-option", option: PlannerExportOptionValue): void;
}>();

const defaultFileOption = computed(() => {
  return props.fileOptions.find((option) => option.isDefault) ?? props.fileOptions[0] ?? null;
});

function selectFileOption(option: PlannerExportFileOption): void {
  if (props.exportBusy) {
    return;
  }
  if (option.id === defaultFileOption.value?.id) {
    emit("export-default");
    return;
  }
  emit("export-option", option.option);
}
</script>

<template>
  <section
    v-if="fileOptions.length > 0"
    class="px-3.5 py-3 md:px-4"
    aria-labelledby="planner-share-export-files-heading"
  >
    <div class="mb-2">
      <h3
        id="planner-share-export-files-heading"
        class="text-[11px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)] text-navy/65"
      >
        Filer
      </h3>
    </div>

    <p
      v-if="exportErrorMessage"
      class="mb-2 border border-burgundy/20 bg-burgundy/5 px-2 py-1.5 text-[11px] font-semibold text-burgundy"
      data-test="planner-export-error"
    >
      {{ exportErrorMessage }}
    </p>

    <div class="grid gap-1.5">
      <button
        v-for="option in fileOptions"
        :key="option.id"
        type="button"
        class="grid h-10 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 rounded-[4px] border border-navy/20 bg-white px-2.5 text-left text-navy transition-colors hover:border-navy/35 hover:bg-canvas/70 disabled:cursor-not-allowed disabled:opacity-55"
        :disabled="exportBusy"
        :data-test="`${fileOptionTestIdPrefix}-${option.id}`"
        :aria-busy="exportBusy && option.id === defaultFileOption?.id ? 'true' : undefined"
        @click="selectFileOption(option)"
      >
        <UiDenseSpinner
          v-if="exportBusy && option.id === defaultFileOption?.id"
          :size="12"
        />
        <IconDownload
          v-else
          :size="13"
        />
        <span class="truncate text-[11px] font-semibold leading-none">
          {{ option.label }}
        </span>
        <span
          v-if="option.isDefault"
          class="text-[10px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)] text-navy/50"
        >
          Standard
        </span>
      </button>
    </div>
  </section>
</template>
