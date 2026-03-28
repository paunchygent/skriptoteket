<script setup lang="ts">
/**
 * Rules-workspace tool rail.
 *
 * This component keeps the active smart-rule tool obvious through icon-first
 * buttons and a dedicated clear-selection affordance.
 */

import { computed } from "vue";

import {
  IconBan,
  IconLink2,
  IconSchool,
} from "../../../components/icons";
import type { SeatingSmartTool } from "../classroomPlannerTypes";

const props = withDefaults(defineProps<{
  activeTool: SeatingSmartTool | null;
  canEdit?: boolean;
  pendingSelectionCount?: number;
}>(), {
  canEdit: false,
  pendingSelectionCount: 0,
});

const emit = defineEmits<{
  (e: "select-tool", tool: SeatingSmartTool): void;
  (e: "clear-selection"): void;
}>();

const toolButtons = computed(() => [
  {
    id: "near_teacher",
    label: "Närmare läraren",
    icon: IconSchool,
  },
  {
    id: "keep_apart",
    label: "Håll isär",
    icon: IconBan,
  },
  {
    id: "keep_near",
    label: "Håll nära",
    icon: IconLink2,
  },
] satisfies Array<{
  id: SeatingSmartTool;
  label: string;
  icon: typeof IconSchool;
}>);
</script>

<template>
  <aside class="border border-navy bg-white p-3 shadow-brutal-sm">
    <div class="space-y-1 border-b border-navy/20 pb-3">
      <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
        Verktyg
      </p>
      <p class="text-sm text-navy/70">
        Ett verktyg åt gången.
      </p>
    </div>

    <div class="mt-3 flex flex-col gap-2">
      <button
        v-for="tool in toolButtons"
        :key="tool.id"
        type="button"
        class="flex items-center gap-3 border px-3 py-3 text-left transition-colors disabled:cursor-not-allowed disabled:border-navy/15 disabled:text-navy/35"
        :class="
          activeTool === tool.id
            ? 'border-burgundy bg-burgundy/10 text-burgundy shadow-brutal-sm'
            : 'border-navy/20 bg-white text-navy hover:bg-canvas'
        "
        :data-test="`rules-tool-${tool.id}`"
        :disabled="!canEdit"
        @click="emit('select-tool', tool.id)"
      >
        <component
          :is="tool.icon"
          :size="18"
        />
        <span class="text-sm font-semibold">
          {{ tool.label }}
        </span>
      </button>
    </div>

    <div class="mt-4 border-t border-navy/20 pt-3">
      <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
        Markering
      </p>
      <p class="mt-1 text-sm text-navy/70">
        {{ pendingSelectionCount }} valda
      </p>
      <button
        type="button"
        class="btn-ghost mt-3 w-full border-navy/30 bg-white px-3 py-1.5 shadow-none"
        data-test="rules-clear-selection"
        :disabled="pendingSelectionCount === 0"
        @click="emit('clear-selection')"
      >
        Rensa markering
      </button>
    </div>
  </aside>
</template>
