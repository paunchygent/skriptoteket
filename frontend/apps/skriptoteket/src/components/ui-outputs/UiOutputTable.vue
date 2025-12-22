<script setup lang="ts">
import type { components } from "../../api/openapi";

type UiTableOutput = components["schemas"]["UiTableOutput"];

defineProps<{ output: UiTableOutput }>();
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
              {{ row[col.key] }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
