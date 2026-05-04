<script setup lang="ts">
/**
 * Combined overview setup panel for class list and classroom selection.
 *
 * Relationships:
 * - used by the Klassrumskartan overview shell for both desktop and phone
 * - keeps class-list and classroom management in one framed panel instead of
 *   competing overview cards
 * - emits only selection and management intents; the parent owns modal and
 *   draft orchestration
 */

import { computed } from "vue";

import { IconEdit, IconPlus, IconTrash } from "../../../components/icons";
import type { RoomTemplate, Roster } from "../classroomPlannerTypes";

const props = withDefaults(
  defineProps<{
    variant?: "desktop" | "phone";
    selectedRoster: Roster | null;
    selectedRosterId: string | null;
    selectedRosterCountLabel?: string | null;
    availableRosters: Roster[];
    selectedTemplate: RoomTemplate | null;
    selectedTemplateId: string | null;
    availableTemplates: RoomTemplate[];
    isLoadingWorkspace: boolean;
    showRosterActions?: boolean;
    showTemplateActions?: boolean;
    rosterCreateDisabledReason?: string | null;
    rosterEditDisabledReason?: string | null;
    rosterDeleteDisabledReason?: string | null;
    templateCreateDisabledReason?: string | null;
    templateEditDisabledReason?: string | null;
    templateDeleteDisabledReason?: string | null;
  }>(),
  {
    variant: "desktop",
    selectedRosterCountLabel: null,
    showRosterActions: true,
    showTemplateActions: true,
    rosterCreateDisabledReason: null,
    rosterEditDisabledReason: null,
    rosterDeleteDisabledReason: null,
    templateCreateDisabledReason: null,
    templateEditDisabledReason: null,
    templateDeleteDisabledReason: null,
  },
);

const emit = defineEmits<{
  (e: "select-roster", rosterId: string): void;
  (e: "create-roster"): void;
  (e: "edit-roster"): void;
  (e: "delete-current-roster"): void;
  (e: "select-template", templateId: string | null): void;
  (e: "create-template"): void;
  (e: "edit-current-template", template?: RoomTemplate): void;
  (e: "delete-current-template"): void;
}>();

const isPhone = computed(() => props.variant === "phone");
const testPrefix = computed(() => (isPhone.value ? "phone-overview" : "overview"));
const rosterPanelTestId = computed(() => `${testPrefix.value}-roster-panel`);
const templatePanelTestId = computed(() => `${testPrefix.value}-template-panel`);
const rosterSelectTestId = computed(() => `${testPrefix.value}-roster-select`);
const templateSelectTestId = computed(() => `${testPrefix.value}-template-select`);
const editRosterTestId = computed(() => `${testPrefix.value}-edit-roster`);
const createRosterTestId = computed(() => `${testPrefix.value}-create-roster`);
const deleteRosterTestId = computed(() => `${testPrefix.value}-delete-roster`);
const editTemplateTestId = computed(() => `${testPrefix.value}-edit-template`);
const createTemplateTestId = computed(() => `${testPrefix.value}-create-template`);
const deleteTemplateTestId = computed(() => `${testPrefix.value}-delete-template`);
const classroomEmptyTestId = computed(() => `${testPrefix.value}-classroom-empty`);

const rosterCountLabel = computed(() => props.selectedRosterCountLabel ?? "0 elever");
const templateCountLabel = computed(() => {
  return props.selectedTemplate ? `${props.selectedTemplate.seats.length} platser` : "Inget valt";
});
const rosterPlaceholderLabel = computed(() => {
  if (isPhone.value && props.availableRosters.length === 0) {
    return "Skapa en klasslista";
  }
  return "Välj klasslista";
});
const templatePlaceholderLabel = computed(() => {
  if (isPhone.value && props.availableTemplates.length === 0) {
    return "Skapa ett klassrum";
  }
  return "Välj klassrum";
});
const isRosterEditDisabled = computed(() => {
  return !props.selectedRoster || Boolean(props.rosterEditDisabledReason);
});
const isRosterDeleteDisabled = computed(() => {
  return !props.selectedRoster || Boolean(props.rosterDeleteDisabledReason);
});
const isTemplateEditDisabled = computed(() => {
  return !props.selectedTemplate || Boolean(props.templateEditDisabledReason);
});
const isTemplateDeleteDisabled = computed(() => {
  return !props.selectedTemplate || Boolean(props.templateDeleteDisabledReason);
});

function selectRoster(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement) || !target.value) {
    return;
  }
  emit("select-roster", target.value);
}

