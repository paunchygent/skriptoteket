<script setup lang="ts">
/**
 * Room template create/edit modal.
 *
 * This modal now acts as the composition shell for the room-template editor.
 * Interactive builder state lives in the extracted editor composable, while the
 * modal keeps ownership of submit/delete transport and open/close lifecycle.
 */

import { computed, nextTick, ref, toRef } from "vue";

import { apiDelete, apiPost, apiPut } from "../../../api/client";
import { IconSave, IconTrash, IconX } from "../../../components/icons";
import SystemMessage from "../../../components/ui/SystemMessage.vue";
import type { RoomTemplate } from "../classroomPlannerTypes";
import { useRoomTemplateEditorState } from "../useRoomTemplateEditorState";
import RoomTemplateBuilderSurface from "./RoomTemplateBuilderSurface.vue";
import RoomTemplateEditorSidebar from "./RoomTemplateEditorSidebar.vue";
import RoomTemplatePreviewScene from "./RoomTemplatePreviewScene.vue";

const props = defineProps<{
  template?: RoomTemplate | null;
  saveTemplate?: (payload: {
    existingTemplate: RoomTemplate | null;
    name: string;
    grid_cols: number;
    grid_rows: number;
    seats: RoomTemplate["seats"];
    fixtures: RoomTemplate["fixtures"];
  }) => Promise<RoomTemplate>;
  deleteTemplate?: (templateId: string) => Promise<void>;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "saved", template: RoomTemplate): void;
  (e: "deleted", templateId: string): void;
}>();

const isEditing = computed(() => Boolean(props.template));
const isSubmitting = ref(false);
const isDeleting = ref(false);
const nameRequiredMessage = "Ge klassrummet ett namn innan du sparar.";
const editorSidebar = ref<InstanceType<typeof RoomTemplateEditorSidebar> | null>(null);

const {
  name,
  selectedTool,
  error,
  roomGrid,
  canShrinkCols,
  canShrinkRows,
  roomFixturePalette,
  parsedSeats,
  parsedFixtures,
  ghostPlacement,
  ghostRenderableFixture,
  builderScale,
  builderScaledSurfaceStyle,
  builderScalePercent,
  isValid,
  updateHoverState,
  focusCell,
  clearHoverState,
  toggleGridCell,
  resizeRoom,
  setBuilderViewportSize,
  zoomOut,
  zoomIn,
  zoomBuilderByFactor,
  resetBuilderZoom,
  clearRoomContents,
} = useRoomTemplateEditorState(toRef(props, "template"));

const nameValidationError = computed(() => {
  return error.value === nameRequiredMessage ? nameRequiredMessage : null;
});
const modalSystemError = computed(() => {
  return error.value && error.value !== nameRequiredMessage ? error.value : null;
});
const primarySaveLabel = computed(() => {
  if (isSubmitting.value) {
    return "Sparar...";
  }
  return isEditing.value ? "Spara" : "Skapa";
});

function updateName(value: string): void {
  name.value = value;
  if (error.value === nameRequiredMessage && value.trim().length > 0) {
    error.value = null;
  }
}

async function showNameRequiredError(): Promise<void> {
  error.value = nameRequiredMessage;
  await nextTick();
  editorSidebar.value?.focusNameInput();
}

async function submit(): Promise<void> {
  if (!isValid.value) {
    await showNameRequiredError();
    return;
  }

  isSubmitting.value = true;
  error.value = null;

  try {
    const payload = {
      name: name.value.trim(),
      grid_cols: roomGrid.value.cols,
      grid_rows: roomGrid.value.rows,
      seats: parsedSeats.value,
      fixtures: parsedFixtures.value,
    };
    const response = props.saveTemplate
      ? await props.saveTemplate({
          existingTemplate: props.template ?? null,
          ...payload,
        })
      : isEditing.value && props.template
        ? await apiPut<RoomTemplate>(
            `/api/v1/apps/classroom.group-seating-studio/templates/${props.template.id}`,
            payload,
          )
        : await apiPost<RoomTemplate>(
            "/api/v1/apps/classroom.group-seating-studio/templates",
            payload,
          );
    emit("saved", response);
  } catch (submitError: unknown) {
    error.value = submitError instanceof Error ? submitError.message : "Kunde inte spara klassrummet.";
  } finally {
    isSubmitting.value = false;
  }
}

async function removeTemplate(): Promise<void> {
  if (!props.template) {
    return;
  }

  isDeleting.value = true;
  error.value = null;

  try {
    if (props.deleteTemplate) {
      await props.deleteTemplate(props.template.id);
    } else {
      await apiDelete<void>(`/api/v1/apps/classroom.group-seating-studio/templates/${props.template.id}`);
    }
    emit("deleted", props.template.id);
  } catch {
    error.value = "Det gick inte att ta bort klassrummet. Försök igen eller stäng dialogrutan.";
  } finally {
    isDeleting.value = false;
  }
}
</script>

