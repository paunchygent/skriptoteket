/**
 * Shared setup for the ExamWorkspaceView guest-mode specs.
 *
 * The guest-mode view specs are split by responsibility (guest intake, AI
 * sign-in prompts, guest save controls); every split file builds its scenario
 * through this module so the fixtures stay identical. Each spec file keeps its
 * own `vi.mock` declarations because `vi.mock` calls are hoisted per file.
 */

import { createPinia } from "pinia";
import { flushPromises } from "@vue/test-utils";
import { ref } from "vue";
import { beforeAll, beforeEach, expect, vi, type Mock } from "vitest";

import type { NativeExamDocument, NativeExamItem } from "../../api/examWorkspace";
import { createTestRouter, mountWithContext } from "../../test/utils";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";
import { createGuestExamWorkspaceStore } from "./exam-workspace/examWorkspaceGuestStore";
import type { ExamWorkspaceGuestStoreDeps } from "./exam-workspace/examWorkspaceGuestStore";
import { createGuestPublicApiMocks } from "./exam-workspace/examWorkspaceGuestStore.specSupport";
import { createExamWorkspaceGuestDraftStorage } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import { createInMemoryExamWorkspaceGuestDraftStorage } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import {
  EXAM_WORKSPACE_LAYOUT_KEY,
  type ExamWorkspaceLayout,
} from "./exam-workspace/useExamWorkspaceLayout";

/** One teacher-transport spy per spec file; the guest view must never call them. */
export type TeacherApiMocks = Record<string, Mock>;

export function installGuestModeObjectUrls(): void {
  beforeAll(() => {
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:picture");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
  });
}

export function resetGuestModeTestState(teacherMocks: TeacherApiMocks): void {
  beforeEach(() => {
    for (const mock of Object.values(teacherMocks)) {
      mock.mockReset();
    }
    document.body.replaceChildren();
    window.history.replaceState({}, "", "/");
  });
}

export function textBody(text: string): NativeExamDocument["instructions"] {
  return [{ heading_level: null, segments: [{ kind: "text", marks: [], text }] }];
}

export function choice(choiceId: string, text: string) {
  return { body: textBody(text), choice_id: choiceId };
}

/** A keyed question without a key: its export blocker carries the AI fix. */
export function keylessItem(sequence: number, kind: "single_choice" | "multiple_response"): NativeExamItem {
  const itemId = `item_${String(sequence).padStart(3, "0")}`;
  return {
    ai_suggestion: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    body: textBody(`Fråga ${sequence}: välj rätt alternativ.`),
    choices: [choice("choice_001", "Avdunstning"), choice("choice_002", "Kondensation"), choice("choice_003", "Nederbörd")],
    criteria: [],
    facit_text: null,
    gaps: [],
    kept_gaps: [],
    import_record: null,
    item_id: itemId,
    kind,
    match_left: [],
    match_right: [],
    points: 2,
    points_estimated: false,
    print_order: [],
    printed_label: null,
    retry_source: null,
    review: { confidence: 0.9, parse_origin: "deterministic", reasons: [], state: "review_complete" },
    sequence,
    source_anchor: null,
    source_points: null,
    suggested_kind: null,
    tick_points: null,
    writing_lines: null,
    leftover_points_text: null,
  };
}

