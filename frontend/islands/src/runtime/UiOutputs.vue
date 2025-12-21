<template>
  <div class="huleedu-stack-sm">
    <template
      v-for="(output, index) in outputs"
      :key="index"
    >
      <div
        v-if="output.kind === 'notice'"
        class="huleedu-alert"
        :class="output.level === 'error' ? 'huleedu-alert-error' : ''"
      >
        {{ output.message }}
      </div>

      <pre v-else-if="output.kind === 'markdown'">{{ output.markdown }}</pre>

      <div v-else-if="output.kind === 'table'">
        <strong v-if="output.title">{{ output.title }}</strong>
        <div style="overflow: auto;">
          <table class="huleedu-table">
            <thead>
              <tr>
                <th
                  v-for="col in output.columns"
                  :key="col.key"
                >
                  {{ col.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, rowIndex) in output.rows"
                :key="rowIndex"
              >
                <td
                  v-for="col in output.columns"
                  :key="col.key"
                >
                  {{ row[col.key] }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-else-if="output.kind === 'json'">
        <strong v-if="output.title">{{ output.title }}</strong>
        <pre>{{ _prettyJson(output.value) }}</pre>
      </div>

      <iframe
        v-else-if="output.kind === 'html_sandboxed'"
        sandbox=""
        :srcdoc="output.html"
        style="
          width: 100%;
          min-height: 260px;
          border: var(--huleedu-border-width) solid var(--huleedu-navy);
          background-color: var(--huleedu-canvas);
        "
      />

      <div v-else-if="output.kind === 'vega_lite'">
        <div class="huleedu-alert huleedu-alert-error">
          Vega-Lite stöds inte ännu i klienten.
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { UiOutput } from "./types";

defineProps<{ outputs: UiOutput[] }>();

function _prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
</script>
