/**
 * Exam workspace slice test harness.
 *
 * Domain purpose:
 *   Shared native exam document builders and view interactions for the exam
 *   workspace slice specs (walking skeleton, exports, enrichment, reopen).
 *
 * Relationships:
 *   - Mounts `ExamWorkspaceView.vue` with Pinia and a memory router that
 *     carries the `/apps/exam-workspace` route.
 *   - Each spec owns its own `api/examWorkspace` module mock.
 */

import { createTestingPinia } from "@pinia/testing";
import { flushPromises, mount } from "@vue/test-utils";
import { vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
  NativeExamItem,
} from "../../api/examWorkspace";
import ExamWorkspaceView from "./ExamWorkspaceView.vue";

export const EXAM_WORKSPACE_PATH = "/apps/exam-workspace";

export function buildFreeTextItem(sequence: number): NativeExamItem {
  return {
    answer_key: { correct_choice_ids: [], origin: "not_applicable" },
    body: [
      { segments: [{ kind: "text", text: `Fråga ${sequence}: beskriv med egna ord.` }] },
    ],
    choices: [],
    gaps: [],
    item_id: `item_${String(sequence).padStart(3, "0")}`,
    kind: "free_text",
    points: 2,
    review: {
      confidence: 0.9,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence,
    source_anchor: null,
    title: `Fråga ${sequence}`,
  };
}

export function buildDocument(): NativeExamDocument {
  const items: NativeExamItem[] = [
    buildFreeTextItem(1),
    {
      ...buildFreeTextItem(2),
      answer_key: { correct_choice_ids: ["choice_a"], origin: "source_provided" },
      choices: [
        { choice_id: "choice_a", text: "Avdunstning" },
        { choice_id: "choice_b", text: "Kondensation" },
        { choice_id: "choice_c", text: "Nederbörd" },
      ],
      kind: "single_choice",
      title: "Vattnets kretslopp",
    },
    {
      ...buildFreeTextItem(3),
      answer_key: {
        correct_choice_ids: ["choice_a", "choice_b"],
        origin: "machine_proposed",
      },
      choices: [
        { choice_id: "choice_a", text: "Syre" },
        { choice_id: "choice_b", text: "Kväve" },
        { choice_id: "choice_c", text: "Argon" },
      ],
      kind: "multiple_response",
      review: {
        confidence: 0.4,
        parse_origin: "llm_parsed",
        reasons: ["föreslaget facit behöver godkännas"],
        state: "review_required",
      },
      title: "Luftens gaser",
    },
    {
      ...buildFreeTextItem(4),
      body: [
        {
          segments: [
            { kind: "text", text: "Vatten kokar vid" },
            { gap_id: "gap_001", kind: "gap" },
            { kind: "text", text: "grader." },
          ],
        },
      ],
      gaps: [{ accepted_values: ["100"], gap_id: "gap_001", hint: null }],
      kind: "gap_fill",
      review: {
        confidence: 0.5,
        parse_origin: "llm_parsed",
        reasons: ["luckan behöver godkända svar"],
        state: "review_required",
      },
      title: "Kokpunkt",
    },
    buildFreeTextItem(5),
    buildFreeTextItem(6),
    buildFreeTextItem(7),
    buildFreeTextItem(8),
  ];

  return {
    assets: [],
    document_id: "doc-1",
    instructions: ["Besvara alla frågor."],
    items,
    origin: {
      extractor_version: "docx-extractor-1",
      kind: "docx_import",
      source_filename: "NO_Prov_HT25.docx",
      source_sha256: "abc123",
    },
    revision: 1,
    schema_version: "native_exam_document_v1",
    title: "NO-prov HT25",
  };
}

export function buildResponse(params: {
  title?: string;
  version: number;
}): ExamWorkspaceDocumentResponse {
  const document = buildDocument();
  return {
    document: {
      ...document,
      revision: params.version,
      title: params.title ?? document.title,
    },
    notes: [],
    summary: {
      lineage_id: "lineage-1",
      name: params.title ?? document.title,
      saved_at: "2026-10-09T08:00:00Z",
      vault_file_id: "file-1",
      version: params.version,
    },
  };
}

export async function mountExamWorkspace(query: Record<string, string> = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ component: { template: "<div />" }, path: EXAM_WORKSPACE_PATH }],
  });
  await router.push({ path: EXAM_WORKSPACE_PATH, query });
  await router.isReady();
  const wrapper = mount(ExamWorkspaceView, {
    global: { plugins: [createTestingPinia({ createSpy: vi.fn }), router] },
  });
  await flushPromises();
  return { router, wrapper };
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
