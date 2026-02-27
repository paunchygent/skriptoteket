<script setup lang="ts">
import type {
  ReagentPrepChefRiskAssessmentResult,
  ReagentPrepChefRiskContext,
  RiskOverrideDraft,
} from "./types";

type Props = {
  riskDraft: ReagentPrepChefRiskAssessmentResult["draft"] | null;
  riskWarnings: string[];
  isRiskLoading: boolean;
  isRiskSaving: boolean;
  isRiskExporting: boolean;
  isSavingRiskPdfToVault: boolean;
  lastSavedRiskPdfVaultRef: string | null;
  riskErrorMessage: string | null;
  riskContextIsComplete: boolean;
  canExportRisk: boolean;
};

const props = defineProps<Props>();
const riskContext = defineModel<ReagentPrepChefRiskContext>("riskContext", { required: true });
const riskOverrides = defineModel<Record<string, RiskOverrideDraft>>("riskOverrides", {
  required: true,
});
const riskMeasuresDraft = defineModel<Record<string, string>>("riskMeasuresDraft", {
  required: true,
});

const emit = defineEmits<{
  (event: "refresh"): void;
  (event: "openSds"): void;
  (event: "updateMeasures", riskId: string): void;
  (event: "back"): void;
  (event: "export"): void;
  (event: "save"): void;
}>();

const MISSING_FLAG_LABELS: Record<string, string> = {
  sds_ref_missing: "SDS-referens saknas.",
  sds_pdf_missing: "SDS saknas offline.",
  sds_density_missing: "Densitet saknas i SDS.",
  sds_clp_bands_missing: "CLP-data saknas i SDS.",
  sds_heuristics_missing: "Kemiska heuristiker saknas i SDS.",
  clp_unavailable_for_target: "CLP-klassning saknas för vald koncentration.",
  heuristics_unavailable: "Kemiska heuristiker saknas.",
};

function formatMissingFlag(flag: string): string {
  return MISSING_FLAG_LABELS[flag] ?? flag;
}
</script>

