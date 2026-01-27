<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { apiGet, apiPost, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import ToolRunArtifacts from "../../components/tool-run/ToolRunArtifacts.vue";

type AppDetailResponse = components["schemas"]["AppDetailResponse"];
type GetSessionStateResult = components["schemas"]["GetSessionStateResult"];
type GetRunResult = components["schemas"]["GetRunResult"];
type InteractiveSessionState = components["schemas"]["InteractiveSessionState"];
type StartActionResult = components["schemas"]["StartActionResult"];
type RunDetails = components["schemas"]["RunDetails"];
type RunStatus = components["schemas"]["RunStatus"];
type JsonValue = components["schemas"]["JsonValue"];

type SourceType = "solid" | "liquid_stock";

type AppState = Record<string, JsonValue>;

type PrepResult = Record<string, JsonValue>;

const route = useRoute();

const appId = computed(() => {
  const param = route.params.appId;
  return typeof param === "string" ? param : "";
});

const app = ref<AppDetailResponse | null>(null);
const sessionState = ref<InteractiveSessionState | null>(null);
const run = ref<RunDetails | null>(null);
const stateRev = ref<number | null>(null);
const latestRunId = ref<string | null>(null);

const isLoading = ref(true);
const isSubmitting = ref(false);
const errorMessage = ref<string | null>(null);
const actionErrorMessage = ref<string | null>(null);

const form = reactive({
  chemicalFormula: "",
  targetMolarity: "0.1",
  volPerGroupMl: "50",
  studentCount: 30,
  studentsPerGroup: 2,
  safetyFactor: "0.10",
  sourceType: "solid" as SourceType,
  stockMolarity: "1.0",
  solutePurity: "1.0",
});

const hasSession = computed(() => sessionState.value !== null && stateRev.value !== null);

const artifacts = computed(() => run.value?.artifacts ?? []);

const result = computed<PrepResult | null>(() => {
  const state = sessionState.value?.state;
  if (!state) return null;
  const raw = state["result"];
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  return raw as PrepResult;
});

const instructions = computed(() => {
  const raw = result.value?.instructions;
  if (!Array.isArray(raw)) return [];
  return raw.filter((value): value is string => typeof value === "string");
});

const warnings = computed(() => {
  const raw = result.value?.warnings;
  if (!Array.isArray(raw)) return [];
  return raw.filter((value): value is string => typeof value === "string");
});

const safety = computed(() => {
  const raw = result.value?.safety;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  return raw as Record<string, JsonValue>;
});

const canExportPdf = computed(() => {
  const state = sessionState.value?.state;
  return Boolean(state && typeof state["export_html"] === "string" && (state["export_html"] as string).trim());
});

const canCalculate = computed(() => {
  if (!hasSession.value) return false;
  if (!form.chemicalFormula.trim()) return false;
  if (!form.targetMolarity.trim()) return false;
  if (!form.volPerGroupMl.trim()) return false;
  if (form.studentCount <= 0 || form.studentsPerGroup <= 0) return false;
  if (!form.safetyFactor.trim()) return false;
  if (!form.solutePurity.trim()) return false;
  if (form.sourceType === "liquid_stock" && !form.stockMolarity.trim()) return false;
  return true;
});

function statusLabel(status: RunStatus): string {
  const labels: Record<RunStatus, string> = {
    queued: "Köad",
    running: "Pågår",
    succeeded: "Lyckades",
    failed: "Misslyckades",
    timed_out: "Tidsgräns",
    cancelled: "Avbruten",
  };
  return labels[status];
}

function applyInputsFromState(state: AppState): void {
  const raw = state["inputs"];
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return;
  const inputs = raw as Record<string, JsonValue>;

  const cf = inputs["chemical_formula"];
  if (typeof cf === "string") form.chemicalFormula = cf;

  const target = inputs["target_molarity"];
  if (typeof target === "string" || typeof target === "number") form.targetMolarity = String(target);

  const vol = inputs["vol_per_group_ml"];
  if (typeof vol === "string" || typeof vol === "number") form.volPerGroupMl = String(vol);

  const students = inputs["student_count"];
  if (typeof students === "number") form.studentCount = students;

  const perGroup = inputs["students_per_group"];
  if (typeof perGroup === "number") form.studentsPerGroup = perGroup;

  const sf = inputs["safety_factor"];
  if (typeof sf === "string" || typeof sf === "number") form.safetyFactor = String(sf);

  const source = inputs["source_type"];
  if (source === "solid" || source === "liquid_stock") form.sourceType = source;

  const stock = inputs["stock_molarity"];
  if (typeof stock === "string" || typeof stock === "number") form.stockMolarity = String(stock);

  const purity = inputs["solute_purity"];
  if (typeof purity === "string" || typeof purity === "number") form.solutePurity = String(purity);
}

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

  applyInputsFromState(response.session_state.state as AppState);
}

