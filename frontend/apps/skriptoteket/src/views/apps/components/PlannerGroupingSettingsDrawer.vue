<script setup lang="ts">
/**
 * Grouping Smart settings drawer.
 *
 * This drawer keeps secondary Smart tuning outside the first-row grouping
 * toolbar. It lets the teacher adjust history, classroom, and seating
 * influence while leaving rule authoring in the dedicated Regler workspace.
 */

import { computed } from "vue";

import { IconX } from "../../../components/icons";
import {
  DENSE_FORM_INPUT_CLASS,
  UiDenseActionButton,
  UiDenseToggle,
} from "../../../components/ui";
import type { RoomTemplate } from "../classroomPlannerTypes";
import { useClassroomState } from "../useClassroomState";

const props = withDefaults(
  defineProps<{
    open: boolean;
    availableTemplates?: RoomTemplate[];
    selectedTemplateId?: string | null;
    showHistorySetting?: boolean;
  }>(),
  {
    availableTemplates: () => [],
    selectedTemplateId: null,
    showHistorySetting: true,
  },
);

const emit = defineEmits<{
  (e: "close"): void;
  (e: "change-grouping-template", templateId: string | null): void;
  (e: "open-rules"): void;
}>();

const state = useClassroomState();

const hasSelectedTemplate = computed(() => {
  return typeof props.selectedTemplateId === "string" && props.selectedTemplateId.length > 0;
});
const classroomHelpText = computed(() => {
  if (props.availableTemplates.length === 0) {
    return "Det finns inga klassrum att välja ännu.";
  }
  return "Välj ett klassrum om Smart ska ta hänsyn till sittschemat.";
});
const seatingHelpText = computed(() => {
  if (!hasSelectedTemplate.value) {
    return "Välj först ett klassrum för att använda sittschemat.";
  }
  return "Med Tillämpa sittschema aktiverat försöker algoritmen skapa grupper av de elever som sitter nära varandra samtidigt som den respekterar dina övriga regler, som \"håll ihop\" och \"håll isär\".";
});

function changeGroupingTemplate(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) {
    return;
  }
  if (!target.value) {
    state.setDraftGroupingSeatingDistanceEnabled(false);
  }
  emit("change-grouping-template", target.value || null);
}

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
      data-test="grouping-settings-drawer"
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
        <section
          v-if="showHistorySetting"
          class="space-y-2 border border-navy/20 bg-canvas p-4"
        >
          <UiDenseToggle
            data-test="grouping-settings-history-toggle"
            label="Historik"
            :model-value="state.draft?.use_history ?? false"
            :disabled="state.isWorkspaceBusy"
            @update:model-value="state.setDraftUseHistoryEnabled($event)"
          />
          <p class="text-sm leading-relaxed text-navy/65">
            Minskar risken att samma elever hamnar i samma grupp igen.
          </p>
        </section>

        <section class="space-y-2 border border-navy/20 bg-canvas p-4">
          <div class="space-y-1">
            <h4 class="text-sm font-semibold text-navy">
              Klassrum
            </h4>
            <p class="text-sm leading-relaxed text-navy/65">
              {{ classroomHelpText }}
            </p>
          </div>
          <label class="block">
            <select
              aria-label="Klassrum"
              :class="[DENSE_FORM_INPUT_CLASS, 'pr-8']"
              :disabled="state.isWorkspaceBusy || availableTemplates.length === 0"
              :value="selectedTemplateId ?? ''"
              data-test="grouping-settings-template-select"
              @change="changeGroupingTemplate"
            >
              <option value="">
                Utan klassrum
              </option>
              <option
                v-for="template in availableTemplates"
                :key="template.id"
                :value="template.id"
              >
                {{ template.name }} · {{ template.seats.length }} platser
              </option>
            </select>
          </label>
        </section>

        <section class="space-y-2 border border-navy/20 bg-canvas p-4">
          <UiDenseToggle
            data-test="grouping-settings-seating-toggle"
            label="Tillämpa sittschema"
            :model-value="state.draft?.grouping_seating_distance_enabled ?? false"
            :disabled="state.isWorkspaceBusy || !hasSelectedTemplate"
            @update:model-value="state.setDraftGroupingSeatingDistanceEnabled($event)"
          />
          <p class="text-sm leading-relaxed text-navy/65">
            {{ seatingHelpText }}
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
            data-test="grouping-settings-open-rules"
            label="Öppna Regler"
            :disabled="state.isWorkspaceBusy"
            @click="openRules"
          />
        </section>
      </div>
    </aside>
  </div>
</template>
