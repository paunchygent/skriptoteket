<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import type { components } from "../../api/openapi";
import { formatBytes } from "../../composables/tools/fileRefHelpers";
import { useVaultFiles } from "../../composables/vault/useVaultFiles";
import { useAuthStore } from "../../stores/auth";
import UiSearchBar from "../ui/UiSearchBar.vue";
import UiSegmentedToggle, { type UiSegmentedToggleOption } from "../ui/UiSegmentedToggle.vue";
import SystemMessage from "../ui/SystemMessage.vue";

import VaultFileList from "./VaultFileList.vue";
import { useVaultFileActions } from "./useVaultFileActions";

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

const auth = useAuthStore();
const selectionError = ref<string | null>(null);
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

const {
  actionError,
  isMutating,
  onDelete,
  onDeleteSelected,
  onRestore,
  onRestoreSelected,
  onDownload,
} = useVaultFileActions({ selectedManageIds, clearManageSelection, deleteFile, restoreFile, refresh });

const searchDraft = ref(search.value);
const searchMinChars = 2;
const searchDebounceMs = 250;
let searchDebounceId: number | null = null;

const stateOptions: UiSegmentedToggleOption[] = [
  { value: "active", label: "Aktiva" },
  { value: "trash", label: "Papperskorg" },
];

const sortOptions: UiSegmentedToggleOption[] = [
  { value: "newest", label: "Nyast", dataTest: "vault-sort-newest" },
  { value: "name", label: "Namn", dataTest: "vault-sort-name" },
  { value: "size", label: "Storlek", dataTest: "vault-sort-size" },
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
const isInitialLoad = computed(() => isLoading.value && files.value.length === 0);
const isRefreshingResults = computed(() => isLoading.value && files.value.length > 0);

const vaultHeaderStatusLabel = computed(() => {
  if (isPickerMode.value) {
    const count = props.modelValue.length;
    if (count === 0) return null;
    return selectionCountLabel.value;
  }
  return manageSelectionLabel.value;
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

function toggleMenu(fileId: string): void {
  openMenuForFileId.value = openMenuForFileId.value === fileId ? null : fileId;
}

function closeMenu(): void {
  openMenuForFileId.value = null;
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
  <section class="border border-navy bg-panel shadow-brutal-sm p-4 space-y-4">
    <header class="space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <p
          v-if="vaultHeaderStatusLabel"
          class="text-xs font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60"
        >
          {{ vaultHeaderStatusLabel }}
        </p>
        <p
          v-else-if="isRefreshingResults"
          class="text-xs font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60"
        >
          Laddar filer…
        </p>

        <UiSegmentedToggle
          :model-value="state"
          :options="stateOptions"
          aria-label="Välj vy"
          width="auto"
          :density="'compact'"
          variant="subrail"
          :columns="2"
          data-test="vault-state-switch"
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
        <div class="h-2 border border-navy/30 bg-panel-muted">
          <div
            class="h-full bg-action"
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

          <div class="self-end">
            <UiSegmentedToggle
              :model-value="sort"
              :options="sortOptions"
              aria-label="Sortera filer"
              width="auto"
              :density="'compact'"
              variant="subrail"
              :columns="3"
              data-test="vault-sort-switch"
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
            class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none border-navy/30 bg-panel shadow-none"
            :disabled="isLoading || manageSelectionDisabled"
            @click="selectAllVisibleManage"
          >
            Markera alla
          </button>
          <button
            type="button"
            class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none border-navy/30 bg-panel shadow-none"
            :disabled="selectedManageIds.length === 0 || manageSelectionDisabled"
            @click="clearManageSelection"
          >
            Avmarkera
          </button>
          <button
            v-if="state === 'active'"
            type="button"
            class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none border-critical/40 text-critical bg-panel shadow-none"
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
      v-if="isInitialLoad"
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

    <VaultFileList
      v-else
      v-model:selected-manage-ids="selectedManageIds"
      :mode="props.mode"
      :state="state"
      :files="files"
      :selected-refs="props.modelValue"
      :is-read-only="props.isReadOnly"
      :is-mutating="isMutating"
      :open-menu-for-file-id="openMenuForFileId"
      :is-refreshing-results="isRefreshingResults"
      :can-load-more="canLoadMore"
      :is-loading="isLoading"
      @toggle-selected="onToggleSelected"
      @toggle-menu="toggleMenu"
      @close-menu="closeMenu"
      @download="onDownload"
      @delete="onDelete"
      @restore="onRestore"
      @load-more="void loadMore()"
    />
  </section>
</template>
