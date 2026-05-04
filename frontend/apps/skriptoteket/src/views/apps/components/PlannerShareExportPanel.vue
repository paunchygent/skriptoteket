<script setup lang="ts">
/**
 * Combined Klassrumskartan distribution surface.
 *
 * Relationships: replaces adjacent export/share toolbar controls and emits
 * separate intents to the existing share and export flow composables.
 */

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";

import { IconArrow, IconLink2, IconX } from "../../../components/icons";
import { UiDenseActionButton, denseMenuItemClass } from "../../../components/ui";
import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";
import type {
  PlannerExportFileOption,
  PlannerExportOptionValue,
  PlannerShareExportScopeOption,
} from "./plannerShareExportActions";
import PlannerShareExportFileSection from "./PlannerShareExportFileSection.vue";
import PlannerShareExportLinkSection from "./PlannerShareExportLinkSection.vue";
import PlannerShareExportScopeList from "./PlannerShareExportScopeList.vue";
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
    triggerVariant?: "toolbar" | "phone-row" | "menu-item" | "inline";
    triggerMeta?: string | null;
    visualVariant?: "default" | "desktop-overview";
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
    visualVariant: "default",
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
const panelRef = ref<HTMLElement | null>(null);
const desktopTriggerRef = ref<InstanceType<typeof UiDenseActionButton> | null>(null);
const phoneTriggerRef = ref<HTMLButtonElement | null>(null);
const isOpen = ref(false);
let previousBodyOverflow: string | null = null;

const isInline = computed(() => props.triggerVariant === "inline");
const isDisabled = computed(() => !props.showFileActions && !props.showShareActions);
const isPanelVisible = computed(() => isInline.value || isOpen.value);

function restoreTriggerFocus(): void {
  desktopTriggerRef.value?.focus();
  phoneTriggerRef.value?.focus();
}

function lockBodyScroll(): void {
  if (previousBodyOverflow !== null) {
    return;
  }
  previousBodyOverflow = document.body.style.overflow;
  document.body.style.overflow = "hidden";
}

function unlockBodyScroll(): void {
  if (previousBodyOverflow === null) {
    return;
  }
  document.body.style.overflow = previousBodyOverflow;
  previousBodyOverflow = null;
}

function focusablePanelElements(): HTMLElement[] {
  const panel = panelRef.value;
  if (!panel) {
    return [];
  }
  const selector = [
    "a[href]",
    "button:not([disabled])",
    "textarea:not([disabled])",
    "input:not([disabled])",
    "select:not([disabled])",
    "[tabindex]:not([tabindex='-1'])",
  ].join(",");
  return [...panel.querySelectorAll<HTMLElement>(selector)]
    .filter((element) => {
      const style = window.getComputedStyle(element);
      return !element.hasAttribute("disabled")
        && style.display !== "none"
        && style.visibility !== "hidden";
    });
}

function focusInitialPanelAction(): void {
  focusablePanelElements()[0]?.focus();
}

function closePanel(options: { returnFocus?: boolean } = {}): void {
  isOpen.value = false;
  if (options.returnFocus ?? true) {
    void nextTick(() => {
      restoreTriggerFocus();
    });
  }
}
function togglePanel(): void {
  if (isInline.value) {
    return;
  }
  const nextOpen = !isOpen.value;
  isOpen.value = nextOpen;
  if (nextOpen) {
    emit("open");
    return;
  }
  void nextTick(() => {
    restoreTriggerFocus();
  });
}

function handleDocumentPointerDown(event: PointerEvent): void {
  if (!isOpen.value) {
    return;
  }
  const target = event.target;
  if (!(target instanceof Node)) {
    return;
  }
  if (target instanceof HTMLElement && target.dataset.test === "planner-share-export-backdrop") {
    closePanel();
    return;
  }
  if (rootRef.value?.contains(target)) {
    return;
  }
  closePanel({ returnFocus: false });
}

function handleEscape(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    closePanel();
  }
}

function handlePanelKeydown(event: KeyboardEvent): void {
  if (event.key !== "Tab") {
    return;
  }
  const focusableElements = focusablePanelElements();
  if (focusableElements.length === 0) {
    event.preventDefault();
    return;
  }
  const firstElement = focusableElements[0];
  const lastElement = focusableElements.at(-1);
  if (!lastElement) {
    return;
  }
  if (event.shiftKey && document.activeElement === firstElement) {
    event.preventDefault();
    lastElement.focus();
    return;
  }
  if (!event.shiftKey && document.activeElement === lastElement) {
    event.preventDefault();
    firstElement.focus();
  }
}

watch(isOpen, async (open) => {
  if (!open || isInline.value) {
    unlockBodyScroll();
    return;
  }
  lockBodyScroll();
  await nextTick();
  focusInitialPanelAction();
});

onMounted(() => {
  document.addEventListener("pointerdown", handleDocumentPointerDown);
  document.addEventListener("keydown", handleEscape);
});

onUnmounted(() => {
  document.removeEventListener("pointerdown", handleDocumentPointerDown);
  document.removeEventListener("keydown", handleEscape);
  unlockBodyScroll();
});
</script>

