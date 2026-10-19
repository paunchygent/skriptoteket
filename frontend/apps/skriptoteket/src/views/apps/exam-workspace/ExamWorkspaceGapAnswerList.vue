<script setup lang="ts">
/**
 * Exam workspace gap answer list.
 *
 * Domain purpose:
 *   Edit one list of accepted answers as one row per answer: a text input
 *   and a remove glyph per row, with a glyph-only add button ("Lägg till
 *   svar" accessible name and tooltip) under the rows. Typing commits while
 *   it happens (each input emits the normalized list, so the owner stores it
 *   after its typing pause), and an input's `change`, removing
 *   a row and the exposed `commit()` emit the normalized list (trimmed,
 *   empty rows dropped, exact duplicates after trim collapsed, commas kept
 *   as ordinary characters) exactly once per change. Typing that normalizes
 *   to an empty list commits nothing: an empty accepted value is refused by
 *   the save rules, so only `change`, remove and `commit()` can emit it.
 *   Every row input, add, Enter-add and remove also emits the normalized
 *   list as `draft`, so the owner can follow unsaved typing without a commit. Enter in a row inserts
 *   an empty row directly below it and focuses it; the new row stays in
 *   local state until a commit normalizes, and a commit never removes the
 *   focused empty row from local state. Removing a row moves focus first,
 *   synchronously before the splice, to the previous row's input, else the
 *   next row's input, else the add button, so the focused remove button is
 *   never detached while focused and the owning popover stays open. At least
 *   one row is always shown;
 *   the list caps at 100 rows with the add button kept rendered and
 *   disabled. Enter during an IME composition is ignored. An external
 *   `values` change replaces the rows only while nothing is pending (the
 *   local normalized list still equals the last committed list), keeping a
 *   focused empty row the teacher added. An owner echo of the last commit
 *   changes no row and no key; a real external change reuses the keys of
 *   rows whose text is unchanged at the same position, keeping a focused
 *   empty row at its insertion position.
 *
 * Relationships:
 *   - Rendered later by `ExamWorkspaceGapPopover` for the text-gap section
 *     (which calls `commit()` on close) and as the Kort svar "Svar" field.
 *   - Row layout, `xw-rm` glyph buttons, nextTick focus handling and the
 *     IME guard mirror the dropdown option rows in
 *     `ExamWorkspaceGapPopover`.
 */

import { nextTick, ref, watch } from "vue";

import { UiGlyph } from "../../../components/ui";

const MAX_ROWS = 100;
const ADD_LABEL = "Lägg till svar";
const REMOVE_LABEL = "Ta bort svaret";
const ADD_CAP_TITLE = "Högst 100 svar";

const props = defineProps<{
  values: string[];
  label: string;
  disabled?: boolean;
  testId: string;
}>();

const emit = defineEmits<{
  commit: [values: string[]];
  draft: [values: string[]];
}>();

interface AnswerRow {
  key: number;
  text: string;
}

let nextKey = 0;
let lastCommitted: string[] = [...props.values];

function makeRow(text: string): AnswerRow {
  nextKey += 1;
  return { key: nextKey, text };
}

function rowsFromValues(values: string[]): AnswerRow[] {
  const rows = values.map((value) => makeRow(value));
  return rows.length > 0 ? rows : [makeRow("")];
}

const rows = ref<AnswerRow[]>(rowsFromValues(props.values));
const root = ref<HTMLElement | null>(null);

