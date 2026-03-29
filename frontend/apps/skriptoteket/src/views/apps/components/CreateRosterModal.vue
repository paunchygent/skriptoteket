<script setup lang="ts">
/**
 * Roster create/edit modal.
 *
 * This modal owns the CRUD surface for reusable class lists used by the
 * classroom planner. Import-from-file now lives inside the same workflow so
 * teachers can start from a Skola24 export, review the parsed result, and only
 * fall back to manual edits when the parser needs help.
 */

import { computed, ref, watch } from "vue";

import { apiDelete, apiPost, apiPut } from "../../../api/client";
import type { AmbiguousRow } from "../useClassListImportFlow";
import { useClassListImportFlow } from "../useClassListImportFlow";
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
const formError = ref<string | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const ambiguousRows = ref<AmbiguousRow[]>([]);

const { isUploading, preview, error: importError, uploadFile, cancel: resetImportState } =
  useClassListImportFlow();

const isEditing = computed(() => Boolean(props.roster));

function buildStudentsForSubmit(lines: string[], existingStudents: Student[]): Student[] {
  const availableIdsByName = new Map<string, string[]>();

  for (const student of existingStudents) {
    const trimmedName = student.display_name.trim();
    const idsForName = availableIdsByName.get(trimmedName) ?? [];
    idsForName.push(student.id);
    availableIdsByName.set(trimmedName, idsForName);
  }

  return lines.map((displayName) => {
    const existingId = availableIdsByName.get(displayName)?.shift();
    return {
      id: existingId ?? crypto.randomUUID(),
      display_name: displayName,
    };
  });
}

watch(
  () => props.roster,
  (roster) => {
    name.value = roster?.name ?? "";
    rawStudents.value = roster?.students.map((student) => student.display_name).join("\n") ?? "";
    formError.value = null;
    ambiguousRows.value = [];
    resetImportState();
  },
  { immediate: true },
);

watch(
  () => preview.value,
  (nextPreview) => {
    if (!nextPreview) {
      ambiguousRows.value = [];
      return;
    }

    name.value = nextPreview.suggested_class_name?.trim() || name.value;
    rawStudents.value = nextPreview.parsed_students.map((student) => student.full_name).join("\n");
    ambiguousRows.value = [...nextPreview.ambiguous_rows];
    formError.value = null;
  },
);

const parsedStudents = computed<Student[]>(() => {
  const lines = rawStudents.value
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  return buildStudentsForSubmit(lines, props.roster?.students ?? []);
});

const isValid = computed(() => {
  return name.value.trim().length > 0 && parsedStudents.value.length > 0;
});

async function submit(): Promise<void> {
  if (!isValid.value) {
    return;
  }

  isSubmitting.value = true;
  formError.value = null;

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
    formError.value =
      submitError instanceof Error ? submitError.message : "Kunde inte spara klasslistan.";
  } finally {
    isSubmitting.value = false;
  }
}

async function removeRoster(): Promise<void> {
  if (!props.roster) {
    return;
  }

  isDeleting.value = true;
  formError.value = null;

  try {
    await apiDelete<void>(`/api/v1/apps/classroom.group-seating-studio/rosters/${props.roster.id}`);
    emit("deleted", props.roster.id);
  } catch (deleteError: unknown) {
    formError.value =
      deleteError instanceof Error ? deleteError.message : "Kunde inte radera klasslistan.";
  } finally {
    isDeleting.value = false;
  }
}

function triggerFileInput(): void {
  fileInput.value?.click();
}

async function onFileSelected(event: Event): Promise<void> {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) {
    return;
  }

  const file = target.files?.[0];
  if (!file) {
    return;
  }

  await uploadFile(file);
  target.value = "";
}

function appendAmbiguousRow(index: number): void {
  const row = ambiguousRows.value[index];
  if (!row) {
    return;
  }

  const nextValue = rawStudents.value.trim();
  rawStudents.value = nextValue.length > 0 ? `${nextValue}\n${row.raw_text}` : row.raw_text;
  ambiguousRows.value.splice(index, 1);
}

function dismissAmbiguousRow(index: number): void {
  ambiguousRows.value.splice(index, 1);
}

function closeModal(): void {
  resetImportState();
  emit("close");
}
</script>

