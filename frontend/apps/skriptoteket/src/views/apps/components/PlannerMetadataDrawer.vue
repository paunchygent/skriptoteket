<script setup lang="ts">
/**
 * Student planning metadata drawer.
 *
 * This component hosts teacher-only planning inputs for the active student. It
 * edits draft-scoped metadata and pair constraints directly through the planner
 * store while keeping those fields out of the draggable roster card surface.
 */

import { computed, ref, watch } from "vue";

import { pairConstraintLabels, type PairConstraintKind } from "../classroomPlannerTypes";
import { useClassroomState } from "../useClassroomState";

const props = defineProps<{
  selectedStudentId?: string | null;
  open?: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

const state = useClassroomState();
const peerStudentId = ref<string | null>(null);

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
  return (
    state.studentPlanningMetaByStudentId[props.selectedStudentId] ?? {
      student_id: props.selectedStudentId,
      teacher_proximity: 0,
      independent_focus_support: 0,
      stability_preference: 0,
      preferred_zone: null,
      avoid_zone: null,
      notes: null,
    }
  );
});

const peerOptions = computed(() => {
  if (!props.selectedStudentId) {
    return [];
  }
  return state.students.filter((student) => student.id !== props.selectedStudentId);
});

watch(
  [() => props.selectedStudentId, peerOptions],
  ([studentId, peers]) => {
    if (!studentId) {
      peerStudentId.value = null;
      return;
    }
    if (peerStudentId.value && peers.some((student) => student.id === peerStudentId.value)) {
      return;
    }
    peerStudentId.value = peers[0]?.id ?? null;
  },
  { immediate: true },
);

function constraintFor(kind: PairConstraintKind) {
  if (!props.selectedStudentId || !peerStudentId.value) {
    return null;
  }
  const [studentIdA, studentIdB] =
    props.selectedStudentId <= peerStudentId.value
      ? [props.selectedStudentId, peerStudentId.value]
      : [peerStudentId.value, props.selectedStudentId];
  return (
    state.pairConstraints.find(
      (constraint) =>
        constraint.student_id_a === studentIdA &&
        constraint.student_id_b === studentIdB &&
        constraint.kind === kind,
    ) ?? null
  );
}

function toggleConstraint(kind: PairConstraintKind, enabled: boolean): void {
  if (!props.selectedStudentId || !peerStudentId.value) {
    return;
  }
  state.setPairConstraint(props.selectedStudentId, peerStudentId.value, kind, enabled, 1);
}

function updateConstraintStrength(kind: PairConstraintKind, strength: number): void {
  if (!props.selectedStudentId || !peerStudentId.value) {
    return;
  }
  state.setPairConstraint(props.selectedStudentId, peerStudentId.value, kind, true, strength);
}
</script>

