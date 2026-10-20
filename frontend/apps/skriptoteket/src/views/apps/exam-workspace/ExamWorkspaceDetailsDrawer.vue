<script setup lang="ts">
/**
 * Exam workspace Provets uppgifter drawer.
 *
 * Domain purpose:
 *   The exam's own facts. The title is part of the exam and saves with
 *   Spara. The file name in Mina filer changes at once with "Byt namn",
 *   without touching the title. The course is chosen from the catalog; it
 *   can be added to the teacher's own courses, a gymnasiet course names its
 *   subject, and without a course the course line the file printed shows.
 *   Centralt innehåll lists the course's central content to tick, with the
 *   questions each part covers; "Föreslå innehåll" lets AI tick it from the
 *   saved exam.
 *
 * Relationships:
 *   - Rendered inside `ExamWorkspaceDrawer` by `ExamWorkspaceView`.
 *   - Course data from `useExamCourseCatalog`; own courses through
 *     `useExamWorkspaceMyCourses`; content through `getExamCourseContent`.
 */

import { computed, nextTick, ref, useId, watch } from "vue";

import type {
  ExamCourseChoice,
  ExamCourseContent,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
  NativeExamHeader,
} from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import { AI_ADMIN_ONLY_NOTE } from "../../../composables/useAiAccess";
import ExamCourseCombobox from "./ExamCourseCombobox.vue";
import { GUEST_AI_SIGN_IN } from "./examWorkspaceGuestCopy";
import { useExamWorkspaceSignIn } from "./examWorkspaceSignIn";
import { useExamCourseCatalog } from "./useExamCourseCatalog";
import { useInjectedExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceMyCourses } from "./useExamWorkspaceMyCourses";
import { PENDING_SAVE_COPY } from "./useExamWorkspaceSaveStatus";
import type { ExamWorkspaceRenameFailure } from "./useExamWorkspaceRename";
import { useExamWorkspaceAiMode } from "./useExamWorkspaceAiMode";

const EXTENSION = ".provdokument.zip";

const props = defineProps<{
  document: NativeExamDocument;
  summary: ExamWorkspaceDocumentSummary;
  renameFile: (fileId: string, stem: string) => Promise<string | null>;
  renameFailure: ExamWorkspaceRenameFailure | null;
  disabled: boolean;
  dirty: boolean;
  contentBusy: boolean;
  /** Said when "Föreslå innehåll" ticked nothing. */
  contentMessage: string | null;
  /** "3" or "4b" for a question id, for the questions a content part covers. */
  questionLabel: (itemId: string) => string | null;
}>();

const emit = defineEmits<{
  "update:title": [title: string];
  "update:course": [course: ExamCourseChoice | null];
  setTags: [tags: NativeExamHeader["tags"]];
  suggestContent: [];
}>();

const id = useId();
const contentAiNoteId = `${id}-ai-note`;
const store = useInjectedExamWorkspaceStore();
const requestSignIn = useExamWorkspaceSignIn();
/** Guest controls stay enabled and ask for sign-in; signed-in controls follow the admin gate. */
const aiMode = useExamWorkspaceAiMode();
const isGuest = computed(() => aiMode.value === "guest");
const adminOnly = computed(() => aiMode.value === "admin_only");
const { courses, courseByKey, error: catalogError } = useExamCourseCatalog(store.shared);
const myCourses = useExamWorkspaceMyCourses(store.shared);

const courseKey = computed(() => props.document.header.course?.key ?? null);
const selectedCourse = computed(() => courseByKey(courseKey.value));

function chooseCourse(key: string | null): void {
  const course = courseByKey(key);
  emit("update:course", course ? { key: course.key, name: course.name } : null);
}

// File name: a separate, immediate rename of the exam's file in Mina filer.
const currentStem = computed(() =>
  props.summary.name.endsWith(EXTENSION) ? props.summary.name.slice(0, -EXTENSION.length) : props.summary.name,
);
const stem = ref(props.renameFailure?.stem ?? currentStem.value);
const renaming = ref(false);
const renameError = computed(() =>
  props.renameFailure?.stem === stem.value ? props.renameFailure.message : null,
);
const canRename = computed(
  () => !props.disabled && !renaming.value && stem.value.trim().length > 0 && stem.value !== currentStem.value,
);
watch(
  () => [props.summary.vault_file_id, props.summary.name],
  () => {
    stem.value = props.renameFailure?.stem ?? currentStem.value;
  },
);
watch(
  () => props.renameFailure,
  (failure) => {
    if (failure) stem.value = failure.stem;
  },
);

async function rename(): Promise<void> {
  if (!canRename.value) return;
  const fileId = props.summary.vault_file_id;
  renaming.value = true;
  try {
    const name = await props.renameFile(fileId, stem.value);
    if (name !== null) {
      stem.value = name.endsWith(EXTENSION) ? name.slice(0, -EXTENSION.length) : name;
    }
  } finally {
    renaming.value = false;
  }
}

