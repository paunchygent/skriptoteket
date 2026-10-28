<script setup lang="ts">
/** Shared optional course picker for import and document metadata. */
import { computed, nextTick, ref, watch } from "vue";

import type { ExamCourse } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import { searchCourses } from "./useExamCourseCatalog";

const props = defineProps<{
  modelValue: string | null;
  courses: ExamCourse[];
  disabled?: boolean;
  inputId: string;
  /** Raw course hint shown beside an empty field when nothing is preselected (D6). */
  hint?: string | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [key: string | null];
}>();

const input = ref<HTMLInputElement | null>(null);
const listbox = ref<HTMLElement | null>(null);
const isOpen = ref(false);
const query = ref("");
const activeIndex = ref(0);
const selected = computed(() => props.courses.find((course) => course.key === props.modelValue));
const inputText = computed(() => isOpen.value ? query.value : (selected.value?.name ?? ""));
const listboxId = computed(() => `${props.inputId}-courses`);
const hintId = computed(() => `${props.inputId}-hint`);
// One extra result tells the teacher when the rendered limit hides more matches.
const matches = computed(() => searchCourses(props.courses, query.value, 51));
const options = computed(() => matches.value.slice(0, 50));
const activeId = computed(() => isOpen.value && options.value[activeIndex.value]
  ? `${listboxId.value}-${activeIndex.value}` : undefined);

function close(): void {
  isOpen.value = false;
  query.value = "";
}

function open(): void {
  if (props.disabled || isOpen.value) return;
  query.value = "";
  activeIndex.value = 0;
  isOpen.value = true;
}

function handleInput(event: Event): void {
  if (props.disabled) return;
  query.value = (event.target as HTMLInputElement).value;
  isOpen.value = true;
  activeIndex.value = 0;
}

function choose(course: ExamCourse): void {
  if (props.disabled) return;
  emit("update:modelValue", course.key);
  close();
}

function clear(): void {
  if (props.disabled) return;
  emit("update:modelValue", null);
  close();
  input.value?.focus();
}

function handleKeydown(event: KeyboardEvent): void {
  if (props.disabled) return;
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    if (!isOpen.value) {
      open();
      activeIndex.value = event.key === "ArrowUp" ? options.value.length - 1 : 0;
    } else if (options.value.length) {
      const direction = event.key === "ArrowDown" ? 1 : -1;
      activeIndex.value = (activeIndex.value + direction + options.value.length) % options.value.length;
    }
  } else if (event.key === "Enter" && isOpen.value) {
    event.preventDefault();
    const course = options.value[activeIndex.value];
    if (course) choose(course);
  } else if (event.key === "Escape" && isOpen.value) {
    event.preventDefault();
    event.stopPropagation();
    close();
  } else if (event.key === "Tab") {
    close();
  }
}

watch(() => props.disabled, (disabled) => { if (disabled) close(); });
watch(options, () => { activeIndex.value = 0; });
watch(activeId, () => {
  void nextTick(() => {
    listbox.value?.querySelector<HTMLElement>("[data-active='true']")?.scrollIntoView?.({ block: "nearest" });
  });
});
</script>

<template>
  <div
    class="grid min-w-0 gap-1"
    data-test="exam-course-combobox"
  >
    <div class="relative">
      <div class="flex items-center border border-navy/35 bg-canvas focus-within:border-action">
        <input
          :id="inputId"
          ref="input"
          type="text"
          role="combobox"
          aria-autocomplete="list"
          aria-haspopup="listbox"
          aria-label="Kurs"
          :aria-expanded="isOpen"
          :aria-controls="listboxId"
          :aria-activedescendant="activeId"
          :aria-describedby="hint && modelValue === null ? hintId : undefined"
          :value="inputText"
          :disabled="disabled"
          autocomplete="off"
          placeholder="Sök kurs eller kurskod"
          class="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm text-navy outline-none disabled:opacity-60"
          @focus="open"
          @click="open"
          @input="handleInput"
          @keydown="handleKeydown"
          @blur="close"
        >
        <button
          type="button"
          aria-label="Rensa kurs"
          title="Rensa kurs"
          class="shrink-0 p-2 text-navy/65 hover:text-navy focus-visible:outline focus-visible:outline-action disabled:opacity-60"
          :class="modelValue === null ? 'invisible' : undefined"
          :disabled="disabled || modelValue === null"
          @mousedown.prevent
          @click="clear"
        >
          <UiGlyph
            meaning="close"
            :size="16"
          />
        </button>
      </div>
      <ul
        v-if="isOpen"
        :id="listboxId"
        ref="listbox"
        role="listbox"
        aria-label="Kurser"
        class="absolute inset-x-0 top-full z-50 mt-1 max-h-56 overflow-y-auto border border-navy/35 bg-modal shadow-md"
      >
        <li
          v-for="(course, index) in options"
          :id="`${listboxId}-${index}`"
          :key="course.key"
          role="option"
          :aria-selected="course.key === modelValue"
          :data-active="index === activeIndex"
          class="cursor-pointer px-3 py-2 text-sm text-navy hover:bg-canvas"
          :class="index === activeIndex ? 'bg-canvas outline outline-1 -outline-offset-1 outline-action' : undefined"
          @pointerdown.prevent
          @click="choose(course)"
        >
          {{ course.name }} · {{ course.code }} · {{ course.school_form === 'gymnasiet' ? `Gymnasiet ${course.reform}` : 'Grundskolan' }}
        </li>
        <li
          v-if="options.length === 0"
          class="px-3 py-2 text-xs text-navy/65"
          role="status"
        >
          Inga kurser hittades.
        </li>
        <li
          v-if="matches.length > 50"
          class="px-3 py-2 text-xs text-navy/65"
          role="status"
        >
          Skriv mer för att begränsa.
        </li>
      </ul>
    </div>
    <p
      v-if="hint && modelValue === null"
      :id="hintId"
      class="text-xs text-navy/65"
    >
      Kursrad i dokumentet: {{ hint }}
    </p>
  </div>
</template>
