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
import type { SeatingExportOption } from "../classroomPlannerExportApi";

type ExportOption = {
  id: string;
  label: string;
  option: SeatingExportOption;
};

const props = withDefaults(
  defineProps<{
    disabled?: boolean;
    busy?: boolean;
  }>(),
  {
    disabled: false,
    busy: false,
  },
);

const emit = defineEmits<{
  (e: "export-default"): void;
  (e: "export-option", option: SeatingExportOption): void;
}>();

const menuRef = ref<HTMLElement | null>(null);
const isMenuOpen = ref(false);
const exportOptions = computed<ExportOption[]>(() => [
  {
    id: "a3",
    label: "Affisch (A3)",
    option: "a3_landscape",
  },
  {
    id: "a4",
    label: "Affisch (A4)",
    option: "a4_landscape",
  },
  {
    id: "xlsx",
    label: "Excel (.xlsx)",
    option: "xlsx",
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

function selectOption(option: SeatingExportOption): void {
  emit("export-option", option);
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
    ref="menuRef"
    class="relative flex items-stretch border-l border-navy/15 pl-3"
    data-test="seating-export-group"
  >
    <button
      type="button"
      class="bg-navy px-3 py-1.5 text-xs font-bold uppercase tracking-widest text-canvas transition-colors hover:bg-navy/90 disabled:cursor-not-allowed disabled:bg-navy/40"
      data-test="seating-export-default"
      :disabled="disabled || busy"
      @click="emit('export-default')"
    >
      {{ busy ? "Exporterar…" : "Exportera" }}
    </button>

    <button
      type="button"
      class="flex items-center border-l border-white/15 bg-navy px-2 text-canvas transition-colors hover:bg-navy/90 disabled:cursor-not-allowed disabled:bg-navy/40"
      aria-label="Fler exportval"
      aria-haspopup="menu"
      :aria-expanded="isMenuOpen"
      :disabled="isMenuDisabled"
      data-test="seating-export-menu-trigger"
      @click.stop="toggleMenu"
    >
      <IconArrow
        :size="12"
        direction="down"
      />
    </button>

    <Transition name="popover">
      <div
        v-if="isMenuOpen"
        class="absolute right-0 top-full z-50 mt-1 min-w-[11rem] border border-navy bg-white shadow-brutal-sm"
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
          @click="selectOption(option.option)"
        >
          <span>{{ option.label }}</span>
          <span
            v-if="option.option === 'a3_landscape'"
            class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/50"
          >
            Standard
          </span>
        </button>
      </div>
    </Transition>
  </div>
</template>
