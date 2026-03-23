<script setup lang="ts">
/**
 * Roster create/edit modal.
 *
 * This modal owns the CRUD surface for reusable class lists used by the
 * classroom planner. It keeps roster editing outside the draft workspace so the
 * selection gate can manage class assets without leaking that responsibility
 * into the planner canvas components.
 */

import { computed, ref, watch } from "vue";

import { apiDelete, apiPost, apiPut } from "../../../api/client";
import type { Roster, Student } from "../classroomPlannerTypes";

const props = defineProps<{
  roster?: Roster | null;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "saved", roster: Roster): void;
  (e: "deleted", rosterId: string): void;
}>();

const name = ref("");
const rawStudents = ref("");
const isSubmitting = ref(false);
const isDeleting = ref(false);
const error = ref<string | null>(null);

const isEditing = computed(() => Boolean(props.roster));

watch(
  () => props.roster,
  (roster) => {
    name.value = roster?.name ?? "";
    rawStudents.value = roster?.students.map((student) => student.display_name).join("\n") ?? "";
    error.value = null;
  },
  { immediate: true },
);

const parsedStudents = computed<Student[]>(() => {
  const lines = rawStudents.value
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  const existingStudents = props.roster?.students ?? [];

  return lines.map((displayName, index) => ({
    id: existingStudents[index]?.id ?? crypto.randomUUID(),
    display_name: displayName,
  }));
});

const isValid = computed(() => {
  return name.value.trim().length > 0 && parsedStudents.value.length > 0;
});

async function submit(): Promise<void> {
  if (!isValid.value) {
    return;
  }

  isSubmitting.value = true;
  error.value = null;

  try {
    const payload = {
      name: name.value.trim(),
      students: parsedStudents.value,
    };
    const response = isEditing.value && props.roster
      ? await apiPut<Roster>(
          `/api/v1/apps/classroom.group-seating-studio/rosters/${props.roster.id}`,
          payload,
        )
      : await apiPost<Roster>("/api/v1/apps/classroom.group-seating-studio/rosters", payload);
    emit("saved", response);
  } catch (submitError: unknown) {
    error.value = submitError instanceof Error ? submitError.message : "Kunde inte spara klasslistan.";
  } finally {
    isSubmitting.value = false;
  }
}

async function removeRoster(): Promise<void> {
  if (!props.roster) {
    return;
  }

  isDeleting.value = true;
  error.value = null;

  try {
    await apiDelete<void>(`/api/v1/apps/classroom.group-seating-studio/rosters/${props.roster.id}`);
    emit("deleted", props.roster.id);
  } catch (deleteError: unknown) {
    error.value = deleteError instanceof Error ? deleteError.message : "Kunde inte radera klasslistan.";
  } finally {
    isDeleting.value = false;
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 overflow-y-auto p-4">
    <button
      type="button"
      aria-label="Stäng modal"
      class="fixed inset-0 bg-navy/70"
      @click="emit('close')"
    />
    <div class="relative flex min-h-full items-start justify-center py-4">
      <div class="flex max-h-[calc(100vh-2rem)] w-full max-w-2xl flex-col border border-navy bg-white shadow-brutal">
        <div class="flex items-start justify-between gap-4 border-b border-navy/20 pb-4">
          <div class="min-w-0 space-y-1 px-6 pt-6 md:px-8 md:pt-8">
            <p class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              Klasslistor
            </p>
            <h2 class="font-serif text-2xl text-navy">
              {{ isEditing ? "Redigera klasslista" : "Ny klasslista" }}
            </h2>
          </div>
          <button
            type="button"
            class="mr-6 mt-6 btn-ghost h-[32px] w-[32px] px-0 py-0 shadow-none border-navy/30 bg-canvas md:mr-8 md:mt-8"
            @click="emit('close')"
          >
            ×
          </button>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto px-6 pb-6 pt-4 md:px-8 md:pb-8">
          <div
            v-if="error"
            class="system-message system-message-error"
          >
            <div class="system-message-content">
              {{ error }}
            </div>
          </div>

          <div class="mt-6 space-y-5">
            <div class="space-y-1">
              <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                Klassens namn
              </label>
              <input
                v-model="name"
                type="text"
                placeholder="Till exempel Klass 9A"
                class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
              >
            </div>

            <div class="space-y-2">
              <div class="flex items-end justify-between gap-3">
                <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                  Elever
                </label>
                <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                  {{ parsedStudents.length }} namn
                </span>
              </div>
              <textarea
                v-model="rawStudents"
                rows="12"
                placeholder="Anna Andersson&#10;Bilal Berg&#10;Cecilia Ceder"
                class="min-h-[280px] w-full resize-y border border-navy bg-white px-3 py-3 font-mono text-sm text-navy shadow-brutal-sm"
              />
              <p class="text-[11px] leading-relaxed text-navy/60">
                Skriv eller klistra in ett namn per rad.
              </p>
            </div>
          </div>
        </div>

        <div class="sticky bottom-0 flex flex-col gap-3 border-t border-navy/20 bg-white px-6 py-4 sm:flex-row sm:items-center sm:justify-between md:px-8">
          <div>
            <button
              v-if="isEditing"
              type="button"
              class="btn-ghost border-burgundy/40 bg-white text-burgundy"
              :disabled="isDeleting"
              @click="removeRoster"
            >
              {{ isDeleting ? "Raderar..." : "Radera klasslista" }}
            </button>
          </div>
          <div class="flex flex-wrap justify-end gap-3">
            <button
              type="button"
              class="btn-ghost border-navy/30 bg-canvas shadow-none"
              @click="emit('close')"
            >
              Avbryt
            </button>
            <button
              type="button"
              class="btn-primary"
              :disabled="!isValid || isSubmitting"
              @click="submit"
            >
              {{ isSubmitting ? "Sparar..." : isEditing ? "Spara ändringar" : "Skapa klasslista" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
