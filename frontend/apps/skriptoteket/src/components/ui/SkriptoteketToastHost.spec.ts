import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { useToastStore } from "../../stores/toast";
import SkriptoteketToastHost from "./SkriptoteketToastHost.vue";

function mountHost() {
  return mount(SkriptoteketToastHost, {
    global: { plugins: [createPinia()], stubs: { teleport: true } },
  });
}

describe("SkriptoteketToastHost", () => {
  let wrapper: ReturnType<typeof mountHost>;

  beforeEach(() => {
    vi.useFakeTimers();
    wrapper = mountHost();
  });

  afterEach(() => {
    useToastStore().dismissAll();
    wrapper.unmount();
    vi.useRealTimers();
  });

  function renderedMessages() {
    return wrapper.findAll("article p").map((message) => message.text());
  }

  it("passes newest-first order to the bottom host without changing FIFO eviction", async () => {
    const store = useToastStore();
    for (const message of ["A", "B", "C"]) {
      store.info(message, { durationMs: 0 });
    }
    await nextTick();

    expect(renderedMessages()).toEqual(["C", "B", "A"]);
    expect(store.toasts.map((toast) => toast.message)).toEqual(["A", "B", "C"]);
    expect(wrapper.get('[data-ui="toast-host"]').attributes("data-placement")).toBe("bottom");

    store.info("D", { durationMs: 0 });
    await nextTick();

    expect(renderedMessages()).toEqual(["D", "C", "B"]);
    expect(store.toasts.map((toast) => toast.message)).toEqual(["B", "C", "D"]);
  });

  it("dismisses only the id belonging to the selected toast", async () => {
    const store = useToastStore();
    const ids = ["A", "B", "C"].map((message) => store.info(message, { durationMs: 0 }));
    await nextTick();

    const middleToast = wrapper.findAll("article").find((toast) => toast.get("p").text() === "B");
    expect(middleToast).toBeDefined();
    await middleToast!.get('button[aria-label="Stäng avisering"]').trigger("click");

    expect(store.toasts.map((toast) => toast.id)).toEqual([ids[0], ids[2]]);
    expect(renderedMessages()).toEqual(["C", "A"]);
  });

  it("removes only the expired entry when a newer toast has a shorter lifetime", async () => {
    const store = useToastStore();
    const a = store.info("A", { durationMs: 10_000 });
    store.warning("B", { durationMs: 1_000 });
    const c = store.success("C", { durationMs: 0 });
    await nextTick();

    vi.advanceTimersByTime(999);
    await nextTick();
    expect(renderedMessages()).toEqual(["C", "B", "A"]);

    vi.advanceTimersByTime(1);
    await nextTick();
    expect(store.toasts.map((toast) => toast.id)).toEqual([a, c]);
    expect(renderedMessages()).toEqual(["C", "A"]);

    vi.advanceTimersByTime(9_000);
    await nextTick();
    expect(store.toasts.map((toast) => toast.id)).toEqual([c]);
    expect(renderedMessages()).toEqual(["C"]);
  });
});
