<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiGet, apiPost, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import { RunResultPanel } from "../components/run-results";

type GetRunResult = components["schemas"]["GetRunResult"];
type StartActionResult = components["schemas"]["StartActionResult"];
type GetSessionStateResult = components["schemas"]["GetSessionStateResult"];

const route = useRoute();
const router = useRouter();

const runId = computed(() => {
  const param = route.params.runId;
  return typeof param === "string" ? param : "";
});

const run = ref<GetRunResult["run"] | null>(null);
const stateRev = ref<number | null>(null);

const isLoading = ref(true);
const isSubmittingAction = ref(false);
const errorMessage = ref<string | null>(null);
const actionErrorMessage = ref<string | null>(null);

const hasNextActions = computed(() => (run.value?.ui_payload?.next_actions ?? []).length > 0);
const canSubmitActions = computed(() => stateRev.value !== null);

let pollIntervalId: number | null = null;

async function fetchRun(): Promise<void> {
  if (!runId.value) return;
  const response = await apiGet<GetRunResult>(`/api/v1/runs/${encodeURIComponent(runId.value)}`);
  run.value = response.run;
}

async function fetchSessionState(toolId: string): Promise<void> {
  const response = await apiGet<GetSessionStateResult>(
    `/api/v1/tools/${encodeURIComponent(toolId)}/sessions/default`,
  );
  stateRev.value = response.session_state.state_rev;
}

async function load(): Promise<void> {
  if (!runId.value) {
    errorMessage.value = "Missing route params";
    return;
  }

  isLoading.value = true;
  errorMessage.value = null;
  actionErrorMessage.value = null;

  try {
    await fetchRun();
  } catch (error: unknown) {
    run.value = null;
    stateRev.value = null;

    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Failed to load run";
    }

    isLoading.value = false;
    return;
  }

  if (hasNextActions.value && run.value) {
    try {
      await fetchSessionState(run.value.tool_id);
    } catch (error: unknown) {
      stateRev.value = null;
      actionErrorMessage.value = isApiError(error) ? error.message : "Det gick inte att ladda sessionen just nu.";
    }
  } else {
    stateRev.value = null;
  }

  isLoading.value = false;
}

function startPolling(): void {
  if (pollIntervalId !== null) return;

  pollIntervalId = window.setInterval(() => {
    void fetchRun().catch(() => {
      // Keep polling silent; main error handling happens on load().
    });
  }, 2000);
}

function stopPolling(): void {
  if (pollIntervalId === null) return;
  window.clearInterval(pollIntervalId);
  pollIntervalId = null;
}

async function submitAction(payload: { actionId: string; input: Record<string, components["schemas"]["JsonValue"]> }): Promise<void> {
  if (!run.value) return;
  if (stateRev.value === null) {
    actionErrorMessage.value = "Sessionen är inte redo än. Försök igen.";
    return;
  }
  if (isSubmittingAction.value) return;

  isSubmittingAction.value = true;
  actionErrorMessage.value = null;

  try {
    const response = await apiPost<StartActionResult>("/api/v1/start_action", {
      tool_id: run.value.tool_id,
      context: "default",
      action_id: payload.actionId,
      input: payload.input,
      expected_state_rev: stateRev.value,
    });

    stateRev.value = response.state_rev;
    await router.replace({
      name: "my-runs-detail",
      params: { runId: response.run_id },
    });
  } catch (error: unknown) {
    if (isApiError(error)) {
      actionErrorMessage.value = error.status === 409 ? "Din session har ändrats i en annan flik. Uppdatera och försök igen." : error.message;
    } else if (error instanceof Error) {
      actionErrorMessage.value = error.message;
    } else {
      actionErrorMessage.value = "Det gick inte att köra åtgärden just nu.";
    }
  } finally {
    isSubmittingAction.value = false;
  }
}

onMounted(() => {
  void load();
});

watch(runId, () => {
  void load();
});

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

onUnmounted(() => {
  stopPolling();
});
</script>

<template>
  <div class="max-w-3xl space-y-6">
    <RouterLink
      to="/my-runs"
      class="text-sm text-navy/70 underline hover:text-burgundy"
    >
      ← Tillbaka
    </RouterLink>

    <div class="space-y-2">
      <h1 class="text-2xl font-semibold text-navy">
        {{ run?.tool_title ?? (isLoading ? "Laddar..." : "Körning") }}
      </h1>

      <div
        v-if="run?.tool_slug"
        class="flex flex-wrap items-center gap-3 text-sm"
      >
        <RouterLink
          :to="{ name: 'tool-run', params: { slug: run.tool_slug } }"
          class="underline text-burgundy hover:text-navy"
        >
          Kör igen →
        </RouterLink>
        <RouterLink
          :to="{ name: 'tool-result', params: { slug: run.tool_slug, runId: run.run_id } }"
          class="underline text-navy/70 hover:text-burgundy"
        >
          Visa i verktyget →
        </RouterLink>
      </div>
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

    <template v-else-if="run">
      <RunResultPanel
        :run="run"
        :id-base="`my-runs-run-${run.run_id}`"
        :is-submitting-action="isSubmittingAction"
        :can-submit-actions="canSubmitActions"
        :action-error-message="actionErrorMessage"
        @submit-action="submitAction"
      />
    </template>
  </div>
</template>

