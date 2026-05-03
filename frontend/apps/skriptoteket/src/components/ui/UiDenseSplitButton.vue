<script setup lang="ts">
/**
 * Generic dense split button with shared menu and keyboard behavior.
 *
 * Relationships:
 * - wraps the canonical main-action + disclosure pattern for export-like controls
 * - consumed by planner export wrappers and future editor/planner split actions
 */

import { computed, ref } from "vue";

import { IconArrow } from "../icons";
import { DENSE_MENU_PANEL_CLASS, denseMenuItemClass } from "./denseToolPrimitives";
import UiDenseActionButton from "./UiDenseActionButton.vue";
import { useDenseMenuSurface } from "./useDenseMenuSurface";

export type UiDenseSplitButtonItem = {
  id: string;
  label: string;
  disabled?: boolean;
  metaLabel?: string | null;
  tone?: "default" | "danger";
};

const props = withDefaults(
  defineProps<{
    label: string;
    busyLabel?: string;
    menuLabel?: string;
    items: UiDenseSplitButtonItem[];
    disabled?: boolean;
    busy?: boolean;
    rootTestId?: string;
    mainButtonTestId?: string;
    menuTriggerTestId?: string;
    itemTestIdPrefix?: string;
  }>(),
  {
    busyLabel: undefined,
    menuLabel: "Fler val",
    disabled: false,
    busy: false,
    rootTestId: undefined,
    mainButtonTestId: undefined,
    menuTriggerTestId: undefined,
    itemTestIdPrefix: undefined,
  },
);

const emit = defineEmits<{
  trigger: [];
  select: [id: string];
}>();

const containerRef = ref<HTMLElement | null>(null);
const menuRef = ref<HTMLElement | null>(null);
const disclosureRef = ref<HTMLElement | null>(null);
const isMenuOpen = ref(false);

const {
  closeMenu,
  toggleMenu,
  onTriggerKeydown,
  onMenuKeydown,
} = useDenseMenuSurface({
  isOpen: isMenuOpen,
  containerRef,
  menuRef,
  triggerRef: disclosureRef,
});

const hasEnabledItems = computed(() => props.items.some((item) => !item.disabled));
const mainDisabled = computed(() => props.disabled || props.busy);
const menuDisabled = computed(() => props.disabled || props.busy || !hasEnabledItems.value);
const resolvedBusyLabel = computed(() => props.busyLabel ?? props.label);

function triggerDefault(): void {
  if (mainDisabled.value) {
    return;
  }
  emit("trigger");
}

function selectItem(id: string, disabled?: boolean): void {
  if (disabled) {
    return;
  }
  emit("select", id);
  closeMenu();
}
</script>

<template>
  <div
    ref="containerRef"
    class="relative inline-flex items-stretch"
    data-ui="dense-split-button"
    :data-test="rootTestId"
  >
    <UiDenseActionButton
      :label="label"
      :busy="busy"
      :busy-label="resolvedBusyLabel"
      :disabled="mainDisabled"
      tone="primary"
      group-position="start"
      :data-test="mainButtonTestId"
      @click="triggerDefault"
    />

    <UiDenseActionButton
      ref="disclosureRef"
      label=""
      :aria-label="menuLabel"
      :title="menuLabel"
      :disabled="menuDisabled"
      tone="primary"
      size="utility"
      icon-only
      group-position="end"
      has-popup="menu"
      :expanded="isMenuOpen"
      :data-test="menuTriggerTestId"
      @click.stop="toggleMenu()"
      @keydown="onTriggerKeydown"
    >
      <template #leading>
        <IconArrow
          :size="12"
          direction="down"
        />
      </template>
    </UiDenseActionButton>

    <Transition name="popover">
      <div
        v-if="isMenuOpen"
        ref="menuRef"
        class="absolute right-0 top-full mt-2 min-w-[12rem]"
        :class="DENSE_MENU_PANEL_CLASS"
        role="menu"
        :aria-label="menuLabel"
        @click.stop
        @keydown="onMenuKeydown"
      >
        <button
          v-for="item in items"
          :key="item.id"
          type="button"
          role="menuitem"
          :class="denseMenuItemClass(item.tone ?? 'default')"
          :disabled="item.disabled"
          :data-test="itemTestIdPrefix ? `${itemTestIdPrefix}-${item.id}` : undefined"
          @click="selectItem(item.id, item.disabled)"
        >
          <span>{{ item.label }}</span>
          <span
            v-if="item.metaLabel"
            class="ml-auto text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/50"
          >
            {{ item.metaLabel }}
          </span>
        </button>
      </div>
    </Transition>
  </div>
</template>
