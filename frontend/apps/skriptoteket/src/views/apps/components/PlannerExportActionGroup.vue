<script setup lang="ts">
/**
 * Compact export action cluster for seating poster exports.
 *
 * This component renders the export subsection inside the seating toolbar with
 * one primary default action and a one-click-away alternate-options menu. It
 * stays presentational so the route shell can own export orchestration.
 */

import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { IconArrow } from "../../../components/icons";
import type { SeatingExportPaperSize } from "../classroomPlannerExportApi";

type ExportOption = {
  id: string;
  label: string;
  paperSize: SeatingExportPaperSize;
};

const props = withDefaults(
  defineProps<{
    disabled?: boolean;
    busy?: boolean;
    statusLabel?: string | null;
    errorMessage?: string | null;
    canDownloadLatest?: boolean;
  }>(),
  {
    disabled: false,
    busy: false,
    statusLabel: null,
    errorMessage: null,
    canDownloadLatest: false,
  },
);

const emit = defineEmits<{
  (e: "export-default"): void;
  (e: "export-option", paperSize: SeatingExportPaperSize): void;
  (e: "download-latest"): void;
}>();

const menuRef = ref<HTMLElement | null>(null);
const isMenuOpen = ref(false);
const exportOptions = computed<ExportOption[]>(() => [
  {
    id: "a3",
    label: "Affisch (A3)",
    paperSize: "a3_landscape",
  },
  {
    id: "a4",
    label: "Affisch (A4)",
    paperSize: "a4_landscape",
  },
]);
const isMenuDisabled = computed(() => props.disabled || props.busy);

function closeMenu(): void {
  isMenuOpen.value = false;
}

function toggleMenu(): void {
  if (isMenuDisabled.value) {
    return;
  }
  isMenuOpen.value = !isMenuOpen.value;
}

function handleDocumentClick(event: MouseEvent): void {
  const target = event.target as Node | null;
  if (!target || !menuRef.value || menuRef.value.contains(target)) {
    return;
  }
  closeMenu();
}

function handleEscape(event: KeyboardEvent): void {
  if (event.key !== "Escape" || !isMenuOpen.value) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  closeMenu();
}

function selectOption(paperSize: SeatingExportPaperSize): void {
  emit("export-option", paperSize);
  closeMenu();
}

onMounted(() => {
  document.addEventListener("click", handleDocumentClick);
  document.addEventListener("keydown", handleEscape);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick);
  document.removeEventListener("keydown", handleEscape);
});
</script>

<template>
  <div
    class="ml-auto flex min-w-[14rem] flex-col items-end gap-1 border-l border-navy/15 pl-3"
    data-test="seating-export-group"
  >
    <span class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
      Export
    </span>

    <div class="flex items-stretch gap-1">
      <button
        type="button"
        class="btn-primary"
        data-test="seating-export-default"
        :disabled="disabled || busy"
        @click="emit('export-default')"
      >
        {{ busy ? "Exporterar…" : "Exportera" }}
      </button>

      <div
        ref="menuRef"
        class="relative"
      >
        <button
          type="button"
          class="grid h-9 w-9 place-items-center border border-navy/30 bg-white text-navy transition-colors hover:bg-canvas disabled:cursor-not-allowed disabled:border-navy/15 disabled:text-navy/35"
          aria-label="Fler exportval"
          title="Fler exportval"
          aria-haspopup="menu"
          :aria-expanded="isMenuOpen"
          :disabled="isMenuDisabled"
          data-test="seating-export-menu-trigger"
          @click.stop="toggleMenu"
        >
          <IconArrow
            :size="16"
            direction="down"
          />
        </button>

        <Transition name="popover">
          <div
            v-if="isMenuOpen"
            class="absolute right-0 z-50 mt-2 min-w-[11rem] border border-navy bg-white shadow-brutal-sm"
            role="menu"
            aria-label="Exportval"
            @click.stop
          >
            <button
              v-for="option in exportOptions"
              :key="option.id"
              type="button"
              role="menuitem"
              class="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm text-navy transition-colors hover:bg-canvas"
              :data-test="`seating-export-option-${option.id}`"
              @click="selectOption(option.paperSize)"
            >
              <span>{{ option.label }}</span>
              <span
                v-if="option.paperSize === 'a3_landscape'"
                class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/50"
              >
                Standard
              </span>
            </button>
          </div>
        </Transition>
      </div>
    </div>

    <div
      v-if="statusLabel || errorMessage || canDownloadLatest"
      class="flex flex-wrap items-center justify-end gap-x-3 gap-y-1 text-xs"
    >
      <p
        v-if="statusLabel"
        class="text-navy/60"
        data-test="seating-export-status"
      >
        {{ statusLabel }}
      </p>
      <p
        v-if="errorMessage"
        class="font-semibold text-burgundy"
        data-test="seating-export-error"
      >
        {{ errorMessage }}
      </p>
      <button
        v-if="canDownloadLatest"
        type="button"
        class="font-semibold text-navy underline underline-offset-2 transition-colors hover:text-burgundy"
        data-test="seating-export-download-latest"
        @click="emit('download-latest')"
      >
        Ladda ned igen
      </button>
    </div>
  </div>
</template>
