<script setup lang="ts">
/**
 * Purpose:
 *     Provide the shared top-bar theme selector button and its menu.
 *
 * Relationships:
 *     - Builds on UiDenseActionButton with a menu popup and aria-expanded.
 *     - Applies and stores the choice through the consumer-provided
 *       ThemePreferenceStore, normally built from themePreference.ts.
 *     - Draws the state glyphs from uiGlyphs.ts and the dark swatches from the
 *       fixed swatch tokens.
 *     - Takes geometry, spacing and the menu-row type role from shared tokens.
 *       UiGlyph accepts a numeric size only, so the workbench icon role sizes
 *       its svg through scoped CSS instead of a size prop.
 *     - Follows props.themePreference.read() with a reactive effect, so several
 *       selectors mounted on one page show the same choice. Ordinary consumer
 *       stores whose read() is not reactive keep the explicit updates from the
 *       menu choice and the re-read on open.
 *     - ThemeChoice repeats themePreference.ts's union because a type import
 *       across the package's theme and vue subtrees does not resolve in the
 *       consumer sync layout; the two unions must stay identical.
 */

import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";

import type { UiGlyphMeaning } from "../uiGlyphs";
import UiDenseActionButton from "./UiDenseActionButton.vue";
import UiGlyph from "./UiGlyph.vue";

export type ThemeChoice = "light" | "dark" | "midnight" | "system";

export interface ThemePreferenceStore {
  read: () => ThemeChoice;
  apply: (choice: ThemeChoice) => void;
  store: (choice: ThemeChoice) => void;
}

type ThemeOption = {
  value: ThemeChoice;
  label: string;
  glyph: UiGlyphMeaning;
  swatchClass?: string;
};

const props = defineProps<{
  themePreference: ThemePreferenceStore;
}>();

const THEME_OPTIONS: readonly ThemeOption[] = [
  { value: "light", label: "Ljust", glyph: "theme-light" },
  {
    value: "midnight",
    label: "Midnatt",
    glyph: "theme-dark",
    swatchClass: "bg-[var(--huleedu-theme-swatch-midnight)]",
  },
  {
    value: "dark",
    label: "Bläck",
    glyph: "theme-dark",
    swatchClass: "bg-[var(--huleedu-theme-swatch-dark)]",
  },
  { value: "system", label: "Följ enheten", glyph: "theme-system" },
];

const MENU_ITEM_SELECTOR = '[role="menuitemradio"]';
const MENU_ITEM_BASE_CLASS =
  "grid h-[var(--huleedu-action-control-height)] w-full grid-cols-[auto_1fr_auto] items-center gap-[var(--huleedu-space-2)] rounded-[var(--huleedu-radius-md)] px-[var(--huleedu-space-2)] text-left text-[length:var(--huleedu-type-control-value-size)] font-[number:var(--huleedu-type-control-value-weight)] text-navy transition-colors focus-visible:bg-navy/5 focus-visible:outline-none";
const MENU_PANEL_CLASS =
  "absolute right-0 top-full z-[var(--huleedu-z-dropdown)] mt-[var(--huleedu-space-1)] grid w-max gap-[var(--huleedu-space-0-5)] rounded-[var(--huleedu-radius-lg)] border border-[var(--huleedu-panel-border)] bg-modal p-[var(--huleedu-space-1)] shadow-[var(--huleedu-shadow-md)]";

type FocusableElement = Element & { focus: () => void };

const menuId = useId();
const rootRef = ref<Element | null>(null);
const menuRef = ref<Element | null>(null);
const triggerRef = ref<InstanceType<typeof UiDenseActionButton> | null>(null);
const isOpen = ref(false);
const currentChoice = ref<ThemeChoice>(props.themePreference.read());

watch(
  () => props.themePreference.read(),
  (choice) => {
    currentChoice.value = choice;
  },
);

const currentLabel = computed(
  () => THEME_OPTIONS.find((option) => option.value === currentChoice.value)?.label ?? "",
);
const buttonLabel = computed(() => `Färgtema: ${currentLabel.value}`);
const buttonGlyph = computed<UiGlyphMeaning>(() => {
  if (currentChoice.value === "light") {
    return "theme-light";
  }
  if (currentChoice.value === "system") {
    return "theme-system";
  }
  return "theme-dark";
});

function optionClass(option: ThemeOption): string {
  return option.value === currentChoice.value
    ? `${MENU_ITEM_BASE_CLASS} bg-action/10`
    : `${MENU_ITEM_BASE_CLASS} hover:bg-navy/5`;
}

function isFocusableElement(element: Element): element is FocusableElement {
  return typeof (element as { focus?: unknown }).focus === "function";
}

function menuItems(): FocusableElement[] {
  const menu = menuRef.value;
  if (menu === null) {
    return [];
  }
  return Array.from(menu.querySelectorAll(MENU_ITEM_SELECTOR)).filter(isFocusableElement);
}

