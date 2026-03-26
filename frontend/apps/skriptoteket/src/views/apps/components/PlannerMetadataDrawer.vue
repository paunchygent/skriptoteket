<script setup lang="ts">
/**
 * Student notes drawer.
 *
 * This component hosts teacher-authored notes for the active student inside
 * the seating workflow. It keeps the UI anchored in concrete teacher
 * observations instead of exposing speculative rule-engine controls.
 */

import { computed } from "vue";

import { emptyStudentPlanningMeta } from "../classroomPlannerTypes";
import { useClassroomState } from "../useClassroomState";

const props = defineProps<{
  selectedStudentId?: string | null;
  open?: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

const state = useClassroomState();

const selectedStudent = computed(() => {
  if (!props.selectedStudentId) {
    return null;
  }
  return state.studentsById[props.selectedStudentId] ?? null;
});

const currentMeta = computed(() => {
  if (!props.selectedStudentId) {
    return null;
  }
  return state.studentPlanningMetaByStudentId[props.selectedStudentId] ?? emptyStudentPlanningMeta(props.selectedStudentId);
});
</script>

<template>
  <div v-if="open">
    <div
      class="fixed inset-0 z-40 bg-navy/40"
      @click="emit('close')"
    />
    <aside
      class="fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-[28rem] flex-col border border-navy bg-white shadow-brutal"
    >
      <div class="flex items-start justify-between gap-3 border-b border-navy/20 p-4">
        <div class="min-w-0">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Elevanteckningar
          </p>
          <h3 class="font-serif text-xl text-navy">
            {{ selectedStudent?.display_name ?? "Välj en elev" }}
          </h3>
        </div>
        <button
          type="button"
          class="btn-ghost h-[28px] w-[28px] px-0 py-0 shadow-none border-navy/30 bg-canvas"
          @click="emit('close')"
        >
          ×
        </button>
      </div>

      <div
        v-if="!selectedStudent || !currentMeta"
        class="flex flex-1 items-center justify-center p-6 text-center text-sm leading-relaxed text-navy/60"
      >
        Klicka på en elev i sittschemat för att öppna lärarens elevanteckningar.
      </div>

      <div
        v-else
        class="flex-1 space-y-5 overflow-y-auto p-4"
      >
        <section class="space-y-3 border border-navy/20 bg-canvas p-4">
          <h4 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Lärarens observationer
          </h4>

          <p class="text-sm leading-relaxed text-navy/65">
            Spara fria läraranteckningar här medan den nya smart-regelmodellen
            byggs ut i egna kontroller.
          </p>

          <label class="block space-y-1">
            <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              Anteckningar
            </span>
            <textarea
              :value="currentMeta.notes ?? ''"
              rows="4"
              class="w-full border border-navy/30 bg-white px-3 py-2 text-sm text-navy"
              @input="state.setStudentPlanningMeta(selectedStudent.id, { notes: ($event.target as HTMLTextAreaElement).value || null })"
            />
          </label>

          <button
            type="button"
            class="btn-ghost border-navy/30 bg-white shadow-none"
            @click="state.resetStudentPlanningMeta(selectedStudent.id)"
          >
            Återställ elevanteckningar
          </button>
        </section>
      </div>
    </aside>
  </div>
</template>