// Centralt innehåll for the chosen course.
const content = ref<ExamCourseContent | null>(null);
const contentError = ref(false);
watch(
  courseKey,
  async (key) => {
    content.value = null;
    contentError.value = false;
    const teacher = store.teacher;
    if (!key || !teacher) return;
    try {
      const response = await teacher.getExamCourseContent(key);
      if (courseKey.value === key) content.value = response;
    } catch {
      if (courseKey.value === key) contentError.value = true;
    }
  },
  { immediate: true },
);

const tagsById = computed(() => new Map(props.document.header.tags.map((tag) => [tag.id, tag])));
const suggestBlocked = computed(() =>
  !courseKey.value ? "Välj en kurs först." : props.dirty ? PENDING_SAVE_COPY : null,
);

function toggleTag(entryId: string, text: string): void {
  const tags = props.document.header.tags;
  emit(
    "setTags",
    tagsById.value.has(entryId)
      ? tags.filter((tag) => tag.id !== entryId)
      : [...tags, { id: entryId, origin: "teacher", question_ids: [], text }],
  );
}

/**
 * A refused edit leaves the native checkbox flipped while the bound document
 * state is unchanged, so Vue never patches it back. Reset the input to the
 * document state once the parent has had its turn; an accepted edit re-renders
 * from the updated document and this is a no-op.
 */
async function handleToggleTag(event: Event, entryId: string, text: string): Promise<void> {
  toggleTag(entryId, text);
  await nextTick();
  const target = event.target;
  if (target instanceof HTMLInputElement) {
    target.checked = tagsById.value.has(entryId);
  }
}

function handleSuggestContent(): void {
  if (isGuest.value) {
    requestSignIn(GUEST_AI_SIGN_IN);
    return;
  }
  emit("suggestContent");
}

function cites(entryId: string): string | null {
  const tag = tagsById.value.get(entryId);
  if (!tag || tag.question_ids.length === 0) return null;
  const labels = tag.question_ids.map((itemId) => props.questionLabel(itemId)).filter(Boolean);
  return labels.length > 0 ? `Fråga ${labels.join(", ")}` : null;
}
</script>

