import { describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, reactive } from "vue";
import type { Router } from "vue-router";

import { DEFAULT_COMPARE_FIELD, useEditorCompareState } from "./useEditorCompareState";

async function flushPromises(): Promise<void> {
  await nextTick();
  await Promise.resolve();
}

describe("useEditorCompareState", () => {
  it("does not touch the router when compare is not set", async () => {
    const route = reactive({ query: { foo: "bar" } });
    const router = {
      replace: vi.fn().mockResolvedValue(undefined),
    } as unknown as Router;

    const scope = effectScope();
    scope.run(() => {
      useEditorCompareState({ route: route as never, router });
    });

    await flushPromises();

    expect(router.replace).not.toHaveBeenCalled();

    scope.stop();
  });

  it("sets field=tool.py when compare is present and field is missing", async () => {
    const route = reactive({ query: { foo: "bar", compare: "ver-1" } });
    const router = {
      replace: vi.fn().mockResolvedValue(undefined),
    } as unknown as Router;

    const scope = effectScope();
    scope.run(() => {
      useEditorCompareState({ route: route as never, router });
    });

    await flushPromises();

    expect(router.replace).toHaveBeenCalledTimes(1);
    expect(router.replace).toHaveBeenCalledWith({
      query: {
        foo: "bar",
        compare: "ver-1",
        field: DEFAULT_COMPARE_FIELD,
      },
    });

    scope.stop();
  });

  it("does not override field when compare is present and field is valid", async () => {
    const route = reactive({ query: { compare: "ver-1", field: "entrypoint.txt" } });
    const router = {
      replace: vi.fn().mockResolvedValue(undefined),
    } as unknown as Router;

    const scope = effectScope();
    scope.run(() => {
      useEditorCompareState({ route: route as never, router });
    });

    await flushPromises();

    expect(router.replace).not.toHaveBeenCalled();

    scope.stop();
  });
});
