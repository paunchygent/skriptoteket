<script setup lang="ts">
import type { ReagentPrepChefFormState } from "./types";

type Props = {
  derivedGroups: number | null;
  derivedTotalVolumeMl: number | null;
};

const props = defineProps<Props>();
const form = defineModel<ReagentPrepChefFormState>("form", { required: true });

const emit = defineEmits<{
  (event: "back"): void;
  (event: "next"): void;
}>();
</script>

<template>
  <section class="border border-navy bg-white shadow-brutal-sm">
    <div class="p-4 space-y-4">
      <div class="space-y-1">
        <h2 class="text-lg font-semibold text-navy">Klass</h2>
        <p class="text-sm text-navy/60">
          Använd kommatal (t.ex. <span class="font-mono">0,10</span>) om du vill.
        </p>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
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
            class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
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
            class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
          >
        </div>

        <div class="space-y-2">
          <label
            for="rpc-vol-group"
            class="text-sm font-semibold text-navy"
          >Volym per grupp (ml)</label>
          <input
            id="rpc-vol-group"
            v-model="form.volPerGroupMl"
            inputmode="decimal"
            class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
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
            class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
          >
          <p class="text-xs text-navy/60">Ex: 0,10 = 10% extra.</p>
        </div>
      </div>

      <div class="p-3 border border-navy bg-canvas shadow-none text-sm text-navy/80 space-y-1">
        <p class="font-semibold text-navy">Snabb översikt</p>
        <p v-if="props.derivedGroups !== null">
          Grupper: <span class="font-mono">{{ props.derivedGroups }}</span>
        </p>
        <p v-if="props.derivedTotalVolumeMl !== null">
          Totalvolym (ca):
          <span class="font-mono">{{ props.derivedTotalVolumeMl.toFixed(1) }}</span> ml
        </p>
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
          :disabled="props.derivedGroups === null || props.derivedTotalVolumeMl === null"
          @click="emit('next')"
        >
          Fortsätt →
        </button>
      </div>
    </div>
  </section>
</template>
