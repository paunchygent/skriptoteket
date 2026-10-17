<script setup lang="ts">
import { SystemMessage } from "../../../components/ui";
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
  missingRiskContextMessage: string | null;
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
</script>

<template>
  <section class="rounded-[var(--huleedu-panel-radius)] border border-navy/20 bg-panel">
    <div class="p-4 space-y-4">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-1">
          <h2 class="text-lg font-semibold text-navy">Riskbedömning</h2>
          <p class="text-sm text-navy/60">
            Utkastet bygger på beräkningen och appens säkerhetsdata. Bekräfta checklistan innan export.
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

      <SystemMessage v-if="props.isRiskLoading">
        Laddar riskutkast…
      </SystemMessage>

      <SystemMessage
        v-else-if="props.riskErrorMessage"
        tone="failure"
      >
        {{ props.riskErrorMessage }}
      </SystemMessage>

      <template v-else-if="props.riskDraft">
        <SystemMessage
          v-if="props.riskWarnings.length > 0"
          tone="warning"
          class="space-y-1"
        >
          <p class="font-semibold">Varningar</p>
          <ul class="list-disc pl-5 space-y-1">
            <li
              v-for="warning in props.riskWarnings"
              :key="warning"
            >
              {{ warning }}
            </li>
          </ul>
        </SystemMessage>

        <div class="flex flex-wrap items-center gap-2 text-xs text-navy/70">
          <button
            v-if="props.riskDraft.sds.markdown_available"
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
                  class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-3 py-2 text-navy"
                />
              </div>
              <div class="space-y-1">
                <label class="text-xs font-semibold text-navy">Plats</label>
                <input
                  v-model="riskContext.location"
                  type="text"
                  class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-3 py-2 text-navy"
                >
              </div>
              <div class="grid gap-3 sm:grid-cols-2">
                <div class="space-y-1">
                  <label class="text-xs font-semibold text-navy">Deltagare</label>
                  <input
                    v-model="riskContext.participants"
                    type="text"
                    class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-3 py-2 text-navy"
                  >
                </div>
                <div class="space-y-1">
                  <label class="text-xs font-semibold text-navy">Ansvarig/Approver</label>
                  <input
                    v-model="riskContext.approver"
                    type="text"
                    class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-3 py-2 text-navy"
                  >
                </div>
              </div>
              <div class="grid gap-3 sm:grid-cols-2">
                <div class="space-y-1">
                  <label class="text-xs font-semibold text-navy">Datum</label>
                  <input
                    v-model="riskContext.assessment_date"
                    type="date"
                    class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-3 py-2 text-navy"
                  >
                </div>
                <div class="space-y-1">
                  <label class="text-xs font-semibold text-navy">Nästa översyn</label>
                  <input
                    v-model="riskContext.next_review_date"
                    type="date"
                    class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-3 py-2 text-navy"
                  >
                </div>
              </div>
              <div class="space-y-1">
                <label class="text-xs font-semibold text-navy">Lokala rutiner</label>
                <textarea
                  v-model="riskContext.local_routines"
                  rows="2"
                  class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-3 py-2 text-navy"
                />
              </div>
            </div>
          </div>

          <div class="space-y-3">
            <h3 class="text-sm font-semibold text-navy">Säkerhetsdata</h3>
            <div class="p-3 rounded-[var(--huleedu-panel-radius)] border border-navy/20 bg-canvas space-y-1 text-xs text-navy/80">
              <p v-if="props.riskDraft.sheet.safety.level === 'unknown'">
                {{ props.riskDraft.sheet.safety.message || "Konsultera SDS innan användning." }}
              </p>
              <template v-else>
                <p>H-koder: {{ props.riskDraft.sheet.safety.hazard_codes?.join(", ") || "—" }}</p>
                <p>PPE: {{ props.riskDraft.sheet.safety.ppe?.join(", ") || "—" }}</p>
                <p>Avfall: {{ props.riskDraft.sheet.safety.disposal || "—" }}</p>
              </template>
            </div>
          </div>
        </div>

        <div class="space-y-3">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold text-navy">Risker</h3>
            <span
              v-if="props.riskDraft.requires_confirmation"
              class="text-xs text-warning"
            >
              Bekräfta alla risker innan export.
            </span>
          </div>

          <div
            v-for="risk in props.riskDraft.risks"
            :key="risk.id"
            class="rounded-[var(--huleedu-panel-radius)] border border-navy/20 bg-panel p-3 space-y-3"
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
            </div>

            <p
              v-if="risk.hazard_codes?.length"
              class="text-xs text-navy/60"
            >
              H-koder: {{ risk.hazard_codes.join(", ") }}
            </p>

            <label class="flex items-center gap-2 text-xs text-navy/70">
              <input
                v-model="riskOverrides[risk.id].confirmed"
                type="checkbox"
                class="h-4 w-4 border border-navy/20 accent-action"
              >
              Bekräfta
            </label>

            <div class="space-y-1">
              <label class="text-xs font-semibold text-navy">Åtgärder (en per rad)</label>
              <textarea
                v-model="riskMeasuresDraft[risk.id]"
                rows="3"
                class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-2 py-2 text-navy"
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
            {{ props.isRiskExporting ? "Exporterar…" : "Exportera underlag (PDF)" }}
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

        <SystemMessage
          v-if="props.missingRiskContextMessage"
          tone="warning"
        >
          {{ props.missingRiskContextMessage }}
        </SystemMessage>

        <p
          v-if="props.lastSavedRiskPdfVaultRef"
          class="text-xs text-navy/60"
        >
          Sparad i Mina filer.
          <RouterLink
            to="/vault"
            class="underline hover:text-action"
          >
            Öppna Mina filer
          </RouterLink>
        </p>
      </template>
    </div>
  </section>
</template>
