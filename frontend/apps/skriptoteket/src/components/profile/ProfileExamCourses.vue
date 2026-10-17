<script setup lang="ts">
/**
 * The teacher's own exam courses on the profile page.
 *
 * Records the school forms taught and an ordered list of committed catalog
 * keys. The catalog key is the only stored identity; each row resolves its
 * name, code and school form from the committed catalog. Spara replaces the
 * whole value and reports the update to the profile view.
 */
import { computed, ref, watch } from "vue";

import { isApiError } from "../../api/client";
import type { ExamCourse } from "../../api/examWorkspace";
import type { components } from "../../api/openapi";
import {
  EXAM_COURSE_SCHOOL_FORMS,
  type ExamCourseSchoolForm,
  useProfile,
} from "../../composables/useProfile";
import { useToast } from "../../composables/useToast";
import ExamCourseCombobox from "../../views/apps/exam-workspace/ExamCourseCombobox.vue";
import { useExamCourseCatalog } from "../../views/apps/exam-workspace/useExamCourseCatalog";
import { SystemMessage } from "../ui";
import { UiDenseIconButton, UiGlyph } from "../ui/shared";

const props = defineProps<{
  examCourses: components["schemas"]["ExamCourses"] | null;
}>();

const emit = defineEmits<{
  profileUpdated: [];
}>();

const { updateExamCourses } = useProfile();
const { courses, error: catalogError, courseByKey, setRegisteredCourseKeys } =
  useExamCourseCatalog();
const toast = useToast();

const schoolFormLabels: Record<ExamCourseSchoolForm, string> = {
  gymnasiet: "Gymnasiet",
  grundskolan: "Grundskolan",
};

const draftSchoolForms = ref<ExamCourseSchoolForm[]>([]);
const draftCourseKeys = ref<string[]>([]);
const selectedCourseKey = ref<string | null>(null);
const isSaving = ref(false);

const canAdd = computed(() => {
  const key = selectedCourseKey.value;
  return key !== null && !draftCourseKeys.value.includes(key);
});

const courseRows = computed(() =>
  draftCourseKeys.value.map((key) => {
    const course = courseByKey(key);
    return course === null
      ? { key, name: key, detail: "" }
      : { key, name: course.name, detail: `${course.code} · ${courseDetail(course)}` };
  }),
);

function courseDetail(course: ExamCourse): string {
  return course.school_form === "gymnasiet"
    ? `Gymnasiet ${course.reform ?? ""}`.trim()
    : schoolFormLabels.grundskolan;
}

function syncFromProfile(): void {
  draftSchoolForms.value = [...(props.examCourses?.school_forms ?? [])];
  draftCourseKeys.value = [...(props.examCourses?.course_keys ?? [])];
  selectedCourseKey.value = null;
}

watch(() => props.examCourses, syncFromProfile, { immediate: true });

function toggleSchoolForm(form: ExamCourseSchoolForm): void {
  draftSchoolForms.value = draftSchoolForms.value.includes(form)
    ? draftSchoolForms.value.filter((existing) => existing !== form)
    : [...draftSchoolForms.value, form];
}

function addCourse(): void {
  const key = selectedCourseKey.value;
  if (key === null || draftCourseKeys.value.includes(key)) return;
  draftCourseKeys.value = [...draftCourseKeys.value, key];
  selectedCourseKey.value = null;
}

function removeCourse(key: string): void {
  draftCourseKeys.value = draftCourseKeys.value.filter((existing) => existing !== key);
}

function saveFailureMessage(error: unknown): string {
  if (!isApiError(error)) return "Kunde inte spara.";
  const details = error.details as { field?: unknown } | null;
  if (details?.field === "course_keys") {
    return "En kurs i listan finns inte i kurskatalogen. Ta bort den och försök igen.";
  }
  return error.message;
}