async function fetchRun(runId: string): Promise<void> {
  const response = await apiGet<GetRunResult>(`/api/v1/runs/${encodeURIComponent(runId)}`);
  run.value = response.run;
}

async function load(): Promise<void> {
  if (!appId.value) {
    errorMessage.value = "Saknar app-id i länken.";
    isLoading.value = false;
    return;
  }

  isLoading.value = true;
  errorMessage.value = null;
  actionErrorMessage.value = null;
  app.value = null;
  sessionState.value = null;
  run.value = null;
  stateRev.value = null;
  latestRunId.value = null;

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
    errorMessage.value = isApiError(error) ? error.message : "Det gick inte att ladda sessionen.";
    isLoading.value = false;
    return;
  }

  if (latestRunId.value) {
    try {
      await fetchRun(latestRunId.value);
    } catch {
      run.value = null;
    }
  }

  isLoading.value = false;
}

let pollIntervalId: number | null = null;

function startPolling(): void {
  if (pollIntervalId !== null) return;
  pollIntervalId = window.setInterval(() => {
    if (run.value) {
      void fetchRun(run.value.run_id.toString()).catch(() => {
        // ignore during polling
      });
    }
  }, 2000);
}

function stopPolling(): void {
  if (pollIntervalId === null) return;
  window.clearInterval(pollIntervalId);
  pollIntervalId = null;
}

