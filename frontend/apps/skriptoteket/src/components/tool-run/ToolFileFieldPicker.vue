<script setup lang="ts">
import { computed, ref } from "vue";

import UiSegmentedToggle, { type UiSegmentedToggleOption } from "../ui/UiSegmentedToggle.vue";
import VaultPickerModal from "../vault/VaultPickerModal.vue";

import type {
  FileFieldSelection,
  FileSelectionMode,
  ToolFileFieldSpec,
} from "../../composables/tools/useToolInputs";
import type { FileRefInfo } from "../../composables/tools/fileRefHelpers";
import { formatBytes, getFileRefSource } from "../../composables/tools/fileRefHelpers";

const props = withDefaults(defineProps<{
  fields: ToolFileFieldSpec[];
  selections: Record<string, FileFieldSelection>;
  acceptByField: Record<string, string | undefined>;
  errors: Record<string, string | null>;
  availableRefs: FileRefInfo[];
  density?: "default" | "compact";
  isReadOnly?: boolean;
}>(), {
  density: "default",
  isReadOnly: false,
});

const emit = defineEmits<{
  (event: "update:mode", payload: { field: string; mode: FileSelectionMode }): void;
  (event: "update:uploads", payload: { field: string; files: File[] }): void;
  (event: "update:refs", payload: { field: string; refs: string[] }): void;
  (event: "delete:refs", payload: { field: string; refs: string[] }): void;
}>();

const isCompact = computed(() => props.density === "compact");

const sortedRefs = computed(() => {
  return [...props.availableRefs].sort((a, b) => a.name.localeCompare(b.name, "sv"));
});

const activeVaultField = ref<ToolFileFieldSpec | null>(null);

function selectionFor(field: ToolFileFieldSpec): FileFieldSelection {
  return props.selections[field.name] ?? { mode: "upload", uploads: [], refs: [] };
}

function refsForField(field: ToolFileFieldSpec): FileRefInfo[] {
  return sortedRefs.value.filter((ref) => !ref.field || ref.field === field.name);
}

function sessionRefsForField(field: ToolFileFieldSpec): FileRefInfo[] {
  return refsForField(field).filter((ref) => getFileRefSource(ref.ref) === "session");
}

function vaultRefsSelected(field: ToolFileFieldSpec): string[] {
  return selectionFor(field).refs.filter((ref) => getFileRefSource(ref) === "vault");
}

function sessionRefsSelected(field: ToolFileFieldSpec): string[] {
  return selectionFor(field).refs.filter((ref) => getFileRefSource(ref) === "session");
}

function remainingVaultSlots(field: ToolFileFieldSpec): number {
  return Math.max(0, field.max - sessionRefsSelected(field).length);
}

function fileNameForRef(refValue: string): string {
  return props.availableRefs.find((ref) => ref.ref === refValue)?.name ?? refValue;
}

function countLabel(field: ToolFileFieldSpec): string {
  const selection = selectionFor(field);
  const count = selection.mode === "upload" ? selection.uploads.length : selection.refs.length;
  if (count === 0) return "Inga valda";
  return count === 1 ? "1 vald" : `${count} valda`;
}

function isFileSelectionMode(value: string): value is FileSelectionMode {
  return value === "upload" || value === "refs";
}

function onModeChange(field: ToolFileFieldSpec, mode: string): void {
  if (props.isReadOnly) return;
  if (!isFileSelectionMode(mode)) return;
  emit("update:mode", { field: field.name, mode });
}

function onFilesSelected(field: ToolFileFieldSpec, event: Event): void {
  if (!(event.target instanceof HTMLInputElement)) return;
  const { files } = event.target;
  if (!files) return;
  emit("update:uploads", { field: field.name, files: Array.from(files) });
}

function onToggleSessionRef(field: ToolFileFieldSpec, refValue: string, event: Event): void {
  if (props.isReadOnly) return;
  if (!(event.target instanceof HTMLInputElement)) return;
  const selection = selectionFor(field);
  const current = selection.refs ?? [];
  const next = event.target.checked
    ? Array.from(new Set([...current, refValue]))
    : current.filter((value) => value !== refValue);
  if (next.length > field.max) return;
  emit("update:refs", { field: field.name, refs: next });
}

