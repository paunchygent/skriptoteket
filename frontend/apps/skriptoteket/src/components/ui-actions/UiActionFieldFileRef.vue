<script setup lang="ts">
import { computed, ref } from "vue";

import type { components } from "../../api/openapi";
import type { FileRefInfo, FileRefSource } from "../../composables/tools/fileRefHelpers";
import {
  filterFileRefsBySources,
  formatBytes,
  getFileRefSource,
} from "../../composables/tools/fileRefHelpers";
import VaultPickerModal from "../vault/VaultPickerModal.vue";

type UiFileRefField = components["schemas"]["UiFileRefField"];

const props = withDefaults(defineProps<{
  field: UiFileRefField;
  modelValue: string[];
  availableFileRefs: FileRefInfo[];
  density?: "default" | "compact";
  errorMessage?: string | null;
  sourcesOverride?: FileRefSource[] | null;
  isReadOnly?: boolean;
}>(), {
  density: "default",
  errorMessage: null,
  sourcesOverride: null,
  isReadOnly: false,
});

const emit = defineEmits<{ "update:modelValue": [value: string[]] }>();

const isCompact = computed(() => props.density === "compact");
const isVaultPickerOpen = ref(false);

const allowedSources = computed<FileRefSource[] | null>(() => {
  if (props.sourcesOverride && props.sourcesOverride.length > 0) {
    return props.sourcesOverride;
  }
  if (props.field.sources && props.field.sources.length > 0) {
    return props.field.sources;
  }
  return null;
});

const effectiveSources = computed<FileRefSource[]>(() => {
  return allowedSources.value ?? ["session", "vault"];
});

const sessionRefs = computed(() => {
  if (!effectiveSources.value.includes("session")) return [];
  const refs = filterFileRefsBySources(props.availableFileRefs, ["session"]);
  return [...refs].sort((a, b) => a.name.localeCompare(b.name, "sv"));
});

const selectedSessionRefs = computed(() => {
  if (!effectiveSources.value.includes("session")) return [];
  return (props.modelValue ?? []).filter((ref) => getFileRefSource(ref) === "session");
});

const selectedVaultRefs = computed(() => {
  if (!effectiveSources.value.includes("vault")) return [];
  return (props.modelValue ?? []).filter((ref) => getFileRefSource(ref) === "vault");
});

const remainingVaultSlots = computed(() => {
  return Math.max(0, props.field.max - selectedSessionRefs.value.length);
});

function fileNameForRef(refValue: string): string {
  return props.availableFileRefs.find((ref) => ref.ref === refValue)?.name ?? refValue;
}

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

function isAtMax(refValue: string): boolean {
  const selected = props.modelValue ?? [];
  if (selected.includes(refValue)) return false;
  return selected.length >= props.field.max;
}

function openVaultPicker(): void {
  if (props.isReadOnly) return;
  if (!effectiveSources.value.includes("vault")) return;
  if (remainingVaultSlots.value === 0) return;
  isVaultPickerOpen.value = true;
}

function closeVaultPicker(): void {
  isVaultPickerOpen.value = false;
}

function removeVaultRef(refValue: string): void {
  const current = props.modelValue ?? [];
  emit("update:modelValue", current.filter((value) => value !== refValue));
}

function onVaultConfirm(selected: string[]): void {
  const sessionSelected = selectedSessionRefs.value;
  const next = Array.from(new Set([...sessionSelected, ...selected]));
  emit("update:modelValue", next);
  closeVaultPicker();
}

function sourceLabel(ref: FileRefInfo): string {
  const source = getFileRefSource(ref.ref);
  if (source === "vault") return "Filvalv";
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

    <div :class="[isCompact ? 'space-y-2' : 'space-y-3']">
      <div
        v-if="effectiveSources.includes('vault')"
        :class="[isCompact ? 'space-y-1.5' : 'space-y-2']"
      >
        <div class="flex items-center justify-between gap-3">
          <p :class="[isCompact ? 'text-[10px] font-semibold uppercase tracking-wide text-navy/60' : 'text-xs font-semibold uppercase tracking-wide text-navy/70']">
            Mina filer
          </p>
          <button
            type="button"
            class="btn-ghost border-navy/30 bg-canvas shadow-none"
            :disabled="isReadOnly || remainingVaultSlots === 0"
            @click="openVaultPicker"
          >
            Välj bland Mina filer
          </button>
        </div>

        <div
          v-if="selectedVaultRefs.length > 0"
          class="space-y-1"
        >
          <div
            v-for="refValue in selectedVaultRefs"
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
              @click="removeVaultRef(refValue)"
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
          v-if="remainingVaultSlots === 0"
          :class="[isCompact ? 'text-[11px] text-navy/50' : 'text-xs text-navy/50']"
        >
          Avmarkera en sessionfil för att välja bland Mina filer.
        </p>
      </div>

      <div
        v-if="effectiveSources.includes('session')"
        :class="[isCompact ? 'space-y-1' : 'space-y-2']"
      >
        <p :class="[isCompact ? 'text-[10px] font-semibold uppercase tracking-wide text-navy/60' : 'text-xs font-semibold uppercase tracking-wide text-navy/70']">
          Session
        </p>

        <div
          v-if="sessionRefs.length > 0"
          :class="[isCompact ? 'space-y-1' : 'space-y-2']"
        >
          <label
            v-for="sessionRef in sessionRefs"
            :key="sessionRef.ref"
            :class="[
              'flex items-start gap-2 border border-navy/20 bg-white px-2.5 py-2',
              isCompact ? 'text-[11px]' : 'text-sm',
            ]"
          >
            <input
              type="checkbox"
              class="mt-0.5 accent-burgundy"
              :checked="modelValue.includes(sessionRef.ref)"
              :disabled="isReadOnly || isAtMax(sessionRef.ref)"
              @change="onToggleEvent($event, sessionRef.ref)"
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

        <p
          v-else
          :class="[isCompact ? 'text-[11px] text-navy/60' : 'text-xs text-navy/60']"
        >
          Inga sessionfiler tillgängliga.
        </p>
      </div>
    </div>

    <p
      v-if="errorMessage"
      :class="[isCompact ? 'text-[10px] font-semibold text-burgundy' : 'text-xs font-semibold text-burgundy']"
    >
      {{ errorMessage }}
    </p>

    <VaultPickerModal
      :is-open="isVaultPickerOpen"
      :title="`Välj filer (${field.label})`"
      :selected-refs="selectedVaultRefs"
      :max-selected="remainingVaultSlots"
      confirm-label="Välj"
      :is-read-only="isReadOnly"
      @close="closeVaultPicker"
      @confirm="onVaultConfirm"
    />
  </div>
</template>
