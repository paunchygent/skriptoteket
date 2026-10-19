/**
 * Exam workspace column layout wiring.
 *
 * Expected behavior:
 *   The composable owns the view's desktop column wiring: it carries the
 *   remembered widths as the root's inline custom properties and the list
 *   state as open/collapsed only on desktop, and stays silent (no style, no
 *   list state, no rail) on tablet and phone. A first width set on the
 *   collapsed list widens and expands it; the raw set/reset/collapse
 *   operations pass through to the stored sizes.
 */

import { beforeEach, describe, expect, it } from "vitest";
import { computed, ref } from "vue";

import { readExamWorkspaceColumnSizes, writeExamWorkspaceColumnSizes } from "./examWorkspaceColumnSizesStorage";
import { buildDocument } from "../ExamWorkspaceSlice.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceColumnLayout } from "./useExamWorkspaceColumnLayout";
import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";
import type { ExamWorkspaceSideDrawer } from "./useExamWorkspaceSideColumns";

beforeEach(() => {
  localStorage.clear();
});

describe("useExamWorkspaceColumnLayout", () => {
  it("carries no column style or list state off desktop", () => {
    writeExamWorkspaceColumnSizes({ drawer: 360, list: 280, listCollapsed: true });
    const layout = ref<ExamWorkspaceLayout>("tablet");

    const columns = useExamWorkspaceColumnLayout(layout);

    expect(columns.isDesktop.value).toBe(false);
    expect(columns.rootColumnStyle.value).toBeUndefined();
    expect(columns.rootListState.value).toBeUndefined();
    expect(columns.listRailCollapsed.value).toBe(false);
  });

  it("exposes the stored widths and the open list state on desktop", () => {
    writeExamWorkspaceColumnSizes({ drawer: 360, list: 280 });
    const layout = ref<ExamWorkspaceLayout>("desktop");

    const columns = useExamWorkspaceColumnLayout(layout);

    expect(columns.isDesktop.value).toBe(true);
    expect(columns.rootColumnStyle.value).toEqual({
      "--xw-drawer-size": "360px",
      "--xw-list-size": "280px",
    });
    expect(columns.rootListState.value).toBe("open");
    expect(columns.listRailCollapsed.value).toBe(false);
  });

  it("reports the collapsed list state on desktop", () => {
    writeExamWorkspaceColumnSizes({ listCollapsed: true });
    const layout = ref<ExamWorkspaceLayout>("desktop");

    const columns = useExamWorkspaceColumnLayout(layout);

    expect(columns.rootListState.value).toBe("collapsed");
    expect(columns.listRailCollapsed.value).toBe(true);
  });

  it("expands the collapsed list on the first width set", () => {
    writeExamWorkspaceColumnSizes({ listCollapsed: true });
    const layout = ref<ExamWorkspaceLayout>("desktop");
    const columns = useExamWorkspaceColumnLayout(layout);

    columns.setListWidth(300);

    expect(columns.listRailCollapsed.value).toBe(false);
    expect(columns.rootListState.value).toBe("open");
    expect(readExamWorkspaceColumnSizes()).toEqual({ list: 300, listCollapsed: false });
  });

  it("passes setWidth, resetWidth and toggleListCollapsed through to the stored sizes", () => {
    const layout = ref<ExamWorkspaceLayout>("desktop");
    const columns = useExamWorkspaceColumnLayout(layout);

    columns.setWidth("preview", 500);
    expect(columns.rootColumnStyle.value).toEqual({ "--xw-preview-size": "500px" });

    columns.resetWidth("preview");
    expect(columns.rootColumnStyle.value).toEqual({});

    columns.toggleListCollapsed();
    expect(columns.listRailCollapsed.value).toBe(true);
    expect(readExamWorkspaceColumnSizes().listCollapsed).toBe(true);
  });

  it("follows layout changes between desktop and tablet", () => {
    writeExamWorkspaceColumnSizes({ list: 280 });
    const layout = ref<ExamWorkspaceLayout>("desktop");
    const columns = useExamWorkspaceColumnLayout(layout);
    expect(columns.rootListState.value).toBe("open");

    layout.value = "tablet";

    expect(columns.isDesktop.value).toBe(false);
    expect(columns.rootColumnStyle.value).toBeUndefined();
    expect(columns.rootListState.value).toBeUndefined();
  });

  it("reports the open drawer as the side state", () => {
    const layout = ref<ExamWorkspaceLayout>("desktop");
    const columns = useExamWorkspaceColumnLayout(layout, {
      drawer: ref<ExamWorkspaceSideDrawer | null>("details"),
      isPhone: ref(false),
      previewOpen: ref(true),
      store: serverExamWorkspaceStore,
      workspaceDocument: computed(() => buildDocument()),
    });

    expect(columns.side.value).toBe("details");
  });

  it("reports the preview when it renders for a teacher", () => {
    const layout = ref<ExamWorkspaceLayout>("desktop");
    const columns = useExamWorkspaceColumnLayout(layout, {
      drawer: ref<ExamWorkspaceSideDrawer | null>(null),
      isPhone: ref(false),
      previewOpen: ref(true),
      store: serverExamWorkspaceStore,
      workspaceDocument: computed(() => buildDocument()),
    });

    expect(columns.side.value).toBe("preview");
  });

  it("reports none for a guest preview request without a teacher", () => {
    const layout = ref<ExamWorkspaceLayout>("desktop");
    const columns = useExamWorkspaceColumnLayout(layout, {
      drawer: ref<ExamWorkspaceSideDrawer | null>(null),
      isPhone: ref(false),
      previewOpen: ref(true),
      store: { ...serverExamWorkspaceStore, teacher: null },
      workspaceDocument: computed(() => buildDocument()),
    });

    expect(columns.side.value).toBe("none");
  });

  it("reports none with no side open", () => {
    const layout = ref<ExamWorkspaceLayout>("desktop");
    const columns = useExamWorkspaceColumnLayout(layout, {
      drawer: ref<ExamWorkspaceSideDrawer | null>(null),
      isPhone: ref(false),
      previewOpen: ref(false),
      store: serverExamWorkspaceStore,
      workspaceDocument: computed(() => buildDocument()),
    });

    expect(columns.side.value).toBe("none");
  });
});
