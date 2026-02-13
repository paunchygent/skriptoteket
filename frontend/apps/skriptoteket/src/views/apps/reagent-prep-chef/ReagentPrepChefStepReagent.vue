<script setup lang="ts">
import UiSearchBar from "../../../components/ui/UiSearchBar.vue";

import type {
  ReagentPrepChefChemicalOption,
  ReagentPrepChefFormState,
} from "./types";

type Props = {
  chemicals: ReagentPrepChefChemicalOption[];
  chemicalSearchIsActive: boolean;
  chemicalSearchResults: ReagentPrepChefChemicalOption[];
};

const props = defineProps<Props>();
const form = defineModel<ReagentPrepChefFormState>("form", { required: true });
const selectedChemicalKey = defineModel<string>("selectedChemicalKey", { required: true });
const chemicalQuery = defineModel<string>("chemicalQuery", { required: true });

const emit = defineEmits<{
  (event: "selectChemical", item: ReagentPrepChefChemicalOption): void;
  (event: "next"): void;
}>();
</script>

<template>
  <section class="border border-navy bg-white shadow-brutal-sm">
    <div class="p-4 space-y-4">
      <div class="space-y-1">
        <h2 class="text-lg font-semibold text-navy">Ämne</h2>
        <p class="text-sm text-navy/60">
          Exempel: <span class="font-mono">CuSO4·5H2O</span>, <span class="font-mono">NaCl</span>,
          <span class="font-mono">KMnO4</span>
        </p>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-2">
          <label class="text-sm font-semibold text-navy">Ämneslista (valfritt)</label>

          <div class="relative">
            <UiSearchBar
              v-model="chemicalQuery"
              placeholder="Sök (minst 2 tecken)…"
              :show-button="false"
              variant="panel"
            />

            <Transition name="popover">
              <div
                v-if="props.chemicalSearchIsActive"
                class="absolute left-0 right-0 mt-2 z-50 max-h-56 overflow-auto border border-navy bg-white shadow-brutal-sm"
              >
                <div
                  v-if="props.chemicalSearchResults.length === 0"
                  class="p-3 text-xs text-navy/60"
                >
                  Inga träffar.
                </div>
                <ul
                  v-else
                  class="divide-y divide-navy/10"
                  role="listbox"
                >
                  <li
                    v-for="item in props.chemicalSearchResults"
                    :key="item.key"
                  >
                    <button
                      type="button"
                      class="w-full text-left px-3 py-2 hover:bg-canvas transition-colors"
                      @click="emit('selectChemical', item)"
                    >
                      <div class="flex items-baseline justify-between gap-2">
                        <span class="text-sm font-semibold text-navy">{{ item.display_name }}</span>
                        <span class="font-mono text-xs text-navy/60">{{ item.key }}</span>
                      </div>
                    </button>
                  </li>
                </ul>
              </div>
            </Transition>
          </div>

          <select
            v-model="selectedChemicalKey"
            class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
          >
            <option value="">— Välj i listan —</option>
            <option
              v-for="item in props.chemicals"
              :key="item.key"
              :value="item.key"
            >
              {{ item.display_name }} ({{ item.key }})
            </option>
          </select>
          <p class="text-xs text-navy/60">
            Listan fylls på över tid. Saknas ditt ämne? Skriv formeln manuellt.
          </p>
        </div>

        <div class="space-y-2">
          <label
            for="rpc-formula"
            class="text-sm font-semibold text-navy"
          >Kemisk formel</label>
          <input
            id="rpc-formula"
            v-model="form.chemicalFormula"
            type="text"
            placeholder="CuSO4·5H2O"
            class="w-full border border-navy bg-white px-3 py-2 shadow-none text-navy"
          >
          <p class="text-xs text-navy/60">
            Tips: skriv hydrat som <span class="font-mono">CuSO4·5H2O</span>.
          </p>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2 pt-2">
        <button
          type="button"
          class="btn-primary"
          :disabled="!form.chemicalFormula.trim()"
          @click="emit('next')"
        >
          Fortsätt →
        </button>
      </div>
    </div>
  </section>
</template>
