<script setup lang="ts">
import { ref, watch } from "vue";

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
const suggestionsDismissed = ref(false);

watch(chemicalQuery, () => { suggestionsDismissed.value = false; });

function selectChemical(item: ReagentPrepChefChemicalOption): void {
  suggestionsDismissed.value = true;
  emit("selectChemical", item);
}

function chemicalLabel(item: ReagentPrepChefChemicalOption): string {
  const formula = ` (${item.key})`;
  return item.display_name.endsWith(formula) ? item.display_name : `${item.display_name}${formula}`;
}

const emit = defineEmits<{
  (event: "selectChemical", item: ReagentPrepChefChemicalOption): void;
  (event: "next"): void;
}>();
</script>

<template>
  <section class="rounded-[var(--huleedu-panel-radius)] border border-navy/20 bg-panel">
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
          <label
            for="rpc-chemical-list"
            class="text-sm font-semibold text-navy"
          >Ämneslista (valfritt)</label>

          <div class="relative">
            <UiSearchBar
              v-model="chemicalQuery"
              aria-label="Sök ämne"
              placeholder="Sök (minst 2 tecken)…"
              :show-button="false"
              variant="panel"
            />

            <Transition name="popover">
              <div
                v-if="props.chemicalSearchIsActive && !suggestionsDismissed"
                class="absolute left-0 right-0 mt-2 z-50 max-h-56 overflow-auto rounded-[var(--huleedu-radius-md)] border border-navy/20 bg-modal shadow-md"
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
                >
                  <li
                    v-for="item in props.chemicalSearchResults"
                    :key="item.key"
                  >
                    <button
                      type="button"
                      class="w-full text-left px-3 py-2 hover:bg-canvas transition-colors"
                      @click="selectChemical(item)"
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
            id="rpc-chemical-list"
            v-model="selectedChemicalKey"
            class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-3 py-2 text-navy"
          >
            <option value="">— Välj i listan —</option>
            <option
              v-for="item in props.chemicals"
              :key="item.key"
              :value="item.key"
            >
              {{ chemicalLabel(item) }}
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
            class="w-full rounded-[var(--huleedu-radius-sm)] border border-navy/20 bg-panel px-3 py-2 text-navy"
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
