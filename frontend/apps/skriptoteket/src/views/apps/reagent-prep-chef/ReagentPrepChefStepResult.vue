<script setup lang="ts">
import type { ReagentPrepChefPrepSheet } from "./types";

type Props = {
  prep: ReagentPrepChefPrepSheet;
  instructions: string[];
  warnings: string[];
  safety: ReagentPrepChefPrepSheet["safety"] | null;
  safetyPpe: string[];
  isExporting: boolean;
  isSavingPdfToVault: boolean;
  canExport: boolean;
  lastSavedPdfVaultRef: string | null;
  actionErrorMessage: string | null;
};

const props = defineProps<Props>();

const emit = defineEmits<{
  (event: "back"): void;
  (event: "export"): void;
  (event: "save"): void;
  (event: "reset"): void;
}>();
</script>

<template>
  <section class="border border-navy bg-panel shadow-brutal-sm">
    <div class="p-4 space-y-4">
      <h2 class="text-lg font-semibold text-navy">Resultat</h2>

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-1 text-sm">
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-navy/60">Formel</span>
            <span class="font-mono text-navy">{{ props.prep.chemistry.formula_clean }}</span>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-navy/60">Molmassa</span>
            <span class="text-navy">{{ props.prep.chemistry.molar_mass_g_mol }} g/mol</span>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-navy/60">Totalvolym</span>
            <span class="text-navy">{{ props.prep.logistics.total_volume_ml }} ml</span>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-navy/60">Grupper</span>
            <span class="text-navy">{{ props.prep.logistics.total_groups }}</span>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-navy/60">Mängd substans</span>
            <span class="text-navy">{{ props.prep.chemistry.moles_required }} mol</span>
          </div>
          <div
            v-if="props.prep.chemistry.mass_g"
            class="flex items-baseline justify-between gap-3"
          >
            <span class="text-navy/60">Massa</span>
            <span class="text-navy">{{ props.prep.chemistry.mass_g }} g</span>
          </div>
          <template v-if="props.prep.chemistry.stock_volume_ml">
            <div class="flex items-baseline justify-between gap-3">
              <span class="text-navy/60">Stockvolym</span>
              <span class="text-navy">{{ props.prep.chemistry.stock_volume_ml }} ml</span>
            </div>
            <div class="flex items-baseline justify-between gap-3">
              <span class="text-navy/60">Spädningsvatten</span>
              <span class="text-navy">{{ props.prep.chemistry.diluent_volume_ml }} ml</span>
            </div>
          </template>
        </div>

        <div class="space-y-3 text-sm">
          <div
            v-if="props.instructions.length > 0"
            class="space-y-2"
          >
            <p class="font-semibold text-navy">Steg</p>
            <ol class="list-decimal pl-5 space-y-1">
              <li
                v-for="(item, index) in props.instructions"
                :key="index"
                class="text-navy"
              >
                {{ item }}
              </li>
            </ol>
          </div>

          <div
            v-if="props.warnings.length > 0"
            class="p-3 border border-warning bg-warning/10 shadow-none space-y-1"
          >
            <p class="font-semibold text-warning">Varningar</p>
            <ul class="list-disc pl-5 space-y-1 text-warning">
              <li
                v-for="(warning, index) in props.warnings"
                :key="index"
              >
                {{ warning }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div
        v-if="props.safety"
        class="p-3 border border-navy bg-canvas shadow-none space-y-2 text-sm"
      >
        <p class="font-semibold text-navy">Säkerhet</p>
        <p
          v-if="props.safety.level === 'unknown'"
          class="text-warning"
        >
          {{ props.safety.message ?? "Okänt ämne: konsultera SDS innan användning." }}
        </p>
        <div
          v-else
          class="space-y-1"
        >
          <p
            v-if="props.safety.display_name"
            class="text-navy"
          >
            {{ props.safety.display_name }}
          </p>
          <p
            v-if="props.safetyPpe.length > 0"
            class="text-navy/80"
          >
            PPE: {{ props.safetyPpe.join(", ") }}
          </p>
          <p
            v-if="props.safety.disposal"
            class="text-navy/80"
          >
            Avfall: {{ props.safety.disposal }}
          </p>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2 pt-2">
        <button
          type="button"
          class="btn-ghost"
          @click="emit('back')"
        >
          ← Ändra indata
        </button>

        <button
          type="button"
          class="btn-primary"
          :disabled="props.isExporting || !props.canExport"
          @click="emit('export')"
        >
          {{ props.isExporting ? "Exporterar…" : "Exportera PDF" }}
        </button>

        <button
          type="button"
          class="btn-ghost"
          :disabled="props.isSavingPdfToVault || !props.canExport"
          @click="emit('save')"
        >
          {{ props.isSavingPdfToVault ? "Sparar…" : "Spara i Mina filer" }}
        </button>

        <button
          type="button"
          class="btn-ghost"
          :disabled="props.isExporting || props.isSavingPdfToVault"
          @click="emit('reset')"
        >
          Nollställ
        </button>
      </div>

      <p
        v-if="props.lastSavedPdfVaultRef"
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

      <p
        v-if="props.actionErrorMessage"
        class="text-sm text-critical whitespace-pre-wrap"
      >
        {{ props.actionErrorMessage }}
      </p>
    </div>
  </section>
</template>
