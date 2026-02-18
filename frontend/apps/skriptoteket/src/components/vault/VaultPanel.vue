<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import { apiFetchBlob, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { formatBytes } from "../../composables/tools/fileRefHelpers";
import { useVaultFiles } from "../../composables/vault/useVaultFiles";
import { useAuthStore } from "../../stores/auth";
import { useToastStore } from "../../stores/toast";
import { IconDownload, IconMoreVertical, IconTrash, IconUndo } from "../icons";
import UiSearchBar from "../ui/UiSearchBar.vue";
import UiSegmentedToggle, { type UiSegmentedToggleOption } from "../ui/UiSegmentedToggle.vue";
import SystemMessage from "../ui/SystemMessage.vue";

type VaultPanelMode = "manage" | "picker";
type VaultFileInfo = components["schemas"]["VaultFileInfo"];
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
const auth = useAuthStore();
const selectionError = ref<string | null>(null);
const actionError = ref<string | null>(null);
const isMutating = ref(false);
const openMenuForFileId = ref<string | null>(null);
const selectedManageIds = ref<string[]>([]);

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

const searchDraft = ref(search.value);
const searchMinChars = 2;
const searchDebounceMs = 250;
let searchDebounceId: number | null = null;

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

const manageSelectionLabel = computed(() => {
  if (props.mode !== "manage") return null;
  const count = selectedManageIds.value.length;
  if (count === 0) return null;
  return count === 1 ? "1 markerad" : `${count} markerade`;
});

const isPickerMode = computed(() => props.mode === "picker");
const isManageMode = computed(() => props.mode === "manage");
const selectionDisabled = computed(() => props.isReadOnly || !isPickerMode.value || state.value !== "active");
const manageSelectionDisabled = computed(() => props.isReadOnly);
const showBulkActions = computed(() => isManageMode.value);

const canAutoSearch = computed(() => {
  const trimmed = searchDraft.value.trim();
  return trimmed.length === 0 || trimmed.length >= searchMinChars;
});

function clearSearchDebounce(): void {
  if (searchDebounceId === null) return;
  window.clearTimeout(searchDebounceId);
  searchDebounceId = null;
}

async function applySearch(): Promise<void> {
  search.value = searchDraft.value;
  await refresh();
}

function scheduleSearch(): void {
  clearSearchDebounce();
  if (!canAutoSearch.value) {
    return;
  }
  searchDebounceId = window.setTimeout(() => {
    searchDebounceId = null;
    void applySearch();
  }, searchDebounceMs);
}

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

function selectAllVisibleManage(): void {
  if (manageSelectionDisabled.value) return;
  selectedManageIds.value = files.value.map((file) => file.id);
}

function clearManageSelection(): void {
  selectedManageIds.value = [];
}

async function onSearch(): Promise<void> {
  actionError.value = null;
  clearSearchDebounce();
  if (!canAutoSearch.value) {
    actionError.value = `Skriv minst ${searchMinChars} tecken för att söka.`;
    return;
  }
  await applySearch();
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

async function onDeleteSelected(): Promise<void> {
  if (isMutating.value) return;
  if (selectedManageIds.value.length === 0) return;

  isMutating.value = true;
  actionError.value = null;

  try {
    for (const fileId of selectedManageIds.value) {
      await deleteFile(fileId);
    }
    clearManageSelection();
    toast.success("Markerade filer flyttades till papperskorgen.");
    await refresh();
  } catch (error: unknown) {
    if (isApiError(error)) {
      actionError.value = error.message;
    } else if (error instanceof Error) {
      actionError.value = error.message;
    } else {
      actionError.value = "Det gick inte att ta bort filerna.";
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

async function onRestoreSelected(): Promise<void> {
  if (isMutating.value) return;
  if (selectedManageIds.value.length === 0) return;

  isMutating.value = true;
  actionError.value = null;

  try {
    for (const fileId of selectedManageIds.value) {
      await restoreFile(fileId);
    }
    clearManageSelection();
    toast.success("Markerade filer återställdes.");
    await refresh();
  } catch (error: unknown) {
    if (isApiError(error)) {
      actionError.value = error.message;
    } else if (error instanceof Error) {
      actionError.value = error.message;
    } else {
      actionError.value = "Det gick inte att återställa filerna.";
    }
  } finally {
    isMutating.value = false;
  }
}

async function onDownload(file: VaultFileInfo): Promise<void> {
  if (isMutating.value) return;
  isMutating.value = true;
  actionError.value = null;

  try {
    const blob = await apiFetchBlob(downloadHref(file.id));
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = file.name;
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  } catch (error: unknown) {
    if (isApiError(error)) {
      const details = error.details as { resource?: string } | null;
      if (error.code === "NOT_FOUND" && details?.resource === "VaultFile") {
        actionError.value =
          "Filen saknas på servern. Ta bort filen och skapa den igen om du behöver den.";
      } else {
        actionError.value = error.message;
      }
    } else if (error instanceof Error) {
      actionError.value = error.message;
    } else {
      actionError.value = "Det gick inte att ladda ned filen.";
    }
  } finally {
    isMutating.value = false;
  }
}

function downloadHref(fileId: string): string {
  return `/api/v1/vault/files/${encodeURIComponent(fileId)}/download`;
}

function toggleMenu(fileId: string): void {
  openMenuForFileId.value = openMenuForFileId.value === fileId ? null : fileId;
}

function closeMenu(): void {
  openMenuForFileId.value = null;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
}

watch(searchDraft, () => {
  actionError.value = null;
  scheduleSearch();
});

watch(search, (value) => {
  if (value === searchDraft.value) return;
  searchDraft.value = value;
});

watch(state, () => {
  closeMenu();
  clearManageSelection();
});

watch(files, () => {
  closeMenu();
  if (!isManageMode.value) return;
  const ids = new Set(files.value.map((file) => file.id));
  selectedManageIds.value = selectedManageIds.value.filter((id) => ids.has(id));
});

function handleDocumentClick(): void {
  if (openMenuForFileId.value) {
    closeMenu();
  }
}

function handleEscape(event: KeyboardEvent): void {
  if (event.key !== "Escape") return;
  if (openMenuForFileId.value) {
    closeMenu();
    return;
  }
  if (searchDraft.value.trim()) {
    searchDraft.value = "";
  }
}

watch(
  [() => auth.bootstrapped, () => auth.isAuthenticated],
  ([bootstrapped, isAuthenticated]) => {
    if (!bootstrapped || !isAuthenticated) return;
    void refresh();
  },
  { immediate: true },
);

onMounted(() => {
  document.addEventListener("click", handleDocumentClick);
  document.addEventListener("keydown", handleEscape);
});

onUnmounted(() => {
  document.removeEventListener("click", handleDocumentClick);
  document.removeEventListener("keydown", handleEscape);
  clearSearchDebounce();
});
</script>

<template>
  <section class="border border-navy bg-white shadow-brutal-sm p-4 space-y-4">
    <header class="space-y-3">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="space-y-1">
          <h2 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Filer
          </h2>
          <p
            v-if="isPickerMode"
            class="text-xs text-navy/60"
          >
            Välj filer från Mina filer. {{ selectionCountLabel }}
          </p>
          <p
            v-else
            class="text-xs text-navy/60"
          >
            Aktiva filer och papperskorg.
            <span v-if="manageSelectionLabel">· {{ manageSelectionLabel }}</span>
          </p>
        </div>

        <UiSegmentedToggle
          :model-value="state"
          :options="stateOptions"
          aria-label="Välj vy"
          width="auto"
          :density="'compact'"
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

      <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end sm:gap-3 lg:flex-nowrap">
          <div class="w-full sm:min-w-0 sm:flex-1 lg:flex-none lg:min-w-[var(--huleedu-max-width-sm)] lg:max-w-[var(--huleedu-max-width-md)]">
            <UiSearchBar
              v-model="searchDraft"
              label="Sök"
              placeholder="Sök på filnamn…"
              :is-busy="isLoading"
              :show-button="true"
              :button-disabled="isLoading || !canAutoSearch"
              variant="panel"
              @submit="void onSearch()"
            />
            <p
              v-if="searchDraft.trim().length > 0 && searchDraft.trim().length < searchMinChars"
              class="mt-1 text-[11px] text-navy/60"
            >
              Skriv minst {{ searchMinChars }} tecken.
            </p>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wide text-navy/70 mb-1">
              Sortera
            </label>
            <UiSegmentedToggle
              :model-value="sort"
              :options="sortOptions"
              aria-label="Sortera"
              width="auto"
              :density="'compact'"
              :columns="3"
              @update:model-value="onSortUpdate"
            />
          </div>
        </div>

        <div
          v-if="showBulkActions"
          class="flex w-full flex-wrap items-center justify-start gap-2 lg:w-auto lg:justify-end"
        >
          <button
            type="button"
            class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none border-navy/30 bg-white shadow-none"
            :disabled="isLoading || manageSelectionDisabled"
            @click="selectAllVisibleManage"
          >
            Markera alla
          </button>
          <button
            type="button"
            class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none border-navy/30 bg-white shadow-none"
            :disabled="selectedManageIds.length === 0 || manageSelectionDisabled"
            @click="clearManageSelection"
          >
            Avmarkera
          </button>
          <button
            v-if="state === 'active'"
            type="button"
            class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none border-burgundy/40 text-burgundy bg-white shadow-none"
            :disabled="selectedManageIds.length === 0 || isMutating || manageSelectionDisabled"
            @click="void onDeleteSelected()"
          >
            Ta bort markerade
          </button>
          <button
            v-else
            type="button"
            class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none border-navy/30 bg-canvas shadow-none"
            :disabled="selectedManageIds.length === 0 || isMutating || manageSelectionDisabled"
            @click="void onRestoreSelected()"
          >
            Återställ markerade
          </button>
        </div>
      </div>
    </header>

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
      class="p-4 text-sm text-navy/70"
    >
      Laddar Mina filer…
    </div>

    <div
      v-else-if="files.length === 0"
      class="p-4 text-sm text-navy/70"
    >
      <span v-if="state === 'trash'">Papperskorgen är tom.</span>
      <span v-else>Du har inga sparade filer ännu.</span>
    </div>

    <div
      v-else
      class="space-y-2"
    >
      <ul class="space-y-2">
        <li
          v-for="file in files"
          :key="file.id"
          class="border border-navy/20 bg-white hover:bg-canvas/30 transition-colors"
        >
          <div class="grid grid-cols-[minmax(0,1fr)_auto] gap-3 p-3">
            <label
              v-if="isPickerMode || isManageMode"
              class="grid grid-cols-[auto_minmax(0,1fr)] gap-3 items-center min-w-0"
              :class="[
                (isPickerMode && (selectionDisabled || file.is_missing_on_disk))
                  || (isManageMode && manageSelectionDisabled)
                  ? 'cursor-default'
                  : 'cursor-pointer',
              ]"
              :for="`vault-file-select-${file.id}`"
            >
              <input
                v-if="isPickerMode"
                :id="`vault-file-select-${file.id}`"
                type="checkbox"
                class="h-4 w-4 border border-navy/40 bg-white shadow-none accent-burgundy"
                :aria-label="file.name"
                :checked="props.modelValue.includes(file.ref)"
                :disabled="selectionDisabled || file.is_missing_on_disk"
                @change="onToggleSelectedEvent($event, file.ref)"
              >
              <input
                v-else
                :id="`vault-file-select-${file.id}`"
                v-model="selectedManageIds"
                type="checkbox"
                :value="file.id"
                class="h-4 w-4 border border-navy/40 bg-white shadow-none accent-burgundy"
                :aria-label="file.name"
                :disabled="manageSelectionDisabled"
              >

              <div class="min-w-0">
                <div class="font-mono text-sm text-navy truncate">
                  {{ file.name }}
                </div>
                <div class="mt-0.5 flex flex-wrap gap-x-2 gap-y-0.5 text-[11px] text-navy/60">
                  <span v-if="file.source_label">{{ file.source_label }}</span>
                  <span
                    v-if="file.source_label"
                    aria-hidden="true"
                  >·</span>
                  <span>{{ formatBytes(file.bytes) }}</span>
                  <span aria-hidden="true">·</span>
                  <span>{{ formatDate(file.created_at) }}</span>
                  <span
                    v-if="file.is_missing_on_disk"
                    aria-hidden="true"
                  >·</span>
                  <span
                    v-if="file.is_missing_on_disk"
                    class="font-semibold text-burgundy"
                  >Saknas på servern</span>
                </div>
                <p
                  v-if="isPickerMode && state !== 'active'"
                  class="mt-1 text-[11px] text-navy/60"
                >
                  Återställ filen för att kunna välja den.
                </p>
                <p
                  v-if="file.is_missing_on_disk"
                  class="mt-1 text-[11px] text-burgundy"
                >
                  Filen saknas på servern. Ta bort den eller skapa den igen om du behöver den.
                </p>
              </div>
            </label>
            <div
              v-else
              class="min-w-0"
            >
              <div class="font-mono text-sm text-navy truncate">
                {{ file.name }}
              </div>
              <div class="mt-0.5 flex flex-wrap gap-x-2 gap-y-0.5 text-[11px] text-navy/60">
                <span v-if="file.source_label">{{ file.source_label }}</span>
                <span
                  v-if="file.source_label"
                  aria-hidden="true"
                >·</span>
                <span>{{ formatBytes(file.bytes) }}</span>
                <span aria-hidden="true">·</span>
                <span>{{ formatDate(file.created_at) }}</span>
                <span
                  v-if="file.is_missing_on_disk"
                  aria-hidden="true"
                >·</span>
                <span
                  v-if="file.is_missing_on_disk"
                  class="font-semibold text-burgundy"
                >Saknas på servern</span>
              </div>
            </div>

            <div
              v-if="!props.isReadOnly"
              class="relative justify-self-end self-center"
              @click.stop
            >
              <button
                type="button"
                class="h-[30px] w-[30px] grid place-items-center bg-transparent text-navy/70 hover:bg-canvas/50 hover:text-navy shadow-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2"
                :disabled="isMutating"
                :aria-expanded="openMenuForFileId === file.id"
                :aria-controls="`vault-file-actions-${file.id}`"
                aria-label="Filåtgärder"
                @click.stop="toggleMenu(file.id)"
              >
                <IconMoreVertical :size="16" />
              </button>

              <Transition name="popover">
                <div
                  v-if="openMenuForFileId === file.id"
                  :id="`vault-file-actions-${file.id}`"
                  class="absolute right-0 mt-2 w-48 border border-navy bg-white shadow-brutal-sm z-50"
                  role="menu"
                  aria-label="Filåtgärder"
                  @click.stop
                >
                  <button
                    type="button"
                    class="flex items-center gap-2 w-full px-3 py-2 text-sm text-navy hover:bg-canvas transition-colors"
                    role="menuitem"
                    :disabled="isMutating || file.is_missing_on_disk"
                    @click="closeMenu(); void onDownload(file);"
                  >
                    <IconDownload :size="16" />
                    Ladda ned
                  </button>

                  <button
                    v-if="state === 'active'"
                    type="button"
                    class="flex items-center gap-2 w-full px-3 py-2 text-sm text-burgundy hover:bg-canvas transition-colors"
                    role="menuitem"
                    :disabled="isMutating"
                    @click="void onDelete(file.id); closeMenu();"
                  >
                    <IconTrash :size="16" />
                    Ta bort
                  </button>

                  <button
                    v-else
                    type="button"
                    class="flex items-center gap-2 w-full px-3 py-2 text-sm text-navy hover:bg-canvas transition-colors"
                    role="menuitem"
                    :disabled="isMutating"
                    @click="void onRestore(file.id); closeMenu();"
                  >
                    <IconUndo :size="16" />
                    Återställ
                  </button>
                </div>
              </Transition>
            </div>
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