async function save(): Promise<void> {
  if (isSaving.value) return;
  isSaving.value = true;
  try {
    await updateExamCourses({
      school_forms: EXAM_COURSE_SCHOOL_FORMS.filter((form) =>
        draftSchoolForms.value.includes(form),
      ),
      course_keys: draftCourseKeys.value,
    });
    setRegisteredCourseKeys(draftCourseKeys.value);
    toast.success("Kurserna uppdaterades.");
    emit("profileUpdated");
  } catch (error: unknown) {
    toast.failure(saveFailureMessage(error));
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <div
    class="space-y-4"
    data-test="profile-exam-courses"
  >
    <SystemMessage
      v-if="catalogError"
      :model-value="catalogError"
      tone="failure"
      :dismissible="false"
    />

    <fieldset class="courses-fieldset">
      <legend class="courses-legend">Skolformer</legend>
      <div class="flex flex-wrap gap-x-6 gap-y-2 pt-1">
        <label
          v-for="form in EXAM_COURSE_SCHOOL_FORMS"
          :key="form"
          class="flex cursor-pointer items-center gap-2 text-sm text-navy"
          :data-test="`profile-school-form-${form}`"
        >
          <input
            type="checkbox"
            class="h-4 w-4 accent-action"
            :checked="draftSchoolForms.includes(form)"
            :disabled="isSaving"
            @change="toggleSchoolForm(form)"
          >
          {{ schoolFormLabels[form] }}
        </label>
      </div>
    </fieldset>

    <div class="flex items-stretch gap-2">
      <div class="min-w-0 flex-1">
        <ExamCourseCombobox
          v-model="selectedCourseKey"
          :courses="courses"
          :disabled="isSaving"
          input-id="profile-exam-course"
        />
      </div>
      <UiDenseIconButton
        label="Lägg till kurs"
        size="touch"
        data-test="profile-course-add"
        aria-label="Lägg till kurs"
        title="Lägg till kurs"
        :disabled="isSaving || !canAdd"
        @click="addCourse"
      >
        <UiGlyph
          meaning="add"
          :size="16"
        />
      </UiDenseIconButton>
    </div>

    <ol
      v-if="courseRows.length"
      class="courses-list"
      data-test="profile-course-list"
    >
      <li
        v-for="row in courseRows"
        :key="row.key"
        class="courses-row"
        :data-test="`profile-course-${row.key}`"
      >
        <span
          class="min-w-0 truncate text-sm text-navy"
          :title="row.detail ? `${row.name} · ${row.detail}` : row.name"
        >
          {{ row.name }}<template v-if="row.detail"> · {{ row.detail }}</template>
        </span>
        <UiDenseIconButton
          :label="`Ta bort ${row.name}`"
          tone="danger"
          data-test="profile-course-remove"
          :aria-label="`Ta bort ${row.name}`"
          title="Ta bort"
          :disabled="isSaving"
          @click="removeCourse(row.key)"
        >
          <UiGlyph
            meaning="delete"
            :size="14"
          />
        </UiDenseIconButton>
      </li>
    </ol>
    <p
      v-else
      class="text-sm text-navy/60"
    >
      Inga kurser tillagda.
    </p>

    <div class="courses-actions">
      <button
        type="button"
        class="btn-inline-primary"
        data-test="profile-courses-save"
        :disabled="isSaving"
        :aria-busy="isSaving"
        title="Spara kurser"
        @click="save"
      >
        Spara
      </button>
    </div>
  </div>
</template>

<style scoped>
.courses-fieldset {
  border: none;
  margin: 0;
  padding: 0;
}

.courses-legend {
  font-size: var(--huleedu-text-xs);
  font-weight: var(--huleedu-font-semibold);
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
  color: var(--huleedu-navy-70);
}

.courses-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.courses-row {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  min-height: 2.25rem;
  border-bottom: 1px solid var(--huleedu-surface-divider);
}

.courses-row:last-child {
  border-bottom: none;
}

.courses-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--huleedu-surface-divider);
}
</style>