function focusMenuItem(position: "first" | "last"): void {
  const items = menuItems();
  if (items.length === 0) {
    return;
  }
  items[position === "first" ? 0 : items.length - 1]?.focus();
}

function closeMenu(): void {
  if (!isOpen.value) {
    return;
  }
  isOpen.value = false;
  void nextTick(() => triggerRef.value?.focus());
}

async function openMenu(position: "first" | "last"): Promise<void> {
  if (isOpen.value) {
    return;
  }
  currentChoice.value = props.themePreference.read();
  isOpen.value = true;
  await nextTick();
  focusMenuItem(position);
}

function toggleMenu(): void {
  if (isOpen.value) {
    closeMenu();
    return;
  }
  void openMenu("first");
}

function chooseTheme(choice: ThemeChoice): void {
  props.themePreference.apply(choice);
  props.themePreference.store(choice);
  currentChoice.value = choice;
  closeMenu();
}

function onTriggerKeydown(event: KeyboardEvent): void {
  if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
    return;
  }
  event.preventDefault();
  const position = event.key === "ArrowDown" ? "first" : "last";
  if (isOpen.value) {
    focusMenuItem(position);
    return;
  }
  void openMenu(position);
}

function onMenuKeydown(event: KeyboardEvent): void {
  const items = menuItems();
  if (items.length === 0) {
    return;
  }
  if (event.key === "Home") {
    event.preventDefault();
    items[0]?.focus();
    return;
  }
  if (event.key === "End") {
    event.preventDefault();
    items[items.length - 1]?.focus();
    return;
  }
  if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
    return;
  }
  event.preventDefault();
  const currentIndex = items.findIndex((item) => item === document.activeElement);
  const offset = event.key === "ArrowDown" ? 1 : -1;
  const nextIndex =
    currentIndex < 0
      ? event.key === "ArrowDown"
        ? 0
        : items.length - 1
      : (currentIndex + offset + items.length) % items.length;
  items[nextIndex]?.focus();
}

function onDocumentClick(event: MouseEvent): void {
  if (!isOpen.value) {
    return;
  }
  const target = event.target;
  if (!(target instanceof Node) || rootRef.value?.contains(target)) {
    return;
  }
  closeMenu();
}

function onDocumentKeydown(event: KeyboardEvent): void {
  if (!isOpen.value || event.key !== "Escape") {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  closeMenu();
}

onMounted(() => {
  document.addEventListener("click", onDocumentClick);
  document.addEventListener("keydown", onDocumentKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", onDocumentClick);
  document.removeEventListener("keydown", onDocumentKeydown);
});
</script>

<template>
  <div
    ref="rootRef"
    class="relative inline-flex"
  >
    <UiDenseActionButton
      ref="triggerRef"
      :label="buttonLabel"
      :title="buttonLabel"
      :expanded="isOpen"
      has-popup="menu"
      :aria-controls="menuId"
      icon-only
      @click="toggleMenu"
      @keydown="onTriggerKeydown"
    >
      <template #leading>
        <span class="huleedu-theme-selector-glyph inline-flex">
          <UiGlyph :meaning="buttonGlyph" />
        </span>
      </template>
    </UiDenseActionButton>

    <div
      v-if="isOpen"
      :id="menuId"
      ref="menuRef"
      :class="MENU_PANEL_CLASS"
      role="menu"
      aria-label="Färgtema"
      @keydown="onMenuKeydown"
    >
      <button
        v-for="option in THEME_OPTIONS"
        :key="option.value"
        type="button"
        role="menuitemradio"
        tabindex="-1"
        :aria-checked="option.value === currentChoice"
        :class="optionClass(option)"
        @click="chooseTheme(option.value)"
      >
        <span class="huleedu-theme-selector-glyph inline-flex items-center gap-[var(--huleedu-space-1)]">
          <UiGlyph :meaning="option.glyph" />
          <span
            v-if="option.swatchClass"
            class="inline-block size-[var(--huleedu-space-3)] rounded-[var(--huleedu-radius-sm)] border border-navy/30"
            :class="option.swatchClass"
            aria-hidden="true"
          ></span>
        </span>
        <span class="whitespace-nowrap">{{ option.label }}</span>
        <span
          class="huleedu-theme-selector-glyph inline-flex w-[var(--huleedu-workbench-icon-size)] items-center justify-center text-action"
        >
          <UiGlyph
            v-if="option.value === currentChoice"
            meaning="selected"
          />
        </span>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* UiGlyph accepts a numeric size only; the shared icon role sizes its svg. */
.huleedu-theme-selector-glyph :deep(svg) {
  width: var(--huleedu-workbench-icon-size);
  height: var(--huleedu-workbench-icon-size);
}
</style>
