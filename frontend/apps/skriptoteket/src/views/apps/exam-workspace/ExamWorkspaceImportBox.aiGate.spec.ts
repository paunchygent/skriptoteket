/**
 * The import box's per-question "Konvertera igen" retry is admin-only until the
 * AI spend cap ships (TASK-SKRIPT-REP-0044 L3).
 *
 * Expected behavior:
 *   With role "user" or "contributor" the retry button and its type selector are
 *   disabled, the button carries the admin-only note (title, described-by and an
 *   inline note), and clicking emits nothing. With role "admin" or "superuser"
 *   the note is gone and the retry works.
 */

import { mount } from "@vue/test-utils";
import type { DOMWrapper, VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { AI_ADMIN_ONLY_NOTE } from "../../../composables/useAiAccess";
import { useAuthStore } from "../../../stores/auth";
import ExamWorkspaceImportBox from "./ExamWorkspaceImportBox.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";

type Role = "user" | "contributor" | "admin" | "superuser";

function findNotes(wrapper: VueWrapper): DOMWrapper<Element>[] {
  return wrapper
    .findAll("p, small, span")
    .filter((node) => node.text().trim() === AI_ADMIN_ONLY_NOTE);
}

function reviewItem(): NativeExamItem {
  return {
    ai_suggestion: null,
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

describe("ExamWorkspaceImportBox AI gate", () => {
  it.each(["user", "contributor"] as const)(
    "disables the retry, shows the note and emits nothing for role %s",
    async (role) => {
      signIn(pinia, role);
      const wrapper = mountBox(pinia);

      expect(wrapper.get('[data-test="exam-workspace-retry-kind"]').attributes("disabled")).toBeDefined();

      const notes = findNotes(wrapper);
      expect(notes).toHaveLength(1);
      const note = notes[0]!;
      expect(note.text()).toBe(AI_ADMIN_ONLY_NOTE);

      const button = wrapper.get('[data-test="exam-workspace-retry"]');
      expect(button.attributes("disabled")).toBeDefined();
      expect(button.attributes("title")).toBe(AI_ADMIN_ONLY_NOTE);
      expect(button.attributes("aria-describedby")).toBe(note.attributes("id"));
      await button.trigger("click");
      expect(wrapper.emitted("retry")).toBeUndefined();
      wrapper.unmount();
    },
  );

  it.each(["admin", "superuser"] as const)(
    "leaves the retry working without the note for role %s",
    async (role) => {
      signIn(pinia, role);
      const wrapper = mountBox(pinia);

      expect(findNotes(wrapper)).toHaveLength(0);
      expect(wrapper.get('[data-test="exam-workspace-retry-kind"]').attributes("disabled")).toBeUndefined();

      const button = wrapper.get('[data-test="exam-workspace-retry"]');
      expect(button.attributes("disabled")).toBeUndefined();
      await button.trigger("click");
      expect(wrapper.emitted("retry")).toEqual([["gap_fill"]]);
      wrapper.unmount();
    },
  );
});
