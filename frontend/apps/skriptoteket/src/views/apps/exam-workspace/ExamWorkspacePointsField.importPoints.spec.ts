/**
 * Exam workspace points field, import-time source-points hint (TASK-SKRIPT-40-04-23).
 *
 * Expected behavior:
 *   Right after an import, a question whose points differ from the source
 *   shows "Provtexten: {n} p" next to the Poäng field while its id is in the
 *   injected `EXAM_WORKSPACE_IMPORT_POINTS_KEY` set. Without the injection,
 *   with the id not in the set, or with `source_points` null, nothing shows.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick, ref } from "vue";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import ExamWorkspacePointsField from "./ExamWorkspacePointsField.vue";
import { EXAM_WORKSPACE_IMPORT_POINTS_KEY } from "./examWorkspaceImportPoints";

const SOURCE = '[data-test="exam-workspace-points-source"]';
const MISSING = '[data-test="exam-workspace-points-missing"]';

const mounted: Array<VueWrapper> = [];

function mountField(
  item: NativeExamItem,
  provideIds?: Set<string> | null,
  mutableIds?: ReturnType<typeof ref<ReadonlySet<string>>> | null,
) {
  const provide =
    mutableIds !== undefined && mutableIds !== null
      ? { [EXAM_WORKSPACE_IMPORT_POINTS_KEY as symbol]: mutableIds }
      : provideIds === undefined || provideIds === null
        ? undefined
        : { [EXAM_WORKSPACE_IMPORT_POINTS_KEY as symbol]: ref<ReadonlySet<string>>(provideIds) };
  const wrapper = mount(ExamWorkspacePointsField, {
    props: { converting: false, disabled: false, item },
    ...(provide === undefined ? {} : { global: { provide } }),
  });
  mounted.push(wrapper);
  return wrapper;
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
});

describe("ExamWorkspacePointsField import-time source-points hint", () => {
  it("shows 'Provtexten: 4 p' with class xw-warn when the id is marked", () => {
    const item = { ...buildFreeTextItem(1), points: 5, source_points: 4 };
    const wrapper = mountField(item, new Set([item.item_id]));

    const hint = wrapper.get(SOURCE);
    expect(hint.text()).toBe("Provtexten: 4 p");
    expect(hint.classes()).toContain("xw-warn");
  });

  it("shows nothing when the id is not in the set", () => {
    const item = { ...buildFreeTextItem(1), points: 5, source_points: 4 };
    const wrapper = mountField(item, new Set(["item_999"]));

    expect(wrapper.find(SOURCE).exists()).toBe(false);
  });

  it("shows nothing without the injection", () => {
    const item = { ...buildFreeTextItem(1), points: 5, source_points: 4 };
    const wrapper = mountField(item);

    expect(wrapper.find(SOURCE).exists()).toBe(false);
  });

  it("shows nothing when source_points is null", () => {
    const item = { ...buildFreeTextItem(1), points: 5, source_points: null };
    const wrapper = mountField(item, new Set([item.item_id]));

    expect(wrapper.find(SOURCE).exists()).toBe(false);
  });

  it("shows both the hint and 'Saknas' when points are null", () => {
    const item = { ...buildFreeTextItem(1), points: null, source_points: 3 };
    const wrapper = mountField(item, new Set([item.item_id]));

    expect(wrapper.get(SOURCE).text()).toBe("Provtexten: 3 p");
    expect(wrapper.get(MISSING).text()).toContain("Saknas");
  });

  it("removes the hint when the set is emptied", async () => {
    const item = { ...buildFreeTextItem(1), points: 5, source_points: 4 };
    const ids = ref<ReadonlySet<string>>(new Set([item.item_id]));
    const wrapper = mountField(item, undefined, ids);

    expect(wrapper.find(SOURCE).exists()).toBe(true);
    ids.value = new Set<string>();
    await nextTick();
    expect(wrapper.find(SOURCE).exists()).toBe(false);
  });
});
