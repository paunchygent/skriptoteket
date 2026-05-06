<script setup lang="ts">
/**
 * Compact overflow menu for planner secondary actions.
 *
 * Relationships:
 * - planner adapter over the shared dense-menu lifecycle and icon-button primitive
 * - keeps planner overflow content local while reading shared keyboard/focus behavior
 */

import { computed, ref, useSlots, type Component } from "vue";

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
  group?: "primary" | "secondary";
  hasPopup?: "dialog" | "menu";
  expanded?: boolean;
  responsiveVisibility?: "all" | "phone";
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

defineSlots<{
  panel?: () => unknown;
  footer?: () => unknown;
}>();

const slots = useSlots();
const isOpen = ref(false);
const containerRef = ref<HTMLElement | null>(null);
const menuRef = ref<HTMLElement | null>(null);
const triggerRef = ref<HTMLElement | null>(null);
const hasMenuContent = computed(() => (
  props.items.length > 0
  || Boolean(slots.panel)
  || Boolean(slots.footer)
));
const primaryItems = computed(() => props.items.filter((item) => item.group === "primary"));
const secondaryItems = computed(() => props.items.filter((item) => item.group !== "primary"));
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

function handleMenuKeydown(event: KeyboardEvent): void {
  const target = event.target;
  if (
    target instanceof HTMLInputElement
    || target instanceof HTMLSelectElement
    || target instanceof HTMLTextAreaElement
    || (target instanceof HTMLElement && target.isContentEditable)
  ) {
    return;
  }
  onMenuKeydown(event);
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
      :disabled="!hasMenuContent"
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
        @keydown="handleMenuKeydown"
      >
        <div
          v-if="primaryItems.length > 0 || $slots.panel"
          class="border-b border-navy/10"
        >
          <button
            v-for="item in primaryItems"
            :key="item.id"
            type="button"
            role="menuitem"
            :class="[
              denseMenuItemClass(item.tone === 'danger' ? 'danger' : 'default'),
              item.responsiveVisibility === 'phone' ? 'planner-toolbar-menu-item-phone-only' : null,
            ]"
            :data-test="item.testId"
            :disabled="item.disabled"
            :aria-haspopup="item.hasPopup"
            :aria-expanded="item.hasPopup ? item.expanded : undefined"
            @click="handleSelect(item)"
          >
            <component
              :is="item.icon"
              v-if="item.icon"
              :size="16"
            />
            <span>{{ item.label }}</span>
          </button>
          <div
            v-if="$slots.panel"
            :class="[
              'space-y-3 p-3',
              primaryItems.length > 0 ? 'border-t border-navy/10' : null,
            ]"
          >
            <slot name="panel" />
          </div>
        </div>
        <button
          v-for="item in secondaryItems"
          :key="item.id"
          type="button"
          role="menuitem"
          :class="[
            denseMenuItemClass(item.tone === 'danger' ? 'danger' : 'default'),
            item.responsiveVisibility === 'phone' ? 'planner-toolbar-menu-item-phone-only' : null,
          ]"
          :data-test="item.testId"
          :disabled="item.disabled"
          :aria-haspopup="item.hasPopup"
          :aria-expanded="item.hasPopup ? item.expanded : undefined"
          @click="handleSelect(item)"
        >
          <component
            :is="item.icon"
            v-if="item.icon"
            :size="16"
          />
          <span>{{ item.label }}</span>
        </button>
        <div
          v-if="$slots.footer"
          class="border-t border-navy/10"
        >
          <slot name="footer" />
        </div>
      </div>
    </Transition>
  </div>
</template>
