<script setup lang="ts">
/**
 * Exam workspace menu surface.
 *
 * Domain purpose:
 *   One floating menu for every workspace menu (Spara, Exportera, Ny uppgift,
 *   Byt frågetyp, ⋮): it opens under its trigger, right- or left-aligned and
 *   kept inside the window, full width with 12 px margins on a phone. The
 *   first enabled entry takes focus; ArrowUp/ArrowDown, Home and End move
 *   between enabled entries (disabled and reserved entries are skipped);
 *   Escape closes and returns focus to the trigger; Tab or a press outside
 *   closes it.
 *
 * Relationships:
 *   - Rendered by the trigger's owner, which supplies the entries (`.xw-mi`
 *     with a menuitem role) and closes the menu when one is chosen.
 *   - Teleported to the body, so a scroll container or the shell's top bar
 *     never clips it.
 */

import { nextTick, onBeforeUnmount, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    open: boolean;
    anchor: HTMLElement | null;
    label: string;
    align?: "left" | "right";
    /** At least this wide; the course list matches its input. */
    minWidth?: number | null;
    testId?: string;
  }>(),
  { align: "right", minWidth: null, testId: undefined },
);

const emit = defineEmits<{ close: [restoreFocus: boolean] }>();

const ENTRY_SELECTOR = '[role^="menuitem"]:not([disabled]):not([aria-disabled="true"]), [role="option"]';
const EDGE = 12;
const GAP = 6;

const surface = ref<HTMLElement | null>(null);
const position = ref<{ top: number; left: number; width: number | null }>({ top: 0, left: 0, width: null });

function entries(): HTMLElement[] {
  return Array.from(surface.value?.querySelectorAll<HTMLElement>(ENTRY_SELECTOR) ?? []);
}

function place(): void {
  const anchor = props.anchor;
  const menu = surface.value;
  if (!anchor || !menu) {
    return;
  }
  const box = anchor.getBoundingClientRect();
  const width = props.minWidth ? Math.max(props.minWidth, 260) : null;
  position.value = { ...position.value, width };
  void nextTick(() => {
    const menuWidth = menu.offsetWidth;
    const height = Math.min(menu.scrollHeight, window.innerHeight - 80);
    const top = Math.min(box.bottom + GAP, window.innerHeight - height - 8);
    const left =
      props.align === "right"
        ? Math.max(EDGE, box.right - menuWidth)
        : Math.max(EDGE, Math.min(box.left, window.innerWidth - menuWidth - EDGE));
    position.value = { top, left, width };
  });
}

function close(restoreFocus: boolean): void {
  emit("close", restoreFocus);
  if (restoreFocus) {
    void nextTick(() => props.anchor?.focus());
  }
}

function onPointerDown(event: PointerEvent): void {
  const target = event.target;
  if (target === null) {
    return;
  }
  if (!(target instanceof Node)) {
    close(false);
    return;
  }
  if (surface.value?.contains(target) || props.anchor?.contains(target)) {
    return;
  }
  close(false);
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    close(true);
    return;
  }
  if (event.key === "Tab") {
    close(false);
    return;
  }
  if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
    return;
  }
  const list = entries();
  if (list.length === 0) {
    return;
  }
  event.preventDefault();
  const active = document.activeElement;
  const at = active instanceof HTMLElement ? list.indexOf(active) : -1;
  const last = list.length - 1;
  const next =
    event.key === "Home"
      ? 0
      : event.key === "End"
        ? last
        : at < 0
          ? event.key === "ArrowDown" ? 0 : last
          : (at + (event.key === "ArrowDown" ? 1 : -1) + list.length) % list.length;
  list[next]?.focus();
}

function onResize(): void {
  place();
}

watch(
  () => props.open,
  async (open) => {
    if (!open) {
      document.removeEventListener("pointerdown", onPointerDown, true);
      window.removeEventListener("resize", onResize);
      return;
    }
    await nextTick();
    place();
    document.addEventListener("pointerdown", onPointerDown, true);
    window.addEventListener("resize", onResize);
    await nextTick();
    entries()[0]?.focus();
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onPointerDown, true);
  window.removeEventListener("resize", onResize);
});

defineExpose({ place });
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="surface"
      class="xw-menu"
      role="menu"
      :aria-label="label"
      :data-test="testId"
      :style="{
        top: `${position.top}px`,
        left: `${position.left}px`,
        width: position.width === null ? undefined : `${position.width}px`,
      }"
      @keydown="onKeydown"
    >
      <slot />
    </div>
  </Teleport>
</template>
