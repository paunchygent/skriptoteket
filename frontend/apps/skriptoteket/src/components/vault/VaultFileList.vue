<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";
import { formatBytes } from "../../composables/tools/fileRefHelpers";
import { IconDownload, IconMoreVertical, IconTrash, IconUndo } from "../icons";

type VaultFileInfo = components["schemas"]["VaultFileInfo"];
type VaultListState = components["schemas"]["VaultListState"];

const props = defineProps<{
  mode: "manage" | "picker";
  state: VaultListState;
  files: VaultFileInfo[];
  selectedRefs: string[];
  selectedManageIds: string[];
  isReadOnly: boolean;
  isMutating: boolean;
  openMenuForFileId: string | null;
  isRefreshingResults: boolean;
  canLoadMore: boolean;
  isLoading: boolean;
}>();

const emit = defineEmits<{
  "update:selectedManageIds": [value: string[]];
  "toggle-selected": [refValue: string, checked: boolean];
  "toggle-menu": [fileId: string];
  "close-menu": [];
  download: [file: VaultFileInfo];
  delete: [fileId: string];
  restore: [fileId: string];
  "load-more": [];
}>();

const isPickerMode = computed(() => props.mode === "picker");
const isManageMode = computed(() => props.mode === "manage");
const selectionDisabled = computed(() => props.isReadOnly || !isPickerMode.value || props.state !== "active");
const manageSelectionDisabled = computed(() => props.isReadOnly);
const manageSelection = computed({
  get: () => props.selectedManageIds,
  set: (value: string[]) => emit("update:selectedManageIds", value),
});

function onToggleSelectedEvent(event: Event, refValue: string): void {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) return;
  emit("toggle-selected", refValue, target.checked);
}

function savedExports(file: VaultFileInfo): VaultFileInfo[] {
  return file.exports ?? [];
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
}
</script>

<template>
  <div
    class="space-y-2"
    :class="{ 'opacity-70 pointer-events-none': isRefreshingResults }"
    :aria-busy="isRefreshingResults ? 'true' : 'false'"
  >
    <ul class="space-y-2">
      <li
        v-for="file in files"
        :key="file.id"
        class="border border-navy/20 bg-panel hover:bg-action/5 transition-colors"
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
              class="h-4 w-4 border border-navy/40 bg-white shadow-none accent-action"
              :aria-label="file.name"
              :checked="selectedRefs.includes(file.ref)"
              :disabled="selectionDisabled || file.is_missing_on_disk"
              @change="onToggleSelectedEvent($event, file.ref)"
            >
            <input
              v-else
              :id="`vault-file-select-${file.id}`"
              v-model="manageSelection"
              type="checkbox"
              :value="file.id"
              class="h-4 w-4 border border-navy/40 bg-white shadow-none accent-action"
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
                  class="font-semibold text-critical"
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
                class="mt-1 text-[11px] text-critical"
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
                class="font-semibold text-critical"
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
              class="h-[30px] w-[30px] grid place-items-center bg-transparent text-navy/70 hover:bg-canvas/50 hover:text-navy shadow-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-action/40 focus-visible:outline-offset-2"
              :disabled="isMutating"
              :aria-expanded="openMenuForFileId === file.id"
              :aria-controls="`vault-file-actions-${file.id}`"
              aria-label="Filåtgärder"
              @click.stop="emit('toggle-menu', file.id)"
            >
              <IconMoreVertical :size="16" />
            </button>

            <Transition name="popover">
              <div
                v-if="openMenuForFileId === file.id"
                :id="`vault-file-actions-${file.id}`"
                class="absolute right-0 mt-2 w-48 border border-navy bg-modal shadow-md z-50"
                role="menu"
                aria-label="Filåtgärder"
                @click.stop
              >
                <button
                  type="button"
                  class="flex items-center gap-2 w-full px-3 py-2 text-sm text-navy hover:bg-canvas transition-colors"
                  role="menuitem"
                  :disabled="isMutating || file.is_missing_on_disk"
                  @click="emit('close-menu'); emit('download', file);"
                >
                  <IconDownload :size="16" />
                  Ladda ned
                </button>

                <button
                  v-if="state === 'active'"
                  type="button"
                  class="flex items-center gap-2 w-full px-3 py-2 text-sm text-critical hover:bg-canvas transition-colors"
                  role="menuitem"
                  :disabled="isMutating"
                  @click="emit('delete', file.id); emit('close-menu');"
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
                  @click="emit('restore', file.id); emit('close-menu');"
                >
                  <IconUndo :size="16" />
                  Återställ
                </button>
              </div>
            </Transition>
          </div>
        </div>

        <ul
          v-if="isManageMode && savedExports(file).length > 0"
          class="border-t border-navy/10 px-3 pb-3 pt-2 space-y-1"
          aria-label="Sparade exporter"
        >
          <li
            v-for="exportFile in savedExports(file)"
            :key="exportFile.id"
            class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1"
          >
            <span class="min-w-0 truncate font-mono text-[11px] text-navy/80">
              {{ exportFile.name }}
            </span>
            <span class="flex items-center gap-2 text-[11px] text-navy/60">
              <span>{{ formatBytes(exportFile.bytes) }}</span>
              <span
                v-if="exportFile.is_missing_on_disk"
                class="font-semibold text-critical"
              >Saknas på servern</span>
              <button
                v-if="!props.isReadOnly"
                type="button"
                class="btn-ghost h-[26px] px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none border-navy/30 bg-panel shadow-none"
                :disabled="isMutating || exportFile.is_missing_on_disk"
                :aria-label="`Ladda ned ${exportFile.name}`"
                @click.stop="emit('download', exportFile)"
              >
                <IconDownload :size="14" />
                Ladda ned
              </button>
            </span>
          </li>
        </ul>
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
        @click="emit('load-more')"
      >
        Ladda fler
      </button>
    </div>
  </div>
</template>
