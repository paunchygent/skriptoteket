import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent, nextTick, ref } from "vue";
import { mount } from "@vue/test-utils";
import { RouterView, createMemoryHistory, createRouter, useRoute, useRouter } from "vue-router";

import { useScriptEditorDrawers } from "./useScriptEditorDrawers";

async function flushPromises(): Promise<void> {
  await nextTick();
  await Promise.resolve();
}

async function mountHarness() {
  const editorToolId = ref("tool-1");
  const canEditTaxonomy = ref(true);
  const canEditMaintainers = ref(true);
  const loadMaintainers = vi.fn().mockResolvedValue(undefined);
  const confirmDiscardChanges = vi.fn().mockReturnValue(true);

  const TestComponent = defineComponent({
    name: "TestScriptEditorDrawers",
    setup() {
      return useScriptEditorDrawers({
        route: useRoute(),
        router: useRouter(),
        editorToolId,
        canEditTaxonomy,
        canEditMaintainers,
        loadMaintainers,
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
    editorToolId,
    canEditTaxonomy,
    canEditMaintainers,
    loadMaintainers,
    confirmDiscardChanges,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useScriptEditorDrawers", () => {
  it("loads maintainers when opening the maintainers drawer", async () => {
    const { vm, loadMaintainers, wrapper } = await mountHarness();

    vm.toggleMaintainersDrawer();
    await flushPromises();

    expect(vm.activeDrawer).toBe("maintainers");
    expect(loadMaintainers).toHaveBeenCalledWith("tool-1");

    vm.toggleMaintainersDrawer();
    await flushPromises();

    expect(vm.activeDrawer).toBeNull();
    expect(loadMaintainers).toHaveBeenCalledTimes(1);

    wrapper.unmount();
  });

  it("closes non-history drawers on route navigation", async () => {
    const { vm, router, wrapper } = await mountHarness();

    vm.toggleMetadataDrawer();
    await flushPromises();
    expect(vm.activeDrawer).toBe("metadata");

    await router.push({ path: "/editor", query: { foo: "bar", q: "1" } });
    await flushPromises();
    expect(vm.activeDrawer).toBeNull();

    vm.toggleHistoryDrawer();
    await flushPromises();
    expect(vm.activeDrawer).toBe("history");

    await router.push({ path: "/editor", query: { foo: "bar", q: "2" } });
    await flushPromises();
    expect(vm.activeDrawer).toBe("history");

    wrapper.unmount();
  });

  it("closes the drawer on Escape", async () => {
    const { vm, wrapper } = await mountHarness();

    vm.toggleHistoryDrawer();
    await flushPromises();
    expect(vm.activeDrawer).toBe("history");

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await flushPromises();
    expect(vm.activeDrawer).toBeNull();

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
