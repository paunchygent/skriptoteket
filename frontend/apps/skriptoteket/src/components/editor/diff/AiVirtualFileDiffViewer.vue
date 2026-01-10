<script setup lang="ts">
import { json } from "@codemirror/lang-json";
import { python } from "@codemirror/lang-python";
import type { Extension } from "@codemirror/state";
import { computed, ref, watch } from "vue";

import type { VirtualFileId } from "../../../composables/editor/virtualFiles";
import { virtualFileLabel, virtualFileLanguage } from "../../../composables/editor/virtualFiles";
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
    beforeLabel: "Nuvarande",
    afterLabel: "Förslag",
  },
);

const emit = defineEmits<{
  (event: "update:activeFileId", value: VirtualFileId): void;
}>();

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
</script>

<template>
  <div class="panel-inset flex flex-col min-h-0">
    <div class="border-b border-navy/20 bg-canvas px-3 py-2">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <label
            for="ai-edit-ops-diff-file"
            class="text-[10px] font-semibold uppercase tracking-wide text-navy/60"
          >
            Fil
          </label>
          <select
            id="ai-edit-ops-diff-file"
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

        <div class="text-[10px] text-navy/60 whitespace-nowrap">
          <span class="font-semibold uppercase tracking-wide">{{ props.beforeLabel }}</span>
          <span class="px-2 text-navy/40">→</span>
          <span class="font-semibold uppercase tracking-wide">{{ props.afterLabel }}</span>
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
