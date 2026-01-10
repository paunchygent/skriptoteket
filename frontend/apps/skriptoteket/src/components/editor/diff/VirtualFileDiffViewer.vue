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

function mimeTypeForVirtualFile(virtualFileId: VirtualFileId): string {
  const language = virtualFileLanguage(virtualFileId);
  switch (language) {
    case "python":
      return "text/x-python;charset=utf-8";
    case "json":
      return "application/json;charset=utf-8";
    default:
      return "text/plain;charset=utf-8";
  }
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
  downloadTextFile(
    `before-${activeItem.value.virtualFileId}`,
    normalizeTextForPatch(activeItem.value.beforeText),
    mimeTypeForVirtualFile(activeItem.value.virtualFileId),
  );
}

function downloadAfter(): void {
  if (!activeItem.value) return;
  downloadTextFile(
    `after-${activeItem.value.virtualFileId}`,
    normalizeTextForPatch(activeItem.value.afterText),
    mimeTypeForVirtualFile(activeItem.value.virtualFileId),
  );
}

function downloadPatch(): void {
  if (!activeItem.value) return;
  downloadTextFile(
    `${activeItem.value.virtualFileId}.patch`,
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
  <div class="panel-inset flex flex-col min-h-0">
    <div class="border-b border-navy/20 bg-canvas px-3 py-2">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <label
            for="editor-diff-file"
            class="text-[10px] font-semibold uppercase tracking-wide text-navy/60"
          >
            Fil
          </label>
          <select
            id="editor-diff-file"
            class="h-[28px] border border-navy/30 bg-white px-2.5 text-[11px] text-navy shadow-none leading-none max-w-[min(360px,100%)]"
            :value="activeFileId ?? ''"
            :disabled="props.items.length === 0"
            @change="setActiveFileId(($event.target as HTMLSelectElement).value as VirtualFileId)"
          >
            <option
              v-for="item in props.items"
              :key="item.virtualFileId"
              :value="item.virtualFileId"
            >
              {{ item.virtualFileId }} · {{ virtualFileLabel(item.virtualFileId) }}
            </option>
          </select>
        </div>

        <div class="flex flex-wrap items-center justify-end gap-2">
          <div class="min-w-0 text-right">
            <p class="text-[10px] font-semibold uppercase tracking-wide text-navy/60 leading-none">
              Patch (hela diffen)
            </p>
            <p class="text-[10px] text-navy/60 truncate">
              {{ activeItem?.virtualFileId ? `${activeItem.virtualFileId}.patch` : "" }}
            </p>
          </div>
          <button
            type="button"
            class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-white leading-none"
            @click="copyPatch"
          >
            Kopiera
          </button>
          <button
            type="button"
            class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-white leading-none"
            @click="downloadPatch"
          >
            Ladda ned
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="activeItem"
      class="border-b border-navy/20 bg-white"
    >
      <div class="grid grid-cols-1 md:grid-cols-2">
        <div class="flex items-start justify-between gap-3 px-3 py-2 min-w-0">
          <div class="min-w-0">
            <p class="text-[10px] font-semibold uppercase tracking-wide text-navy/60 leading-none">
              Före
            </p>
            <p class="text-[10px] text-navy/60 truncate">
              {{ props.beforeLabel }}
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button
              type="button"
              class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-white leading-none"
              @click="copyBefore"
            >
              Kopiera
            </button>
            <button
              type="button"
              class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-white leading-none"
              @click="downloadBefore"
            >
              Ladda ned
            </button>
          </div>
        </div>

        <div class="flex items-start justify-between gap-3 px-3 py-2 min-w-0 md:border-l md:border-navy/20">
          <div class="min-w-0">
            <p class="text-[10px] font-semibold uppercase tracking-wide text-navy/60 leading-none">
              Efter
            </p>
            <p class="text-[10px] text-navy/60 truncate">
              {{ props.afterLabel }}
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button
              type="button"
              class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-white leading-none"
              @click="copyAfter"
            >
              Kopiera
            </button>
            <button
              type="button"
              class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-white leading-none"
              @click="downloadAfter"
            >
              Ladda ned
            </button>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="!activeItem"
      class="p-4 text-sm text-navy/70"
    >
      Ingen diff att visa.
    </div>
    <div
      v-else
      class="flex-1 min-h-0"
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
