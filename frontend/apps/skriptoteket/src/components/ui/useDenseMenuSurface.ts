/**
 * Shared dense-menu lifecycle and keyboard contract.
 *
 * Relationships:
 * - used by `UiDenseSplitButton` and dense menu wrappers in planner/editor
 * - centralizes outside-click dismissal, focus return, and arrow-key navigation
 */

import { nextTick, onBeforeUnmount, onMounted, type Ref } from "vue";

import { DENSE_MENU_ITEM_SELECTOR } from "./denseToolPrimitives";

type FocusTarget = "first" | "last";
type FocusableTarget = HTMLElement | { focus: () => void } | null;

type DenseMenuSurfaceOptions = {
  isOpen: Ref<boolean>;
  containerRef: Ref<HTMLElement | null>;
  menuRef: Ref<HTMLElement | null>;
  triggerRef: Ref<FocusableTarget>;
  itemSelector?: string;
};

export function useDenseMenuSurface(options: DenseMenuSurfaceOptions) {
  const itemSelector = options.itemSelector ?? DENSE_MENU_ITEM_SELECTOR;

  function menuItems(): HTMLElement[] {
    const menu = options.menuRef.value;
    if (!menu) {
      return [];
    }
    return Array.from(menu.querySelectorAll<HTMLElement>(itemSelector));
  }

  async function focusMenuItem(target: FocusTarget): Promise<void> {
    await nextTick();
    const items = menuItems();
    if (items.length === 0) {
      return;
    }
    const nextItem = target === "last" ? items[items.length - 1] : items[0];
    nextItem?.focus();
  }

  function restoreFocus(): void {
    nextTick(() => {
      options.triggerRef.value?.focus();
    });
  }

  function closeMenu(restoreTriggerFocus = true): void {
    if (!options.isOpen.value) {
      return;
    }
    options.isOpen.value = false;
    if (restoreTriggerFocus) {
      restoreFocus();
    }
  }

  function openMenu(target: FocusTarget = "first"): void {
    if (options.isOpen.value) {
      return;
    }
    options.isOpen.value = true;
    void focusMenuItem(target);
  }

  function toggleMenu(target: FocusTarget = "first"): void {
    if (options.isOpen.value) {
      closeMenu();
      return;
    }
    openMenu(target);
  }

  function moveFocus(direction: "next" | "prev" | "first" | "last"): void {
    const items = menuItems();
    if (items.length === 0) {
      return;
    }

    const activeIndex = items.findIndex((item) => item === document.activeElement);
    if (direction === "first") {
      items[0]?.focus();
      return;
    }
    if (direction === "last") {
      items[items.length - 1]?.focus();
      return;
    }

    const currentIndex = activeIndex >= 0 ? activeIndex : 0;
    const nextIndex =
      direction === "next"
        ? (currentIndex + 1) % items.length
        : (currentIndex - 1 + items.length) % items.length;
    items[nextIndex]?.focus();
  }

  function onTriggerKeydown(event: KeyboardEvent): void {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      toggleMenu("first");
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      toggleMenu("last");
    }
  }

  function onMenuKeydown(event: KeyboardEvent): void {
    if (!options.isOpen.value) {
      return;
    }

    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        moveFocus("next");
        break;
      case "ArrowUp":
        event.preventDefault();
        moveFocus("prev");
        break;
      case "Home":
        event.preventDefault();
        moveFocus("first");
        break;
      case "End":
        event.preventDefault();
        moveFocus("last");
        break;
      case "Tab":
        closeMenu(false);
        break;
      default:
        break;
    }
  }

  function handleDocumentClick(event: MouseEvent): void {
    if (!options.isOpen.value) {
      return;
    }

    const target = event.target as Node | null;
    if (!target) {
      return;
    }
    if (options.containerRef.value?.contains(target)) {
      return;
    }
    closeMenu(false);
  }

  function handleDocumentKeydown(event: KeyboardEvent): void {
    if (event.key !== "Escape" || !options.isOpen.value) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    closeMenu();
  }

  onMounted(() => {
    document.addEventListener("click", handleDocumentClick);
    document.addEventListener("keydown", handleDocumentKeydown);
  });

  onBeforeUnmount(() => {
    document.removeEventListener("click", handleDocumentClick);
    document.removeEventListener("keydown", handleDocumentKeydown);
  });

  return {
    closeMenu,
    openMenu,
    toggleMenu,
    onTriggerKeydown,
    onMenuKeydown,
  };
}
