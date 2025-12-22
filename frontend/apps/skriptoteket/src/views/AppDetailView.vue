<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { apiGet, apiPost, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import { RunResultPanel } from "../components/run-results";

type AppDetailResponse = components["schemas"]["AppDetailResponse"];
type GetSessionStateResult = components["schemas"]["GetSessionStateResult"];
type GetRunResult = components["schemas"]["GetRunResult"];
type StartActionResult = components["schemas"]["StartActionResult"];
type InteractiveSessionState = components["schemas"]["InteractiveSessionState"];

const route = useRoute();

const appId = computed(() => {
  const param = route.params.appId;
  return typeof param === "string" ? param : "";
});

const app = ref<AppDetailResponse | null>(null);
const sessionState = ref<InteractiveSessionState | null>(null);
const run = ref<GetRunResult["run"] | null>(null);
const stateRev = ref<number | null>(null);
const latestRunId = ref<string | null>(null);

const isLoading = ref(true);
const isSubmittingAction = ref(false);
const errorMessage = ref<string | null>(null);
const actionErrorMessage = ref<string | null>(null);

const hasRun = computed(() => run.value !== null);
const canSubmitActions = computed(() => stateRev.value !== null);

let pollIntervalId: number | null = null;

async function fetchApp(): Promise<void> {
  app.value = await apiGet<AppDetailResponse>(`/api/v1/apps/${encodeURIComponent(appId.value)}`);
}

async function fetchSession(): Promise<void> {
  if (!app.value) return;
  const response = await apiGet<GetSessionStateResult>(
    `/api/v1/tools/${encodeURIComponent(app.value.tool_id)}/sessions/default`,
  );
  sessionState.value = response.session_state;
  stateRev.value = response.session_state.state_rev;
   latestRunId.value = response.session_state.latest_run_id ?? null;
}

async function fetchRun(runId: string): Promise<void> {
  const response = await apiGet<GetRunResult>(`/api/v1/runs/${encodeURIComponent(runId)}`);
  run.value = response.run;
}

async function load(): Promise<void> {
  if (!appId.value) {
    errorMessage.value = "Saknar app-id i länken.";
    return;
  }

  isLoading.value = true;
  errorMessage.value = null;
  actionErrorMessage.value = null;
  run.value = null;
  stateRev.value = null;
  sessionState.value = null;

  try {
    await fetchApp();
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att ladda appen.";
    }
    isLoading.value = false;
    return;
  }

  try {
    await fetchSession();
  } catch (error: unknown) {
    sessionState.value = null;
    stateRev.value = null;
    errorMessage.value = isApiError(error)
      ? error.message
      : "Det gick inte att ladda sessionen just nu.";
    isLoading.value = false;
    return;
  }

  if (latestRunId.value) {
    try {
      await fetchRun(latestRunId.value);
    } catch (error: unknown) {
      run.value = null;
      actionErrorMessage.value = isApiError(error)
        ? error.message
        : "Det gick inte att ladda körningen.";
    }
  }

  isLoading.value = false;
}

function startPolling(): void {
  if (pollIntervalId !== null) return;
  pollIntervalId = window.setInterval(() => {
    if (run.value) {
      void fetchRun(run.value.run_id.toString()).catch(() => {
        // Silently ignore during polling; main error handling is in load().
      });
    }
  }, 2000);
}

function stopPolling(): void {
  if (pollIntervalId === null) return;
  window.clearInterval(pollIntervalId);
  pollIntervalId = null;
}

async function performAction(
  actionId: string,
  input: Record<string, components["schemas"]["JsonValue"]>,
): Promise<void> {
  if (!app.value || stateRev.value === null) {
    actionErrorMessage.value = "Sessionen är inte redo än. Uppdatera och försök igen.";
    return;
  }
  if (isSubmittingAction.value) return;

  isSubmittingAction.value = true;
  actionErrorMessage.value = null;

  try {
    const response = await apiPost<StartActionResult>("/api/v1/start_action", {
      tool_id: app.value.tool_id,
      context: "default",
      action_id: actionId,
      input,
      expected_state_rev: stateRev.value,
    });

    stateRev.value = response.state_rev;
    if (sessionState.value) {
      sessionState.value = { ...sessionState.value, latest_run_id: response.run_id };
    }
    latestRunId.value = response.run_id;

    await fetchRun(response.run_id.toString());
  } catch (error: unknown) {
    if (isApiError(error)) {
      actionErrorMessage.value = error.status === 409
        ? "Sessionen ändrades i en annan flik. Uppdatera och försök igen."
        : error.message;
    } else if (error instanceof Error) {
      actionErrorMessage.value = error.message;
    } else {
      actionErrorMessage.value = "Det gick inte att köra åtgärden just nu.";
    }
  } finally {
    isSubmittingAction.value = false;
  }
}

async function startApp(): Promise<void> {
  await performAction("start", {});
}

async function submitAction(payload: { actionId: string; input: Record<string, components["schemas"]["JsonValue"]> }): Promise<void> {
  await performAction(payload.actionId, payload.input);
}

watch(
  () => run.value?.status,
  (status) => {
    if (status === "running") {
      startPolling();
    } else {
      stopPolling();
    }
  },
  { immediate: true },
);

watch(appId, () => {
  void load();
});

onMounted(() => {
  void load();
});

onUnmounted(() => {
  stopPolling();
});
</script>

<template>
  <div class="max-w-3xl space-y-6">
    <div class="flex items-center gap-3 text-sm text-navy/70">
      <RouterLink
        to="/browse"
        class="underline hover:text-burgundy"
      >
        ← Tillbaka till katalog
      </RouterLink>
      <span class="px-2 py-1 border border-navy bg-white shadow-brutal-sm uppercase tracking-wide font-semibold">
        Kurerad app
      </span>
    </div>

    <div class="space-y-2">
      <h1 class="text-2xl font-semibold text-navy">
        {{ app?.title ?? (isLoading ? "Laddar..." : "App") }}
      </h1>
      <p
        v-if="app?.summary"
        class="text-navy/70"
      >
        {{ app.summary }}
      </p>
    </div>

    <div
      v-if="isLoading"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-navy/70 text-sm"
    >
      Laddar...
    </div>

    <div
      v-else-if="errorMessage"
      class="p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
    >
      {{ errorMessage }}
    </div>

    <template v-else>
      <div
        v-if="!hasRun"
        class="space-y-3"
      >
        <p class="text-navy/70 text-sm">
          Starta appen för att se resultat och fortsatta åtgärder.
        </p>
        <button
          type="button"
          class="px-4 py-2 text-sm font-semibold uppercase tracking-wide text-canvas bg-burgundy rounded-sm btn-primary-hover transition-shadow disabled:opacity-60 disabled:cursor-not-allowed"
          :disabled="isSubmittingAction || !canSubmitActions"
          @click="startApp"
        >
          {{ isSubmittingAction ? "Startar..." : "Starta" }}
        </button>
        <p
          v-if="actionErrorMessage"
          class="text-error text-sm"
        >
          {{ actionErrorMessage }}
        </p>
      </div>

      <RunResultPanel
        v-else-if="run"
        :run="run"
        :id-base="`curated-app-${appId}`"
        :is-submitting-action="isSubmittingAction"
        :can-submit-actions="canSubmitActions"
        :action-error-message="actionErrorMessage"
        @submit-action="submitAction"
      />
    </template>
  </div>
</template>

<style scoped>
.shadow-brutal-sm {
  box-shadow: 4px 4px 0 0 var(--huleedu-navy, #1C2E4A);
}
</style>
