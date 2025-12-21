<template>
  <div class="huleedu-stack">
    <div
      v-if="loadError"
      class="huleedu-alert huleedu-alert-error"
    >
      {{ loadError }}
    </div>

    <div
      v-else-if="isLoading || !run"
      class="huleedu-alert huleedu-alert-info"
    >
      Laddar…
    </div>

    <template v-else>
      <div class="huleedu-muted">
        <span class="huleedu-pill">{{ runStatusLabel }}</span>
      </div>

      <div
        v-if="actionError"
        class="huleedu-alert huleedu-alert-error"
      >
        {{ actionError }}
        <button
          v-if="canRefresh"
          type="button"
          class="huleedu-btn huleedu-btn-secondary huleedu-btn-sm"
          @click="refresh"
        >
          Uppdatera
        </button>
      </div>

      <div
        v-if="uiPayload"
        class="huleedu-stack-sm"
      >
        <strong>Resultat</strong>
        <UiOutputs :outputs="uiPayload.outputs" />
      </div>

      <div
        v-if="uiPayload && uiPayload.next_actions.length > 0"
        class="huleedu-stack-sm"
      >
        <strong>Fortsätt</strong>

        <div class="huleedu-stack">
          <form
            v-for="action in uiPayload.next_actions"
            :key="action.action_id"
            class="huleedu-stack huleedu-card"
            @submit.prevent="submitAction(action.action_id)"
          >
            <template
              v-for="(field, fieldIndex) in action.fields"
              :key="field.name"
            >
              <div
                v-if="field.kind === 'string'"
                class="huleedu-form-group"
              >
                <label
                  class="huleedu-label"
                  :for="fieldId(action.action_id, fieldIndex)"
                >
                  {{ field.label }}
                </label>
                <input
                  :id="fieldId(action.action_id, fieldIndex)"
                  v-model="textValues[action.action_id][field.name]"
                  class="huleedu-input"
                >
              </div>

              <div
                v-else-if="field.kind === 'text'"
                class="huleedu-form-group"
              >
                <label
                  class="huleedu-label"
                  :for="fieldId(action.action_id, fieldIndex)"
                >
                  {{ field.label }}
                </label>
                <textarea
                  :id="fieldId(action.action_id, fieldIndex)"
                  v-model="textValues[action.action_id][field.name]"
                  class="huleedu-input"
                />
              </div>

              <div
                v-else-if="field.kind === 'integer'"
                class="huleedu-form-group"
              >
                <label
                  class="huleedu-label"
                  :for="fieldId(action.action_id, fieldIndex)"
                >
                  {{ field.label }}
                </label>
                <input
                  :id="fieldId(action.action_id, fieldIndex)"
                  v-model="textValues[action.action_id][field.name]"
                  type="number"
                  step="1"
                  class="huleedu-input"
                >
              </div>

              <div
                v-else-if="field.kind === 'number'"
                class="huleedu-form-group"
              >
                <label
                  class="huleedu-label"
                  :for="fieldId(action.action_id, fieldIndex)"
                >
                  {{ field.label }}
                </label>
                <input
                  :id="fieldId(action.action_id, fieldIndex)"
                  v-model="textValues[action.action_id][field.name]"
                  type="number"
                  step="any"
                  class="huleedu-input"
                >
              </div>

              <fieldset
                v-else-if="field.kind === 'boolean'"
                class="huleedu-fieldset"
              >
                <legend>{{ field.label }}</legend>
                <div class="huleedu-checkbox-group">
                  <div class="huleedu-checkbox-item">
                    <input
                      :id="fieldId(action.action_id, fieldIndex)"
                      v-model="booleanValues[action.action_id][field.name]"
                      type="checkbox"
                    >
                    <label :for="fieldId(action.action_id, fieldIndex)">Ja</label>
                  </div>
                </div>
              </fieldset>

              <fieldset
                v-else-if="field.kind === 'enum'"
                class="huleedu-fieldset"
              >
                <legend>{{ field.label }}</legend>
                <div class="huleedu-radio-group">
                  <div
                    v-for="(opt, optIndex) in field.options"
                    :key="opt.value"
                    class="huleedu-radio-item"
                  >
                    <input
                      :id="`${fieldId(action.action_id, fieldIndex)}-opt${optIndex}`"
                      v-model="textValues[action.action_id][field.name]"
                      type="radio"
                      :name="`${action.action_id}-${field.name}`"
                      :value="opt.value"
                    >
                    <label :for="`${fieldId(action.action_id, fieldIndex)}-opt${optIndex}`">
                      {{ opt.label }}
                    </label>
                  </div>
                </div>
              </fieldset>

              <fieldset
                v-else-if="field.kind === 'multi_enum'"
                class="huleedu-fieldset"
              >
                <legend>{{ field.label }}</legend>
                <div class="huleedu-checkbox-group">
                  <div
                    v-for="(opt, optIndex) in field.options"
                    :key="opt.value"
                    class="huleedu-checkbox-item"
                  >
                    <input
                      :id="`${fieldId(action.action_id, fieldIndex)}-opt${optIndex}`"
                      v-model="multiEnumValues[action.action_id][field.name]"
                      type="checkbox"
                      :value="opt.value"
                    >
                    <label :for="`${fieldId(action.action_id, fieldIndex)}-opt${optIndex}`">
                      {{ opt.label }}
                    </label>
                  </div>
                </div>
              </fieldset>
            </template>

            <div class="huleedu-flex huleedu-gap-4">
              <button
                type="submit"
                class="huleedu-btn huleedu-btn-navy"
                :disabled="isSubmitting"
              >
                {{ isSubmitting ? "Kör…" : action.label }}
              </button>
            </div>
          </form>
        </div>
      </div>

      <div
        v-if="run.artifacts.length > 0"
        class="huleedu-stack-sm"
      >
        <strong>Filer</strong>
        <ul class="huleedu-list">
          <li
            v-for="a in run.artifacts"
            :key="a.artifact_id"
            class="huleedu-list-item"
          >
            <a
              :href="a.download_url"
              class="huleedu-link"
              hx-boost="false"
              download
            >
              {{ a.path }}
            </a>
            <small class="huleedu-muted">({{ a.bytes }} byte)</small>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";

