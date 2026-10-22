/**
 * Exam workspace picture intake lifetime (TASK-SKRIPT-39-10-04, repair R5 for
 * review F3).
 *
 * Expected behavior:
 *   One intake operation belongs to the opening and live target it started
 *   in. A file read that started in exam A and resolves after exam B (with a
 *   reused item id) is installed declares nothing, places nothing, and leaves
 *   the notice unchanged: B's question body and registry are unchanged.
 */

import { describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick, shallowRef } from "vue";
import { flushPromises, mount } from "@vue/test-utils";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import { createExamWorkspaceNewPictures } from "./examWorkspaceNewPictures";
import type { PictureIntake } from "./examWorkspacePictureIntake";
import {
  createExamWorkspacePictureService,
  provideExamWorkspacePictures,
} from "./examWorkspacePictureService";
import type { RichTextTarget } from "./examWorkspaceRichTextTarget";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import { exam } from "./examWorkspaceGuestStore.specSupport";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";

describe("picture intake lifetime across openings", () => {
  it("keeps a deferred read out of the newly opened exam with a reused item id", async () => {
    vi.stubGlobal(
      "URL",
      class extends URL {
        static createObjectURL(): string {
          return "blob:probe";
        }

        static revokeObjectURL(): void {}
      },
    );
    const A = {
      ...exam("A"),
      instructions: [
        { heading_level: null, segments: [{ kind: "text" as const, marks: [], text: "Instruction A" }] },
      ],
    };
    const B = {
      ...exam("B"),
      document_id: "00000000-0000-4000-8000-000000000002",
      instructions: [
        { heading_level: null, segments: [{ kind: "text" as const, marks: [], text: "Instruction B" }] },
      ],
    };
    expect(A.items[0]!.item_id).toBe(B.items[0]!.item_id);
    const document = shallowRef<NativeExamDocument>(A);
    const newPictures = createExamWorkspaceNewPictures(() => document.value);
    let resolve!: (value: PictureIntake) => void;
    const openingA: ExamWorkspaceOpening = { lineageId: "lineage-a" };
    const openingB: ExamWorkspaceOpening = { lineageId: "lineage-b" };
    let current: ExamWorkspaceOpening = openingA;
    const service = createExamWorkspacePictureService({
      document: () => document.value,
      newPictures,
      canEdit: () => true,
      opening: () => current,
      isOpen: (opening) => opening === current,
      maxExamBytes: async () => 20_000_000,
      read: () =>
        new Promise<PictureIntake>((done) => {
          resolve = done;
        }),
    });
    const Host = defineComponent({
      setup() {
        provideExamWorkspacePictures(service);
        provideRichTextTargetRegistry();
        return () =>
          h(ExamWorkspaceBodyEditor, {
            item: document.value.items[0]!,
            disabled: false,
            onUpdateBody: (
              id: string,
              body: NativeExamDocument["items"][number]["body"],
            ) => {
              document.value = newPictures.withDeclared({
                ...document.value,
                items: document.value.items.map((item) =>
                  item.item_id === id ? { ...item, body } : item,
                ),
              });
            },
          });
      },
    });
    const wrapper = mount(Host, { attachTo: globalThis.document.body });
    try {
      await nextTick();
      await nextTick();
      const rich = wrapper.findComponent({ name: "ExamWorkspaceRichTextEditor" });
      const target = rich.vm.$.exposed?.target as RichTextTarget;
      expect(target).toBeDefined();

      const pending = service.add(target, [new File(["x"], "A.png")]);
      await flushPromises();
      current = openingB;
      document.value = B;
      newPictures.reset();
      await nextTick();
      await nextTick();
      const asset = {
        asset_id: "asset_0000000000000001",
        sha256: "0".repeat(64),
        media_type: "image/png" as const,
        byte_length: 1,
        width: 1,
        height: 1,
      };
      resolve({ kind: "picture", asset, blob: new Blob(["x"]) });
      await pending;
      await nextTick();

      expect(document.value.document_id).toBe(B.document_id);
      expect(document.value.assets.map((entry) => entry.asset_id)).not.toContain(asset.asset_id);
      expect(
        document.value.items[0]!.body.flatMap((paragraph) => paragraph.segments).some(
          (segment) => segment.kind === "asset",
        ),
      ).toBe(false);
      expect(service.notice.value).toBeNull();
    } finally {
      wrapper.unmount();
      newPictures.reset();
      vi.unstubAllGlobals();
    }
  });
});
