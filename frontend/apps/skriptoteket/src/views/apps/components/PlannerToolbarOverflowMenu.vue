<script setup lang="ts">
/**
 * Compact overflow menu for planner secondary actions.
 *
 * Relationships:
 * - planner adapter over the shared dense-menu lifecycle and icon-button primitive
 * - keeps planner overflow content local while reading shared keyboard/focus behavior
 */

import { computed, ref, type Component } from "vue";

import { IconMoreVertical } from "../../../components/icons";
import {
  DENSE_MENU_PANEL_CLASS,
  UiDenseIconButton,
  denseMenuItemClass,
} from "../../../components/ui";
import { useDenseMenuSurface } from "../../../components/ui/useDenseMenuSurface";

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
const containerRef = ref<HTMLElement | null>(null);
const menuRef = ref<HTMLElement | null>(null);
const triggerRef = ref<HTMLElement | null>(null);
const hasItems = computed(() => props.items.length > 0);
const { closeMenu, toggleMenu, onTriggerKeydown, onMenuKeydown } = useDenseMenuSurface({
  isOpen,
  containerRef,
  menuRef,
  triggerRef,
});

function handleSelect(item: PlannerToolbarMenuItem): void {
  if (item.disabled) {
    return;
  }
  item.onSelect();
  closeMenu();
}
</script>

<template>
  <div
    ref="containerRef"
    class="relative"
  >
    <UiDenseIconButton
      ref="triggerRef"
      :label="label"
      size="utility"
      :aria-expanded="isOpen"
      has-popup="menu"
      :data-test="testId"
      :disabled="!hasItems"
      @click.stop="toggleMenu"
      @keydown="onTriggerKeydown"
    >
      <IconMoreVertical :size="16" />
    </UiDenseIconButton>

    <Transition name="popover">
      <div
        v-if="isOpen"
        ref="menuRef"
        class="absolute right-0 z-50 mt-2 min-w-[12rem]"
        :class="DENSE_MENU_PANEL_CLASS"
        role="menu"
        :aria-label="label"
        @click.stop
        @keydown="onMenuKeydown"
      >
        <button
          v-for="item in items"
          :key="item.id"
          type="button"
          role="menuitem"
          :class="denseMenuItemClass(item.tone === 'danger' ? 'danger' : 'default')"
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