function selectTemplate(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) {
    return;
  }
  emit("select-template", target.value || null);
}
</script>

<template>
  <article
    :class="[
      'planner-overview-setup-panel',
      isPhone ? 'planner-overview-setup-panel-phone' : 'planner-overview-setup-panel-desktop',
    ]"
    :data-test="`${testPrefix}-setup-panel`"
  >
    <section
      class="planner-overview-setup-section"
      :data-test="rosterPanelTestId"
    >
      <div class="planner-overview-setup-heading">
        <h3 class="text-sm font-semibold text-navy">
          Klasslista
        </h3>
        <span class="text-xs text-navy/65">
          {{ rosterCountLabel }}
        </span>
      </div>
      <label class="block">
        <select
          aria-label="Klasslista"
          class="planner-overview-setup-select"
          :value="selectedRosterId ?? ''"
          :data-test="rosterSelectTestId"
          :disabled="isLoadingWorkspace || availableRosters.length === 0"
          @change="selectRoster"
        >
          <option value="">
            {{ rosterPlaceholderLabel }}
          </option>
          <option
            v-for="roster in availableRosters"
            :key="roster.id"
            :value="roster.id"
          >
            {{ roster.name }}
          </option>
        </select>
      </label>
      <div
        v-if="showRosterActions"
        class="planner-overview-setup-actions"
      >
        <button
          type="button"
          class="planner-overview-setup-action"
          :data-test="editRosterTestId"
          :disabled="isRosterEditDisabled"
          :title="rosterEditDisabledReason ?? undefined"
          @click="emit('edit-roster')"
        >
          <IconEdit :size="14" />
          Ändra
        </button>
        <button
          type="button"
          class="planner-overview-setup-action"
          :data-test="createRosterTestId"
          :disabled="Boolean(rosterCreateDisabledReason)"
          :title="rosterCreateDisabledReason ?? undefined"
          @click="emit('create-roster')"
        >
          <IconPlus :size="14" />
          Ny
        </button>
        <button
          type="button"
          class="planner-overview-setup-action planner-overview-setup-action-danger"
          :data-test="deleteRosterTestId"
          :disabled="isRosterDeleteDisabled"
          :title="rosterDeleteDisabledReason ?? undefined"
          @click="emit('delete-current-roster')"
        >
          <IconTrash :size="14" />
          Radera
        </button>
      </div>
    </section>

    <section
      class="planner-overview-setup-section"
      :data-test="templatePanelTestId"
    >
      <div class="planner-overview-setup-heading">
        <h3 class="text-sm font-semibold text-navy">
          Klassrum
        </h3>
        <span class="text-xs text-navy/65">
          {{ templateCountLabel }}
        </span>
      </div>
      <label class="block">
        <select
          aria-label="Klassrum"
          class="planner-overview-setup-select"
          :value="selectedTemplateId ?? ''"
          :data-test="templateSelectTestId"
          :disabled="isLoadingWorkspace || availableTemplates.length === 0"
          @change="selectTemplate"
        >
          <option value="">
            {{ templatePlaceholderLabel }}
          </option>
          <option
            v-for="template in availableTemplates"
            :key="template.id"
            :value="template.id"
          >
            {{ template.name }}
          </option>
        </select>
      </label>
      <div
        v-if="showTemplateActions"
        class="planner-overview-setup-actions"
      >
        <button
          type="button"
          class="planner-overview-setup-action"
          :data-test="editTemplateTestId"
          :disabled="isTemplateEditDisabled"
          :title="templateEditDisabledReason ?? undefined"
          @click="emit('edit-current-template', selectedTemplate ?? undefined)"
        >
          <IconEdit :size="14" />
          Ändra
        </button>
        <button
          type="button"
          class="planner-overview-setup-action"
          :data-test="createTemplateTestId"
          :disabled="Boolean(templateCreateDisabledReason)"
          :title="templateCreateDisabledReason ?? undefined"
          @click="emit('create-template')"
        >
          <IconPlus :size="14" />
          Ny
        </button>
        <button
          type="button"
          class="planner-overview-setup-action planner-overview-setup-action-danger"
          :data-test="deleteTemplateTestId"
          :disabled="isTemplateDeleteDisabled"
          :title="templateDeleteDisabledReason ?? undefined"
          @click="emit('delete-current-template')"
        >
          <IconTrash :size="14" />
          Radera
        </button>
      </div>
      <span
        v-if="!selectedTemplate"
        class="sr-only"
        :data-test="classroomEmptyTestId"
      >{{ templatePlaceholderLabel }}</span>
    </section>
  </article>
</template>