/** A converted question awaiting review with its stored source: shows Konvertera igen. */
export function retryItem(): NativeExamItem {
  return {
    ai_suggestion: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    body: textBody("Förklara begreppet."),
    choices: [],
    criteria: [],
    facit_text: null,
    gaps: [],
    kept_gaps: [],
    import_record: {
      original_wording: { answer_key_text: null, question_text: "Förklara begreppet." },
      steps: [],
    },
    item_id: "item_003",
    kind: "free_text",
    match_left: [],
    match_right: [],
    points: 2,
    points_estimated: false,
    print_order: [],
    printed_label: null,
    retry_source: {
      chunks: [
        {
          anchor: "body:0001",
          images: [],
          missing_images: [],
          kind: "question",
          marked_text: "Förklara begreppet.",
          paragraphs: [],
          runs: [],
          text: "Förklara begreppet.",
        },
      ],
      context_chunks: [],
      key_chunks: [],
      label_kind: "gap_fill",
      owned_context_anchors: [],
    },
    review: {
      confidence: 0.4,
      parse_origin: "llm_parsed",
      reasons: ["osäker tolkning"],
      state: "review_required",
    },
    sequence: 3,
    source_anchor: "body:0001",
    source_points: null,
    suggested_kind: null,
    tick_points: null,
    writing_lines: 8,
    leftover_points_text: null,
  };
}

export function blankDocument(): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    header: { tags: [] },
    instructions: [],
    items: [keylessItem(1, "single_choice"), keylessItem(2, "multiple_response"), retryItem()],
    origin: { kind: "docx_import" },
    parents: [],
    revision: 1,
    schema_version: "native_exam_document_v9",
    title: "Nytt prov",
  };
}

export type PublicApi = ExamWorkspaceGuestStoreDeps["api"];

export type GuestSetup = {
  guest: ReturnType<typeof createGuestExamWorkspaceStore>;
  publicMocks: ReturnType<typeof createGuestPublicApiMocks>;
  storage: ReturnType<typeof createExamWorkspaceGuestDraftStorage>;
};

export function setupGuest(): GuestSetup {
  const storage = createExamWorkspaceGuestDraftStorage({
    port: createInMemoryExamWorkspaceGuestDraftStorage(),
  });
  const publicMocks = createGuestPublicApiMocks();
  publicMocks.importPublicExamWorkspaceQti.mockResolvedValue({
    assets: {},
    document: blankDocument(),
    notes: [],
  });
  publicMocks.createPublicExamWorkspaceBlank.mockResolvedValue({
    document: blankDocument(),
    export_blockers: [],
  });
  publicMocks.getPublicExamCourseCatalog.mockResolvedValue({
    courses: [],
    generated_at: "2026-10-18T00:00:00Z",
    registered_course_keys: [],
  });
  const api: PublicApi = publicMocks;
  let counter = 0;
  const guest = createGuestExamWorkspaceStore({
    api,
    ids: {
      now: () => "2026-10-18T10:00:00.000Z",
      uuid: () => {
        counter += 1;
        return `10000000-0000-4000-8000-${String(counter).padStart(12, "0")}`;
      },
    },
    onLimit: () => undefined,
    storage,
  });
  return { guest, publicMocks, storage };
}

export type GuestWrapper = Awaited<ReturnType<typeof mountGuestView>>;

export async function mountGuestView(store: ReturnType<typeof createGuestExamWorkspaceStore>["store"]) {
  const layout = ref<ExamWorkspaceLayout>("desktop");
  const wrapper = mountWithContext(ExamWorkspaceView, {
    props: { store },
    global: {
      plugins: [createPinia(), createTestRouter()],
      provide: { [EXAM_WORKSPACE_LAYOUT_KEY]: layout },
    },
  });
  await flushPromises();
  return wrapper;
}

export function promptText(wrapper: GuestWrapper): string | null {
  const prompt = wrapper.find('[data-test="exam-workspace-sign-in-prompt"]');
  return prompt.exists() ? prompt.text() : null;
}

export async function chooseGuestFile(wrapper: GuestWrapper, file: File): Promise<void> {
  const input = wrapper.find<HTMLInputElement>(
    '[data-test="exam-workspace-source-file-input"]',
  );
  Object.defineProperty(input.element, "files", {
    configurable: true,
    value: [file],
  });
  await input.trigger("change");
  await flushPromises();
}

export function expectNoTeacherCalls(teacherMocks: TeacherApiMocks): void {
  for (const mock of Object.values(teacherMocks)) {
    expect(mock).not.toHaveBeenCalled();
  }
}
