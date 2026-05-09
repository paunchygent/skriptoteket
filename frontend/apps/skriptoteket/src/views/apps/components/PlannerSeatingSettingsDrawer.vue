<script setup lang="ts">
/**
 * Seating advanced Smart settings drawer.
 *
 * This drawer owns the teacher-facing Smart opt-out controls for seating while
 * leaving rule authoring in the dedicated Regler workspace.
 */

import { onMounted, onUnmounted } from "vue";

import { IconX } from "../../../components/icons";
import { UiDenseActionButton, UiDenseToggle } from "../../../components/ui";
import { useToast } from "../../../composables/useToast";
import {
  SMART_DISABLED_NOTICE,
  isHistoryEnabledByDefault,
  isSmartEnabledByDefault,
} from "../classroomPlannerSmartPreferences";
import { useClassroomState } from "../useClassroomState";

const props = withDefaults(defineProps<{
  open: boolean;
  showHistorySetting?: boolean;
}>(), {
  showHistorySetting: true,
});

const emit = defineEmits<{
  (e: "close"): void;
  (e: "open-rules"): void;
}>();

const state = useClassroomState();
const toast = useToast();

function setSmartEnabled(enabled: boolean): void {
  state.setDraftSmartEnabled(enabled);
  if (!enabled) {
    toast.warning(SMART_DISABLED_NOTICE);
  }
}

function openRules(): void {
  emit("open-rules");
  emit("close");
}

function handleDocumentKeydown(event: KeyboardEvent): void {
  if (!props.open || event.key !== "Escape") {
    return;
  }
  emit("close");
}

onMounted(() => {
  document.addEventListener("keydown", handleDocumentKeydown);
});

onUnmounted(() => {
  document.removeEventListener("keydown", handleDocumentKeydown);
});
</script>

<template>
  <div v-if="open">
    <div
      class="fixed inset-0 z-40 bg-navy/40"
      data-test="seating-settings-backdrop"
      @click="emit('close')"
    />
    <aside
      class="fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-[26rem] flex-col border border-navy bg-modal shadow-brutal"
      data-test="seating-settings-drawer"
      role="dialog"
      aria-modal="true"
      aria-labelledby="seating-settings-title"
    >
      <div class="flex items-start justify-between gap-3 border-b border-navy/20 p-4">
        <div class="min-w-0">
          <h3
            id="seating-settings-title"
            class="font-serif text-xl text-navy"
          >
            Avancerade inställningar
          </h3>
        </div>
        <button
          type="button"
          class="btn-ghost planner-btn-ghost-canvas planner-btn-icon-sm"
          aria-label="Stäng avancerade inställningar"
          @click="emit('close')"
        >
          <IconX :size="14" />
        </button>
      </div>

      <div class="flex-1 space-y-4 overflow-y-auto p-4">
        <section class="space-y-2 border border-navy/20 bg-canvas p-4">
          <UiDenseToggle
            data-test="seating-settings-smart-toggle"
            label="Smart placering"
            :model-value="isSmartEnabledByDefault(state.draft)"
            :disabled="state.isWorkspaceBusy"
            @update:model-value="setSmartEnabled"
          />
          <p class="text-sm leading-relaxed text-navy/65">
            Tar hänsyn till dina regler när du skapar en ny placering, till exempel fasta platser eller elever som inte bör sitta nära varandra.
          </p>
        </section>

        <section
          v-if="showHistorySetting"
          class="space-y-2 border border-navy/20 bg-canvas p-4"
        >
          <UiDenseToggle
            data-test="seating-settings-history-toggle"
            label="Historik"
            :model-value="isHistoryEnabledByDefault(state.draft)"
            :disabled="state.isWorkspaceBusy"
            @update:model-value="state.setDraftUseHistoryEnabled($event)"
          />
          <p class="text-sm leading-relaxed text-navy/65">
            Försöker undvika att elever får samma plats eller samma bordsgrannar som tidigare. Stäng av om du vill börja utan historik.
          </p>
        </section>

        <section class="space-y-3 border border-navy/20 bg-canvas p-4">
          <div class="space-y-1">
            <h4 class="text-sm font-semibold text-navy">
              Regler
            </h4>
            <p class="text-sm leading-relaxed text-navy/65">
              Lägg till och ändra regler för placeringar.
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
