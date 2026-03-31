<script setup lang="ts">
/**
 * Seating Smart settings drawer.
 *
 * This drawer keeps secondary Smart tuning outside the first-row seating
 * toolbar. It exposes history as a Smart setting while leaving rule authoring
 * in the dedicated Regler workspace.
 */

import { IconX } from "../../../components/icons";
import { UiDenseActionButton, UiDenseToggle } from "../../../components/ui";
import { useClassroomState } from "../useClassroomState";

defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "open-rules"): void;
}>();

const state = useClassroomState();

function openRules(): void {
  emit("open-rules");
  emit("close");
}
</script>

<template>
  <div v-if="open">
    <div
      class="fixed inset-0 z-40 bg-navy/40"
      @click="emit('close')"
    />
    <aside
      class="fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-[26rem] flex-col border border-navy bg-white shadow-brutal"
      data-test="seating-settings-drawer"
    >
      <div class="flex items-start justify-between gap-3 border-b border-navy/20 p-4">
        <div class="min-w-0 space-y-1">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Smart
          </p>
          <h3 class="font-serif text-xl text-navy">
            Smart-inställningar
          </h3>
        </div>
        <button
          type="button"
          class="btn-ghost planner-btn-ghost-canvas planner-btn-icon-sm"
          aria-label="Stäng Smart-inställningar"
          @click="emit('close')"
        >
          <IconX :size="14" />
        </button>
      </div>

      <div class="flex-1 space-y-4 overflow-y-auto p-4">
        <section class="space-y-2 border border-navy/20 bg-canvas p-4">
          <UiDenseToggle
            data-test="seating-settings-history-toggle"
            label="Historik"
            :model-value="state.draft?.use_history ?? false"
            :disabled="state.isWorkspaceBusy"
            @update:model-value="state.setDraftUseHistoryEnabled($event)"
          />
          <p class="text-sm leading-relaxed text-navy/65">
            Om du tidigare har exporterat ett sittschema kan Smart använda det för att variera placeringen över tid.
          </p>
        </section>

        <section class="space-y-3 border border-navy/20 bg-canvas p-4">
          <div class="space-y-1">
            <h4 class="text-sm font-semibold text-navy">
              Regler
            </h4>
            <p class="text-sm leading-relaxed text-navy/65">
              Du lägger till och ändrar regler i arbetsytan Regler.
            </p>
          </div>
          <UiDenseActionButton
            data-test="seating-settings-open-rules"
            label="Öppna Regler"
            :disabled="state.isWorkspaceBusy"
            @click="openRules"
          />
        </section>
      </div>
    </aside>
  </div>
</template>
