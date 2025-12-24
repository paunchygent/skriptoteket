<script setup lang="ts">
import type { components } from "../../api/openapi";

type UiTableOutput = components["schemas"]["UiTableOutput"];
type JsonValue = components["schemas"]["JsonValue"];

defineProps<{ output: UiTableOutput }>();

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
  <div class="border border-navy bg-white shadow-brutal-sm">
    <div
      v-if="output.title"
      class="px-4 py-3 border-b border-navy font-semibold text-navy"
    >
      {{ output.title }}
    </div>

    <div class="overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead>
          <tr class="text-left text-navy/70">
            <th
              v-for="col in output.columns"
              :key="col.key"
              class="px-4 py-2 border-b border-navy/20 whitespace-nowrap"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody class="text-navy">
          <tr
            v-for="(row, rowIndex) in output.rows"
            :key="rowIndex"
            class="border-b border-navy/10"
          >
            <td
              v-for="col in output.columns"
              :key="col.key"
              class="px-4 py-2 align-top whitespace-nowrap"
            >
              {{ formatCell(row[col.key]) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
