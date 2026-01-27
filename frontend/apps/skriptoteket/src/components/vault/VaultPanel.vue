<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { formatBytes } from "../../composables/tools/fileRefHelpers";
import { useVaultFiles } from "../../composables/vault/useVaultFiles";
import { useToastStore } from "../../stores/toast";
import UiSegmentedToggle, { type UiSegmentedToggleOption } from "../ui/UiSegmentedToggle.vue";
import SystemMessage from "../ui/SystemMessage.vue";

type VaultPanelMode = "manage" | "picker";
type VaultListSort = components["schemas"]["VaultListSort"];
type VaultListState = components["schemas"]["VaultListState"];

const props = withDefaults(defineProps<{
  mode: VaultPanelMode;
  modelValue?: string[];
  maxSelected?: number;
  isReadOnly?: boolean;
}>(), {
  modelValue: () => [],
  maxSelected: 1,
  isReadOnly: false,
});

const emit = defineEmits<{
  "update:modelValue": [value: string[]];
}>();

const toast = useToastStore();
const selectionError = ref<string | null>(null);
const actionError = ref<string | null>(null);
const isMutating = ref(false);

const {
  state,
  sort,
  search,
  files,
  usage,
  canLoadMore,
  isLoading,
  errorMessage,
  refresh,
  loadMore,
  deleteFile,
  restoreFile,
} = useVaultFiles();

const stateOptions: UiSegmentedToggleOption[] = [
  { value: "active", label: "Aktiva" },
  { value: "trash", label: "Papperskorg" },
];

const sortOptions: UiSegmentedToggleOption[] = [
  { value: "newest", label: "Nyast" },
  { value: "name", label: "Namn" },
  { value: "size", label: "Storlek" },
];

function isVaultListState(value: string): value is VaultListState {
  return value === "active" || value === "trash";
}

function isVaultListSort(value: string): value is VaultListSort {
  return value === "newest" || value === "name" || value === "size";
}

function onStateUpdate(value: string): void {
  if (!isVaultListState(value)) return;
  state.value = value;
}

function onSortUpdate(value: string): void {
  if (!isVaultListSort(value)) return;
  sort.value = value;
}

const usagePercent = computed(() => {
  const max = usage.value?.max_total_bytes ?? 0;
  const total = usage.value?.bytes_total ?? 0;
  if (max <= 0) return 0;
  return Math.max(0, Math.min(1, total / max));
});

const selectionCountLabel = computed(() => {
  if (props.mode !== "picker") return null;
  const count = props.modelValue.length;
  return count === 1 ? "1 vald" : `${count} valda`;
});

const isPickerMode = computed(() => props.mode === "picker");
const selectionDisabled = computed(() => props.isReadOnly || !isPickerMode.value || state.value !== "active");

function onToggleSelected(refValue: string, checked: boolean): void {
  selectionError.value = null;
  if (selectionDisabled.value) return;

  const current = props.modelValue ?? [];
  if (!checked) {
    emit("update:modelValue", current.filter((value) => value !== refValue));
    return;
  }

  const max = Math.max(1, props.maxSelected ?? 1);
  if (max === 1) {
    emit("update:modelValue", [refValue]);
    return;
  }

  if (current.includes(refValue)) return;
  if (current.length >= max) {
    selectionError.value = `Du kan välja max ${max} filer.`;
    return;
  }
  emit("update:modelValue", [...current, refValue]);
}

function onToggleSelectedEvent(event: Event, refValue: string): void {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) return;
  onToggleSelected(refValue, target.checked);
}

async function onSearch(): Promise<void> {
  actionError.value = null;
  await refresh();
}

async function onDelete(fileId: string): Promise<void> {
  if (isMutating.value) return;
  isMutating.value = true;
  actionError.value = null;

  try {
    await deleteFile(fileId);
    toast.success("Filen flyttades till papperskorgen.");
    await refresh();
  } catch (error: unknown) {
    if (isApiError(error)) {
      actionError.value = error.message;
    } else if (error instanceof Error) {
      actionError.value = error.message;
    } else {
      actionError.value = "Det gick inte att ta bort filen.";
    }
  } finally {
    isMutating.value = false;
  }
}

async function onRestore(fileId: string): Promise<void> {
  if (isMutating.value) return;
  isMutating.value = true;
  actionError.value = null;

  try {
    await restoreFile(fileId);
    toast.success("Filen återställdes.");
    await refresh();
  } catch (error: unknown) {
    if (isApiError(error)) {
      actionError.value = error.message;
    } else if (error instanceof Error) {
      actionError.value = error.message;
    } else {
      actionError.value = "Det gick inte att återställa filen.";
    }
  } finally {
    isMutating.value = false;
  }
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
}

onMounted(() => {
  void refresh();
});
</script>