<template>
  <component
    :is="isInline ? 'fieldset' : 'div'"
    ref="rootRef"
    :class="[
      'relative flex items-stretch',
      triggerVariant === 'inline'
        ? 'planner-share-export-inline w-full'
        : triggerVariant === 'toolbar'
          ? 'planner-share-export-toolbar border-l border-navy/15 pl-3'
          : triggerVariant === 'menu-item'
            ? 'planner-share-export-menu w-full'
            : 'planner-share-export-row w-full',
      isInline && isDisabled ? 'planner-share-export-inline-disabled' : null,
    ]"
    :disabled="isInline && isDisabled ? true : undefined"
    :data-test="triggerVariant === 'inline' ? triggerTestId : 'planner-share-export-management'"
  >
    <UiDenseActionButton
      v-if="triggerVariant === 'toolbar'"
      ref="desktopTriggerRef"
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
      v-else-if="triggerVariant === 'phone-row'"
      ref="phoneTriggerRef"
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
      <span
        v-if="triggerMeta !== ''"
        class="text-xs text-navy/55"
      >
        {{ triggerMeta ?? "Länk + filer" }}
      </span>
    </button>
    <button
      v-else-if="triggerVariant === 'menu-item'"
      ref="phoneTriggerRef"
      type="button"
      :class="denseMenuItemClass()"
      :data-test="triggerTestId"
      :disabled="!showFileActions && !showShareActions"
      :aria-expanded="isOpen"
      aria-haspopup="dialog"
      @click="togglePanel"
    >
      <IconLink2 :size="16" />
      <span>Dela</span>
    </button>

    <div
      v-if="isOpen && !isInline"
      class="fixed inset-0 z-[39] bg-navy/70 md:hidden"
      data-test="planner-share-export-backdrop"
      @click="() => closePanel()"
    />

    <section
      v-if="isPanelVisible"
      ref="panelRef"
      :class="[
        isInline
          ? 'planner-share-export-inline-panel flex w-full flex-col overflow-hidden border border-navy bg-white'
          : 'fixed inset-x-0 bottom-0 z-[40] flex max-h-[85dvh] flex-col overflow-hidden rounded-t-xl border-t-2 border-navy bg-white pb-[env(safe-area-inset-bottom)] md:absolute md:inset-x-auto md:bottom-auto md:right-0 md:top-[calc(100%+0.375rem)] md:z-[50] md:max-h-[min(70vh,42rem)] md:w-[34rem] md:rounded-none md:border md:border-navy md:pb-0 md:shadow-brutal-sm',
      ]"
      :role="isInline ? undefined : 'dialog'"
      :aria-modal="isInline ? undefined : 'true'"
      aria-label="Dela och exportera"
      tabindex="-1"
      :data-test="panelTestId"
      @keydown="handlePanelKeydown"
    >
      <div
        v-if="!isInline"
        class="flex justify-center px-3 pb-1 pt-2 md:hidden"
        aria-hidden="true"
      >
        <span class="h-1 w-9 rounded-full bg-navy/20" />
      </div>

      <header
        :class="[
          'flex items-start justify-between gap-3 border-b border-navy/15',
          isInline ? 'px-3 py-3' : 'px-3.5 pb-3 pt-2 md:grid md:grid-cols-[minmax(0,1fr)_auto] md:items-start md:px-4 md:pt-3.5',
        ]"
      >
        <div>
          <h2 class="text-sm font-semibold leading-tight text-navy">
            Dela och exportera
          </h2>
          <p
            v-if="!isInline"
            class="mt-1 text-[11px] leading-snug text-navy/60"
          >
            Skapa länk eller spara en fil från det aktuella utkastet.
          </p>
        </div>
        <button
          v-if="!isInline"
          type="button"
          class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[4px] border border-navy/20 bg-transparent text-navy/55 md:hidden"
          aria-label="Stäng dela och exportera"
          data-test="planner-share-export-close"
          @click="() => closePanel()"
        >
          <IconX :size="14" />
        </button>
      </header>

      <div
        :class="[
          'min-h-0 flex-1',
          isInline ? 'overflow-visible' : 'overflow-y-auto overscroll-contain',
        ]"
        data-test="planner-share-export-scroll"
      >
        <PlannerShareExportScopeList
          :scope-value="scopeValue"
          :scope-options="scopeOptions"
          @select-scope="emit('select-scope', $event)"
        />

        <PlannerShareExportLinkSection
          v-if="showShareActions"
          :shares="shares"
          :share-loading="shareLoading"
          :share-busy="shareBusy"
          :share-status-label="shareStatusLabel"
          :share-error-message="shareErrorMessage"
          :revoking-share-id="revokingShareId"
          :show-revoke-action="showRevokeAction"
          :visual-variant="visualVariant"
          :create-share-test-id="createShareTestId"
          :create-share-mobile-test-id="createShareMobileTestId"
          @create-share="emit('create-share')"
          @copy-share="emit('copy-share', $event)"
          @revoke-share="emit('revoke-share', $event)"
        />

        <PlannerShareExportFileSection
          v-if="showFileActions"
          :file-options="fileOptions"
          :export-busy="exportBusy"
          :export-error-message="exportErrorMessage"
          :file-option-test-id-prefix="fileOptionTestIdPrefix"
          :visual-variant="visualVariant"
          @export-default="emit('export-default')"
          @export-option="emit('export-option', $event)"
        />
      </div>
    </section>
  </component>
</template>
