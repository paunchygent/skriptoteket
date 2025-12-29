<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { isApiError } from "../../api/client";
import LoginEventsPanel from "../../components/admin/LoginEventsPanel.vue";
import {
  getAdminUser,
  getAdminUserLoginEvents,
  type AdminUser,
  type LoginEvent,
} from "../../composables/admin/useAdminUsers";

const route = useRoute();
const userId = computed(() => String(route.params.userId ?? ""));

const user = ref<AdminUser | null>(null);
const events = ref<LoginEvent[]>([]);
const isLoadingUser = ref(true);
const isLoadingEvents = ref(true);
const userError = ref<string | null>(null);
const eventsError = ref<string | null>(null);

	function formatDateTime(value: string | null | undefined): string {
	  if (!value) return "—";
	  const date = new Date(value);
	  if (Number.isNaN(date.getTime())) {
	    return value;
	  }
  return date.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
}

async function loadUser(): Promise<void> {
  isLoadingUser.value = true;
  userError.value = null;
  try {
    const response = await getAdminUser(userId.value);
    user.value = response.user;
  } catch (error: unknown) {
    if (isApiError(error)) {
      userError.value = error.message;
    } else if (error instanceof Error) {
      userError.value = error.message;
    } else {
      userError.value = "Det gick inte att ladda användaren.";
    }
  } finally {
    isLoadingUser.value = false;
  }
}

async function loadEvents(): Promise<void> {
  isLoadingEvents.value = true;
  eventsError.value = null;
  try {
    const response = await getAdminUserLoginEvents(userId.value, { limit: 50 });
    events.value = response.events;
  } catch (error: unknown) {
    if (isApiError(error)) {
      eventsError.value = error.message;
    } else if (error instanceof Error) {
      eventsError.value = error.message;
    } else {
      eventsError.value = "Det gick inte att ladda login events.";
    }
  } finally {
    isLoadingEvents.value = false;
  }
}

async function load(): Promise<void> {
  if (!userId.value) {
    userError.value = "Ogiltigt användar-id.";
    return;
  }
  await Promise.all([loadUser(), loadEvents()]);
}

onMounted(() => {
  void load();
});

watch(
  () => userId.value,
  () => {
    void load();
  },
);
</script>

<template>
  <div class="page">
    <header class="page-header">
      <RouterLink
        to="/admin/users"
        class="back-link"
      >
        ← Till användare
      </RouterLink>
      <div class="page-header-title">
        <p class="page-kicker">Superuser</p>
        <h1 class="page-title">Användardetaljer</h1>
      </div>
    </header>

    <section class="panel">
      <div
        v-if="isLoadingUser"
        class="panel-state"
      >
        Laddar användare…
      </div>
      <div
        v-else-if="userError"
        class="panel-state text-error"
      >
        {{ userError }}
      </div>
      <div
        v-else-if="!user"
        class="panel-state"
      >
        Ingen användare hittades.
      </div>
      <div
        v-else
        class="user-grid"
      >
        <div>
          <p class="label">Email</p>
          <p class="value font-mono">{{ user.email }}</p>
        </div>
        <div>
          <p class="label">Roll</p>
          <p class="value">{{ user.role }}</p>
        </div>
        <div>
          <p class="label">Status</p>
          <p class="value">{{ user.is_active ? "Aktiv" : "Inaktiv" }}</p>
        </div>
        <div>
          <p class="label">Senaste login</p>
          <p class="value">{{ formatDateTime(user.last_login_at) }}</p>
        </div>
        <div>
          <p class="label">Senaste misslyckade</p>
          <p class="value">{{ formatDateTime(user.last_failed_login_at) }}</p>
        </div>
        <div>
          <p class="label">Misslyckade försök</p>
          <p class="value">{{ user.failed_login_attempts }}</p>
        </div>
        <div>
          <p class="label">Låst till</p>
          <p class="value">{{ formatDateTime(user.locked_until) }}</p>
        </div>
      </div>
    </section>

    <LoginEventsPanel
      :events="events"
      :is-loading="isLoadingEvents"
      :error-message="eventsError"
    />
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
  flex-direction: column;
  gap: var(--huleedu-space-4);
}

.page-header-title {
  display: flex;
  flex-direction: column;
  gap: var(--huleedu-space-1);
}

.back-link {
  color: var(--huleedu-navy-70);
  text-decoration: none;
  font-size: var(--huleedu-text-sm);
}

.back-link:hover {
  color: var(--huleedu-burgundy);
}

.page-kicker {
  text-transform: uppercase;
  font-size: var(--huleedu-text-xs);
  letter-spacing: var(--huleedu-tracking-label);
  color: var(--huleedu-navy-60);
  margin: 0;
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

.user-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--huleedu-space-4);
}

@media (max-width: 480px) {
  .user-grid {
    grid-template-columns: 1fr;
  }
}

.label {
  text-transform: uppercase;
  font-size: var(--huleedu-text-xs);
  letter-spacing: var(--huleedu-tracking-label);
  color: var(--huleedu-navy-60);
  margin: 0 0 var(--huleedu-space-1);
}

.value {
  font-size: var(--huleedu-text-sm);
  margin: 0;
  word-break: break-word;
}
</style>
