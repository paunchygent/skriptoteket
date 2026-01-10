<script setup lang="ts">
import { computed } from "vue";
import type { components } from "../../api/openapi";

type UiTableOutput = components["schemas"]["UiTableOutput"];
type JsonValue = components["schemas"]["JsonValue"];

const props = withDefaults(defineProps<{ output: UiTableOutput; density?: "default" | "compact" }>(), {
  density: "default",
});

const isCompact = computed(() => props.density === "compact");

function formatCell(value: JsonValue | undefined): string {
  if (value === undefined || value === null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}
</script>

<template>
  <div :class="[isCompact ? 'panel-inset' : 'border border-navy bg-white shadow-brutal-sm']">
    <div
      v-if="props.output.title"
      :class="[isCompact ? 'px-3 py-2 border-b border-navy/20 font-semibold text-[11px] text-navy' : 'px-4 py-3 border-b border-navy font-semibold text-navy']"
    >
      {{ props.output.title }}
    </div>

    <div class="overflow-x-auto">
      <table :class="[isCompact ? 'min-w-full text-[11px]' : 'min-w-full text-sm']">
        <thead>
          <tr :class="[isCompact ? 'text-left text-navy/70' : 'text-left text-navy/70']">
            <th
              v-for="col in props.output.columns"
              :key="col.key"
              :class="[isCompact ? 'px-3 py-2 border-b border-navy/20 whitespace-nowrap' : 'px-4 py-2 border-b border-navy/20 whitespace-nowrap']"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody class="text-navy">
          <tr
            v-for="(row, rowIndex) in props.output.rows"
            :key="rowIndex"
            class="border-b border-navy/10"
          >
            <td
              v-for="col in props.output.columns"
              :key="col.key"
              :class="[isCompact ? 'px-3 py-2 align-top whitespace-nowrap' : 'px-4 py-2 align-top whitespace-nowrap']"
            >
              {{ formatCell(row[col.key]) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