<template>
  <div class="room-template-modal-root fixed inset-0 z-50 overflow-y-auto p-4">
    <button
      type="button"
      aria-label="Stäng modal"
      class="planner-overlay-backdrop"
      @click="emit('close')"
    />
    <div class="room-template-modal-positioner relative flex min-h-full items-start justify-center py-4">
      <div
        class="room-template-modal-panel flex max-h-[calc(100vh-1rem)] w-full max-w-[96vw] flex-col border border-navy bg-modal shadow-brutal 2xl:max-w-[1680px]"
        data-test="room-template-modal-panel"
      >
        <div class="room-template-modal-header flex items-start justify-between gap-4 border-b border-navy/20 pb-4">
          <div class="space-y-1 px-6 pt-6 md:px-8 md:pt-8">
            <h2 class="font-serif text-2xl text-navy">
              {{ isEditing ? "Redigera klassrum" : "Nytt klassrum" }}
            </h2>
            <p class="max-w-[40rem] text-sm leading-relaxed text-navy/70">
              Placera ut sittplatser och möbler i klassrummet.
            </p>
          </div>
          <button
            type="button"
            class="mr-6 mt-6 btn-ghost planner-btn-ghost-canvas planner-btn-icon-md shrink-0 md:mr-8 md:mt-8"
            aria-label="Stäng modal"
            @click="emit('close')"
          >
            ×
          </button>
        </div>

        <div class="room-template-modal-body min-h-0 flex-1 overflow-y-auto px-6 pb-6 pt-4 md:px-8 md:pb-8">
          <SystemMessage
            v-if="modalSystemError"
            v-model="error"
            variant="error"
          />

          <div class="room-template-modal-editor-grid mt-6 grid gap-6 xl:grid-cols-[240px_minmax(0,1fr)] xl:items-start">
            <RoomTemplateEditorSidebar
              ref="editorSidebar"
              :name="name"
              :name-error="nameValidationError"
              :selected-tool="selectedTool"
              :seat-count="parsedSeats.length"
              :room-grid="roomGrid"
              :can-shrink-cols="canShrinkCols"
              :can-shrink-rows="canShrinkRows"
              :room-fixture-palette="roomFixturePalette"
              @update:name="updateName"
              @update:selected-tool="selectedTool = $event"
              @resize-room="resizeRoom($event.axis, $event.delta)"
              @clear-room="clearRoomContents"
            />

            <section class="room-template-modal-builder-column flex min-h-0 min-w-0 flex-col gap-4">
              <RoomTemplateBuilderSurface
                :room-grid="roomGrid"
                :seats="parsedSeats"
                :fixtures="parsedFixtures"
                :ghost-placement="ghostPlacement"
                :ghost-renderable-fixture="ghostRenderableFixture"
                :builder-scale="builderScale"
                :builder-scaled-surface-style="builderScaledSurfaceStyle"
                :builder-scale-percent="builderScalePercent"
                @zoom-out="zoomOut"
                @zoom-in="zoomIn"
                @zoom-by-factor="zoomBuilderByFactor"
                @zoom-fit="resetBuilderZoom"
                @clear-hover="clearHoverState"
                @cell-hover="updateHoverState"
                @cell-focus="focusCell"
                @cell-click="toggleGridCell"
                @viewport-size="setBuilderViewportSize"
              />

              <RoomTemplatePreviewScene
                :room-grid="roomGrid"
                :seats="parsedSeats"
                :fixtures="parsedFixtures"
              />
            </section>
          </div>
        </div>

        <div class="room-template-modal-footer sticky bottom-0 flex flex-col gap-3 border-t border-navy/20 bg-modal px-6 py-4 sm:flex-row sm:items-center sm:justify-between md:px-8">
          <div class="room-template-modal-footer-danger">
            <button
              v-if="isEditing"
              type="button"
              class="room-template-modal-footer-button btn-ghost planner-btn-danger inline-flex items-center justify-center gap-2"
              data-test="room-template-delete-button"
              :disabled="isDeleting"
              @click="removeTemplate"
            >
              <IconTrash :size="14" />
              <span>{{ isDeleting ? "Raderar..." : "Radera" }}</span>
            </button>
          </div>
          <div class="room-template-modal-footer-actions flex flex-wrap justify-end gap-3">
            <button
              type="button"
              class="room-template-modal-footer-button btn-ghost planner-btn-ghost-canvas inline-flex items-center justify-center gap-2"
              data-test="room-template-cancel-button"
              @click="emit('close')"
            >
              <IconX :size="14" />
              <span>Avbryt</span>
            </button>
            <button
              type="button"
              class="room-template-modal-footer-button btn-primary inline-flex items-center justify-center gap-2"
              data-test="room-template-save-button"
              :disabled="isSubmitting"
              @click="submit"
            >
              <IconSave :size="14" />
              <span>{{ primarySaveLabel }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
