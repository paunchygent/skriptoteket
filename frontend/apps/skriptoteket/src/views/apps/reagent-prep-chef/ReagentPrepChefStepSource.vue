<script setup lang="ts">
import { SystemMessage } from "../../../components/ui";
import type { ReagentPrepChefFieldErrors, ReagentPrepChefFormState } from "./types";

type Props = {
  isCalculating: boolean;
  isExporting: boolean;
  canCalculate: boolean;
  actionErrorMessage: string | null;
  fieldErrors: ReagentPrepChefFieldErrors;
  prerequisiteErrors: string[];
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
  <section class="rounded-[var(--huleedu-panel-radius)] border border-navy/20 bg-panel">
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
            :aria-invalid="Boolean(props.fieldErrors.targetMolarity)"
            :aria-describedby="props.fieldErrors.targetMolarity ? 'rpc-target-error' : undefined"
            inputmode="decimal"
            class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-3 py-2 text-navy"
          >
          <p
            v-if="props.fieldErrors.targetMolarity"
            id="rpc-target-error"
            class="text-xs text-error"
            role="alert"
          >
            {{ props.fieldErrors.targetMolarity }}
          </p>
        </div>

        <div class="space-y-2">
          <label
            for="rpc-source"
            class="text-sm font-semibold text-navy"
          >Källa</label>
          <select
            id="rpc-source"
            v-model="form.sourceType"
            class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-3 py-2 text-navy"
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
            :aria-invalid="Boolean(props.fieldErrors.stockMolarity)"
            :aria-describedby="props.fieldErrors.stockMolarity ? 'rpc-stock-error' : undefined"
            inputmode="decimal"
            class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-3 py-2 text-navy"
          >
          <p
            v-if="props.fieldErrors.stockMolarity"
            id="rpc-stock-error"
            class="text-xs text-error"
            role="alert"
          >
            {{ props.fieldErrors.stockMolarity }}
          </p>
        </div>

        <div class="space-y-2">
          <label
            for="rpc-purity"
            class="text-sm font-semibold text-navy"
          >Renhet (0–1)</label>
          <input
            id="rpc-purity"
            v-model="form.solutePurity"
            :aria-invalid="Boolean(props.fieldErrors.solutePurity)"
            :aria-describedby="props.fieldErrors.solutePurity ? 'rpc-purity-error' : undefined"
            inputmode="decimal"
            class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-3 py-2 text-navy"
          >
          <p class="text-xs text-navy/60">Ex: 0,95 om du har teknisk kvalitet.</p>
          <p
            v-if="props.fieldErrors.solutePurity"
            id="rpc-purity-error"
            class="text-xs text-error"
            role="alert"
          >
            {{ props.fieldErrors.solutePurity }}
          </p>
        </div>
      </div>

      <SystemMessage
        v-if="props.prerequisiteErrors.length"
        tone="failure"
      >
        <ul>
          <li
            v-for="message in props.prerequisiteErrors"
            :key="message"
          >
            {{ message }}
          </li>
        </ul>
      </SystemMessage>

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

      <SystemMessage
        v-if="props.actionErrorMessage"
        tone="failure"
        class="whitespace-pre-wrap"
      >
        {{ props.actionErrorMessage }}
      </SystemMessage>
    </div>
  </section>
</template>
