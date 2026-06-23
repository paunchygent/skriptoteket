/**
 * Exam Converter authenticated presentation identity behavior.
 *
 * Slice purpose:
 *   Prove canonical protected Exam Converter and Audio Transcription entries
 *   render as separate teacher-facing identities while legacy query residue is
 *   ignored by the generic backend app host.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { reactive } from "vue";
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
  it("renders canonical Audio Transcription identity without shared mode tabs", () => {
    const wrapper = mount(ExamConverterAuthenticatedView, {
      props: { presentationMode: "transcript" },
    });

    expect(wrapper.find('[data-test="transcript-host-layout"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-converter-workflow-rail-shell"]').exists()).toBe(
      false,
    );
    expect(wrapper.find('[data-test="conversion-hub-mode-exam"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="conversion-hub-mode-transcript"]').exists()).toBe(false);
    expect(routeMocks.router.replace).not.toHaveBeenCalled();
  });

  it("renders canonical Exam Converter identity without shared mode tabs", () => {
    const wrapper = mount(ExamConverterAuthenticatedView, {
      props: { presentationMode: "exam" },
    });

    expect(wrapper.find('[data-test="exam-converter-workflow-rail-shell"]').exists()).toBe(
      true,
    );
    expect(wrapper.find('[data-test="transcript-host-layout"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="conversion-hub-mode-exam"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="conversion-hub-mode-transcript"]').exists()).toBe(false);
    expect(routeMocks.router.replace).not.toHaveBeenCalled();
  });

  it("ignores transcript mode query residue and renders the default Exam Converter host", () => {
    setRouteQuery({ mode: "transcript" });

    const wrapper = mount(ExamConverterAuthenticatedView);

    expect(wrapper.find('[data-test="exam-converter-workflow-rail-shell"]').exists()).toBe(
      true,
    );
    expect(wrapper.find('[data-test="transcript-host-layout"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="conversion-hub-mode-exam"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="conversion-hub-mode-transcript"]').exists()).toBe(false);
    expect(routeMocks.router.replace).not.toHaveBeenCalled();
  });

  it("ignores exam mode query residue and renders the default Exam Converter host", () => {
    setRouteQuery({ mode: "exam", source: "dashboard" });

    const wrapper = mount(ExamConverterAuthenticatedView);

    expect(wrapper.find('[data-test="exam-converter-workflow-rail-shell"]').exists()).toBe(
      true,
    );
    expect(wrapper.find('[data-test="transcript-host-layout"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="conversion-hub-mode-exam"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="conversion-hub-mode-transcript"]').exists()).toBe(false);
    expect(routeMocks.router.replace).not.toHaveBeenCalled();
  });

  it.each<[string, TestRouteQuery]>([
    ["absent", {}],
    ["invalid", { mode: "audio" }],
    ["empty", { mode: "" }],
    ["repeated", { mode: ["exam", "transcript"] }],
    ["array-valued", { mode: ["transcript"] }],
  ])(
    "defaults %s query residue to exam without canonicalizing the URL",
    (_, query) => {
      setRouteQuery(query);

      const wrapper = mount(ExamConverterAuthenticatedView);

      expect(wrapper.find('[data-test="exam-converter-workflow-rail-shell"]').exists()).toBe(
        true,
      );
      expect(wrapper.find('[data-test="transcript-host-layout"]').exists()).toBe(false);
      expect(wrapper.find('[data-test="conversion-hub-mode-exam"]').exists()).toBe(false);
      expect(wrapper.find('[data-test="conversion-hub-mode-transcript"]').exists()).toBe(false);
      expect(routeMocks.router.replace).not.toHaveBeenCalled();
    },
  );

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
    expect(wrapper.find('[data-test="conversion-hub-mode-exam"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="conversion-hub-mode-transcript"]').exists()).toBe(false);

    expect(routeMocks.router.replace).not.toHaveBeenCalled();
  });
});
