/**
 * Exam workspace slice test harness.
 *
 * Domain purpose:
 *   Shared native exam document builders and view interactions for the exam
 *   workspace slice specs (walking skeleton, exports, enrichment, reopen).
 *
 * Relationships:
 *   - Mounts `ExamWorkspaceView.vue` with Pinia, a memory router that
 *     carries the `/apps/exam-workspace` route, and a provided layout ref
 *     the spec can change to move between layouts.
 *   - Each spec owns its own `api/examWorkspace` module mock.
 */

import { createTestingPinia } from "@pinia/testing";
import { flushPromises, mount } from "@vue/test-utils";
import { vi } from "vitest";
import { ref } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";

import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
  NativeExamItem,
} from "../../api/examWorkspace";
import { buildFreeTextItem } from "../../test/examWorkspaceFixtures";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";

export { buildFreeTextItem } from "../../test/examWorkspaceFixtures";
import { buildSavedExamSummary } from "./exam-workspace/useExamWorkspaceDocument.specSupport";
import {
  EXAM_WORKSPACE_LAYOUT_KEY,
  type ExamWorkspaceLayout,
} from "./exam-workspace/useExamWorkspaceLayout";

export const EXAM_WORKSPACE_PATH = "/apps/exam-workspace";

export function buildDocument(): NativeExamDocument {
  const items: NativeExamItem[] = [
    buildFreeTextItem(1),
    {
      ...buildFreeTextItem(2),
      answer_key: { correct_choice_ids: ["choice_001"], match_pairs: [], origin: "source_provided" },
      choices: [
        { choice_id: "choice_001", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Avdunstning" }] }] },
        { choice_id: "choice_002", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Kondensation" }] }] },
        { choice_id: "choice_003", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Nederbörd" }] }] },
      ],
      kind: "single_choice",
    },
    {
      ...buildFreeTextItem(3),
      answer_key: {
        correct_choice_ids: ["choice_001", "choice_002"],
        match_pairs: [],
        origin: "machine_proposed",
      },
      choices: [
        { choice_id: "choice_001", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Syre" }] }] },
        { choice_id: "choice_002", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Kväve" }] }] },
        { choice_id: "choice_003", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Argon" }] }] },
      ],
      kind: "multiple_response",
      review: {
        confidence: 0.4,
        parse_origin: "llm_parsed",
        reasons: ["föreslaget facit behöver godkännas"],
        state: "review_required",
      },
    },
    {
      ...buildFreeTextItem(4),
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "machine_proposed" },
      body: [
        { heading_level: null, segments: [
            { kind: "text", marks: [], text: "Vatten kokar vid" },
            { gap_id: "gap_001", kind: "gap" },
            { kind: "text", marks: [], text: "grader." },
          ],
        },
      ],
      gaps: [{ accepted_values: ["100"], automatic_values: [], excluded_automatic_values: [], gap_id: "gap_001", options: [], correct_option_id: null }],
      kind: "gap_fill",
      review: {
        confidence: 0.5,
        parse_origin: "llm_parsed",
        reasons: ["luckan behöver godkända svar"],
        state: "review_required",
      },
    },
    buildFreeTextItem(5),
    buildFreeTextItem(6),
    buildFreeTextItem(7),
    buildFreeTextItem(8),
  ];

  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    instructions: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Besvara alla frågor." }] }],
    items,
    origin: {
      extractor_version: "docx-extractor-1",
      kind: "docx_import",
      source_filename: "NO_Prov_HT25.docx",
      source_sha256: "a".repeat(64),
    },
    parents: [],
    revision: 1,
    header: { tags: [] },
    schema_version: "native_exam_document_v6",
    title: "NO-prov HT25",
  };
}

/**
 * A saved document response for `lineage-1`. `conversion` is the import's
 * status the server reads with the document: a document fetched while an
 * import is followed always carries it, so the import's specs pass the status
 * their conversion poll returns for that revision.
 */
export function buildResponse(params: {
  conversion?: ExamWorkspaceConversionStatus | null;
  title?: string;
  version: number;
}): ExamWorkspaceDocumentResponse {
  const document = buildDocument();
  return {
    history_cursor: "00000000-0000-4000-8000-000000000001",
    conversion: params.conversion ?? null,
    document: {
      ...document,
      revision: params.version,
      title: params.title ?? document.title,
    },
    saved_document: {
      ...document,
      revision: params.version,
      title: params.title ?? document.title,
    },
    notes: [],
    summary: buildSavedExamSummary({
      name: params.title ?? document.title,
      saved_at: "2026-10-09T08:00:00Z",
      title: params.title ?? document.title,
      version: params.version,
    }),
  };
}

export async function mountExamWorkspace(
  query: Record<string, string> = {},
  layout: ExamWorkspaceLayout = "desktop",
  attachTo?: HTMLElement,
  pinia = createTestingPinia({ createSpy: vi.fn }),
) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ component: { template: "<div />" }, path: EXAM_WORKSPACE_PATH }],
  });
  await router.push({ path: EXAM_WORKSPACE_PATH, query });
  await router.isReady();
  const layoutRef = ref<ExamWorkspaceLayout>(layout);
  const wrapper = mount(ExamWorkspaceView, {
    attachTo,
    global: {
      plugins: [pinia, router],
      provide: { [EXAM_WORKSPACE_LAYOUT_KEY as symbol]: layoutRef },
    },
  });
  await flushPromises();
  return { layout: layoutRef, router, wrapper };
}

export type ViewWrapper = Awaited<ReturnType<typeof mountExamWorkspace>>["wrapper"];

export async function importFixtureDocument(wrapper: ViewWrapper) {
  const input = wrapper.find<HTMLInputElement>(
    '[data-test="exam-workspace-source-file-input"]',
  );
  Object.defineProperty(input.element, "files", {
    configurable: true,
    value: [
      new File(["prov"], "NO_Prov_HT25.docx", {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      }),
    ],
  });
  await input.trigger("change");
  await flushPromises();
}

export async function selectItemRow(wrapper: ViewWrapper, itemId: string) {
  await wrapper.find(`[data-test="exam-workspace-item-row-${itemId}"]`).trigger("click");
}

export async function saveDocument(wrapper: ViewWrapper) {
  await wrapper.find('[data-test="exam-workspace-save"]').trigger("click");
  await flushPromises();
}
