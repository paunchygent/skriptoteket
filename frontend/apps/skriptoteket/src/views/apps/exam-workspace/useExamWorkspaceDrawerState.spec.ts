/**
 * Exam workspace drawer state behavior.
 *
 * Expected behavior:
 *   The header toggles a drawer open and closed and switches between
 *   drawers; selecting a question closes the drawer except the docked
 *   Exportera drawer off the phone; Öppna is open on arrival without an
 *   exam; and a requested import pick opens Öppna and stays pending until
 *   it is consumed.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, ref } from "vue";

import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";
import { useExamWorkspaceDrawerState } from "./useExamWorkspaceDrawerState";

function mountState(options: { examOpen?: boolean; layout?: ExamWorkspaceLayout } = {}) {
  const layout = ref<ExamWorkspaceLayout>(options.layout ?? "desktop");
  let state!: ReturnType<typeof useExamWorkspaceDrawerState>;
  const wrapper = mount(
    defineComponent({
      setup() {
        state = useExamWorkspaceDrawerState({ isExamOpen: () => options.examOpen ?? true, layout });
        return () => null;
      },
    }),
  );
  return { state, wrapper };
}

describe("useExamWorkspaceDrawerState", () => {
  it("toggles a drawer and switches between drawers", () => {
    const { state } = mountState();
    expect(state.drawer.value).toBeNull();

    state.toggleDrawer("details");
    expect(state.drawer.value).toBe("details");
    state.toggleDrawer("open");
    expect(state.drawer.value).toBe("open");
    state.toggleDrawer("open");
    expect(state.drawer.value).toBeNull();
  });

  it("opens Öppna on arrival only without an open exam", () => {
    expect(mountState({ examOpen: false }).state.drawer.value).toBe("open");
    expect(mountState({ examOpen: true }).state.drawer.value).toBeNull();
  });

  it.each([
    ["desktop", "export", "export"],
    ["tablet", "export", "export"],
    ["phone", "export", null],
    ["desktop", "details", null],
    ["desktop", "open", null],
  ] as const)("after selecting a question on %s the %s drawer is %s", (layout, drawerName, expected) => {
    const { state } = mountState({ layout });
    state.toggleDrawer(drawerName);

    state.closeAfterGoto();

    expect(state.drawer.value).toBe(expected);
  });

  it("opens Öppna and holds the import pick request until it is consumed", () => {
    const { state } = mountState();
    state.toggleDrawer("export");
    expect(state.importPickPending.value).toBe(false);

    state.requestImportPick();
    expect(state.drawer.value).toBe("open");
    expect(state.importPickPending.value).toBe(true);

    state.consumeImportPick();
    expect(state.importPickPending.value).toBe(false);
    expect(state.drawer.value).toBe("open");
  });
});