<template>
  <div class="fixed inset-0 z-50 overflow-y-auto p-4">
    <button
      type="button"
      aria-label="Stäng modal"
      class="planner-overlay-backdrop"
      @click="closeModal"
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
            class="mr-6 mt-6 btn-ghost planner-btn-ghost-canvas planner-btn-icon-md md:mr-8 md:mt-8"
            @click="closeModal"
          >
            ×
          </button>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto px-6 pb-6 pt-4 md:px-8 md:pb-8">
          <div
            v-if="formError"
            class="system-message system-message-error"
          >
            <div class="system-message-content">
              {{ formError }}
            </div>
          </div>

          <div class="mt-6 space-y-5">
            <section class="space-y-3 border border-navy/20 bg-canvas p-4 shadow-brutal-sm">
              <input
                ref="fileInput"
                type="file"
                class="hidden"
                accept=".xlsx,.xls,.csv,.tsv,.txt,.pdf"
                @change="onFileSelected"
              >

              <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div class="space-y-1">
                  <p class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                    Importera från fil
                  </p>
                  <p class="text-sm leading-relaxed text-navy/75">
                    Börja gärna med en Skola24-klasslista eller grupplista i Excel
                    (`.xls`), PDF eller text (`.txt`). Även `.csv` och `.tsv` stöds.
                  </p>
                </div>
                <button
                  type="button"
                  class="btn-primary shrink-0"
                  data-test="roster-modal-import-trigger"
                  :disabled="isUploading"
                  @click="triggerFileInput"
                >
                  {{ isUploading ? "Läser in fil..." : "Importera från fil" }}
                </button>
              </div>

              <div
                v-if="importError"
                class="system-message system-message-error"
              >
                <div class="system-message-content">
                  {{ importError }}
                </div>
              </div>

              <div
                v-if="preview"
                class="space-y-2 border border-navy/20 bg-white p-3"
                data-test="roster-import-summary"
              >
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <div class="space-y-1">
                    <p class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                      Importförslag
                    </p>
                    <p class="text-sm text-navy">
                      {{ preview.file_name }}
                    </p>
                  </div>
                  <div class="text-right text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                    {{ preview.parsed_students.length }} elever
                  </div>
                </div>
                <p class="text-sm text-navy/70">
                  Klassnamn och elevlista har fyllts i automatiskt nedan. Justera bara om parsern
                  har missat något.
                </p>
              </div>
            </section>

            <div class="space-y-1">
              <label
                for="roster-name"
                class="text-xs font-semibold uppercase tracking-wide text-navy/70"
              >
                Klassens namn
              </label>
              <input
                id="roster-name"
                v-model="name"
                type="text"
                placeholder="Till exempel Klass 9A"
                class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
              >
            </div>

            <div class="space-y-2">
              <div class="flex items-end justify-between gap-3">
                <label
                  for="roster-students"
                  class="text-xs font-semibold uppercase tracking-wide text-navy/70"
                >
                  Elever
                </label>
                <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                  {{ parsedStudents.length }} namn
                </span>
              </div>
              <textarea
                id="roster-students"
                v-model="rawStudents"
                rows="12"
                placeholder="Anna Andersson&#10;Bilal Berg&#10;Cecilia Ceder"
                class="min-h-[280px] w-full resize-y border border-navy bg-white px-3 py-3 font-mono text-sm text-navy shadow-brutal-sm"
              />
              <p class="text-[11px] leading-relaxed text-navy/60">
                Skriv eller klistra in ett namn per rad.
              </p>
            </div>

            <div
              v-if="ambiguousRows.length > 0"
              class="space-y-3 border border-burgundy/20 bg-burgundy/5 p-4"
              data-test="roster-import-ambiguous"
            >
              <div class="space-y-1">
                <p class="text-xs font-semibold uppercase tracking-wide text-burgundy">
                  Otydliga rader från importen
                </p>
                <p class="text-sm text-burgundy/80">
                  Lägg till sådant som faktiskt är elevnamn, eller ignorera rader som inte hör till
                  klasslistan.
                </p>
              </div>

              <div class="space-y-2">
                <div
                  v-for="(row, index) in ambiguousRows"
                  :key="`${row.raw_text}-${index}`"
                  class="space-y-2 border border-burgundy/20 bg-white p-3"
                >
                  <div class="break-all font-mono text-sm text-burgundy">
                    {{ row.raw_text }}
                  </div>
                  <div class="flex flex-wrap gap-3">
                    <button
                      type="button"
                      class="planner-text-link-danger"
                      @click="appendAmbiguousRow(index)"
                    >
                      Lägg till i elevlistan
                    </button>
                    <button
                      type="button"
                      class="planner-text-link-muted"
                      @click="dismissAmbiguousRow(index)"
                    >
                      Ignorera
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="sticky bottom-0 flex flex-col gap-3 border-t border-navy/20 bg-white px-6 py-4 sm:flex-row sm:items-center sm:justify-between md:px-8">
          <div>
            <button
              v-if="isEditing"
              type="button"
              class="btn-ghost planner-btn-danger"
              :disabled="isDeleting"
              @click="removeRoster"
            >
              {{ isDeleting ? "Raderar..." : "Radera klasslista" }}
            </button>
          </div>
          <div class="flex flex-wrap justify-end gap-3">
            <button
              type="button"
              class="btn-ghost planner-btn-ghost-canvas"
              @click="closeModal"
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
