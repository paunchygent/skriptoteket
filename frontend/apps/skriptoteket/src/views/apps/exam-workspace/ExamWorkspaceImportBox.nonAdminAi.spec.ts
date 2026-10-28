/**
 * The import box's per-question "Konvertera igen" retry runs for every
 * signed-in user.
 *
 * Expected behavior:
 *   With role "user" or "contributor" the retry button and its type selector
 *   are enabled, no admin-only note shows (inline, title or described-by),
 *   and clicking emits the retry.
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { useAuthStore } from "../../../stores/auth";
import ExamWorkspaceImportBox from "./ExamWorkspaceImportBox.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";

/** Distinctive fragment of the removed admin-only note; the full note must not render. */
const REMOVED_ADMIN_NOTE = "bara tillgängliga för administratörer";

type Role = "user" | "contributor";

function reviewItem(): NativeExamItem {
  return {
    ai_suggestion: null,
    answer_key_retry: "none",
    writing_lines: null,
    leftover_points_text: null,
    criteria: [],
    facit_text: null,
    import_record: {
      original_wording: { answer_key_text: null, question_text: "Förklara begreppet." },
      steps: [],
    },
    printed_label: null,
    print_order: [],
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Förklara begreppet." }] }],
    choices: [],
    gaps: [],
    kept_gaps: [],
    item_id: "item_001",
    kind: "free_text",
    match_left: [],
    match_right: [],
    points: 2,
    points_estimated: false,
    review: { confidence: 0.4, parse_origin: "llm_parsed", reasons: ["osäker tolkning"], state: "review_required" },
    retry_source: { chunks: [], context_chunks: [], owned_context_anchors: [], key_chunks: [], label_kind: "gap_fill" },
    sequence: 1,
    source_anchor: "body:0001",
    source_points: null,
    conflicting_source_points: [],
    suggested_kind: null,
    tick_points: null,
  };
}

function signIn(pinia: Pinia, role: Role): void {
  setActivePinia(pinia);
  useAuthStore().user = { id: "u1", email: "u@example.test", role, auth_provider: "local" };
}

function mountBox(pinia: Pinia) {
  return mount(ExamWorkspaceImportBox, {
    props: { item: reviewItem(), origin: "docx_import", open: true, disabled: false },
    global: {
      plugins: [pinia, examWorkspaceProvidersPlugin()],
    },
  });
}

let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
});

describe("ExamWorkspaceImportBox non-admin AI", () => {
  it.each(["user", "contributor"] as const)(
    "leaves the retry working without the admin-only note for role %s",
    async (role) => {
      signIn(pinia, role);
      const wrapper = mountBox(pinia);

      expect(wrapper.text()).not.toContain(REMOVED_ADMIN_NOTE);
      expect(wrapper.get('[data-test="exam-workspace-retry-kind"]').attributes("disabled")).toBeUndefined();

      const button = wrapper.get('[data-test="exam-workspace-retry"]');
      expect(button.attributes("disabled")).toBeUndefined();
      expect(button.attributes("title")).toBeUndefined();
      await button.trigger("click");
      expect(wrapper.emitted("retry")).toEqual([["gap_fill"]]);
      wrapper.unmount();
    },
  );
});
