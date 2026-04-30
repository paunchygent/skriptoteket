<script setup lang="ts">
/**
 * Owned Klassrumskartan share-link management surface.
 *
 * Relationships:
 * - receives owner-scoped share metadata from the authenticated route shell
 *   or the current browser-owned public guest share from the public route
 * - owns the Dela trigger, desktop popover, and mobile bottom-sheet shell
 * - emits create/copy/revoke intents back to the share-flow composable
 */

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { Copy } from "lucide-vue-next";

import { IconLink2, IconPlus, IconTrash, IconX } from "../../../components/icons";
import { UiDenseActionButton } from "../../../components/ui";
import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";

const props = withDefaults(
  defineProps<{
    shares?: ClassroomPlannerShareArtifact[];
    revokingShareId?: string | null;
    loading?: boolean;
    busy?: boolean;
    statusLabel?: string | null;
    errorMessage?: string | null;
    showRevokeAction?: boolean;
    triggerTestId?: string;
    panelTestId?: string;
  }>(),
  {
    shares: () => [],
    revokingShareId: null,
    loading: false,
    busy: false,
    statusLabel: null,
    errorMessage: null,
    showRevokeAction: true,
    triggerTestId: "planner-share-links-trigger",
    panelTestId: "planner-share-links-panel",
  },
);

const emit = defineEmits<{
  (e: "create-share"): void;
  (e: "copy-share", share: ClassroomPlannerShareArtifact): void;
  (e: "revoke-share", share: ClassroomPlannerShareArtifact): void;
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
  isOpen.value = !isOpen.value;
}

function createShare(): void {
  emit("create-share");
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

function syncBodyScrollLock(): void {
  if (typeof window === "undefined") {
    return;
  }
  const isMobileSheet = window.matchMedia("(max-width: 767px)").matches;
  document.body.style.overflow = isOpen.value && isMobileSheet ? "hidden" : "";
}

watch(isOpen, async (open) => {
  syncBodyScrollLock();
  if (!open) {
    return;
  }
  await nextTick();
  createButtonRef.value?.focus();
});

onMounted(() => {
  document.addEventListener("pointerdown", handleDocumentPointerDown);
  document.addEventListener("keydown", handleEscape);
  window.addEventListener("resize", syncBodyScrollLock);
});

onUnmounted(() => {
  document.removeEventListener("pointerdown", handleDocumentPointerDown);
  document.removeEventListener("keydown", handleEscape);
  window.removeEventListener("resize", syncBodyScrollLock);
  document.body.style.overflow = "";
});
</script>

<template>
  <div
    ref="rootRef"
    class="relative"
    data-test="planner-share-links-management"
  >
    <UiDenseActionButton
      label="Dela"
      :data-test="triggerTestId"
      :expanded="isOpen"
      has-popup="dialog"
      @click="togglePanel"
    >
      <template #leading>
        <IconLink2 :size="14" />
      </template>
    </UiDenseActionButton>

    <Teleport to="body">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[39] bg-navy/70 md:hidden"
        data-test="planner-share-links-backdrop"
        @click="closePanel"
      />
    </Teleport>

    <section
      v-if="isOpen"
      class="fixed inset-x-0 bottom-0 z-[40] max-h-[85vh] overflow-y-auto rounded-t-xl border-t-2 border-navy bg-white pb-[env(safe-area-inset-bottom)] md:absolute md:inset-x-auto md:bottom-auto md:right-0 md:top-[calc(100%+0.375rem)] md:z-[50] md:w-[32rem] md:overflow-visible md:rounded-none md:border md:border-navy md:pb-0 md:shadow-brutal-sm"
      role="dialog"
      aria-label="Delade länkar"
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
            Delade länkar
          </h2>
          <p class="mt-1 text-[11px] leading-snug text-navy/60">
            Aktiva länkar visas här. Återkallade länkar tas bort från listan.
          </p>
        </div>
        <div class="hidden md:block md:justify-self-end">
          <UiDenseActionButton
            ref="createButtonRef"
            label="Skapa länk"
            :disabled="busy"
            tone="primary"
            class="min-w-[8.5rem]"
            data-test="planner-share-create"
            @click="createShare"
          >
            <template #leading>
              <IconPlus :size="10" />
            </template>
          </UiDenseActionButton>
        </div>
        <button
          type="button"
          class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[4px] border border-navy/20 bg-transparent text-navy/55 md:hidden"
          aria-label="Stäng delade länkar"
          data-test="planner-share-close"
          @click="closePanel"
        >
          <IconX :size="14" />
        </button>
      </header>

      <div class="border-b border-navy/10 px-3.5 py-2 md:hidden">
        <button
          type="button"
          class="inline-flex h-10 w-full items-center justify-center gap-2 rounded-[4px] border border-navy bg-navy px-3 text-[11px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)] text-canvas disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="busy"
          data-test="planner-share-create-mobile"
          @click="createShare"
        >
          <IconPlus :size="12" />
          Skapa länk
        </button>
      </div>

      <p
        v-if="statusLabel"
        class="border-b border-navy/10 px-3.5 py-2 text-[11px] font-semibold text-navy/65"
        data-test="planner-share-status"
      >
        {{ statusLabel }}
      </p>
      <p
        v-if="errorMessage"
        class="border-b border-burgundy/20 bg-burgundy/5 px-3.5 py-2 text-[11px] font-semibold text-burgundy"
        data-test="planner-share-error"
      >
        {{ errorMessage }}
      </p>

      <p
        v-if="loading && activeShareCount === 0"
        class="px-3.5 py-4 text-sm font-semibold text-navy/65"
      >
        Hämtar länkar…
      </p>
      <p
        v-else-if="activeShareCount === 0"
        class="px-3.5 py-4 text-sm text-navy/65"
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
              @click="emit('revoke-share', share)"
            >
              <IconTrash :size="12" />
              <span class="sr-only md:not-sr-only">
                {{ revokingShareId === share.id ? "Återkallar" : "Återkalla" }}
              </span>
            </button>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>
