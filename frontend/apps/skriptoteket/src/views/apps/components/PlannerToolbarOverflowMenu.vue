<script setup lang="ts">
/**
 * Compact overflow menu for planner secondary actions.
 *
 * This keeps group and seating toolbars visually light by collapsing
 * lower-priority actions behind a shared overflow trigger while still using
 * Skriptoteket's canonical icon resources and accessible menu semantics.
 */

import { computed, onBeforeUnmount, onMounted, ref, type Component } from "vue";

import { IconMoreVertical } from "../../../components/icons";

type PlannerToolbarMenuItem = {
  id: string;
  label: string;
  icon?: Component;
  disabled?: boolean;
  testId?: string;
  tone?: "default" | "danger";
  onSelect: () => void;
};

const props = withDefaults(
  defineProps<{
    items: PlannerToolbarMenuItem[];
    label?: string;
    testId?: string;
  }>(),
  {
    label: "Fler åtgärder",
    testId: undefined,
  },
);

const isOpen = ref(false);
const menuRef = ref<HTMLElement | null>(null);
const hasItems = computed(() => props.items.length > 0);

function closeMenu(): void {
  isOpen.value = false;
}

function toggleMenu(): void {
  if (!hasItems.value) {
    return;
  }
  isOpen.value = !isOpen.value;
}

function handleSelect(item: PlannerToolbarMenuItem): void {
  if (item.disabled) {
    return;
  }
  item.onSelect();
  closeMenu();
}

function handleDocumentClick(event: MouseEvent): void {
  const target = event.target as Node | null;
  if (!target || !menuRef.value || menuRef.value.contains(target)) {
    return;
  }
  closeMenu();
}

function handleEscape(event: KeyboardEvent): void {
  if (event.key !== "Escape" || !isOpen.value) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
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
    class="relative"
  >
    <button
      type="button"
      class="grid h-9 w-9 place-items-center rounded-sm bg-transparent text-navy transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:text-navy/25 hover:bg-canvas/60"
      :aria-label="label"
      :title="label"
      :aria-expanded="isOpen"
      aria-haspopup="menu"
      :data-test="testId"
      :disabled="!hasItems"
      @click.stop="toggleMenu"
    >
      <IconMoreVertical :size="18" />
    </button>

    <Transition name="popover">
      <div
        v-if="isOpen"
        class="absolute right-0 z-50 mt-2 min-w-[12rem] border border-navy bg-white shadow-brutal-sm"
        role="menu"
        :aria-label="label"
        @click.stop
      >
        <button
          v-for="item in items"
          :key="item.id"
          type="button"
          role="menuitem"
          class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-canvas disabled:cursor-not-allowed disabled:text-navy/35"
          :class="item.tone === 'danger' ? 'text-burgundy' : 'text-navy'"
          :data-test="item.testId"
          :disabled="item.disabled"
          @click="handleSelect(item)"
        >
          <component
            :is="item.icon"
            v-if="item.icon"
            :size="16"
          />
          <span>{{ item.label }}</span>
        </button>
      </div>
    </Transition>
  </div>
</template>
