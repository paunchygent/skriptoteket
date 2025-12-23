<script setup lang="ts">
import type { components } from "../../api/openapi";

type UiOutput = NonNullable<components["schemas"]["UiPayloadV2"]["outputs"]>[number];

defineProps<{
  outputs: UiOutput[];
}>();

function renderMarkdown(output: UiOutput): string {
  if (output.kind === "markdown") {
    return output.markdown;
  }
  if (output.kind === "notice") {
    return output.message;
  }
  return "";
}

function noticeClass(output: UiOutput): string {
  if (output.kind !== "notice") return "";
  if (output.level === "error") return "text-error";
  if (output.level === "warning") return "text-warning";
  return "text-navy";
}
</script>

<template>
  <div
    v-if="outputs.length > 0"
    class="space-y-3"
  >
    <template
      v-for="(output, index) in outputs"
      :key="index"
    >
      <div
        v-if="output.kind === 'notice'"
        class="text-sm"
        :class="noticeClass(output)"
      >
        {{ output.message }}
      </div>

      <pre
        v-else-if="output.kind === 'markdown'"
        class="whitespace-pre-wrap font-mono text-sm text-navy bg-canvas p-3 border-l-2 border-navy/30"
      >{{ output.markdown }}</pre>

      <div
        v-else-if="output.kind === 'table'"
        class="overflow-x-auto"
      >
        <table class="w-full text-sm border-collapse">
          <thead>
            <tr class="border-b border-navy/30">
              <th
                v-for="col in output.columns"
                :key="col.key"
                class="text-left px-2 py-1 font-semibold text-navy/70"
              >
                {{ col.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, rowIdx) in output.rows"
              :key="rowIdx"
              class="border-b border-navy/10"
            >
              <td
                v-for="(cell, cellIdx) in row"
                :key="cellIdx"
                class="px-2 py-1"
              >
                {{ cell }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <pre
        v-else-if="output.kind === 'json'"
        class="whitespace-pre-wrap font-mono text-xs text-navy/80 bg-canvas p-3 border-l-2 border-navy/30 overflow-x-auto"
      >{{ JSON.stringify(output.value, null, 2) }}</pre>

      <iframe
        v-else-if="output.kind === 'html_sandboxed'"
        sandbox=""
        :srcdoc="output.html"
        class="block w-full min-h-[260px] border border-navy/20 bg-canvas"
      />

      <div
        v-else-if="output.kind === 'vega_lite'"
        class="text-sm text-navy/60 italic"
      >
        [Vega-Lite chart - not yet supported]
      </div>

      <div
        v-else
        class="text-sm text-navy/60 italic"
      >
        [Okänd utdatatyp]
      </div>
    </template>
  </div>
</template>
