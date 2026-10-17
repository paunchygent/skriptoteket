<script setup lang="ts">
/**
 * The teacher's own exam courses on the profile page.
 *
 * Records the school forms taught and an ordered list of committed catalog
 * keys. The catalog key is the only stored identity; each row resolves its
 * name, code and school form from the committed catalog. Choosing a course
 * adds it, and every change replaces the whole value at once. Saves run one
 * at a time; a failed save restores the last saved value.
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

type ExamCourses = { school_forms: ExamCourseSchoolForm[]; course_keys: string[] };

const props = defineProps<{
  examCourses: components["schemas"]["ExamCourses"] | null;
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
const saveState = ref<"idle" | "saving" | "saved">("idle");
let lastSaved: ExamCourses = { school_forms: [], course_keys: [] };
let isSaving = false;
let hasUnsavedChange = false;
let hasLocalChange = false;

const statusText = computed(() =>
  saveState.value === "saving" ? "Sparar…" : saveState.value === "saved" ? "Sparat" : "",
);

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

function applyValue(value: ExamCourses): void {
  draftSchoolForms.value = [...value.school_forms];
  draftCourseKeys.value = [...value.course_keys];
}

function syncFromProfile(): void {
  // This section is the only writer of the value on the page. After its first
  // change it holds the acknowledged value, and a profile reload that started
  // before a save could carry an older one.
  if (hasLocalChange) return;
  lastSaved = {
    school_forms: [...(props.examCourses?.school_forms ?? [])],
    course_keys: [...(props.examCourses?.course_keys ?? [])],
  };
  applyValue(lastSaved);
}

watch(() => props.examCourses, syncFromProfile, { immediate: true });

function toggleSchoolForm(form: ExamCourseSchoolForm): void {
  draftSchoolForms.value = draftSchoolForms.value.includes(form)
    ? draftSchoolForms.value.filter((existing) => existing !== form)
    : [...draftSchoolForms.value, form];
  void save();
}

function chooseCourse(key: string | null): void {
  if (key === null || draftCourseKeys.value.includes(key)) return;
  draftCourseKeys.value = [...draftCourseKeys.value, key];
  void save();
}

function removeCourse(key: string): void {
  draftCourseKeys.value = draftCourseKeys.value.filter((existing) => existing !== key);
  void save();
}

function saveFailureMessage(error: unknown): string {
  if (!isApiError(error)) return "Kunde inte spara.";
  const details = error.details as { field?: unknown } | null;
  if (details?.field === "course_keys") {
    return "En kurs i listan finns inte i kurskatalogen. Ta bort den och försök igen.";
  }
  return error.message;
}

/** Saves the current draft; a change made during a save is saved after it. */
async function save(): Promise<void> {
  hasLocalChange = true;
  hasUnsavedChange = true;
  if (isSaving) return;
  isSaving = true;
  saveState.value = "saving";
  try {
    while (hasUnsavedChange) {
      hasUnsavedChange = false;
      const value: ExamCourses = {
        school_forms: EXAM_COURSE_SCHOOL_FORMS.filter((form) =>
          draftSchoolForms.value.includes(form),
        ),
        course_keys: [...draftCourseKeys.value],
      };
      await updateExamCourses(value);
      lastSaved = value;
      setRegisteredCourseKeys(value.course_keys);
    }
    saveState.value = "saved";
  } catch (error: unknown) {
    hasUnsavedChange = false;
    applyValue(lastSaved);
    saveState.value = "idle";
    toast.failure(saveFailureMessage(error));
  } finally {
    isSaving = false;
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
      <div class="flex flex-wrap gap-x-6 gap-y-2 pt-2">
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
            @change="toggleSchoolForm(form)"
          >
          {{ schoolFormLabels[form] }}
        </label>
      </div>
    </fieldset>

    <div class="flex items-center gap-3">
      <div class="min-w-0 flex-1">
        <ExamCourseCombobox
          :model-value="null"
          :courses="courses"
          input-id="profile-exam-course"
          @update:model-value="chooseCourse"
        />
      </div>
      <span
        class="courses-status"
        data-test="profile-courses-status"
        role="status"
        aria-live="polite"
      >{{ statusText }}</span>
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
          class="shrink-0"
          tone="danger"
          data-test="profile-course-remove"
          :aria-label="`Ta bort ${row.name}`"
          title="Ta bort"
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
  </div>
</template>

<style scoped>
.courses-fieldset {
  border: none;
  /* Inline only: the block margin is the section's space-y gap to the search box. */
  margin-inline: 0;
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

.courses-status {
  flex-shrink: 0;
  width: 4rem;
  font-size: var(--huleedu-text-xs);
  color: var(--huleedu-navy-70);
}
</style>