import UiOutputs from "./UiOutputs.vue";
import type {
  ApiErrorResponse,
  GetRunResult,
  GetSessionStateResult,
  StartActionResult,
  UiFormAction,
  UiPayloadV2,
  RunStatus,
} from "./types";

const props = defineProps<{ toolId: string; runId: string; context: string }>();

const isLoading = ref(true);
const isSubmitting = ref(false);
const loadError = ref<string | null>(null);
const actionError = ref<string | null>(null);
const canRefresh = ref(false);

const currentRunId = ref(props.runId);
const stateRev = ref<number | null>(null);
const latestRunId = ref<string | null>(null);
const run = ref<GetRunResult["run"] | null>(null);

const uiPayload = computed<UiPayloadV2 | null>(() => run.value?.ui_payload ?? null);

const runStatusLabel = computed<string>(() => {
  const status = run.value?.status;
  if (!status) return "Okänd";
  return _runStatusLabel(status);
});

const textValues = reactive<Record<string, Record<string, string>>>({});
const booleanValues = reactive<Record<string, Record<string, boolean>>>({});
const multiEnumValues = reactive<Record<string, Record<string, string[]>>>({});

function _runStatusLabel(status: RunStatus): string {
  const labels: Record<RunStatus, string> = {
    running: "Pågår",
    succeeded: "Lyckades",
    failed: "Misslyckades",
    timed_out: "Tidsgräns",
  };
  return labels[status];
}

function fieldId(actionId: string, fieldIndex: number): string {
  return `rt-${currentRunId.value}-a-${actionId}-f-${fieldIndex}`;
}

function _ensureFormState(): void {
  if (!uiPayload.value) return;
  for (const action of uiPayload.value.next_actions) {
    const actionId = action.action_id;

    if (!textValues[actionId]) textValues[actionId] = {};
    if (!booleanValues[actionId]) booleanValues[actionId] = {};
    if (!multiEnumValues[actionId]) multiEnumValues[actionId] = {};

    for (const field of action.fields) {
      if (field.kind === "boolean") {
        if (booleanValues[actionId][field.name] === undefined) {
          booleanValues[actionId][field.name] = false;
        }
        continue;
      }

      if (field.kind === "multi_enum") {
        if (multiEnumValues[actionId][field.name] === undefined) {
          multiEnumValues[actionId][field.name] = [];
        }
        continue;
      }

      if (textValues[actionId][field.name] === undefined) {
        textValues[actionId][field.name] = "";
      }
    }
  }
}

async function _parseJsonOrNull<T>(response: Response): Promise<T | null> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return null;
  return (await response.json()) as T;
}

function _uiErrorMessage(error: ApiErrorResponse | null, statusCode: number): string {
  if (statusCode === 409) {
    return "Din session har ändrats i en annan flik. Uppdatera och försök igen.";
  }
  if (statusCode === 403) return "Du saknar behörighet för detta.";
  if (statusCode === 404) return "Hittades inte.";
  if (statusCode === 503) return "Tjänsten är tillfälligt otillgänglig. Försök igen.";

  const apiMessage = error?.error?.message;
  if (apiMessage && apiMessage.trim()) return apiMessage;
  return "Ett oväntat fel inträffade.";
}

