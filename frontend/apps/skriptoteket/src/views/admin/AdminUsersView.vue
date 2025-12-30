<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { isApiError } from "../../api/client";
import { listAdminUsers, type AdminUser } from "../../composables/admin/useAdminUsers";

const router = useRouter();

const users = ref<AdminUser[]>([]);
const total = ref<number | null>(null);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);

function navigateToUser(userId: string): void {
  void router.push(`/admin/users/${userId}`);
}

	function formatDateTime(value: string | null | undefined): string {
	  if (!value) return "—";
	  const date = new Date(value);
	  if (Number.isNaN(date.getTime())) {
	    return value;
	  }
  return date.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
}

function statusLabel(user: AdminUser): string {
  if (!user.is_active) return "Inaktiv";
  if (user.locked_until) return "Låst";
  return "Aktiv";
}

function statusClass(user: AdminUser): string {
  if (!user.is_active) return "bg-navy/10 text-navy border border-navy/30";
  if (user.locked_until) return "bg-error/10 text-error border border-error/30";
  return "bg-success/10 text-success border border-success/30";
}

async function load(): Promise<void> {
  isLoading.value = true;
  errorMessage.value = null;

  try {
    const response = await listAdminUsers({ limit: 100 });
    users.value = response.users;
    total.value = response.total;
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att ladda användare.";
    }
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  void load();
});
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <p class="page-kicker">Superuser</p>
        <h1 class="page-title">Användare</h1>
      </div>
      <div class="page-meta">
        <span v-if="total !== null">Totalt: {{ total }}</span>
      </div>
    </header>

    <section class="panel">
      <div
        v-if="isLoading"
        class="panel-state"
      >
        Laddar användare…
      </div>
      <div
        v-else-if="errorMessage"
        class="panel-state text-error"
      >
        {{ errorMessage }}
      </div>
      <div
        v-else-if="users.length === 0"
        class="panel-state"
      >
        Inga användare hittades.
      </div>
      <div
        v-else
        class="table-wrapper"
      >
        <table class="panel-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Roll</th>
              <th>Status</th>
              <th>Senaste login</th>
              <th>Misslyckade</th>
              <th>Låst till</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="user in users"
              :key="user.id"
              @click="navigateToUser(user.id)"
            >
              <td class="font-mono text-xs">{{ user.email }}</td>
              <td>{{ user.role }}</td>
              <td>
                <span
                  class="status-pill"
                  :class="statusClass(user)"
                >
                  {{ statusLabel(user) }}
                </span>
              </td>
              <td class="text-xs">{{ formatDateTime(user.last_login_at) }}</td>
              <td class="text-xs">{{ user.failed_login_attempts }}</td>
              <td class="text-xs">{{ formatDateTime(user.locked_until) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--huleedu-space-6);
}

.page-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--huleedu-space-4);
}

.page-kicker {
  text-transform: uppercase;
  font-size: var(--huleedu-text-xs);
  letter-spacing: var(--huleedu-tracking-label);
  color: var(--huleedu-navy-60);
  margin: 0 0 var(--huleedu-space-2);
}


.page-meta {
  font-size: var(--huleedu-text-sm);
  color: var(--huleedu-navy-70);
}

.panel {
  border: var(--huleedu-border-width) solid var(--huleedu-navy);
  background-color: white;
  box-shadow: var(--huleedu-shadow-brutal-sm);
  padding: var(--huleedu-space-4);
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
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-navy-10);
  vertical-align: top;
}

.panel-table th {
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
  font-size: var(--huleedu-text-xs);
  color: var(--huleedu-navy-60);
}

.panel-table tbody tr {
  cursor: pointer;
  transition: background-color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.panel-table tbody tr:hover {
  background-color: var(--huleedu-navy-02);
}

</style>
