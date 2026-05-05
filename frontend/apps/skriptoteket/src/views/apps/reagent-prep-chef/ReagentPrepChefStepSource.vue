<script setup lang="ts">
import type { ReagentPrepChefFormState } from "./types";

type Props = {
  isCalculating: boolean;
  isExporting: boolean;
  canCalculate: boolean;
  actionErrorMessage: string | null;
};

const props = defineProps<Props>();
const form = defineModel<ReagentPrepChefFormState>("form", { required: true });

const emit = defineEmits<{
  (event: "back"): void;
  (event: "calculate"): void;
  (event: "reset"): void;
}>();
</script>

<template>
  <section class="border border-navy bg-panel shadow-brutal-sm">
    <div class="p-4 space-y-4">
      <div class="space-y-1">
        <h2 class="text-lg font-semibold text-navy">Källa</h2>
        <p class="text-sm text-navy/60">
          Välj om du väger fast ämne eller späder från en stocklösning.
        </p>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-2">
          <label
            for="rpc-target"
            class="text-sm font-semibold text-navy"
          >Målmolaritet (M)</label>
          <input
            id="rpc-target"
            v-model="form.targetMolarity"
            inputmode="decimal"
            class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
          >
        </div>

        <div class="space-y-2">
          <label
            for="rpc-source"
            class="text-sm font-semibold text-navy"
          >Källa</label>
          <select
            id="rpc-source"
            v-model="form.sourceType"
            class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
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
            class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
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
            class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
          >
          <p class="text-xs text-navy/60">Ex: 0,95 om du har teknisk kvalitet.</p>
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
          class="btn-cta min-w-[140px]"
          :disabled="props.isCalculating || !props.canCalculate"
          @click="emit('calculate')"
        >
          {{ props.isCalculating ? "Beräknar…" : "Beräkna" }}
        </button>

        <button
          type="button"
          class="btn-ghost"
          :disabled="props.isCalculating || props.isExporting"
          @click="emit('reset')"
        >
          Nollställ
        </button>
      </div>

      <p
        v-if="props.actionErrorMessage"
        class="text-sm text-critical whitespace-pre-wrap"
      >
        {{ props.actionErrorMessage }}
      </p>
    </div>
  </section>
</template>
