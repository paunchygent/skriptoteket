<script setup lang="ts">
/** Document title edits use toolbar save; vault rename is a separate immediate action. */
import { computed, ref, useId, watch } from "vue";

import { IconX } from "../../../components/icons";
import { useExamWorkspaceDialogFocus } from "./useExamWorkspaceDialogFocus";
import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";
import type { ExamWorkspaceRenameFailure } from "./useExamWorkspaceRename";

const props = defineProps<{
  title: string;
  name: string;
  vaultFileId: string;
  renameFile: (fileId: string, stem: string) => Promise<string | null>;
  renameFailure: ExamWorkspaceRenameFailure | null;
  disabled: boolean;
  layout: ExamWorkspaceLayout;
}>();
const emit = defineEmits<{
  close: [];
  "update:title": [title: string];
}>();

const EXTENSION = ".provdokument.zip";
const FRAME_CLASS: Record<ExamWorkspaceLayout, string> = {
  desktop: "min-h-0 w-[clamp(18rem,24vw,22rem)] shrink-0 overflow-y-auto border-l border-navy/20",
  phone: "fixed inset-0 z-50 overflow-y-auto bg-modal outline-none",
  tablet:
    "absolute inset-y-0 right-0 z-10 w-[min(22rem,90%)] overflow-y-auto border-l border-navy bg-modal shadow-brutal-sm outline-none",
};
const frame = ref<HTMLElement | null>(null);
const id = useId();
const currentStem = computed(() => props.name.endsWith(EXTENSION)
  ? props.name.slice(0, -EXTENSION.length) : props.name);
const stem = ref(props.renameFailure?.stem ?? currentStem.value);
const renaming = ref(false);
const renameError = computed(() => props.renameFailure?.stem === stem.value
  ? props.renameFailure.message : null);
const canRename = computed(() => !props.disabled && !renaming.value
  && stem.value.trim().length > 0 && stem.value !== currentStem.value);
const isModal = computed(() => props.layout === "phone");

watch(() => [props.vaultFileId, props.name], () => {
  stem.value = props.renameFailure?.stem ?? currentStem.value;
});
watch(() => props.renameFailure, (failure) => {
  if (failure) stem.value = failure.stem;
});

useExamWorkspaceDialogFocus(frame, {
  modal: () => isModal.value,
  takesFocus: () => props.layout !== "desktop",
  fallbackFocus: () => document.querySelector<HTMLElement>('[data-test="exam-workspace-summary-title"]'),
  onClose: () => emit("close"),
});

async function rename(): Promise<void> {
  if (!canRename.value) return;
  const fileId = props.vaultFileId;
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
</script>

<template>
  <div
    ref="frame"
    :class="FRAME_CLASS[layout]"
    :role="isModal ? 'dialog' : undefined"
    :aria-modal="isModal ? 'true' : undefined"
    :aria-labelledby="isModal ? `${id}-heading` : undefined"
    :tabindex="layout === 'desktop' ? undefined : -1"
    data-test="exam-workspace-metadata-drawer-frame"
  >
    <aside
      class="grid content-start gap-5 p-4 text-navy"
      :aria-labelledby="`${id}-heading`"
      data-test="exam-workspace-metadata-drawer"
    >
      <header class="flex items-center justify-between gap-3">
        <h3
          :id="`${id}-heading`"
          class="text-sm font-semibold leading-tight"
        >
          Provets uppgifter
        </h3>
        <button
          type="button"
          class="inline-flex h-9 w-9 items-center justify-center border border-navy/35 bg-panel hover:bg-canvas"
          aria-label="Stäng provets uppgifter"
          data-test="exam-workspace-metadata-drawer-close"
          @click="emit('close')"
        >
          <IconX
            :size="16"
            class="h-4 w-4"
            aria-hidden="true"
          />
        </button>
      </header>
      <div class="grid gap-2">
        <label
          :for="`${id}-title`"
          class="text-sm font-semibold"
        >Titel</label>
        <input
          :id="`${id}-title`"
          :value="title"
          :disabled="disabled"
          :aria-invalid="!title.trim() || undefined"
          :aria-describedby="!title.trim() ? `${id}-title-guidance` : undefined"
          class="w-full min-w-0 border border-navy/35 bg-canvas px-3 py-2 text-sm"
          data-test="exam-workspace-metadata-title"
          @input="emit('update:title', ($event.target as HTMLInputElement).value)"
        >
        <p
          v-if="!title.trim()"
          :id="`${id}-title-guidance`"
          class="text-sm text-error"
        >
          Skriv en titel innan du sparar provet.
        </p>
      </div>
      <form
        class="grid gap-2"
        @submit.prevent="rename"
      >
        <label
          :for="`${id}-name`"
          class="text-sm font-semibold"
        >Filnamn i Mina filer</label>
        <input
          :id="`${id}-name`"
          v-model="stem"
          :disabled="disabled || renaming"
          :aria-invalid="!!renameError || undefined"
          :aria-describedby="renameError ? `${id}-name-error` : undefined"
          class="w-full min-w-0 border border-navy/35 bg-canvas px-3 py-2 text-sm"
          data-test="exam-workspace-metadata-name"
        >
        <button
          type="submit"
          class="btn-ghost justify-self-start shadow-none"
          :disabled="!canRename"
          data-test="exam-workspace-metadata-rename"
        >
          Byt namn
        </button>
        <p
          v-if="renameError"
          :id="`${id}-name-error`"
          role="alert"
          class="text-sm text-error"
          data-test="exam-workspace-metadata-name-error"
        >
          {{ renameError }}
        </p>
      </form>
      <!-- U6: official course combobox and read-only gymnasiet subject mount here. -->
      <slot name="course" />
    </aside>
  </div>
</template>
