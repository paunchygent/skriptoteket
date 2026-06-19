/**
 * Exam Converter authenticated route-mode behavior.
 *
 * Slice purpose:
 *   Prove the authenticated `documents.conversion_hub` host can deep-link to
 *   Exam Converter or transcript mode through route query state while keeping
 *   UI-inspection fixtures exam-only.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { nextTick, reactive } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";

type TestRouteQuery = Record<string, string | null | string[]>;

const routeMocks = vi.hoisted(() => ({
  route: null as { query: TestRouteQuery } | null,
  router: {
    replace: vi.fn(),
  },
}));

vi.mock("vue-router", () => ({
  useRoute: () => routeMocks.route,
  useRouter: () => routeMocks.router,
}));

beforeEach(() => {
  routeMocks.route = reactive({ query: {} });
  routeMocks.router.replace.mockReset();
  routeMocks.router.replace.mockImplementation((location: { query?: TestRouteQuery }) => {
    if (location.query) {
      routeMocks.route!.query = location.query;
    }
    return Promise.resolve();
  });
});

function setRouteQuery(query: TestRouteQuery): void {
  routeMocks.route = reactive({ query });
}

describe("ExamConverterAuthenticatedView route mode", () => {
  it("opens transcript mode from the authenticated route query without rewriting the URL", () => {
    setRouteQuery({ mode: "transcript" });

    const wrapper = mount(ExamConverterAuthenticatedView);

    expect(wrapper.find('[data-test="transcript-host-layout"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-converter-workflow-rail-shell"]').exists()).toBe(
      false,
    );
    expect(
      wrapper.get('[data-test="conversion-hub-mode-transcript"]').attributes("aria-pressed"),
    ).toBe("true");
    expect(routeMocks.router.replace).not.toHaveBeenCalled();
  });

  it("opens exam mode from the authenticated route query without rewriting the URL", () => {
    setRouteQuery({ mode: "exam", source: "dashboard" });

    const wrapper = mount(ExamConverterAuthenticatedView);

    expect(wrapper.find('[data-test="exam-converter-workflow-rail-shell"]').exists()).toBe(
      true,
    );
    expect(wrapper.find('[data-test="transcript-host-layout"]').exists()).toBe(false);
    expect(
      wrapper.get('[data-test="conversion-hub-mode-exam"]').attributes("aria-pressed"),
    ).toBe("true");
    expect(routeMocks.router.replace).not.toHaveBeenCalled();
  });

  it.each<[string, TestRouteQuery]>([
    ["absent", {}],
    ["invalid", { mode: "audio" }],
    ["empty", { mode: "" }],
    ["repeated", { mode: ["exam", "transcript"] }],
    ["array-valued", { mode: ["transcript"] }],
  ])(
    "defaults %s mode query state to exam without canonicalizing the URL",
    (_, query) => {
      setRouteQuery(query);

      const wrapper = mount(ExamConverterAuthenticatedView);

      expect(wrapper.find('[data-test="exam-converter-workflow-rail-shell"]').exists()).toBe(
        true,
      );
      expect(wrapper.find('[data-test="transcript-host-layout"]').exists()).toBe(false);
      expect(routeMocks.router.replace).not.toHaveBeenCalled();
    },
  );

  it("writes selected tab mode into the query while preserving unrelated keys", async () => {
    setRouteQuery({
      debug: "1",
      mode: "exam",
      preview: null,
      source: ["dashboard", "favorites"],
    });
    const wrapper = mount(ExamConverterAuthenticatedView);

    await wrapper.get('[data-test="conversion-hub-mode-transcript"]').trigger("click");
    await nextTick();

    expect(routeMocks.router.replace).toHaveBeenCalledWith({
      query: {
        debug: "1",
        mode: "transcript",
        preview: null,
        source: ["dashboard", "favorites"],
      },
    });
    expect(wrapper.find('[data-test="transcript-host-layout"]').exists()).toBe(true);

    await wrapper.get('[data-test="conversion-hub-mode-exam"]').trigger("click");

    expect(routeMocks.router.replace).toHaveBeenLastCalledWith({
      query: {
        debug: "1",
        mode: "exam",
        preview: null,
        source: ["dashboard", "favorites"],
      },
    });
  });

  it("keeps exam UI-inspection fixtures exam-only and skips mode query writes", async () => {
    setRouteQuery({ mode: "transcript", source: "inspection" });
    const wrapper = mount(ExamConverterAuthenticatedView, {
      props: { inspectionFixtureId: "complete-qti-ready" },
    });

    await flushPromises();

    expect(wrapper.find('[data-test="exam-converter-workflow-rail-shell"]').exists()).toBe(
      true,
    );
    expect(wrapper.find('[data-test="transcript-host-layout"]').exists()).toBe(false);

    await wrapper.get('[data-test="conversion-hub-mode-transcript"]').trigger("click");

    expect(routeMocks.router.replace).not.toHaveBeenCalled();
  });
});
