import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent, nextTick, ref } from "vue";
import { mount } from "@vue/test-utils";
import { RouterView, createMemoryHistory, createRouter } from "vue-router";

import { useUnsavedChangesGuards } from "./useUnsavedChangesGuards";

async function flushPromises(): Promise<void> {
  await nextTick();
  await Promise.resolve();
}

async function mountHarness() {
  const hasDirtyChanges = ref(false);
  const isSaving = ref(false);

  const Guarded = defineComponent({
    name: "TestUnsavedChangesGuards",
    setup() {
      return useUnsavedChangesGuards({ hasDirtyChanges, isSaving });
    },
    template: "<div />",
  });

  const Other = { template: "<div />" };

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/a", component: Guarded },
      { path: "/b", component: Other },
    ],
  });

  await router.push("/a");
  await router.isReady();

  const wrapper = mount(RouterView, { global: { plugins: [router] } });
  await flushPromises();

  const guardedWrapper = wrapper.findComponent({ name: "TestUnsavedChangesGuards" });
  return { wrapper, router, guardedWrapper, hasDirtyChanges, isSaving };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useUnsavedChangesGuards", () => {
  it("registers and unregisters the beforeunload handler", async () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    const removeSpy = vi.spyOn(window, "removeEventListener");

    const { wrapper } = await mountHarness();

    const addCall = addSpy.mock.calls.find(([event]) => event === "beforeunload");
    expect(addCall).toBeTruthy();
    const handler = addCall?.[1];
    expect(typeof handler).toBe("function");

    wrapper.unmount();

    const removed = removeSpy.mock.calls.some(
      ([event, removedHandler]) => event === "beforeunload" && removedHandler === handler,
    );
    expect(removed).toBe(true);
  });

  it("blocks unload when there are unsaved changes", async () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    const { hasDirtyChanges, isSaving, wrapper } = await mountHarness();

    const addCall = addSpy.mock.calls.find(([event]) => event === "beforeunload");
    const handler = addCall?.[1] as ((event: BeforeUnloadEvent) => void) | undefined;
    expect(handler).toBeTypeOf("function");

    const event = { preventDefault: vi.fn(), returnValue: undefined } as unknown as BeforeUnloadEvent;

    hasDirtyChanges.value = false;
    isSaving.value = false;
    handler?.(event);
    expect(event.preventDefault).not.toHaveBeenCalled();

    hasDirtyChanges.value = true;
    isSaving.value = false;
    handler?.(event);
    expect(event.preventDefault).toHaveBeenCalled();
    expect(event.returnValue).toBe("");

    wrapper.unmount();
  });

  it("gates confirmation prompts behind blocking unsaved changes", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const { guardedWrapper, hasDirtyChanges, isSaving, wrapper } = await mountHarness();

    const vm = guardedWrapper.vm as unknown as ReturnType<typeof useUnsavedChangesGuards>;

    hasDirtyChanges.value = false;
    isSaving.value = false;
    expect(vm.confirmDiscardChanges("hello")).toBe(true);
    expect(confirmSpy).not.toHaveBeenCalled();

    hasDirtyChanges.value = true;
    isSaving.value = true;
    expect(vm.confirmDiscardChanges("hello")).toBe(true);
    expect(confirmSpy).not.toHaveBeenCalled();

    hasDirtyChanges.value = true;
    isSaving.value = false;
    confirmSpy.mockReturnValueOnce(false);
    expect(vm.confirmDiscardChanges("hello")).toBe(false);
    expect(confirmSpy).toHaveBeenCalledWith("hello");

    wrapper.unmount();
  });

  it("prompts on route leave with the expected Swedish message", async () => {
    const confirmSpy = vi.spyOn(window, "confirm");
    const { router, hasDirtyChanges, isSaving, wrapper } = await mountHarness();

    hasDirtyChanges.value = true;
    isSaving.value = false;

    confirmSpy.mockReturnValueOnce(false);
    await router.push("/b");
    expect(router.currentRoute.value.path).toBe("/a");
    expect(confirmSpy).toHaveBeenCalledWith("Du har osparade ändringar. Vill du lämna sidan?");

    confirmSpy.mockReturnValueOnce(true);
    await router.push("/b");
    expect(router.currentRoute.value.path).toBe("/b");

    wrapper.unmount();
  });
});
