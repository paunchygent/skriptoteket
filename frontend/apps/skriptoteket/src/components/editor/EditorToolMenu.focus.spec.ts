import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";
import { createMemoryHistory, createRouter, useRoute, useRouter } from "vue-router";

import { useScriptEditorDrawers } from "../../composables/editor/useScriptEditorDrawers";
import EditorToolMenu from "./EditorToolMenu.vue";

vi.mock("../../api/client", () => ({
  apiGet: vi.fn().mockResolvedValue({ tools: [] }),
  apiPost: vi.fn(),
  isApiError: () => false,
}));
vi.mock("../../stores/auth", () => ({ useAuthStore: () => ({ user: { id: "editor-user" } }) }));

const wrappers: ReturnType<typeof mount>[] = [];

afterEach(() => {
  wrappers.forEach((wrapper) => wrapper.unmount());
  wrappers.length = 0;
  document.body.replaceChildren();
});

async function mountEditor(historyOpen = false) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/admin/tools/:toolId", component: { render: () => null } }],
  });
  await router.push("/admin/tools/current");
  await router.isReady();
  let drawers!: ReturnType<typeof useScriptEditorDrawers>;
  const Editor = defineComponent({
    setup() {
      drawers = useScriptEditorDrawers({
        route: useRoute(),
        router: useRouter(),
        confirmDiscardChanges: () => true,
      });
      if (historyOpen) drawers.toggleHistoryDrawer();
      return () => h(EditorToolMenu, {
        activeToolId: "current",
        activeToolTitle: "Aktuellt verktyg",
        activeToolSlug: "current",
        canCreateTool: true,
      });
    },
  });
  const wrapper = mount(Editor, { attachTo: document.body, global: { plugins: [router, createPinia()] } });
  wrappers.push(wrapper);
  await flushPromises();
  const trigger = wrapper.get<HTMLButtonElement>('button[aria-haspopup="menu"]');

  async function openCreate() {
    trigger.element.focus();
    await trigger.trigger("click");
    await flushPromises();
    const create = wrapper.findAll("button").find((button) => button.text().includes("Skapa nytt"))!;
    create.element.focus();
    await create.trigger("click");
    await flushPromises();
    return document.querySelector<HTMLElement>('[role="dialog"]')!;
  }

  return { drawers, trigger, openCreate };
}

function pressKey(target: EventTarget, key: string) {
  const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
  target.dispatchEvent(event);
  return event;
}

describe("editor menu create-dialog focus ownership", () => {
  it("focuses the title after the menu closes, and returns to the trigger across repeated openings", async () => {
    const { trigger, openCreate } = await mountEditor();
    for (let cycle = 0; cycle < 2; cycle += 1) {
      const dialog = await openCreate();
      expect(document.activeElement).toBe(dialog.querySelector("input"));
      dialog.querySelector<HTMLButtonElement>('button[aria-label="Stäng"]')!.click();
      await flushPromises();
      expect(document.querySelector('[role="dialog"]')).toBeNull();
      expect(document.activeElement).toBe(trigger.element);
    }
  });

  it.each([false, true])("Escape in the dialog preserves editor chat and history (history open: %s)", async (historyOpen) => {
    const { drawers, openCreate } = await mountEditor(historyOpen);
    const dialog = await openCreate();
    const title = dialog.querySelector<HTMLInputElement>("input")!;
    title.focus();
    const escape = pressKey(title, "Escape");
    await flushPromises();
    expect(document.querySelector('[role="dialog"]')).toBeNull();
    expect(drawers.isChatCollapsed.value).toBe(false);
    expect(drawers.isHistoryDrawerOpen.value).toBe(historyOpen);
    expect(escape.defaultPrevented).toBe(true);
  });

  it("owns Escape from background focus only while the modal is open, leaving other keys alone", async () => {
    const { drawers, trigger, openCreate } = await mountEditor(true);
    const dialog = await openCreate();
    const ordinaryKey = pressKey(dialog.querySelector("input")!, "ArrowLeft");
    await flushPromises();
    expect(ordinaryKey.defaultPrevented).toBe(false);
    expect(document.querySelector('[role="dialog"]')).toBe(dialog);
    trigger.element.focus();
    const escape = pressKey(trigger.element, "Escape");
    await flushPromises();
    expect(document.querySelector('[role="dialog"]')).toBeNull();
    expect(drawers.isHistoryDrawerOpen.value).toBe(true);
    expect(drawers.isChatCollapsed.value).toBe(false);
    expect(escape.defaultPrevented).toBe(true);
    // Once the modal is gone the existing editor Escape action still works.
    pressKey(trigger.element, "Escape");
    expect(drawers.isHistoryDrawerOpen.value).toBe(false);
    pressKey(trigger.element, "Escape");
    expect(drawers.isChatCollapsed.value).toBe(true);
  });
});
