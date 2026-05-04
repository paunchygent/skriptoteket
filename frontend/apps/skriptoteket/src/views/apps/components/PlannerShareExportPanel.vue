<script setup lang="ts">
/**
 * Combined Klassrumskartan distribution surface.
 *
 * Relationships: replaces adjacent export/share toolbar controls and emits
 * separate intents to the existing share and export flow composables.
 */

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { Copy } from "lucide-vue-next";

import { IconArrow, IconCheck, IconDownload, IconLink2, IconPlus, IconTrash, IconX } from "../../../components/icons";
import { UiDenseActionButton, UiDenseSpinner } from "../../../components/ui";
import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";
import type {
  PlannerExportFileOption,
  PlannerExportOptionValue,
  PlannerShareExportScopeOption,
} from "./plannerShareExportActions";
const props = withDefaults(
  defineProps<{
    fileOptions?: PlannerExportFileOption[];
    shares?: ClassroomPlannerShareArtifact[];
    revokingShareId?: string | null;
    shareLoading?: boolean;
    shareBusy?: boolean;
    shareStatusLabel?: string | null;
    shareErrorMessage?: string | null;
    exportBusy?: boolean;
    exportErrorMessage?: string | null;
    showFileActions?: boolean;
    showShareActions?: boolean;
    showRevokeAction?: boolean;
    triggerTestId?: string;
    panelTestId?: string;
    createShareTestId?: string;
    createShareMobileTestId?: string;
    fileOptionTestIdPrefix?: string;
    triggerVariant?: "toolbar" | "phone-row";
    triggerMeta?: string | null;
    scopeValue?: string | null;
    scopeOptions?: PlannerShareExportScopeOption[];
  }>(),
  {
    fileOptions: () => [],
    shares: () => [],
    revokingShareId: null,
    shareLoading: false,
    shareBusy: false,
    shareStatusLabel: null,
    shareErrorMessage: null,
    exportBusy: false,
    exportErrorMessage: null,
    showFileActions: true,
    showShareActions: true,
    showRevokeAction: true,
    triggerTestId: "planner-share-export-trigger",
    panelTestId: "planner-share-export-panel",
    createShareTestId: "planner-share-create",
    createShareMobileTestId: "planner-share-create-mobile",
    fileOptionTestIdPrefix: "planner-share-export-file",
    triggerVariant: "toolbar",
    triggerMeta: null,
    scopeValue: null,
    scopeOptions: () => [],
  },
);
const emit = defineEmits<{
  (e: "open"): void;
  (e: "select-scope", value: string): void;
  (e: "create-share"): void;
  (e: "copy-share", share: ClassroomPlannerShareArtifact): void;
  (e: "revoke-share", share: ClassroomPlannerShareArtifact): void;
  (e: "export-default"): void;
  (e: "export-option", option: PlannerExportOptionValue): void;
}>();

const rootRef = ref<HTMLElement | null>(null);
const createButtonRef = ref<InstanceType<typeof UiDenseActionButton> | null>(null);
const isOpen = ref(false);
const dateFormatter = new Intl.DateTimeFormat("sv-SE", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

const activeShares = computed(() => props.shares.filter((share) => !share.revoked_at));
const activeShareCount = computed(() => activeShares.value.length);
const defaultFileOption = computed(() => {
  return props.fileOptions.find((option) => option.isDefault) ?? props.fileOptions[0] ?? null;
});

function formatDate(value: string): string {
  return dateFormatter.format(new Date(value));
}
function formatActiveMeta(share: ClassroomPlannerShareArtifact): string {
  return `Skapad ${formatDate(share.created_at)}`;
}
function closePanel(): void {
  isOpen.value = false;
}
function togglePanel(): void {
  const nextOpen = !isOpen.value;
  isOpen.value = nextOpen;
  if (nextOpen) {
    emit("open");
  }
}

function selectScope(option: PlannerShareExportScopeOption): void {
  if (option.disabled) {
    return;
  }
  emit("select-scope", option.value);
}

function createShare(): void {
  emit("create-share");
}
function selectFileOption(option: PlannerExportFileOption): void {
  if (props.exportBusy) {
    return;
  }
  if (option.id === defaultFileOption.value?.id) {
    emit("export-default");
    return;
  }
  emit("export-option", option.option);
}
function handleDocumentPointerDown(event: PointerEvent): void {
  if (!isOpen.value) {
    return;
  }
  const target = event.target;
  if (!(target instanceof Node)) {
    return;
  }
  if (rootRef.value?.contains(target)) {
    return;
  }
  closePanel();
}

function handleEscape(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    closePanel();
  }
}

