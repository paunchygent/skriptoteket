<script setup lang="ts">
/**
 * Grouping advanced Smart settings drawer.
 *
 * This drawer owns the teacher-facing Smart opt-out controls for grouping.
 * It keeps rule authoring in the dedicated Regler workspace while preserving
 * grouping-only classroom and seating influence settings.
 */

import { computed, onMounted, onUnmounted } from "vue";

import { IconX } from "../../../components/icons";
import {
  DENSE_FORM_INPUT_CLASS,
  UiDenseActionButton,
  UiDenseToggle,
} from "../../../components/ui";
import { useToast } from "../../../composables/useToast";
import {
  SMART_DISABLED_NOTICE,
  isGroupingSeatingDistanceEnabledByDefault,
  isHistoryEnabledByDefault,
  isSmartEnabledByDefault,
} from "../classroomPlannerSmartDefaults";
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
const toast = useToast();

const hasSelectedTemplate = computed(() => {
  return typeof props.selectedTemplateId === "string" && props.selectedTemplateId.length > 0;
});
const classroomHelpText = computed(() => {
  if (props.availableTemplates.length === 0) {
    return "Det finns inga klassrum att välja ännu.";
  }
  return "Välj vilket klassrum gruppindelningen hör till. Det avgör vilket sittschema Smart kan använda när Tillämpa sittschema är på.";
});
const seatingHelpText = computed(() => {
  if (!hasSelectedTemplate.value) {
    return "Välj först ett klassrum så Smart vet vilket sittschema som kan användas.";
  }
  return "Försöker lägga elever som redan sitter nära varandra i samma grupp. Det kan göra gruppstarten lugnare när eleverna ska arbeta från sina platser.";
});

function setSmartEnabled(enabled: boolean): void {
  state.setDraftSmartEnabled(enabled);
  if (!enabled) {
    toast.warning(SMART_DISABLED_NOTICE);
  }
}

function changeGroupingTemplate(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) {
    return;
  }
  emit("change-grouping-template", target.value || null);
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
      data-test="grouping-settings-backdrop"
      @click="emit('close')"
    />
    <aside
      class="fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-[26rem] flex-col border border-navy bg-modal shadow-brutal"
      data-test="grouping-settings-drawer"
      role="dialog"
      aria-modal="true"
      aria-labelledby="grouping-settings-title"
    >
      <div class="flex items-start justify-between gap-3 border-b border-navy/20 p-4">
        <div class="min-w-0">
          <h3
            id="grouping-settings-title"
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
            data-test="grouping-settings-smart-toggle"
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
            data-test="grouping-settings-history-toggle"
            label="Historik"
            :model-value="isHistoryEnabledByDefault(state.draft)"
            :disabled="state.isWorkspaceBusy"
            @update:model-value="state.setDraftUseHistoryEnabled($event)"
          />
          <p class="text-sm leading-relaxed text-navy/65">
            Försöker undvika att elever får samma plats eller samma bordsgrannar som tidigare. Stäng av om du vill börja utan historik.
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
            :model-value="hasSelectedTemplate && isGroupingSeatingDistanceEnabledByDefault(state.draft)"
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
              Lägg till och ändra regler för placeringar.
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