function onSelectAllRefs(field: ToolFileFieldSpec): void {
  if (props.isReadOnly) return;
  const selection = selectionFor(field);
  const current = selection.refs ?? [];
  const refs = sessionRefsForField(field).map((ref) => ref.ref);
  const next = Array.from(new Set([...current, ...refs]));
  const limited = next.slice(0, Math.max(0, field.max));
  emit("update:refs", { field: field.name, refs: limited });
}

function onClearRefs(field: ToolFileFieldSpec): void {
  if (props.isReadOnly) return;
  emit("update:refs", { field: field.name, refs: [] });
}

function onDeleteSelectedRefs(field: ToolFileFieldSpec): void {
  if (props.isReadOnly) return;
  const selection = selectionFor(field);
  const deletable = selection.refs.filter((ref) => getFileRefSource(ref) === "session");
  if (deletable.length === 0) return;
  emit("delete:refs", { field: field.name, refs: deletable });
  const remaining = selection.refs.filter((ref) => !deletable.includes(ref));
  emit("update:refs", { field: field.name, refs: remaining });
}

function canDeleteSelected(field: ToolFileFieldSpec): boolean {
  if (props.isReadOnly) return false;
  return selectionFor(field).refs.some((ref) => getFileRefSource(ref) === "session");
}

function openVaultPicker(field: ToolFileFieldSpec): void {
  if (props.isReadOnly) return;
  activeVaultField.value = field;
}

function closeVaultPicker(): void {
  activeVaultField.value = null;
}

function onVaultPickerConfirm(selected: string[]): void {
  const field = activeVaultField.value;
  if (!field) return;

  const selection = selectionFor(field);
  const sessionSelected = selection.refs.filter((ref) => getFileRefSource(ref) === "session");
  const next = Array.from(new Set([...sessionSelected, ...selected]));
  emit("update:refs", { field: field.name, refs: next });
  closeVaultPicker();
}

function sourceLabel(ref: FileRefInfo): string {
  const source = getFileRefSource(ref.ref);
  if (source === "vault") return "Filvalv";
  if (source === "session") return "Session";
  return "Okänt";
}

function modeOptions(field: ToolFileFieldSpec): UiSegmentedToggleOption[] {
  return [
    { value: "upload", label: "Ladda upp" },
    { value: "refs", label: "Välj sparade" },
  ].map((opt) => ({
    ...opt,
    disabled: props.isReadOnly,
    title: field.label,
  }));
}

function modeSurfaceKey(field: ToolFileFieldSpec): string {
  return `${field.name}:${selectionFor(field).mode}`;
}
</script>