<template>
  <section class="border border-navy bg-white shadow-brutal-sm">
    <div class="p-4 space-y-4">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-1">
          <h2 class="text-lg font-semibold text-navy">Riskbedömning</h2>
          <p class="text-sm text-navy/60">
            Utkastet bygger på beräkningen och kuraterad SDS-data. Bekräfta varje risk innan export.
          </p>
        </div>
        <button
          type="button"
          class="btn-ghost"
          :disabled="props.isRiskLoading"
          @click="emit('refresh')"
        >
          {{ props.isRiskLoading ? "Uppdaterar…" : "Uppdatera" }}
        </button>
      </div>

      <p
        v-if="props.isRiskSaving"
        class="text-xs text-navy/60"
      >
        Sparar utkast…
      </p>

      <div
        v-if="props.isRiskLoading"
        class="p-3 border border-navy bg-canvas shadow-none text-sm text-navy/70"
      >
        Laddar riskutkast…
      </div>

      <div
        v-else-if="props.riskErrorMessage"
        class="p-3 border border-error bg-white shadow-brutal-sm text-error text-sm"
      >
        {{ props.riskErrorMessage }}
      </div>

      <template v-else-if="props.riskDraft">
        <div
          v-if="props.riskWarnings.length > 0"
          class="p-3 border border-burgundy bg-canvas shadow-none space-y-1"
        >
          <p class="font-semibold text-burgundy">Varningar</p>
          <ul class="list-disc pl-5 space-y-1 text-burgundy text-sm">
            <li
              v-for="warning in props.riskWarnings"
              :key="warning"
            >
              {{ warning }}
            </li>
          </ul>
        </div>

        <div class="flex flex-wrap items-center gap-2 text-xs text-navy/70">
          <button
            v-if="props.riskDraft.sds.pdf_available"
            type="button"
            class="btn-ghost"
            @click="emit('openSds')"
          >
            Öppna SDS
          </button>
          <span v-else>SDS saknas offline.</span>
        </div>

        <div class="grid gap-4 lg:grid-cols-2">
          <div class="space-y-3">
            <h3 class="text-sm font-semibold text-navy">Lokal kontext</h3>
            <div class="grid gap-3">
              <div class="space-y-1">
                <label class="text-xs font-semibold text-navy">Omfattning</label>
                <textarea
                  v-model="riskContext.scope"
                  rows="3"
                  class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                />
              </div>
              <div class="space-y-1">
                <label class="text-xs font-semibold text-navy">Plats</label>
                <input
                  v-model="riskContext.location"
                  type="text"
                  class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                >
              </div>
              <div class="grid gap-3 sm:grid-cols-2">
                <div class="space-y-1">
                  <label class="text-xs font-semibold text-navy">Deltagare</label>
                  <input
                    v-model="riskContext.participants"
                    type="text"
                    class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                  >
                </div>
                <div class="space-y-1">
                  <label class="text-xs font-semibold text-navy">Ansvarig/Approver</label>
                  <input
                    v-model="riskContext.approver"
                    type="text"
                    class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                  >
                </div>
              </div>
              <div class="grid gap-3 sm:grid-cols-2">
                <div class="space-y-1">
                  <label class="text-xs font-semibold text-navy">Datum</label>
                  <input
                    v-model="riskContext.assessment_date"
                    type="date"
                    class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                  >
                </div>
                <div class="space-y-1">
                  <label class="text-xs font-semibold text-navy">Nästa översyn</label>
                  <input
                    v-model="riskContext.next_review_date"
                    type="date"
                    class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                  >
                </div>
              </div>
              <div class="space-y-1">
                <label class="text-xs font-semibold text-navy">Lokala rutiner</label>
                <textarea
                  v-model="riskContext.local_routines"
                  rows="2"
                  class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
                />
              </div>
            </div>
          </div>

          <div class="space-y-3">
            <h3 class="text-sm font-semibold text-navy">CLP & heuristik</h3>
            <div class="p-3 border border-navy bg-canvas shadow-none space-y-1 text-xs text-navy/80">
              <p>H-koder: {{ props.riskDraft.clp.hazard_codes?.join(", ") || "—" }}</p>
              <p>Piktogram: {{ props.riskDraft.clp.pictograms?.join(", ") || "—" }}</p>
              <p>Signalord: {{ props.riskDraft.clp.signal_word || "—" }}</p>
              <p v-if="props.riskDraft.clp.notes?.length">
                Noteringar: {{ props.riskDraft.clp.notes.join(", ") }}
              </p>
            </div>
            <div class="p-3 border border-navy bg-canvas shadow-none space-y-1 text-xs text-navy/80">
              <p>
                Inkompatibiliteter: {{ props.riskDraft.heuristics.incompatibilities?.join(", ") || "—" }}
              </p>
              <p>Exotermitet: {{ props.riskDraft.heuristics.exothermicity || "—" }}</p>
              <p v-if="props.riskDraft.heuristics.reaction_notes?.length">
                Noteringar: {{ props.riskDraft.heuristics.reaction_notes.join(", ") }}
              </p>
            </div>
          </div>
        </div>

        <div class="space-y-3">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold text-navy">Risker</h3>
            <span
              v-if="props.riskDraft.requires_confirmation"
              class="text-xs text-burgundy"
            >
              Bekräfta alla risker innan export.
            </span>
          </div>

          <div
            v-for="risk in props.riskDraft.risks"
            :key="risk.id"
            class="border border-navy/20 bg-white p-3 shadow-none space-y-3"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="space-y-1">
                <p class="font-semibold text-navy">{{ risk.title }}</p>
                <p
                  v-if="risk.description"
                  class="text-xs text-navy/60"
                >
                  {{ risk.description }}
                </p>
              </div>
              <span class="text-xs text-navy/60 uppercase">{{ risk.final.level }}</span>
            </div>

            <p
              v-if="risk.hazard_codes?.length"
              class="text-xs text-navy/60"
            >
              H-koder: {{ risk.hazard_codes.join(", ") }}
            </p>

            <div class="grid gap-3 sm:grid-cols-3 text-sm">
              <div class="space-y-1">
                <label class="text-xs font-semibold text-navy">Allvar (1–5)</label>
                <select
                  v-model.number="riskOverrides[risk.id].severity"
                  class="w-full border border-navy bg-white px-2 py-1 text-navy"
                >
                  <option
                    v-for="value in [1, 2, 3, 4, 5]"
                    :key="value"
                    :value="value"
                  >
                    {{ value }}
                  </option>
                </select>
              </div>
              <div class="space-y-1">
                <label class="text-xs font-semibold text-navy">Sannolikhet (1–5)</label>
                <select
                  v-model.number="riskOverrides[risk.id].likelihood"
                  class="w-full border border-navy bg-white px-2 py-1 text-navy"
                >
                  <option
                    v-for="value in [1, 2, 3, 4, 5]"
                    :key="value"
                    :value="value"
                  >
                    {{ value }}
                  </option>
                </select>
              </div>
              <div class="space-y-1 text-xs text-navy/70">
                <p>Poäng: <span class="font-mono">{{ risk.final.score }}</span></p>
                <p>Nivå: <span class="font-mono">{{ risk.final.level }}</span></p>
                <label class="flex items-center gap-2 pt-1">
                  <input
                    v-model="riskOverrides[risk.id].confirmed"
                    type="checkbox"
                    class="h-4 w-4 border border-navy"
                  >
                  Bekräfta
                </label>
              </div>
            </div>

            <div class="space-y-1">
              <label class="text-xs font-semibold text-navy">Åtgärder (en per rad)</label>
              <textarea
                v-model="riskMeasuresDraft[risk.id]"
                rows="3"
                class="w-full border border-navy bg-white px-2 py-2 text-navy"
                @input="emit('updateMeasures', risk.id)"
              />
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2 pt-2">
          <button
            type="button"
            class="btn-ghost"
            @click="emit('back')"
          >
            ← Tillbaka
          </button>
          <button
            type="button"
            class="btn-primary"
            :disabled="props.isRiskExporting || !props.canExportRisk"
            @click="emit('export')"
          >
            {{ props.isRiskExporting ? "Exporterar…" : "Exportera risk-PDF" }}
          </button>
          <button
            type="button"
            class="btn-ghost"
            :disabled="props.isSavingRiskPdfToVault || !props.canExportRisk"
            @click="emit('save')"
          >
            {{ props.isSavingRiskPdfToVault ? "Sparar…" : "Spara i Mina filer" }}
          </button>
        </div>

        <div
          v-if="(props.riskDraft.export_gate?.missing_data_flags ?? []).length > 0"
          class="p-3 border border-burgundy bg-canvas shadow-none space-y-1"
        >
          <p class="font-semibold text-burgundy text-xs">Kan inte exportera ännu</p>
          <ul class="list-disc pl-5 space-y-1 text-burgundy text-xs">
            <li
              v-for="flag in props.riskDraft.export_gate?.missing_data_flags ?? []"
              :key="flag"
            >
              {{ formatMissingFlag(flag) }}
            </li>
          </ul>
        </div>

        <p
          v-if="!props.riskContextIsComplete"
          class="text-xs text-burgundy"
        >
          Fyll i omfattning, deltagare, ansvarig, datum och nästa översyn innan export.
        </p>

        <p
          v-if="props.lastSavedRiskPdfVaultRef"
          class="text-xs text-navy/60"
        >
          Sparad i Mina filer.
          <RouterLink
            to="/vault"
            class="underline hover:text-burgundy"
          >
            Öppna Mina filer
          </RouterLink>
        </p>
      </template>
    </div>
  </section>
</template>