function sameValues(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

/** Trimmed, empties dropped, exact duplicates collapsed, first order kept. */
function normalizedRows(): string[] {
  const seen = new Set<string>();
  const normalized: string[] = [];
  for (const row of rows.value) {
    const text = row.text.trim();
    if (text === "" || seen.has(text)) {
      continue;
    }
    seen.add(text);
    normalized.push(text);
  }
  return normalized;
}

function commit(): void {
  if (props.disabled) {
    return;
  }
  const values = normalizedRows();
  if (sameValues(values, lastCommitted)) {
    return;
  }
  lastCommitted = values;
  emit("commit", values);
}

/** The current normalized list, so the owner can follow unsaved typing. */
function emitDraft(): void {
  if (props.disabled) {
    return;
  }
  emit("draft", normalizedRows());
}

function rowInputs(): HTMLInputElement[] {
  return [...(root.value?.querySelectorAll<HTMLInputElement>(
    `[data-test="${props.testId}-input"]`,
  ) ?? [])];
}

function addButtonElement(): HTMLElement | null {
  return root.value?.querySelector<HTMLElement>(`[data-test="${props.testId}-add"]`) ?? null;
}

function focusRowInput(index: number): void {
  rowInputs()[index]?.focus();
}

function handleRowInput(key: number, event: Event): void {
  const target = event.target;
  if (target instanceof HTMLInputElement) {
    const row = rows.value.find((candidate) => candidate.key === key);
    if (row) {
      row.text = target.value;
      emitDraft();
      // Typing an empty list commits nothing: the save rules refuse an empty
      // accepted value. `change` and the exposed `commit()` still emit it.
      if (normalizedRows().length > 0) {
        commit();
      }
    }
  }
}

function handleRowChange(index: number, event: Event): void {
  const target = event.target;
  if (target instanceof HTMLInputElement) {
    rows.value[index].text = target.value;
  }
  commit();
}

function handleRowKeydown(index: number, event: KeyboardEvent): void {
  if (event.isComposing || event.keyCode === 229 || event.key !== "Enter") {
    return;
  }
  event.preventDefault();
  if (props.disabled || rows.value.length >= MAX_ROWS) {
    return;
  }
  rows.value.splice(index + 1, 0, makeRow(""));
  emitDraft();
  void nextTick(() => focusRowInput(index + 1));
}

function handleRemove(index: number): void {
  if (props.disabled) {
    return;
  }
  // The row and its button disappear; move focus before the splice so the
  // focused remove button is never detached while focused.
  const inputs = rowInputs();
  (inputs[index - 1] ?? inputs[index + 1] ?? addButtonElement())?.focus();
  rows.value.splice(index, 1);
  if (rows.value.length === 0) {
    rows.value.push(makeRow(""));
  }
  emitDraft();
  commit();
}

function handleAdd(): void {
  if (props.disabled || rows.value.length >= MAX_ROWS) {
    return;
  }
  rows.value.push(makeRow(""));
  emitDraft();
  void nextTick(() => focusRowInput(rows.value.length - 1));
}

function focusFirst(): void {
  focusRowInput(0);
}

// Follow externally changed values, but never clobber answers being typed.
// An echo of the last commit changes no row and no key; a real external
// change reuses the keys of rows whose text is unchanged at the same
// position, keeping a focused empty row at its insertion position.
watch(
  () => props.values,
  (values) => {
    if (!sameValues(normalizedRows(), lastCommitted)) {
      return;
    }
    if (sameValues(values, normalizedRows())) {
      lastCommitted = [...values];
      return;
    }
    const inputs = rowInputs();
    const focusedIndex = rows.value.findIndex(
      (row, index) => row.text === "" && inputs[index] === document.activeElement,
    );
    const focusedEmptyRow = focusedIndex >= 0 ? rows.value[focusedIndex] : undefined;
    const kept =
      focusedIndex >= 0
        ? rows.value.filter((row, index) => index !== focusedIndex)
        : rows.value;
    const next: AnswerRow[] = values.map((value, index) =>
      kept[index] !== undefined && kept[index].text === value
        ? kept[index]
        : makeRow(value),
    );
    if (next.length === 0) {
      if (focusedEmptyRow !== undefined) {
        next.push(focusedEmptyRow);
      } else {
        next.push(makeRow(""));
      }
    } else if (focusedEmptyRow !== undefined) {
      next.splice(Math.min(focusedIndex, next.length), 0, focusedEmptyRow);
    }
    rows.value = next;
    lastCommitted = [...values];
    if (focusedEmptyRow !== undefined) {
      const keptRow = focusedEmptyRow;
      // The row keeps its DOM identity through the patch; refocus it at its
      // reconciled position as a safety net.
      void nextTick(() => {
        focusRowInput(rows.value.indexOf(keptRow));
      });
    }
  },
);

defineExpose({ commit, focusFirst });
</script>

<template>
  <div
    ref="root"
    class="grid min-w-0 gap-1.5"
    role="group"
    :aria-label="label"
    :data-test="testId"
  >
    <div
      v-for="(row, index) in rows"
      :key="row.key"
      class="flex min-w-0 items-center gap-1"
    >
      <input
        class="min-h-10 min-w-0 flex-1 border border-navy/35 bg-canvas px-3 text-sm font-normal text-navy"
        type="text"
        :value="row.text"
        :disabled="disabled"
        :aria-label="`Svar ${index + 1}`"
        :data-test="`${testId}-input`"
        @input="handleRowInput(row.key, $event)"
        @change="handleRowChange(index, $event)"
        @keydown="handleRowKeydown(index, $event)"
      >
      <button
        type="button"
        class="xw-rm"
        :disabled="disabled"
        :aria-label="REMOVE_LABEL"
        :title="REMOVE_LABEL"
        :data-test="`${testId}-remove`"
        @click="handleRemove(index)"
      >
        <UiGlyph
          meaning="delete"
          :size="16"
        />
      </button>
    </div>
    <button
      type="button"
      class="btn-ghost justify-center shadow-none"
      :disabled="disabled || rows.length >= MAX_ROWS"
      :aria-label="ADD_LABEL"
      :title="rows.length >= MAX_ROWS ? ADD_CAP_TITLE : ADD_LABEL"
      :data-test="`${testId}-add`"
      @click="handleAdd"
    >
      <UiGlyph
        meaning="add"
        :size="16"
      />
    </button>
  </div>
</template>
