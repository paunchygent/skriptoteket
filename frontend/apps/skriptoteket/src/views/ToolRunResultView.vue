<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiGet, apiPost, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import { UiActionForm } from "../components/ui-actions";
import { UiOutputRenderer } from "../components/ui-outputs";

type ToolMetadataResponse = components["schemas"]["ToolMetadataResponse"];
type GetRunResult = components["schemas"]["GetRunResult"];
type StartActionResult = components["schemas"]["StartActionResult"];
type GetSessionStateResult = components["schemas"]["GetSessionStateResult"];
type RunStatus = components["schemas"]["RunStatus"];

type UiOutput = NonNullable<components["schemas"]["UiPayloadV2"]["outputs"]>[number];
type UiFormAction = components["schemas"]["UiFormAction"];

const route = useRoute();
const router = useRouter();

const slug = computed(() => {
  const param = route.params.slug;
  return typeof param === "string" ? param : "";
});

const runId = computed(() => {
  const param = route.params.runId;
  return typeof param === "string" ? param : "";
});

const tool = ref<ToolMetadataResponse | null>(null);
const run = ref<GetRunResult["run"] | null>(null);
const stateRev = ref<number | null>(null);

const isLoading = ref(true);
const isSubmittingAction = ref(false);
const errorMessage = ref<string | null>(null);
const actionErrorMessage = ref<string | null>(null);

let pollIntervalId: number | null = null;

function statusLabel(status: RunStatus): string {
  const labels: Record<RunStatus, string> = {
    running: "Pågår",
    succeeded: "Lyckades",
    failed: "Misslyckades",
    timed_out: "Tidsgräns",
  };
  return labels[status];
}

const outputs = computed<UiOutput[]>(() => run.value?.ui_payload?.outputs ?? []);
const nextActions = computed<UiFormAction[]>(() => run.value?.ui_payload?.next_actions ?? []);
const artifacts = computed(() => run.value?.artifacts ?? []);

async function fetchTool(): Promise<void> {
  if (!slug.value) return;
  tool.value = await apiGet<ToolMetadataResponse>(`/api/v1/tools/${encodeURIComponent(slug.value)}`);
}

async function fetchRun(): Promise<void> {
  if (!runId.value) return;
  const response = await apiGet<GetRunResult>(`/api/v1/runs/${encodeURIComponent(runId.value)}`);
  run.value = response.run;
}

async function fetchSessionState(): Promise<void> {
  if (!tool.value) return;
  const response = await apiGet<GetSessionStateResult>(
    `/api/v1/tools/${encodeURIComponent(tool.value.id)}/sessions/default`,
  );
  stateRev.value = response.session_state.state_rev;
}

async function load(): Promise<void> {
  if (!slug.value || !runId.value) {
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

  try {
    await fetchTool();
  } catch {
    tool.value = null;
  }

  if (nextActions.value.length > 0 && tool.value) {
    try {
      await fetchSessionState();
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
  if (!tool.value) return;
  if (stateRev.value === null) {
    actionErrorMessage.value = "Sessionen är inte redo än. Försök igen.";
    return;
  }
  if (isSubmittingAction.value) return;

  isSubmittingAction.value = true;
  actionErrorMessage.value = null;

  try {
    const response = await apiPost<StartActionResult>("/api/v1/start_action", {
      tool_id: tool.value.id,
      context: "default",
      action_id: payload.actionId,
      input: payload.input,
      expected_state_rev: stateRev.value,
    });

    stateRev.value = response.state_rev;
    await router.replace({
      name: "tool-result",
      params: { slug: slug.value, runId: response.run_id },
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

watch([slug, runId], () => {
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
      to="/browse"
      class="text-sm text-navy/70 underline hover:text-burgundy"
    >
      ← Tillbaka till katalog
    </RouterLink>

    <div class="space-y-2">
      <h1 class="text-2xl font-semibold text-navy">
        {{ tool?.title ?? (isLoading ? "Laddar..." : "Körning") }}
      </h1>
      <p
        v-if="tool?.summary"
        class="text-navy/60"
      >
        {{ tool.summary }}
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

    <template v-else-if="run">
      <div class="flex items-center gap-3 text-sm text-navy/70">
        <span class="px-2 py-1 border border-navy bg-white shadow-brutal-sm font-semibold uppercase tracking-wide">
          {{ statusLabel(run.status) }}
        </span>
        <span class="font-mono text-xs text-navy/50">{{ run.run_id }}</span>
      </div>

      <div
        v-if="run.error_summary"
        class="p-4 border border-error bg-white shadow-brutal-sm text-error"
      >
        <p class="font-semibold">Ett fel uppstod</p>
        <pre class="mt-2 whitespace-pre-wrap font-mono text-xs">{{ run.error_summary }}</pre>
      </div>

      <div
        v-if="outputs.length > 0"
        class="space-y-3"
      >
        <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
          Resultat
        </h2>
        <UiOutputRenderer
          v-for="(output, index) in outputs"
          :key="index"
          :output="output"
        />
      </div>

      <div
        v-if="nextActions.length > 0"
        class="space-y-3"
      >
        <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
          Fortsätt
        </h2>

        <div
          v-if="actionErrorMessage"
          class="p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
        >
          {{ actionErrorMessage }}
        </div>

        <UiActionForm
          v-for="action in nextActions"
          :key="action.action_id"
          :action="action"
          :id-base="`tool-${slug}-run-${run.run_id}`"
          :disabled="isSubmittingAction"
          @submit="submitAction"
        />
      </div>

      <div
        v-if="artifacts.length > 0"
        class="space-y-2"
      >
        <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
          Filer
        </h2>

        <ul class="space-y-2">
          <li
            v-for="a in artifacts"
            :key="a.artifact_id"
            class="p-4 border border-navy bg-white shadow-brutal-sm flex items-center justify-between gap-4"
          >
            <div class="min-w-0">
              <a
                :href="a.download_url"
                class="underline text-burgundy hover:text-navy break-all"
                download
              >{{ a.path }}</a>
              <div class="text-xs text-navy/60">
                {{ a.bytes }} byte
              </div>
            </div>
            <span class="text-xs font-mono text-navy/50">{{ a.artifact_id }}</span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>