watch(isOpen, async (open) => {
  if (!open) {
    return;
  }
  await nextTick();
  createButtonRef.value?.focus();
});

onMounted(() => {
  document.addEventListener("pointerdown", handleDocumentPointerDown);
  document.addEventListener("keydown", handleEscape);
});

onUnmounted(() => {
  document.removeEventListener("pointerdown", handleDocumentPointerDown);
  document.removeEventListener("keydown", handleEscape);
});
</script>

<template>
  <div
    ref="rootRef"
    :class="[
      'relative flex items-stretch',
      triggerVariant === 'toolbar' ? 'border-l border-navy/15 pl-3' : 'w-full',
    ]"
    data-test="planner-share-export-management"
  >
    <UiDenseActionButton
      v-if="triggerVariant === 'toolbar'"
      label="Dela"
      :data-test="triggerTestId"
      :expanded="isOpen"
      has-popup="dialog"
      @click="togglePanel"
    >
      <template #leading>
        <IconLink2 :size="14" />
      </template>
      <template #trailing>
        <IconArrow
          :size="12"
          direction="down"
        />
      </template>
    </UiDenseActionButton>
    <button
      v-else
      type="button"
      class="planner-phone-row-action w-full"
      :data-test="triggerTestId"
      :disabled="!showFileActions && !showShareActions"
      :aria-expanded="isOpen"
      aria-haspopup="dialog"
      @click="togglePanel"
    >
      <span class="inline-flex items-center gap-2">
        <IconLink2 :size="15" />
        Dela
      </span>
      <span class="text-xs text-navy/55">{{ triggerMeta ?? "Länk + filer" }}</span>
    </button>

    <section
      v-if="isOpen"
      class="fixed inset-x-0 bottom-0 z-[40] max-h-[85vh] overflow-y-auto rounded-t-xl border-t-2 border-navy bg-white pb-[env(safe-area-inset-bottom)] md:absolute md:inset-x-auto md:bottom-auto md:right-0 md:top-[calc(100%+0.375rem)] md:z-[50] md:w-[34rem] md:overflow-visible md:rounded-none md:border md:border-navy md:pb-0 md:shadow-brutal-sm"
      role="dialog"
      aria-label="Dela och exportera"
      :data-test="panelTestId"
    >
      <div
        class="flex justify-center px-3 pb-1 pt-2 md:hidden"
        aria-hidden="true"
      >
        <span class="h-1 w-9 rounded-full bg-navy/20" />
      </div>

      <header class="flex items-start justify-between gap-3 border-b border-navy/15 px-3.5 pb-3 pt-2 md:grid md:grid-cols-[minmax(0,1fr)_auto] md:items-start md:px-4 md:pt-3.5">
        <div>
          <h2 class="text-sm font-semibold leading-tight text-navy">
            Dela och exportera
          </h2>
          <p class="mt-1 text-[11px] leading-snug text-navy/60">
            Skapa länk eller spara en fil från det aktuella utkastet.
          </p>
        </div>
        <button
          type="button"
          class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[4px] border border-navy/20 bg-transparent text-navy/55 md:hidden"
          aria-label="Stäng dela och exportera"
          data-test="planner-share-export-close"
          @click="closePanel"
        >
          <IconX :size="14" />
        </button>
      </header>

      <section
        v-if="scopeOptions.length > 0"
        class="border-b border-navy/15 px-3.5 py-3 md:px-4"
        aria-label="Välj vad som ska delas"
      >
        <p class="mb-2 text-[11px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)] text-navy/65">
          Välj innehåll
        </p>
        <div class="grid gap-1.5">
          <button
            v-for="option in scopeOptions"
            :key="option.value"
            type="button"
            class="grid min-h-10 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 rounded-[4px] border px-2.5 text-left text-navy transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            :class="option.value === scopeValue ? 'border-navy/35 bg-canvas' : 'border-navy/20 bg-white hover:border-navy/35 hover:bg-canvas/70'"
            :disabled="option.disabled"
            :title="option.disabledReason ?? undefined"
            :aria-pressed="option.value === scopeValue"
            :data-test="`planner-share-export-scope-${option.value}`"
            @click="selectScope(option)"
          >
            <IconCheck
              v-if="option.value === scopeValue"
              :size="13"
            />
            <span
              v-else
              class="h-[13px] w-[13px]"
              aria-hidden="true"
            />
            <span class="truncate text-[11px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)]">
              {{ option.label }}
            </span>
            <span
              v-if="option.meta"
              class="truncate text-[10px] font-semibold leading-none"
              :class="option.value === scopeValue ? 'text-navy/60' : 'text-navy/50'"
            >
              {{ option.meta }}
            </span>
          </button>
        </div>
      </section>

      <section
        v-if="showShareActions"
        class="border-b border-navy/15"
        aria-labelledby="planner-share-export-link-heading"
      >
        <div class="grid gap-3 px-3.5 py-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-start md:px-4">
          <div>
            <h3
              id="planner-share-export-link-heading"
              class="text-[11px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)] text-navy/65"
            >
              Länk
            </h3>
            <p class="mt-1 text-[11px] leading-snug text-navy/60">
              Aktiva länkar visas här. Återkallade länkar tas bort från listan.
            </p>
          </div>
          <div class="hidden md:block">
            <UiDenseActionButton
              ref="createButtonRef"
              label="Skapa länk"
              :disabled="shareBusy"
              :busy="shareBusy"
              busy-label="Skapar länk"
              tone="primary"
              class="min-w-[8.5rem]"
              :data-test="createShareTestId"
              @click="createShare"
            >
              <template #leading>
                <IconPlus :size="10" />
              </template>
            </UiDenseActionButton>
          </div>
        </div>

        <div class="border-t border-navy/10 px-3.5 py-2 md:hidden">
          <button
            type="button"
            class="inline-flex h-10 w-full items-center justify-center gap-2 rounded-[4px] border border-navy bg-navy px-3 text-[11px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)] text-canvas disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="shareBusy"
            :data-test="createShareMobileTestId"
            :aria-busy="shareBusy ? 'true' : undefined"
            :aria-label="shareBusy ? 'Skapar länk' : undefined"
            @click="createShare"
          >
            <UiDenseSpinner
              v-if="shareBusy"
              :size="12"
            />
            <IconPlus
              v-else
              :size="12"
            />
            Skapa länk
          </button>
        </div>

        <p
          v-if="shareStatusLabel"
          class="border-t border-navy/10 px-3.5 py-2 text-[11px] font-semibold text-navy/65"
          data-test="planner-share-status"
        >
          {{ shareStatusLabel }}
        </p>
        <p
          v-if="shareErrorMessage"
          class="border-t border-burgundy/20 bg-burgundy/5 px-3.5 py-2 text-[11px] font-semibold text-burgundy"
          data-test="planner-share-error"
        >
          {{ shareErrorMessage }}
        </p>

        <p
          v-if="shareLoading && activeShareCount === 0"
          class="px-3.5 py-3 text-sm font-semibold text-navy/65"
        >
          Hämtar länkar…
        </p>
        <p
          v-else-if="activeShareCount === 0"
          class="px-3.5 py-3 text-sm text-navy/65"
          data-test="planner-share-links-empty"
        >
          Inga aktiva delade länkar för det här utkastet.
        </p>

        <ul
          v-else
          class="divide-y divide-navy/10"
        >
          <li
            v-for="share in activeShares"
            :key="share.id"
            class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-3.5 py-3"
            :data-test="`planner-share-link-${share.id}`"
          >
            <div class="min-w-0">
              <p class="truncate text-sm font-semibold leading-tight text-navy">
                {{ share.title }}
              </p>
              <p class="mt-0.5 truncate font-mono text-[10px] text-navy/50">
                {{ formatActiveMeta(share) }}
              </p>
            </div>
            <div class="flex min-w-max items-center justify-end gap-1.5">
              <button
                type="button"
                class="inline-flex h-8 w-8 items-center justify-center rounded-[4px] border border-navy/20 bg-white text-navy transition-colors hover:border-navy/35 hover:bg-navy/5 disabled:cursor-not-allowed disabled:opacity-40 md:h-[26px] md:w-auto md:gap-1 md:px-2 md:text-[10px] md:font-semibold md:uppercase md:tracking-[var(--huleedu-tracking-label)]"
                :disabled="!share.public_url"
                :data-test="`planner-share-copy-${share.id}`"
                title="Kopiera länk till urklipp"
                @click="emit('copy-share', share)"
              >
                <Copy
                  :size="12"
                  :stroke-width="2.25"
                  aria-hidden="true"
                />
                <span class="sr-only md:not-sr-only">Kopiera</span>
              </button>
              <button
                v-if="showRevokeAction"
                type="button"
                class="inline-flex h-8 w-8 items-center justify-center rounded-[4px] border border-burgundy/30 bg-white text-burgundy transition-colors hover:bg-burgundy/5 disabled:cursor-not-allowed disabled:opacity-40 md:h-[26px] md:w-auto md:gap-1 md:px-2 md:text-[10px] md:font-semibold md:uppercase md:tracking-[var(--huleedu-tracking-label)]"
                :disabled="revokingShareId === share.id"
                :data-test="`planner-share-revoke-${share.id}`"
                title="Återkalla länken"
                :aria-busy="revokingShareId === share.id ? 'true' : undefined"
                :aria-label="revokingShareId === share.id ? 'Återkallar länken' : undefined"
                @click="emit('revoke-share', share)"
              >
                <UiDenseSpinner
                  v-if="revokingShareId === share.id"
                  :size="12"
                />
                <IconTrash
                  v-else
                  :size="12"
                />
                <span class="sr-only md:not-sr-only">
                  Återkalla
                </span>
              </button>
            </div>
          </li>
        </ul>
      </section>

      <section
        v-if="showFileActions && fileOptions.length > 0"
        class="px-3.5 py-3 md:px-4"
        aria-labelledby="planner-share-export-files-heading"
      >
        <div class="mb-2">
          <h3
            id="planner-share-export-files-heading"
            class="text-[11px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)] text-navy/65"
          >
            Filer
          </h3>
          <p class="mt-1 text-[11px] leading-snug text-navy/60">
            Filer sparas i Mina filer.
          </p>
        </div>

        <p
          v-if="exportErrorMessage"
          class="mb-2 border border-burgundy/20 bg-burgundy/5 px-2 py-1.5 text-[11px] font-semibold text-burgundy"
          data-test="planner-export-error"
        >
          {{ exportErrorMessage }}
        </p>

        <div class="grid gap-1.5">
          <button
            v-for="option in fileOptions"
            :key="option.id"
            type="button"
            class="grid h-10 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 rounded-[4px] border border-navy/20 bg-white px-2.5 text-left text-navy transition-colors hover:border-navy/35 hover:bg-canvas/70 disabled:cursor-not-allowed disabled:opacity-55"
            :disabled="exportBusy"
            :data-test="`${fileOptionTestIdPrefix}-${option.id}`"
            :aria-busy="exportBusy && option.id === defaultFileOption?.id ? 'true' : undefined"
            @click="selectFileOption(option)"
          >
            <UiDenseSpinner
              v-if="exportBusy && option.id === defaultFileOption?.id"
              :size="12"
            />
            <IconDownload
              v-else
              :size="13"
            />
            <span class="truncate text-[11px] font-semibold leading-none">
              {{ option.label }}
            </span>
            <span
              v-if="option.isDefault"
              class="text-[10px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)] text-navy/50"
            >
              Standard
            </span>
          </button>
        </div>
      </section>
    </section>
  </div>
</template>