async function _fetchRun(runId: string): Promise<void> {
  const response = await fetch(`/api/runs/${runId}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    const error = await _parseJsonOrNull<ApiErrorResponse>(response);
    throw new Error(_uiErrorMessage(error, response.status));
  }

  const data = (await response.json()) as GetRunResult;
  run.value = data.run;
}

async function _fetchSessionState(): Promise<void> {
  const response = await fetch(`/api/tools/${props.toolId}/sessions/${props.context}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    const error = await _parseJsonOrNull<ApiErrorResponse>(response);
    throw new Error(_uiErrorMessage(error, response.status));
  }

  const data = (await response.json()) as GetSessionStateResult;
  stateRev.value = data.session_state.state_rev;
  latestRunId.value = data.session_state.latest_run_id;
}

async function refresh(): Promise<void> {
  actionError.value = null;
  canRefresh.value = false;

  try {
    isLoading.value = true;
    await _fetchSessionState();
    if (latestRunId.value) {
      currentRunId.value = latestRunId.value;
    }
    await _fetchRun(currentRunId.value);
    _ensureFormState();
  } catch (err) {
    console.error(err);
    actionError.value = "Det gick inte att uppdatera just nu.";
  } finally {
    isLoading.value = false;
  }
}

function _buildActionInput(action: UiFormAction): Record<string, unknown> {
  const actionId = action.action_id;
  const input: Record<string, unknown> = {};

  for (const field of action.fields) {
    if (field.kind === "boolean") {
      input[field.name] = booleanValues[actionId]?.[field.name] ?? false;
      continue;
    }

    if (field.kind === "multi_enum") {
      input[field.name] = multiEnumValues[actionId]?.[field.name] ?? [];
      continue;
    }

    const raw = textValues[actionId]?.[field.name] ?? "";
    const rawStr = String(raw);

    if (field.kind === "integer") {
      const str = rawStr.trim();
      if (!str) continue;
      const parsed = Number.parseInt(str, 10);
      if (Number.isNaN(parsed)) throw new Error(`Ogiltigt heltal: ${field.label}`);
      input[field.name] = parsed;
      continue;
    }

    if (field.kind === "number") {
      const str = rawStr.trim();
      if (!str) continue;
      const parsed = Number.parseFloat(str);
      if (Number.isNaN(parsed)) throw new Error(`Ogiltigt tal: ${field.label}`);
      input[field.name] = parsed;
      continue;
    }

    if (field.kind === "enum") {
      if (!rawStr) continue;
      input[field.name] = rawStr;
      continue;
    }

    input[field.name] = rawStr;
  }

  return input;
}

async function submitAction(actionId: string): Promise<void> {
  if (isSubmitting.value) return;
  actionError.value = null;
  canRefresh.value = false;

  const payload = uiPayload.value;
  if (!payload) return;

  const action = payload.next_actions.find((candidate) => candidate.action_id === actionId) ?? null;
  if (!action) {
    actionError.value = "Åtgärden hittades inte. Ladda om sidan.";
    return;
  }

  if (stateRev.value === null) {
    actionError.value = "Sessionen är inte redo än. Försök igen.";
    return;
  }

  isSubmitting.value = true;
  try {
    const input = _buildActionInput(action);
    const response = await fetch("/api/start_action", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        tool_id: props.toolId,
        context: props.context,
        action_id: actionId,
        input,
        expected_state_rev: stateRev.value,
      }),
    });

    if (!response.ok) {
      const error = await _parseJsonOrNull<ApiErrorResponse>(response);
      actionError.value = _uiErrorMessage(error, response.status);
      canRefresh.value = response.status === 409;
      return;
    }

    const data = (await response.json()) as StartActionResult;
    stateRev.value = data.state_rev;
    currentRunId.value = data.run_id;

    await _fetchRun(currentRunId.value);
    _ensureFormState();
  } catch (err) {
    console.error(err);
    actionError.value = (err as Error).message || "Det gick inte att köra åtgärden just nu.";
  } finally {
    isSubmitting.value = false;
  }
}

async function load(): Promise<void> {
  loadError.value = null;
  actionError.value = null;
  canRefresh.value = false;
  isLoading.value = true;

  try {
    await _fetchSessionState();
    await _fetchRun(currentRunId.value);
    _ensureFormState();
  } catch (err) {
    console.error(err);
    loadError.value = "Det gick inte att ladda körningen just nu.";
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  load().catch((err) => console.error(err));
});

watch(uiPayload, () => {
  _ensureFormState();
});
</script>
