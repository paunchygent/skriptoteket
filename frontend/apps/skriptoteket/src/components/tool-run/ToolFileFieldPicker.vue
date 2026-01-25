<script setup lang="ts">
import { computed } from "vue";

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

function selectionFor(field: ToolFileFieldSpec): FileFieldSelection {
  return props.selections[field.name] ?? { mode: "upload", uploads: [], refs: [] };
}

function refsForField(field: ToolFileFieldSpec): FileRefInfo[] {
  return sortedRefs.value.filter((ref) => !ref.field || ref.field === field.name);
}

function countLabel(field: ToolFileFieldSpec): string {
  const selection = selectionFor(field);
  const count = selection.mode === "upload" ? selection.uploads.length : selection.refs.length;
  if (count === 0) return "Inga valda";
  return count === 1 ? "1 vald" : `${count} valda`;
}

function onModeChange(field: ToolFileFieldSpec, mode: FileSelectionMode): void {
  if (props.isReadOnly) return;
  emit("update:mode", { field: field.name, mode });
}

function onFilesSelected(field: ToolFileFieldSpec, event: Event): void {
  if (!(event.target instanceof HTMLInputElement)) return;
  const { files } = event.target;
  if (!files) return;
  emit("update:uploads", { field: field.name, files: Array.from(files) });
}

function onToggleRef(field: ToolFileFieldSpec, refValue: string, event: Event): void {
  if (props.isReadOnly) return;
  if (!(event.target instanceof HTMLInputElement)) return;
  const selection = selectionFor(field);
  const current = selection.refs ?? [];
  const next = event.target.checked
    ? Array.from(new Set([...current, refValue]))
    : current.filter((value) => value !== refValue);
  emit("update:refs", { field: field.name, refs: next });
}

function onSelectAllRefs(field: ToolFileFieldSpec): void {
  if (props.isReadOnly) return;
  const refs = refsForField(field).map((ref) => ref.ref);
  const limited = refs.slice(0, Math.max(0, field.max));
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

function sourceLabel(ref: FileRefInfo): string {
  const source = getFileRefSource(ref.ref);
  if (source === "vault") return "Valv";
  if (source === "session") return "Session";
  return "Okänt";
}
</script>

<template>
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

        <div
          :class="[
            'inline-flex overflow-hidden border border-navy/30 bg-white',
            isCompact ? 'rounded-sm' : 'rounded',
          ]"
          role="group"
          aria-label="Välj filkälla"
        >
          <button
            type="button"
            :disabled="isReadOnly"
            :class="[
              'btn-ghost border-0 shadow-none rounded-none active:translate-x-0 active:translate-y-0',
              isCompact
                ? 'h-[26px] px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none'
                : 'h-[32px] px-3 py-1 text-xs font-semibold tracking-wide',
              selectionFor(field).mode === 'upload'
                ? 'bg-canvas text-navy'
                : 'bg-white text-navy/60 hover:text-navy',
            ]"
            @click="onModeChange(field, 'upload')"
          >
            Ladda upp
          </button>
          <button
            type="button"
            :disabled="isReadOnly"
            :class="[
              'btn-ghost border-0 shadow-none rounded-none active:translate-x-0 active:translate-y-0 border-l border-navy/20',
              isCompact
                ? 'h-[26px] px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none'
                : 'h-[32px] px-3 py-1 text-xs font-semibold tracking-wide',
              selectionFor(field).mode === 'refs'
                ? 'bg-canvas text-navy'
                : 'bg-white text-navy/60 hover:text-navy',
            ]"
            @click="onModeChange(field, 'refs')"
          >
            Välj sparade
          </button>
        </div>
      </div>

      <div v-if="selectionFor(field).mode === 'upload'">
        <div
          :class="[
            'flex items-center gap-2 w-full border border-navy/30 bg-white px-2.5 py-1.5',
            isCompact ? 'h-[28px]' : 'h-[36px]',
          ]"
        >
          <label
            :class="[
              'btn-ghost shrink-0',
              isCompact
                ? 'h-[26px] px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none'
                : 'px-3 py-1 text-xs font-semibold tracking-wide',
              { 'opacity-60 pointer-events-none': isReadOnly },
            ]"
          >
            Välj filer
            <input
              type="file"
              :multiple="field.max > 1"
              :accept="acceptByField[field.name]"
              class="sr-only"
              :disabled="isReadOnly"
              @change="onFilesSelected(field, $event)"
            >
          </label>
          <span :class="[isCompact ? 'text-[11px] text-navy/60 truncate' : 'text-sm text-navy/60 truncate']">
            {{
              selectionFor(field).uploads.length > 0
                ? `${selectionFor(field).uploads.length} fil(er) valda`
                : "Inga filer valda"
            }}
          </span>
        </div>
      </div>

      <div v-else>
        <div
          v-if="refsForField(field).length > 0"
          :class="[isCompact ? 'space-y-1' : 'space-y-2']"
        >
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
          <label
            v-for="ref in refsForField(field)"
            :key="ref.ref"
            :class="[
              'flex items-start gap-2 border border-navy/20 bg-white px-2.5 py-2',
              isCompact ? 'text-[11px]' : 'text-sm',
              isReadOnly ? 'opacity-60 pointer-events-none' : '',
            ]"
          >
            <input
              type="checkbox"
              class="mt-0.5 accent-burgundy"
              :checked="selectionFor(field).refs.includes(ref.ref)"
              :disabled="isReadOnly"
              @change="onToggleRef(field, ref.ref, $event)"
            >
            <span class="flex-1 min-w-0">
              <span class="block font-mono text-navy truncate">{{ ref.name }}</span>
              <span
                :class="[
                  'block text-navy/50',
                  isCompact ? 'text-[10px]' : 'text-xs',
                ]"
              >
                {{ formatBytes(ref.bytes) }} · {{ sourceLabel(ref) }}
                <span v-if="ref.field">· fält: {{ ref.field }}</span>
              </span>
            </span>
          </label>
        </div>
        <p
          v-else
          :class="[isCompact ? 'text-[11px] text-navy/60' : 'text-xs text-navy/60']"
        >
          Inga sparade filer.
        </p>
      </div>

      <p
        v-if="errors[field.name]"
        :class="[isCompact ? 'text-[10px] font-semibold text-burgundy' : 'text-xs font-semibold text-burgundy']"
      >
        {{ errors[field.name] }}
      </p>
    </div>
  </div>
</template>
