import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { RouterView, createMemoryHistory, createRouter, useRoute, useRouter } from "vue-router";

import { useScriptEditorDrawers } from "./useScriptEditorDrawers";

async function flushPromises(): Promise<void> {
  await nextTick();
  await Promise.resolve();
}

async function mountHarness() {
  const confirmDiscardChanges = vi.fn().mockReturnValue(true);

  const TestComponent = defineComponent({
    name: "TestScriptEditorDrawers",
    setup() {
      return useScriptEditorDrawers({
        route: useRoute(),
        router: useRouter(),
        confirmDiscardChanges,
      });
    },
    template: "<div />",
  });

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/editor", component: TestComponent }],
  });

  await router.push({ path: "/editor", query: { foo: "bar" } });
  await router.isReady();

  const wrapper = mount(RouterView, { global: { plugins: [router] } });
  await flushPromises();

  const drawersWrapper = wrapper.findComponent({ name: "TestScriptEditorDrawers" });
  const vm = drawersWrapper.vm as unknown as ReturnType<typeof useScriptEditorDrawers>;
  return {
    wrapper,
    router,
    vm,
    confirmDiscardChanges,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useScriptEditorDrawers", () => {
  it("defaults to open chat and closed history", async () => {
    const { vm, router, wrapper } = await mountHarness();

    expect(vm.isChatDrawerOpen).toBe(true);
    expect(vm.isHistoryDrawerOpen).toBe(false);
    expect(vm.isChatCollapsed).toBe(false);

    await router.push({ path: "/editor", query: { foo: "bar", version: "ver-1" } });
    await flushPromises();

    expect(vm.isChatDrawerOpen).toBe(true);
    expect(vm.isHistoryDrawerOpen).toBe(false);
    expect(vm.isChatCollapsed).toBe(false);

    wrapper.unmount();
  });

  it("toggles history and collapsed states", async () => {
    const { vm, wrapper } = await mountHarness();

    vm.toggleChatCollapsed();
    await flushPromises();
    expect(vm.isChatCollapsed).toBe(true);

    vm.toggleChatCollapsed();
    await flushPromises();
    expect(vm.isChatCollapsed).toBe(false);

    vm.toggleHistoryDrawer();
    await flushPromises();
    expect(vm.isHistoryDrawerOpen).toBe(true);
    expect(vm.isChatDrawerOpen).toBe(true);

    vm.closeDrawer();
    await flushPromises();
    expect(vm.isHistoryDrawerOpen).toBe(false);
    expect(vm.isChatDrawerOpen).toBe(true);

    vm.closeDrawer();
    await flushPromises();
    expect(vm.isChatDrawerOpen).toBe(true);
    expect(vm.isChatCollapsed).toBe(true);

    wrapper.unmount();
  });

  it("resets history and collapse on navigation", async () => {
    const { vm, router, wrapper } = await mountHarness();

    vm.toggleHistoryDrawer();
    vm.toggleChatCollapsed();
    await flushPromises();

    await router.push({ path: "/editor", query: { foo: "bar", version: "ver-2" } });
    await flushPromises();

    expect(vm.isHistoryDrawerOpen).toBe(false);
    expect(vm.isChatDrawerOpen).toBe(true);
    expect(vm.isChatCollapsed).toBe(false);

    wrapper.unmount();
  });

  it("closes history before chat on Escape", async () => {
    const { vm, wrapper } = await mountHarness();

    vm.toggleHistoryDrawer();
    await flushPromises();
    expect(vm.isHistoryDrawerOpen).toBe(true);

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await flushPromises();
    expect(vm.isHistoryDrawerOpen).toBe(false);
    expect(vm.isChatDrawerOpen).toBe(true);
    expect(vm.isChatCollapsed).toBe(false);

    wrapper.unmount();
  });

  it("updates router query when selecting a history version", async () => {
    const { vm, router, confirmDiscardChanges, wrapper } = await mountHarness();
    const replaceSpy = vi.spyOn(router, "replace");

    confirmDiscardChanges.mockReturnValueOnce(false);
    vm.selectHistoryVersion("ver-1");
    await flushPromises();
    expect(replaceSpy).not.toHaveBeenCalled();

    confirmDiscardChanges.mockReturnValueOnce(true);
    vm.selectHistoryVersion("ver-2");
    await flushPromises();

    expect(confirmDiscardChanges).toHaveBeenCalledWith(
      "Du har osparade ändringar. Vill du byta version?",
    );
    expect(replaceSpy).toHaveBeenCalledWith({
      query: {
        foo: "bar",
        version: "ver-2",
      },
    });

    wrapper.unmount();
  });
});