<template>
  <div>
    <div
      v-if="fields.length > 0"
      :class="[isCompact ? 'space-y-3' : 'space-y-4']"
    >
      <div
        v-for="field in fields"
        :key="field.name"
        :class="[
          isCompact
            ? 'panel-inset p-3 space-y-3'
            : 'border border-navy/20 bg-canvas/30 p-4 shadow-brutal-sm space-y-3',
        ]"
      >
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="space-y-1">
            <p
              :class="[
                'font-semibold uppercase tracking-wide',
                isCompact ? 'text-[10px] text-navy/60' : 'text-xs text-navy/70',
              ]"
            >
              {{ field.label }}
            </p>
            <p :class="[isCompact ? 'text-[10px] text-navy/50' : 'text-xs text-navy/60']">
              Min {{ field.min }} · Max {{ field.max }} · {{ countLabel(field) }}
            </p>
          </div>

          <UiSegmentedToggle
            :model-value="selectionFor(field).mode"
            :options="modeOptions(field)"
            :disabled="isReadOnly"
            :density="isCompact ? 'compact' : 'default'"
            aria-label="Välj filkälla"
            :columns="2"
            @update:model-value="onModeChange(field, $event)"
          />
        </div>

        <div class="tool-file-picker-mode-stage">
          <Transition name="tool-file-picker-mode-swap">
            <div
              :key="modeSurfaceKey(field)"
              class="tool-file-picker-mode-surface"
              :data-test="`tool-file-picker-mode-${selectionFor(field).mode}`"
            >
              <div v-if="selectionFor(field).mode === 'upload'">
                <label
                  :class="[
                    'group flex items-center gap-2 w-full border border-navy/30 bg-white px-2.5 py-1.5',
                    isCompact ? 'h-[28px]' : 'h-[36px]',
                    isReadOnly
                      ? 'opacity-60 cursor-not-allowed'
                      : 'cursor-pointer hover:bg-canvas/30 transition-colors',
                  ]"
                >
                  <span
                    :class="[
                      'shrink-0 font-semibold uppercase underline underline-offset-4 decoration-navy/30',
                      isCompact
                        ? 'text-[10px] tracking-[var(--huleedu-tracking-label)] text-navy/80'
                        : 'text-xs tracking-wide text-navy',
                      isReadOnly ? '' : 'group-hover:text-burgundy',
                    ]"
                  >
                    Välj filer
                  </span>
                  <span :class="[isCompact ? 'text-[11px] text-navy/60 truncate' : 'text-sm text-navy/60 truncate']">
                    {{
                      selectionFor(field).uploads.length > 0
                        ? `${selectionFor(field).uploads.length} fil(er) valda`
                        : "Inga filer valda"
                    }}
                  </span>
                  <input
                    type="file"
                    :multiple="field.max > 1"
                    :accept="acceptByField[field.name]"
                    class="sr-only"
                    :disabled="isReadOnly"
                    @change="onFilesSelected(field, $event)"
                  >
                </label>
              </div>

              <div v-else>
                <div :class="[isCompact ? 'space-y-2' : 'space-y-3']">
                  <div class="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      :disabled="isReadOnly"
                      :class="[
                        'btn-ghost border-navy/30 bg-canvas shadow-none',
                        isCompact
                          ? 'h-[26px] px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none'
                          : 'h-[30px] px-3 py-1 text-xs font-semibold tracking-wide',
                      ]"
                      @click="onSelectAllRefs(field)"
                    >
                      Markera alla
                    </button>
                    <button
                      type="button"
                      :disabled="isReadOnly"
                      :class="[
                        'btn-ghost border-navy/30 bg-white shadow-none',
                        isCompact
                          ? 'h-[26px] px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none'
                          : 'h-[30px] px-3 py-1 text-xs font-semibold tracking-wide',
                      ]"
                      @click="onClearRefs(field)"
                    >
                      Avmarkera
                    </button>
                    <button
                      type="button"
                      :disabled="!canDeleteSelected(field)"
                      :class="[
                        'btn-ghost border-burgundy/40 text-burgundy shadow-none',
                        isCompact
                          ? 'h-[26px] px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none'
                          : 'h-[30px] px-3 py-1 text-xs font-semibold tracking-wide',
                      ]"
                      @click="onDeleteSelectedRefs(field)"
                    >
                      Ta bort markerade
                    </button>
                  </div>

                  <div
                    v-if="sessionRefsForField(field).length > 0"
                    :class="[isCompact ? 'space-y-1' : 'space-y-2']"
                  >
                    <p :class="[isCompact ? 'text-[10px] font-semibold uppercase tracking-wide text-navy/60' : 'text-xs font-semibold uppercase tracking-wide text-navy/70']">
                      Session
                    </p>
                    <label
                      v-for="sessionRef in sessionRefsForField(field)"
                      :key="sessionRef.ref"
                      :class="[
                        'flex items-start gap-2 border border-navy/20 bg-white px-2.5 py-2',
                        isCompact ? 'text-[11px]' : 'text-sm',
                        isReadOnly ? 'opacity-60 pointer-events-none' : '',
                      ]"
                    >
                      <input
                        type="checkbox"
                        class="mt-0.5 accent-burgundy"
                        :checked="selectionFor(field).refs.includes(sessionRef.ref)"
                        :disabled="isReadOnly || (!selectionFor(field).refs.includes(sessionRef.ref) && selectionFor(field).refs.length >= field.max)"
                        @change="onToggleSessionRef(field, sessionRef.ref, $event)"
                      >
                      <span class="flex-1 min-w-0">
                        <span class="block font-mono text-navy truncate">{{ sessionRef.name }}</span>
                        <span
                          :class="[
                            'block text-navy/50',
                            isCompact ? 'text-[10px]' : 'text-xs',
                          ]"
                        >
                          {{ formatBytes(sessionRef.bytes) }} · {{ sourceLabel(sessionRef) }}
                          <span v-if="sessionRef.field">· fält: {{ sessionRef.field }}</span>
                        </span>
                      </span>
                    </label>
                  </div>

                  <div :class="[isCompact ? 'space-y-1.5' : 'space-y-2']">
                    <div class="flex items-center justify-between gap-3">
                      <p :class="[isCompact ? 'text-[10px] font-semibold uppercase tracking-wide text-navy/60' : 'text-xs font-semibold uppercase tracking-wide text-navy/70']">
                        Mina filer
                      </p>
                      <button
                        type="button"
                        class="btn-ghost border-navy/30 bg-canvas shadow-none"
                        :disabled="isReadOnly || remainingVaultSlots(field) === 0"
                        @click="openVaultPicker(field)"
                      >
                        Välj bland Mina filer
                      </button>
                    </div>

                    <div
                      v-if="vaultRefsSelected(field).length > 0"
                      class="space-y-1"
                    >
                      <div
                        v-for="refValue in vaultRefsSelected(field)"
                        :key="refValue"
                        class="flex items-center justify-between gap-3 border border-navy/20 bg-white px-2.5 py-2"
                      >
                        <span class="font-mono text-navy truncate text-sm">
                          {{ fileNameForRef(refValue) }}
                        </span>
                        <button
                          type="button"
                          class="btn-ghost h-[26px] px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-burgundy/40 text-burgundy bg-white leading-none"
                          :disabled="isReadOnly"
                          @click="emit('update:refs', { field: field.name, refs: selectionFor(field).refs.filter((value) => value !== refValue) })"
                        >
                          Ta bort
                        </button>
                      </div>
                    </div>
                    <p
                      v-else
                      :class="[isCompact ? 'text-[11px] text-navy/60' : 'text-xs text-navy/60']"
                    >
                      Inga valda filer från Mina filer.
                    </p>

                    <p
                      v-if="remainingVaultSlots(field) === 0"
                      :class="[isCompact ? 'text-[11px] text-navy/50' : 'text-xs text-navy/50']"
                    >
                      Avmarkera en sessionfil för att välja bland Mina filer.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </Transition>
        </div>

        <p
          v-if="errors[field.name]"
          :class="[isCompact ? 'text-[10px] font-semibold text-burgundy' : 'text-xs font-semibold text-burgundy']"
        >
          {{ errors[field.name] }}
        </p>
      </div>
    </div>

    <VaultPickerModal
      :is-open="activeVaultField !== null"
      :title="activeVaultField ? `Välj filer (${activeVaultField.label})` : 'Välj filer'"
      :selected-refs="activeVaultField ? vaultRefsSelected(activeVaultField) : []"
      :max-selected="activeVaultField ? remainingVaultSlots(activeVaultField) : 1"
      confirm-label="Välj"
      :is-read-only="isReadOnly"
      @close="closeVaultPicker"
      @confirm="onVaultPickerConfirm"
    />
  </div>
</template>

<style scoped>
.tool-file-picker-mode-stage {
  position: relative;
}

.tool-file-picker-mode-swap-enter-active,
.tool-file-picker-mode-swap-leave-active {
  transition: opacity var(--huleedu-duration-fast, 150ms) var(--huleedu-ease-default, ease);
}

.tool-file-picker-mode-swap-enter-from,
.tool-file-picker-mode-swap-leave-to {
  opacity: 0;
}

.tool-file-picker-mode-surface.tool-file-picker-mode-swap-leave-active {
  position: absolute;
  inset: 0;
  width: 100%;
  pointer-events: none;
}

@media (prefers-reduced-motion: reduce) {
  .tool-file-picker-mode-swap-enter-active,
  .tool-file-picker-mode-swap-leave-active {
    transition: none;
  }
}
</style>
