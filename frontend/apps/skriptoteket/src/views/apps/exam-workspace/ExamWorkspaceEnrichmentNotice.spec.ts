/**
 * Exam workspace enrichment notice.
 *
 * Expected behavior:
 *   The notice under the header shows the enrichment message, or the failed
 *   lost-job lookup with a `Försök igen` retry that reruns the session's
 *   lookup. It renders nothing while neither a message nor a lookup error
 *   is set.
 */

import { mount } from "@vue/test-utils";
import { computed, ref } from "vue";
import { describe, expect, it, vi } from "vitest";

import ExamWorkspaceEnrichmentNotice from "./ExamWorkspaceEnrichmentNotice.vue";
import type { useExamWorkspaceEnrichment } from "./useExamWorkspaceEnrichment";

type EnrichmentSession = ReturnType<typeof useExamWorkspaceEnrichment>;

function makeEnrichment(session: {
  message: string | null;
  lookupError: string | null;
  retry: () => Promise<void>;
}): EnrichmentSession {
  const message = ref(session.message);
  const lookupError = ref(session.lookupError);
  return {
    enrichmentLookupError: computed(() => lookupError.value),
    enrichmentMessage: computed(() => message.value),
    enrichmentStatus: computed(() => null),
    isEnrichmentPending: computed(() => false),
    isRequesting: computed(() => false),
    requestSuggestionForItem: () => Promise.resolve(),
    requestSuggestionsForAll: () => Promise.resolve(),
    retryEnrichmentLookup: session.retry,
  };
}

describe("ExamWorkspaceEnrichmentNotice", () => {
  it("shows the enrichment message without a retry button", () => {
    const wrapper = mount(ExamWorkspaceEnrichmentNotice, {
      props: {
        enrichment: makeEnrichment({
          message: "Facitförslagen tas fram …",
          lookupError: null,
          retry: () => Promise.resolve(),
        }),
      },
    });

    const notice = wrapper.get('[data-test="exam-workspace-enrichment"]');
    expect(notice.classes()).toContain("xw-notice");
    expect(notice.attributes("role")).toBe("status");
    expect(wrapper.get('[data-test="exam-workspace-enrichment-message"]').text()).toBe(
      "Facitförslagen tas fram …",
    );
    expect(wrapper.find('[data-test="exam-workspace-enrichment-lookup-error"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-enrichment-lookup-retry"]').exists()).toBe(false);
  });

  it("shows the lookup error with a retry that reruns the session lookup", async () => {
    const retry = vi.fn(() => Promise.resolve());
    const wrapper = mount(ExamWorkspaceEnrichmentNotice, {
      props: {
        enrichment: makeEnrichment({
          message: null,
          lookupError: "Kunde inte hämta väntande facitförslag.",
          retry,
        }),
      },
    });

    expect(wrapper.get('[data-test="exam-workspace-enrichment-lookup-error"]').text()).toBe(
      "Kunde inte hämta väntande facitförslag.",
    );
    const action = wrapper.get('[data-test="exam-workspace-enrichment-lookup-retry"]');
    expect(action.text()).toBe("Försök igen");

    await action.trigger("click");
    expect(retry).toHaveBeenCalledTimes(1);
  });

  it("renders nothing while neither message nor error is set", () => {
    const wrapper = mount(ExamWorkspaceEnrichmentNotice, {
      props: {
        enrichment: makeEnrichment({
          message: null,
          lookupError: null,
          retry: () => Promise.resolve(),
        }),
      },
    });

    expect(wrapper.find('[data-test="exam-workspace-enrichment"]').exists()).toBe(false);
  });
});