<template>
  <section class="sect">
    <h3>
      <label :for="`${id}-title`">Titel</label>
    </h3>
    <input
      :id="`${id}-title`"
      class="xw-input"
      :value="document.title"
      :disabled="disabled"
      :aria-invalid="!document.title.trim() || undefined"
      :aria-describedby="!document.title.trim() ? `${id}-title-guidance` : undefined"
      data-test="exam-workspace-metadata-title"
      @input="emit('update:title', ($event.target as HTMLInputElement).value)"
    >
    <p
      v-if="!document.title.trim()"
      :id="`${id}-title-guidance`"
      class="xw-errline"
    >
      <UiGlyph
        meaning="blocker"
        :size="16"
      />Skriv en titel innan du exporterar provet.
    </p>
  </section>

  <form
    v-if="!isGuest"
    class="sect"
    @submit.prevent="rename"
  >
    <h3>
      <label :for="`${id}-name`">Filnamn i Mina filer</label>
    </h3>
    <div class="sect__row">
      <input
        :id="`${id}-name`"
        v-model="stem"
        class="xw-input"
        :disabled="disabled || renaming"
        :aria-invalid="!!renameError || undefined"
        :aria-describedby="renameError ? `${id}-name-error` : undefined"
        data-test="exam-workspace-metadata-name"
      >
      <button
        type="submit"
        class="xw-btn"
        :disabled="!canRename"
        data-test="exam-workspace-metadata-rename"
      >
        Byt namn
      </button>
    </div>
    <p
      v-if="renameError"
      :id="`${id}-name-error`"
      role="alert"
      class="xw-errline"
      data-test="exam-workspace-metadata-name-error"
    >
      <UiGlyph
        meaning="blocker"
        :size="16"
      />{{ renameError }}
    </p>
  </form>

  <section class="sect">
    <h3>
      <label :for="`${id}-course`">Kurs</label>
    </h3>
    <ExamCourseCombobox
      :model-value="courseKey"
      :courses="courses"
      :disabled="disabled"
      :input-id="`${id}-course`"
      :hint="document.header.course_hint"
      @update:model-value="chooseCourse"
    />
    <p
      v-if="catalogError"
      role="alert"
      class="xw-errline"
    >
      {{ catalogError }}
    </p>
    <div
      v-if="selectedCourse"
      class="coursefoot"
    >
      <span
        v-if="myCourses.isMine(selectedCourse.key)"
        class="xw-okline"
        data-test="exam-workspace-course-mine"
      ><UiGlyph
        meaning="completed"
        :size="16"
      />I mina kurser</span>
      <button
        v-else
        type="button"
        class="xw-linkbtn"
        :disabled="myCourses.adding.value"
        data-test="exam-workspace-course-add-mine"
        @click="myCourses.addCourse(selectedCourse)"
      >
        <UiGlyph
          meaning="add"
          :size="16"
        />Lägg till i mina kurser
      </button>
      <span
        v-if="selectedCourse.school_form === 'gymnasiet'"
        class="xw-okline"
        data-test="exam-workspace-metadata-subject"
      >Ämne: {{ selectedCourse.subject_name }}</span>
    </div>
    <p
      v-else-if="document.header.course_hint"
      class="xw-hint"
      data-test="exam-workspace-course-hint"
    >
      <UiGlyph
        meaning="document"
        :size="16"
      />Kursrad i dokumentet: {{ document.header.course_hint }}
    </p>
  </section>

  <section
    class="sect"
    data-test="exam-workspace-content"
  >
    <h3>
      <span class="xw-grow">Centralt innehåll</span>
      <button
        type="button"
        class="xw-btn xw-btn--compact"
        :disabled="isGuest ? disabled : (!content || contentBusy || suggestBlocked !== null || disabled || adminOnly)"
        :title="adminOnly ? AI_ADMIN_ONLY_NOTE : suggestBlocked ?? undefined"
        :aria-describedby="adminOnly ? contentAiNoteId : undefined"
        data-test="exam-workspace-content-suggest"
        @click="handleSuggestContent"
      >
        <UiGlyph
          :meaning="contentBusy ? 'busy' : 'ai-assist'"
          :size="16"
          :class="{ 'xw-spin': contentBusy }"
        />Föreslå innehåll
      </button>
    </h3>
    <p
      v-if="adminOnly"
      :id="contentAiNoteId"
      class="xw-hint"
    >
      {{ AI_ADMIN_ONLY_NOTE }}
    </p>
    <p
      v-if="!courseKey"
      class="xw-hint"
    >
      <UiGlyph
        meaning="info"
        :size="16"
      />Välj en kurs för att se kursens centrala innehåll.
    </p>
    <p
      v-else-if="contentError"
      class="xw-errline"
    >
      Kursens centrala innehåll kunde inte hämtas.
    </p>
    <template v-else-if="content">
      <p
        v-if="suggestBlocked && courseKey"
        class="xw-hint"
      >
        <UiGlyph
          meaning="info"
          :size="16"
        />{{ suggestBlocked }}
      </p>
      <p
        v-if="contentMessage"
        class="xw-hint"
        role="status"
        data-test="exam-workspace-content-message"
      >
        <UiGlyph
          meaning="info"
          :size="16"
        />{{ contentMessage }}
      </p>
      <div
        class="checklist"
        :class="{ 'checklist--busy': contentBusy }"
        role="group"
        aria-label="Centralt innehåll"
      >
        <label
          v-for="entry in content.items"
          :key="entry.id"
          class="cl"
        >
          <input
            type="checkbox"
            class="cl__box"
            :checked="tagsById.has(entry.id)"
            :disabled="disabled || contentBusy"
            :data-test="`exam-workspace-content-${entry.id}`"
            @change="handleToggleTag($event, entry.id, entry.text)"
          >
          <span>
            {{ entry.text }}
            <span
              v-if="cites(entry.id)"
              class="cl__cites"
            ><UiGlyph
              v-if="tagsById.get(entry.id)?.origin === 'suggested'"
              meaning="ai-assist"
              :size="14"
              class="xw-ai"
            />{{ cites(entry.id) }}</span>
          </span>
        </label>
      </div>
    </template>
  </section>
</template>

<style scoped>
.sect h3 {
  display: flex; align-items: center; gap: var(--huleedu-space-2); min-height: 28px; margin: 0 0 var(--huleedu-space-2-5);
  font-size: var(--huleedu-text-sm); font-weight: var(--huleedu-font-semibold);
}
.sect__row { display: flex; gap: var(--huleedu-space-2); }
.sect__row .xw-input { flex: 1; min-width: 0; }
.coursefoot { display: flex; flex-wrap: wrap; align-items: center; gap: var(--huleedu-space-3); margin-top: var(--huleedu-space-1-5); }
.checklist { border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-radius-lg); background: var(--huleedu-surface-content); }
.checklist--busy { opacity: 0.5; }
.cl {
  display: grid; grid-template-columns: 18px minmax(0, 1fr); gap: var(--huleedu-space-3); cursor: pointer;
  padding: var(--huleedu-space-2-5) var(--huleedu-space-3); border-top: 1px solid var(--huleedu-surface-divider); font-size: var(--huleedu-text-sm);
}
.cl:first-child { border-top: 0; }
.cl__box { width: 18px; height: 18px; margin: 2px 0 0; accent-color: var(--huleedu-action); }
.cl__cites { display: flex; align-items: center; gap: var(--huleedu-space-1-5); margin-top: 2px; font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-60); }
</style>
