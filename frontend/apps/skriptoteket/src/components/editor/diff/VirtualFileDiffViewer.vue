<script setup lang="ts">
import { json } from "@codemirror/lang-json";
import { python } from "@codemirror/lang-python";
import type { Extension } from "@codemirror/state";
import { computed, ref, watch } from "vue";

import { buildUnifiedPatch, normalizeTextForPatch } from "../../../composables/editor/diff/unifiedPatch";
import type { VirtualFileId } from "../../../composables/editor/virtualFiles";
import { virtualFileLabel, virtualFileLanguage } from "../../../composables/editor/virtualFiles";
import { useToast } from "../../../composables/useToast";
import CodeMirrorMergeDiff from "./CodeMirrorMergeDiff.vue";

type DiffViewerItem = {
  virtualFileId: VirtualFileId;
  beforeText: string;
  afterText: string;
};

const props = withDefaults(
  defineProps<{
    items: DiffViewerItem[];
    activeFileId?: VirtualFileId | null;
    beforeLabel?: string;
    afterLabel?: string;
  }>(),
  {
    activeFileId: null,
    beforeLabel: "Före",
    afterLabel: "Efter",
  },
);

const emit = defineEmits<{
  (event: "update:activeFileId", value: VirtualFileId): void;
}>();

const toast = useToast();

const activeFileFallback = ref<VirtualFileId | null>(props.activeFileId ?? null);

const activeFileId = computed(() => {
  const requested = props.activeFileId;
  if (requested && props.items.some((item) => item.virtualFileId === requested)) {
    return requested;
  }

  const fallback = activeFileFallback.value;
  if (fallback && props.items.some((item) => item.virtualFileId === fallback)) {
    return fallback;
  }

  return props.items[0]?.virtualFileId ?? null;
});

watch(
  () => props.activeFileId,
  (value) => {
    if (value !== null) {
      activeFileFallback.value = value;
    }
  },
);

watch(
  () => [props.items, props.activeFileId] as const,
  ([items, requested]) => {
    if (items.length === 0) {
      activeFileFallback.value = null;
      return;
    }

    if (requested && !items.some((item) => item.virtualFileId === requested)) {
      emit("update:activeFileId", items[0]!.virtualFileId);
      return;
    }

    const fallback = activeFileFallback.value;
    if (fallback && items.some((item) => item.virtualFileId === fallback)) {
      return;
    }

    activeFileFallback.value = items[0]!.virtualFileId;
  },
  { immediate: true },
);

const activeItem = computed(() => {
  const selected = activeFileId.value;
  if (!selected) return null;
  return props.items.find((item) => item.virtualFileId === selected) ?? null;
});

const activeItemLabel = computed(() => {
  const item = activeItem.value;
  return item ? virtualFileLabel(item.virtualFileId) : "";
});

const activeLanguage = computed<Extension | null>(() => {
  const fileId = activeItem.value?.virtualFileId;
  if (!fileId) return null;

  const language = virtualFileLanguage(fileId);
  switch (language) {
    case "python":
      return python();
    case "json":
      return json();
    default:
      return null;
  }
});

const activeTabSize = computed(() => {
  const fileId = activeItem.value?.virtualFileId;
  if (!fileId) return 4;
  return virtualFileLanguage(fileId) === "json" ? 2 : 4;
});

function setActiveFileId(fileId: VirtualFileId): void {
  activeFileFallback.value = fileId;
  emit("update:activeFileId", fileId);
}

async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

function downloadTextFile(filename: string, content: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

async function copyBefore(): Promise<void> {
  if (!activeItem.value) return;
  try {
    await copyToClipboard(normalizeTextForPatch(activeItem.value.beforeText));
    toast.success("Kopierade före.");
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Kunde inte kopiera.";
    toast.failure(message);
  }
}

async function copyAfter(): Promise<void> {
  if (!activeItem.value) return;
  try {
    await copyToClipboard(normalizeTextForPatch(activeItem.value.afterText));
    toast.success("Kopierade efter.");
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Kunde inte kopiera.";
    toast.failure(message);
  }
}

async function copyPatch(): Promise<void> {
  if (!activeItem.value) return;
  try {
    await copyToClipboard(
      buildUnifiedPatch({
        virtualFileId: activeItem.value.virtualFileId,
        before: activeItem.value.beforeText,
        after: activeItem.value.afterText,
      }),
    );
    toast.success("Kopierade patch.");
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Kunde inte kopiera patch.";
    toast.failure(message);
  }
}

function downloadBefore(): void {
  if (!activeItem.value) return;
  downloadTextFile("before.txt", normalizeTextForPatch(activeItem.value.beforeText), "text/plain;charset=utf-8");
}

function downloadAfter(): void {
  if (!activeItem.value) return;
  downloadTextFile("after.txt", normalizeTextForPatch(activeItem.value.afterText), "text/plain;charset=utf-8");
}

function downloadPatch(): void {
  if (!activeItem.value) return;
  downloadTextFile(
    "changes.patch",
    buildUnifiedPatch({
      virtualFileId: activeItem.value.virtualFileId,
      before: activeItem.value.beforeText,
      after: activeItem.value.afterText,
    }),
    "text/x-diff;charset=utf-8",
  );
}
</script>

<template>
  <div class="border border-navy bg-white shadow-brutal-sm">
    <div class="border-b border-navy/20 bg-canvas p-4 space-y-3">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-1 min-w-0">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Versiondiff
          </div>
          <div
            v-if="activeItem"
            class="text-sm text-navy flex flex-wrap items-center gap-2 min-w-0"
          >
            <span class="font-mono">
              {{ activeItem.virtualFileId }}
            </span>
            <span class="text-navy/50">·</span>
            <span class="text-navy/70">
              {{ activeItemLabel }}
            </span>
          </div>
        </div>

        <div class="text-xs text-navy/60">
          {{ props.beforeLabel }} → {{ props.afterLabel }}
        </div>
      </div>

      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          @click="copyBefore"
        >
          Kopiera före
        </button>
        <button
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          @click="copyAfter"
        >
          Kopiera efter
        </button>
        <button
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          @click="copyPatch"
        >
          Kopiera patch
        </button>

        <button
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          @click="downloadBefore"
        >
          Ladda ner före
        </button>
        <button
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          @click="downloadAfter"
        >
          Ladda ner efter
        </button>
        <button
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          @click="downloadPatch"
        >
          Ladda ner patch
        </button>
      </div>

      <div class="flex flex-wrap gap-2">
        <button
          v-for="item in props.items"
          :key="item.virtualFileId"
          type="button"
          :class="[
            'px-3 py-1 border shadow-brutal-sm text-xs font-semibold',
            item.virtualFileId === activeFileId
              ? 'border-burgundy bg-burgundy/5 text-burgundy'
              : 'border-navy/30 bg-white hover:bg-canvas hover:border-navy text-navy/70',
          ]"
          @click="setActiveFileId(item.virtualFileId)"
        >
          <span class="font-mono">
            {{ item.virtualFileId }}
          </span>
        </button>
      </div>
    </div>

    <div
      v-if="!activeItem"
      class="p-4 text-sm text-navy/70"
    >
      Inget att jämföra.
    </div>
    <div
      v-else
      class="h-[560px] border-t border-navy/20"
    >
      <CodeMirrorMergeDiff
        :before-text="activeItem.beforeText"
        :after-text="activeItem.afterText"
        :language="activeLanguage"
        :tab-size="activeTabSize"
        :collapse-unchanged="true"
      />
    </div>
  </div>
</template>