<template>
  <section class="panel space-y-4">
    <div class="flex flex-col gap-3">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Filer
          </h2>
          <p
            v-if="isPickerMode"
            class="text-xs text-navy/60"
          >
            Välj filer från ditt valv. {{ selectionCountLabel }}
          </p>
          <p
            v-else
            class="text-xs text-navy/60"
          >
            Aktiva filer och papperskorg.
          </p>
        </div>

        <UiSegmentedToggle
          :model-value="state"
          :options="stateOptions"
          aria-label="Välj vy"
          width="auto"
          @update:model-value="onStateUpdate"
        />
      </div>

      <div
        v-if="usage"
        class="border border-navy/20 bg-canvas/30 p-3 space-y-2"
      >
        <div class="flex items-center justify-between gap-3 text-xs text-navy/70">
          <span class="font-semibold uppercase tracking-wide">Kvot</span>
          <span>{{ formatBytes(usage.bytes_total) }} / {{ formatBytes(usage.max_total_bytes) }}</span>
        </div>
        <div class="h-2 border border-navy/30 bg-white">
          <div
            class="h-full bg-burgundy"
            :style="{ width: `${Math.round(usagePercent * 100)}%` }"
          />
        </div>
        <div class="text-[11px] text-navy/60 flex flex-wrap gap-x-4 gap-y-1">
          <span>Max fil: {{ formatBytes(usage.max_file_bytes) }}</span>
          <span>Max totalt: {{ formatBytes(usage.max_total_bytes) }}</span>
        </div>
      </div>

      <div class="flex flex-col sm:flex-row gap-2 sm:items-end sm:justify-between">
        <div class="flex-1">
          <label class="block text-xs font-semibold text-navy/70 mb-1">
            Sök
          </label>
          <input
            v-model="search"
            type="search"
            class="w-full px-3 py-2 border border-navy bg-white text-navy"
            placeholder="Sök på filnamn…"
            @keydown.enter.prevent="void onSearch()"
          >
        </div>

        <div class="flex items-end gap-2">
          <div>
            <label class="block text-xs font-semibold text-navy/70 mb-1">
              Sortera
            </label>
            <UiSegmentedToggle
              :model-value="sort"
              :options="sortOptions"
              aria-label="Sortera"
              width="auto"
              @update:model-value="onSortUpdate"
            />
          </div>

          <button
            type="button"
            class="btn-ghost h-[38px] px-3 py-2"
            :disabled="isLoading"
            @click="void onSearch()"
          >
            Sök
          </button>
        </div>
      </div>
    </div>

    <SystemMessage
      v-if="errorMessage"
      :model-value="errorMessage"
      variant="error"
      :dismissible="false"
    />
    <SystemMessage
      v-else
      :model-value="actionError"
      variant="error"
      @update:model-value="actionError = $event"
    />

    <SystemMessage
      v-if="selectionError"
      :model-value="selectionError"
      variant="error"
      @update:model-value="selectionError = $event"
    />

    <div
      v-if="isLoading"
      class="panel-state"
    >
      Laddar valv…
    </div>

    <div
      v-else-if="files.length === 0"
      class="panel-state"
    >
      <span v-if="state === 'trash'">Papperskorgen är tom.</span>
      <span v-else>Du har inga filer i valvet ännu.</span>
    </div>

    <div
      v-else
      class="space-y-2"
    >
      <ul class="space-y-1">
        <li
          v-for="file in files"
          :key="file.id"
          class="border border-navy/20 bg-white px-3 py-2 flex items-start gap-3"
        >
          <input
            v-if="isPickerMode"
            type="checkbox"
            class="mt-1 accent-burgundy"
            :checked="modelValue.includes(file.ref)"
            :disabled="selectionDisabled"
            @change="onToggleSelectedEvent($event, file.ref)"
          >

          <div class="flex-1 min-w-0">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="font-mono text-sm text-navy truncate">
                  {{ file.name }}
                </div>
                <div class="text-xs text-navy/60">
                  {{ formatBytes(file.bytes) }} · {{ formatDate(file.created_at) }}
                </div>
              </div>

              <div class="flex items-center gap-2 shrink-0">
                <button
                  v-if="state === 'active'"
                  type="button"
                  class="btn-ghost h-[30px] px-3 py-1 text-xs font-semibold tracking-wide border-burgundy/40 text-burgundy bg-white shadow-none"
                  :disabled="isMutating"
                  @click="void onDelete(file.id)"
                >
                  Ta bort
                </button>
                <button
                  v-else
                  type="button"
                  class="btn-ghost h-[30px] px-3 py-1 text-xs font-semibold tracking-wide border-navy/30 bg-canvas shadow-none"
                  :disabled="isMutating"
                  @click="void onRestore(file.id)"
                >
                  Återställ
                </button>
              </div>
            </div>

            <p
              v-if="isPickerMode && state !== 'active'"
              class="mt-1 text-[11px] text-navy/60"
            >
              Återställ filen för att kunna välja den.
            </p>
          </div>
        </li>
      </ul>

      <div
        v-if="canLoadMore"
        class="flex justify-center"
      >
        <button
          type="button"
          class="btn-ghost"
          :disabled="isLoading"
          @click="void loadMore()"
        >
          Ladda fler
        </button>
      </div>
    </div>
  </section>
</template>
