<script setup lang="ts">
import type { LoginEvent } from "../../composables/admin/useAdminUsers";
import { SystemMessage, UiDenseStatusPill } from "../ui";

const props = defineProps<{
  events: LoginEvent[];
  isLoading: boolean;
  errorMessage: string | null;
}>();

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
}

function statusLabel(event: LoginEvent): string {
  return event.status === "success" ? "Lyckad" : "Misslyckad";
}

</script>

<template>
  <section class="panel">
    <header class="panel-header">
      <h2 class="panel-title">Inloggningshändelser</h2>
      <span class="panel-subtitle">Senaste 90 dagar</span>
    </header>

    <div
      v-if="isLoading"
      class="panel-state"
    >
      Laddar login events…
    </div>
    <SystemMessage
      v-else-if="errorMessage"
      :model-value="errorMessage"
      tone="failure"
      role="alert"
    />
    <div
      v-else-if="props.events.length === 0"
      class="panel-state"
    >
      Inga händelser hittades.
    </div>
    <div
      v-else
      class="table-wrapper"
    >
      <table class="panel-table">
        <thead>
          <tr>
            <th>Tid</th>
            <th>Status</th>
            <th>IP</th>
            <th>User agent</th>
            <th>Fel</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="event in props.events"
            :key="event.id"
          >
            <td class="font-mono text-xs">{{ formatDateTime(event.created_at) }}</td>
            <td>
              <UiDenseStatusPill
                :label="statusLabel(event)"
                :tone="event.status === 'success' ? 'success' : 'error'"
              />
            </td>
            <td class="font-mono text-xs">{{ event.ip_address ?? "—" }}</td>
            <td
              class="truncate text-xs"
              :title="event.user_agent ?? ''"
            >
              {{ event.user_agent ?? "—" }}
            </td>
            <td class="font-mono text-xs">
              {{ event.failure_code ?? "—" }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.panel {
  border: var(--huleedu-border-width) solid var(--huleedu-panel-border);
  border-radius: var(--huleedu-panel-radius);
  background-color: var(--huleedu-panel);
  padding: var(--huleedu-space-4);
}

.panel-header {
  display: flex;
  flex-direction: column;
  gap: var(--huleedu-space-1);
  margin-bottom: var(--huleedu-space-4);
}

.panel-title {
  font-family: var(--huleedu-font-sans);
  font-size: var(--huleedu-text-lg);
  color: var(--huleedu-navy);
  margin: 0;
}

.panel-subtitle {
  font-size: var(--huleedu-text-xs);
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
  color: var(--huleedu-navy-60);
}

.panel-state {
  font-size: var(--huleedu-text-sm);
  color: var(--huleedu-navy-70);
}

.table-wrapper {
  overflow-x: auto;
}

.panel-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--huleedu-text-sm);
}

.panel-table th,
.panel-table td {
  padding: var(--huleedu-space-2);
  text-align: left;
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-surface-divider);
  vertical-align: top;
}

.panel-table th {
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
  font-size: var(--huleedu-text-xs);
  color: var(--huleedu-navy-60);
}

.truncate {
  max-width: 280px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