<template>
  <div>
    <div
      v-if="open"
      class="fixed inset-0 z-40 bg-navy/40 lg:hidden"
      @click="emit('close')"
    />
    <aside
      class="flex h-full flex-col border border-navy bg-white shadow-brutal lg:shadow-brutal-sm"
      :class="open ? 'fixed inset-y-0 right-0 z-50 w-full max-w-[28rem] lg:static lg:w-auto' : 'hidden lg:flex'"
    >
      <div class="flex items-start justify-between gap-3 border-b border-navy/20 p-4">
        <div class="min-w-0">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Planeringsmetadata
          </p>
          <h3 class="font-serif text-xl text-navy">
            {{ selectedStudent?.display_name ?? "Välj en elev" }}
          </h3>
        </div>
        <button
          type="button"
          class="btn-ghost h-[28px] w-[28px] px-0 py-0 shadow-none border-navy/30 bg-canvas lg:hidden"
          @click="emit('close')"
        >
          ×
        </button>
      </div>

      <div
        v-if="!selectedStudent || !currentMeta"
        class="flex flex-1 items-center justify-center p-6 text-center text-sm leading-relaxed text-navy/60"
      >
        Klicka på en elev i grupp- eller sittplatsvyn för att redigera lärarens planeringsnoteringar.
      </div>

      <div
        v-else
        class="flex-1 space-y-5 overflow-y-auto p-4"
      >
        <section class="space-y-3 border border-navy/20 bg-canvas p-4">
          <h4 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Individuell profil
          </h4>

          <label class="block space-y-1">
            <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              Lärarnärhet
            </span>
            <input
              :value="currentMeta.teacher_proximity"
              type="range"
              min="0"
              max="3"
              step="1"
              class="w-full"
              @input="state.setStudentPlanningMeta(selectedStudent.id, { teacher_proximity: Number(($event.target as HTMLInputElement).value) })"
            >
          </label>

          <label class="block space-y-1">
            <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              Fokusstöd
            </span>
            <input
              :value="currentMeta.independent_focus_support"
              type="range"
              min="0"
              max="3"
              step="1"
              class="w-full"
              @input="state.setStudentPlanningMeta(selectedStudent.id, { independent_focus_support: Number(($event.target as HTMLInputElement).value) })"
            >
          </label>

          <label class="block space-y-1">
            <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              Stabilitetsbehov
            </span>
            <input
              :value="currentMeta.stability_preference"
              type="range"
              min="0"
              max="3"
              step="1"
              class="w-full"
              @input="state.setStudentPlanningMeta(selectedStudent.id, { stability_preference: Number(($event.target as HTMLInputElement).value) })"
            >
          </label>

          <div class="grid gap-3 md:grid-cols-2">
            <label class="space-y-1">
              <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                Föredragen zon
              </span>
              <select
                :value="currentMeta.preferred_zone ?? ''"
                class="w-full border border-navy/30 bg-white px-3 py-2 text-sm text-navy"
                @change="state.setStudentPlanningMeta(selectedStudent.id, { preferred_zone: ($event.target as HTMLSelectElement).value || null })"
              >
                <option value="">
                  Ingen
                </option>
                <option
                  v-for="zone in state.zones"
                  :key="zone"
                  :value="zone"
                >
                  {{ zone }}
                </option>
              </select>
            </label>

            <label class="space-y-1">
              <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                Undvik zon
              </span>
              <select
                :value="currentMeta.avoid_zone ?? ''"
                class="w-full border border-navy/30 bg-white px-3 py-2 text-sm text-navy"
                @change="state.setStudentPlanningMeta(selectedStudent.id, { avoid_zone: ($event.target as HTMLSelectElement).value || null })"
              >
                <option value="">
                  Ingen
                </option>
                <option
                  v-for="zone in state.zones"
                  :key="zone"
                  :value="zone"
                >
                  {{ zone }}
                </option>
              </select>
            </label>
          </div>

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
            Återställ elevdata
          </button>
        </section>

        <section class="space-y-3 border border-navy/20 bg-white p-4">
          <h4 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Parrelationer
          </h4>

          <label class="block space-y-1">
            <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              Jämför med elev
            </span>
            <select
              v-model="peerStudentId"
              class="w-full border border-navy/30 bg-canvas px-3 py-2 text-sm text-navy"
            >
              <option
                v-for="student in peerOptions"
                :key="student.id"
                :value="student.id"
              >
                {{ student.display_name }}
              </option>
            </select>
          </label>

          <div
            v-for="kind in (Object.keys(pairConstraintLabels) as PairConstraintKind[])"
            :key="kind"
            class="space-y-2 border border-navy/20 bg-canvas p-3"
          >
            <label class="flex items-center justify-between gap-3">
              <span class="text-sm font-semibold text-navy">
                {{ pairConstraintLabels[kind] }}
              </span>
              <input
                :checked="Boolean(constraintFor(kind))"
                type="checkbox"
                class="h-4 w-4"
                @change="toggleConstraint(kind, ($event.target as HTMLInputElement).checked)"
              >
            </label>

            <div
              v-if="constraintFor(kind)"
              class="space-y-1"
            >
              <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                Styrka
              </span>
              <input
                :value="constraintFor(kind)?.strength ?? 1"
                type="range"
                min="1"
                max="3"
                step="1"
                class="w-full"
                @input="updateConstraintStrength(kind, Number(($event.target as HTMLInputElement).value))"
              >
            </div>
          </div>
        </section>
      </div>
    </aside>
  </div>
</template>
