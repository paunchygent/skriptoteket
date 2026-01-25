<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";
import type { FileRefInfo, FileRefSource } from "../../composables/tools/fileRefHelpers";
import {
  filterFileRefsBySources,
  formatBytes,
  getFileRefSource,
} from "../../composables/tools/fileRefHelpers";

type UiFileRefField = components["schemas"]["UiFileRefField"];

const props = defineProps<{
  field: UiFileRefField;
  modelValue: string[];
  availableFileRefs: FileRefInfo[];
  density?: "default" | "compact";
  errorMessage?: string | null;
  sourcesOverride?: FileRefSource[] | null;
}>();

const emit = defineEmits<{ "update:modelValue": [value: string[]] }>();

const isCompact = computed(() => props.density === "compact");

const allowedSources = computed<FileRefSource[] | null>(() => {
  if (props.sourcesOverride && props.sourcesOverride.length > 0) {
    return props.sourcesOverride;
  }
  if (props.field.sources && props.field.sources.length > 0) {
    return props.field.sources;
  }
  return null;
});

const filteredRefs = computed(() => {
  const refs = filterFileRefsBySources(props.availableFileRefs, allowedSources.value);
  return [...refs].sort((a, b) => a.name.localeCompare(b.name, "sv"));
});

function onToggle(refValue: string, checked: boolean): void {
  const current = props.modelValue ?? [];
  const next = checked
    ? Array.from(new Set([...current, refValue]))
    : current.filter((value) => value !== refValue);
  emit("update:modelValue", next);
}

function onToggleEvent(event: Event, refValue: string): void {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) return;
  onToggle(refValue, target.checked);
}

function sourceLabel(ref: FileRefInfo): string {
  const source = getFileRefSource(ref.ref);
  if (source === "vault") return "Valv";
  if (source === "session") return "Session";
  return "Okänt";
}
</script>

<template>
  <div :class="[isCompact ? 'space-y-1.5' : 'space-y-2']">
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
        Min {{ field.min }} · Max {{ field.max }}
      </p>
    </div>

    <div
      v-if="filteredRefs.length > 0"
      :class="[isCompact ? 'space-y-1' : 'space-y-2']"
    >
      <label
        v-for="ref in filteredRefs"
        :key="ref.ref"
        :class="[
          'flex items-start gap-2 border border-navy/20 bg-white px-2.5 py-2',
          isCompact ? 'text-[11px]' : 'text-sm',
        ]"
      >
        <input
          type="checkbox"
          class="mt-0.5 accent-burgundy"
          :checked="modelValue.includes(ref.ref)"
          @change="onToggleEvent($event, ref.ref)"
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
      Inga filer tillgängliga.
    </p>

    <p
      v-if="errorMessage"
      :class="[isCompact ? 'text-[10px] font-semibold text-burgundy' : 'text-xs font-semibold text-burgundy']"
    >
      {{ errorMessage }}
    </p>
  </div>
</template>
