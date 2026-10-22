/**
 * Exam workspace picture control notices: where a refusal shows and clears.
 *
 * Expected behavior (TASK-SKRIPT-39-10-04, unit U6):
 *   - An accepted picture reaches the exam instruction and its body declares
 *     the asset; a refused file after it leaves the instruction unchanged and
 *     shows as the notice.
 *   - A refused file in the question editor shows at the top of the editor.
 *   - The signed-in pane shows a refusal, clears it on dismiss and on
 *     selection change.
 *
 * The question body editor cases live in `ExamWorkspacePictureControl`; how
 * an accepted picture reaches the save lives in `.saves`.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick } from "vue";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceBodyEditor from "./ExamWorkspaceBodyEditor.vue";
import ExamWorkspaceEditorPane from "./ExamWorkspaceEditorPane.vue";
import ExamWorkspaceExamInstructionEditor from "./ExamWorkspaceExamInstructionEditor.vue";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { buildRecordedParent } from "./examWorkspaceParentDocument.specSupport";
import { WHITE_JPEG_PICTURE } from "./examWorkspacePictureFixtures.specSupport";
import { installGuestStoreObjectUrls } from "./examWorkspaceGuestStore.specSupport";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import {
  choosePicture,
  entryFor,
  assetSegmentId,
  freeTextItem,
  limitStore,
  pictureFile,
  standAloneService,
  textFile,
  TYPE_COPY,
} from "./examWorkspacePictureControl.specSupport";
import { exam, openEditing, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";
import { provideExamWorkspacePictures } from "./examWorkspacePictureService";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../api/examWorkspaceStructureCommands", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspaceStructureCommands")>()),
  changeExamWorkspaceItemType: api.changeExamWorkspaceItemType,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

installGuestStoreObjectUrls();

let mounted: VueWrapper | null = null;

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  mounted?.unmount();
  mounted = null;
  document.body.innerHTML = "";
  stopScopes();
  vi.unstubAllGlobals();
});

describe("ExamWorkspacePictureControl notices", () => {
  it("inserts into the exam instruction and shows a refused file as the notice", async () => {
    const parent = buildRecordedParent();
    const { newPictures, service } = standAloneService(freeTextItem());
    // eslint-disable-next-line vue/one-component-per-file -- spec host with the provided service
    const Host = defineComponent({
      setup() {
        provideExamWorkspacePictures(service);
        return () =>
          h(ExamWorkspaceExamInstructionEditor, {
            instructions: parent.instruction,
            disabled: false,
            notice: service.notice.value,
          });
      },
    });
    mounted = mount(Host, { attachTo: document.body });
    await nextTick();
    await nextTick();

    await choosePicture(mounted, pictureFile(WHITE_JPEG_PICTURE, "instruktion.jpg"));

    const editor = mounted.findComponent(ExamWorkspaceExamInstructionEditor);
    const updates = editor.emitted("updateInstructions") as
      | Array<[NativeExamItem["body"], boolean]>
      | undefined;
    expect(updates).toHaveLength(1);
    const [emittedBody] = updates![0]!;
    const assetId = assetSegmentId(emittedBody);
    expect(assetId).toMatch(/^asset_[0-9a-f]{16}$/);
    const assetParagraphs = emittedBody.filter((paragraph) =>
      paragraph.segments.some((segment) => segment.kind === "asset"),
    );
    expect(assetParagraphs).toHaveLength(1);
    expect(assetParagraphs[0]!.segments).toHaveLength(1);
    const declared = newPictures.withDeclared({ ...exam("Prov", 0), instructions: emittedBody });
    expect(declared.assets.map((entry) => entry.asset_id)).toEqual([assetId]);

    await choosePicture(mounted, textFile());
    expect((editor.emitted("updateInstructions") as Array<unknown> | undefined)?.length).toBe(1);
    expect(service.notice.value).toEqual({ kind: "refused", text: TYPE_COPY });
    expect(mounted.get('[data-test="exam-workspace-delete-notice"]').text()).toContain(TYPE_COPY);
  });

  it("shows the refusal at the top of the question editor", async () => {
    const item = freeTextItem();
    const { service } = standAloneService(item);
    // eslint-disable-next-line vue/one-component-per-file -- spec host with the provided service
    const Host = defineComponent({
      setup() {
        provideExamWorkspacePictures(service);
        return () =>
          h(ExamWorkspaceQuestionEditor, {
            item,
            label: "1",
            origin: "created",
            parent: null,
            child: null,
            converting: false,
            disabled: false,
            notice: service.notice.value,
            importOpen: false,
          });
      },
    });
    mounted = mount(Host, {
      attachTo: document.body,
      global: { plugins: [examWorkspaceProvidersPlugin()] },
    });
    await nextTick();
    await nextTick();

    await choosePicture(mounted, textFile());

    expect(mounted.get('[data-test="exam-workspace-delete-notice"]').text()).toContain(TYPE_COPY);
    expect(mounted.findComponent(ExamWorkspaceBodyEditor).emitted("updateBody")).toBeUndefined();
  });

  it("shows, dismisses and clears the pane refusal on selection change", async () => {
    const { editing } = await openEditing(api);
    const stored = () => editing.workspaceDocument.value!;
    const selected = () => stored().items.find((entry) => entry.item_id === "item_001")!;
    const other = () => stored().items.find((entry) => entry.item_id === "item_002")!;
    mounted = mount(ExamWorkspaceEditorPane, {
      attachTo: document.body,
      global: { plugins: [examWorkspaceProvidersPlugin({ store: limitStore() })] },
      props: {
        editing,
        workspaceDocument: stored(),
        examInstructionsSelected: false,
        selectedParent: null,
        selectedParentEntry: null,
        parentChildren: [],
        entries: [entryFor(selected(), "1"), entryFor(other(), "2")],
        selectedItem: selected(),
        itemEntry: entryFor(selected(), "1"),
        itemParent: null,
        itemChild: null,
        itemNotice: null,
        converting: false,
        disabled: false,
        importOpen: false,
        openDrawerShown: true,
      },
    });
    await nextTick();
    await nextTick();

    await choosePicture(mounted, textFile());
    expect(mounted.get('[data-test="exam-workspace-delete-notice"]').text()).toContain(TYPE_COPY);

    await mounted.get('[data-test="exam-workspace-delete-notice-close"]').trigger("click");
    expect(mounted.find('[data-test="exam-workspace-delete-notice"]').exists()).toBe(false);

    await choosePicture(mounted, textFile());
    expect(mounted.find('[data-test="exam-workspace-delete-notice"]').exists()).toBe(true);

    await mounted.setProps({ selectedItem: other(), itemEntry: entryFor(other(), "2") });
    await nextTick();
    expect(mounted.find('[data-test="exam-workspace-delete-notice"]').exists()).toBe(false);
  });
});