watch(
  () => run.value?.status,
  (status) => {
    if (status === "running" || status === "queued") {
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

async function performAction(actionId: string, input: Record<string, JsonValue>): Promise<void> {
  if (!app.value || stateRev.value === null) {
    actionErrorMessage.value = "Sessionen är inte redo än. Uppdatera och försök igen.";
    return;
  }
  if (isSubmitting.value) return;

  isSubmitting.value = true;
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
    latestRunId.value = response.run_id;

    await Promise.all([fetchRun(response.run_id.toString()), fetchSession()]);
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
    isSubmitting.value = false;
  }
}

async function calculate(): Promise<void> {
  const payload: Record<string, JsonValue> = {
    chemical_formula: form.chemicalFormula,
    target_molarity: form.targetMolarity,
    vol_per_group_ml: form.volPerGroupMl,
    student_count: form.studentCount,
    students_per_group: form.studentsPerGroup,
    safety_factor: form.safetyFactor,
    source_type: form.sourceType,
    solute_purity: form.solutePurity,
  };
  if (form.sourceType === "liquid_stock") {
    payload.stock_molarity = form.stockMolarity;
  }
  await performAction("calculate", payload);
}

async function reset(): Promise<void> {
  await performAction("reset", {});
  run.value = null;
}

async function exportPdf(): Promise<void> {
  await performAction("export_pdf", {});
}
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

    <header class="space-y-2">
      <h1 class="page-title">{{ app?.title ?? (isLoading ? "Laddar..." : "Reagensberedning") }}</h1>
      <p
        v-if="app?.summary"
        class="page-description"
      >
        {{ app.summary }}
      </p>
    </header>

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
      <div class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/80 space-y-2">
        <p class="font-semibold">Säkerhet</p>
        <p>
          Den här appen ger endast kuraterade råd för ämnen i listan. Om ämnet saknas: konsultera alltid SDS och lokala rutiner.
        </p>
      </div>

      <section class="border border-navy bg-white shadow-brutal-sm">
        <div class="p-4 space-y-4">
          <div class="flex items-start justify-between gap-4">
            <div class="space-y-1">
              <h2 class="text-lg font-semibold text-navy">Indata</h2>
              <p class="text-sm text-navy/60">
                Exempel: <span class="font-mono">CuSO4·5H2O</span>, <span class="font-mono">NaCl</span>, <span class="font-mono">KMnO4</span>
              </p>
            </div>
            <div
              v-if="run"
              class="text-right text-xs text-navy/60"
            >
              <div class="inline-flex items-center gap-2">
                <span class="px-2 py-1 border border-navy font-semibold uppercase tracking-wide text-xs">
                  {{ statusLabel(run.status) }}
                </span>
                <span class="font-mono">{{ run.run_id.slice(0, 8) }}</span>
              </div>
              <p
                v-if="run.error_summary"
                class="mt-2 text-burgundy whitespace-pre-wrap"
              >
                {{ run.error_summary }}
              </p>
            </div>
          </div>

          <form
            class="space-y-4"
            @submit.prevent="calculate"
          >
            <div class="grid gap-4 sm:grid-cols-2">
              <div class="space-y-2">
                <label
                  for="rpc-formula"
                  class="text-sm font-semibold text-navy"
                >Ämne (formel)</label>
                <input
                  id="rpc-formula"
                  v-model="form.chemicalFormula"
                  type="text"
                  placeholder="CuSO4·5H2O"
                  class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
                  :disabled="isSubmitting"
                >
              </div>

              <div class="space-y-2">
                <label
                  for="rpc-target"
                  class="text-sm font-semibold text-navy"
                >Målmolaritet (M)</label>
                <input
                  id="rpc-target"
                  v-model="form.targetMolarity"
                  inputmode="decimal"
                  class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
                  :disabled="isSubmitting"
                >
              </div>

              <div class="space-y-2">
                <label
                  for="rpc-vol-group"
                  class="text-sm font-semibold text-navy"
                >Volym per grupp (mL)</label>
                <input
                  id="rpc-vol-group"
                  v-model="form.volPerGroupMl"
                  inputmode="decimal"
                  class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
                  :disabled="isSubmitting"
                >
              </div>

              <div class="space-y-2">
                <label
                  for="rpc-students"
                  class="text-sm font-semibold text-navy"
                >Antal elever</label>
                <input
                  id="rpc-students"
                  v-model.number="form.studentCount"
                  type="number"
                  min="1"
                  class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
                  :disabled="isSubmitting"
                >
              </div>

              <div class="space-y-2">
                <label
                  for="rpc-per-group"
                  class="text-sm font-semibold text-navy"
                >Elever per grupp</label>
                <input
                  id="rpc-per-group"
                  v-model.number="form.studentsPerGroup"
                  type="number"
                  min="1"
                  class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
                  :disabled="isSubmitting"
                >
              </div>

              <div class="space-y-2">
                <label
                  for="rpc-safety-factor"
                  class="text-sm font-semibold text-navy"
                >Marginal (0–0,5)</label>
                <input
                  id="rpc-safety-factor"
                  v-model="form.safetyFactor"
                  inputmode="decimal"
                  class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
                  :disabled="isSubmitting"
                >
                <p class="text-xs text-navy/60">Ex: 0.10 = 10% extra.</p>
              </div>

              <div class="space-y-2">
                <label
                  for="rpc-source"
                  class="text-sm font-semibold text-navy"
                >Källa</label>
                <select
                  id="rpc-source"
                  v-model="form.sourceType"
                  class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
                  :disabled="isSubmitting"
                >
                  <option value="solid">Fast ämne</option>
                  <option value="liquid_stock">Späd från stocklösning</option>
                </select>
              </div>

              <div
                v-if="form.sourceType === 'liquid_stock'"
                class="space-y-2"
              >
                <label
                  for="rpc-stock"
                  class="text-sm font-semibold text-navy"
                >Stockmolaritet (M)</label>
                <input
                  id="rpc-stock"
                  v-model="form.stockMolarity"
                  inputmode="decimal"
                  class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
                  :disabled="isSubmitting"
                >
              </div>

              <div class="space-y-2">
                <label
                  for="rpc-purity"
                  class="text-sm font-semibold text-navy"
                >Renhet (0–1)</label>
                <input
                  id="rpc-purity"
                  v-model="form.solutePurity"
                  inputmode="decimal"
                  class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
                  :disabled="isSubmitting"
                >
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2 pt-2">
              <button
                type="submit"
                class="btn-cta min-w-[120px]"
                :disabled="isSubmitting || !canCalculate"
              >
                {{ isSubmitting ? "Beräknar…" : "Beräkna" }}
              </button>

              <button
                type="button"
                class="btn-ghost"
                :disabled="isSubmitting || !hasSession"
                @click="reset"
              >
                Nollställ
              </button>

              <button
                type="button"
                class="btn-primary"
                :disabled="isSubmitting || !hasSession || !canExportPdf"
                @click="exportPdf"
              >
                Exportera PDF
              </button>
            </div>

            <p
              v-if="actionErrorMessage"
              class="text-sm text-burgundy"
            >
              {{ actionErrorMessage }}
            </p>
          </form>
        </div>
      </section>

      <section
        v-if="result"
        class="border border-navy bg-white shadow-brutal-sm"
      >
        <div class="p-4 space-y-4">
          <h2 class="text-lg font-semibold text-navy">Resultat</h2>

          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1 text-sm">
              <div class="flex items-baseline justify-between gap-3">
                <span class="text-navy/60">Formel</span>
                <span class="font-mono text-navy">{{ result.formula_clean }}</span>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <span class="text-navy/60">Molar massa</span>
                <span class="text-navy">{{ result.molar_mass_g_mol }} g/mol</span>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <span class="text-navy/60">Totalvolym</span>
                <span class="text-navy">{{ result.total_volume_ml }} mL</span>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <span class="text-navy/60">Grupper</span>
                <span class="text-navy">{{ result.total_groups }}</span>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <span class="text-navy/60">Mängd substans</span>
                <span class="text-navy">{{ result.moles_required }} mol</span>
              </div>
              <div
                v-if="result.mass_g"
                class="flex items-baseline justify-between gap-3"
              >
                <span class="text-navy/60">Massa</span>
                <span class="text-navy">{{ result.mass_g }} g</span>
              </div>
              <template v-if="result.stock_volume_ml">
                <div class="flex items-baseline justify-between gap-3">
                  <span class="text-navy/60">Stockvolym</span>
                  <span class="text-navy">{{ result.stock_volume_ml }} mL</span>
                </div>
                <div class="flex items-baseline justify-between gap-3">
                  <span class="text-navy/60">Spädningsvatten</span>
                  <span class="text-navy">{{ result.diluent_volume_ml }} mL</span>
                </div>
              </template>
            </div>

            <div class="space-y-3 text-sm">
              <div
                v-if="instructions.length > 0"
                class="space-y-2"
              >
                <p class="font-semibold text-navy">Steg</p>
                <ol class="list-decimal pl-5 space-y-1">
                  <li
                    v-for="(step, index) in instructions"
                    :key="index"
                    class="text-navy"
                  >
                    {{ step }}
                  </li>
                </ol>
              </div>

              <div
                v-if="warnings.length > 0"
                class="p-3 border border-burgundy bg-canvas shadow-brutal-sm space-y-1"
              >
                <p class="font-semibold text-burgundy">Varningar</p>
                <ul class="list-disc pl-5 space-y-1 text-burgundy">
                  <li
                    v-for="(warning, index) in warnings"
                    :key="index"
                  >
                    {{ warning }}
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <div
            v-if="safety"
            class="p-3 border border-navy bg-canvas shadow-brutal-sm space-y-2 text-sm"
          >
            <p class="font-semibold text-navy">Säkerhet</p>
            <p
              v-if="safety.level === 'unknown'"
              class="text-burgundy"
            >
              Okänt ämne: konsultera SDS innan användning.
            </p>
            <div
              v-else
              class="space-y-1"
            >
              <p
                v-if="safety.display_name"
                class="text-navy"
              >
                {{ safety.display_name }}
              </p>
              <p
                v-if="Array.isArray(safety.ppe) && safety.ppe.length > 0"
                class="text-navy/80"
              >
                PPE: {{ (safety.ppe as string[]).join(", ") }}
              </p>
              <p
                v-if="safety.disposal"
                class="text-navy/80"
              >
                Avfall: {{ safety.disposal }}
              </p>
            </div>
          </div>

          <ToolRunArtifacts :artifacts="artifacts" />
        </div>
      </section>
    </template>
  </div>
</template>
