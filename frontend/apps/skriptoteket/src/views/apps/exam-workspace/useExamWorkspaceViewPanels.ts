/**
 * Exam workspace view panels (view seam).
 *
 * Domain purpose:
 *   Own the view's panel wiring that belongs together: the drawer state, the
 *   document address sync and the side columns (phone list, import box and
 *   print preview). The drawer and the preview stay exclusive, and a lineage
 *   change dismisses the guest sign-in prompt it interrupted. The address is
 *   an adapter over the gate-owned replacement coordinator: drawer opens
 *   submit route intents through the same entrance as every other
 *   document-replacing entry, and the coordinator alone publishes the address.
 *
 * Relationships:
 *   - Composes `useExamWorkspaceDrawerState`, `useExamWorkspaceAddress` and
 *     `useExamWorkspaceSideColumns`; consumed by `ExamWorkspaceView`.
 *   - The view keeps the layout, the editing session and the sign-in prompt;
 *     this seam only wires which panel is open and which document the route
 *     names. The template bindings keep their names.
 */

import { computed } from "vue";
import type { Ref } from "vue";

import type { ExamWorkspaceDocumentSummary, NativeExamDocument } from "../../../api/examWorkspace";
import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceAddress } from "./useExamWorkspaceAddress";
import { useExamWorkspaceColumnLayout } from "./useExamWorkspaceColumnLayout";
import { useExamWorkspaceDrawerState } from "./useExamWorkspaceDrawerState";
import type { ExamWorkspaceRouteProjection } from "./examWorkspaceRouteProjection";
import { useExamWorkspaceSideColumns } from "./useExamWorkspaceSideColumns";

export type ExamWorkspaceViewPanelsDeps = {
  /** True while an exam is open; the drawer starts on Öppna otherwise. */
  isExamOpen: () => boolean;
  /** The view layout; phone drives the list overlay, desktop the docked columns. */
  layout: Ref<ExamWorkspaceLayout>;
  /** The editing session's history cursor; the preview refreshes after each saved edit. */
  historyCursor: Ref<string | null>;
  /** The editing session's history position; the preview follows redo and undo. */
  historyPosition: Ref<string | null>;
  /** Submit a route-open intent synchronously to the replacement coordinator. */
  submitRoute: (lineageId: string) => void;
  /** The address the coordinator stands behind: its desired target, else its source. */
  currentAddress: () => string | null;
  /** The shared router adapter: observed by the address, published only by the coordinator. */
  projection: ExamWorkspaceRouteProjection;
  /** The saved version the open copy stands on; the preview renders it. */
  savedRevision: Ref<number | null>;
  /** The selected question; the preview highlights it. */
  selectedItemId: Ref<string | null>;
  /** The exam workspace store; the preview reads through it. */
  store: ExamWorkspaceStore;
  /** The open exam summary; its lineage names the address and the preview. */
  summary: Ref<ExamWorkspaceDocumentSummary | null>;
  /** The working copy; the width owner renders its columns only while an exam is open. */
  workspaceDocument: Ref<NativeExamDocument | null>;
  /** Dismiss the guest sign-in prompt a lineage change interrupted. */
  dismissSignInPrompt: () => void;
};

export function useExamWorkspaceViewPanels(deps: ExamWorkspaceViewPanelsDeps) {
  useExamWorkspaceAddress({
    currentAddress: deps.currentAddress,
    projection: deps.projection,
    submitRoute: deps.submitRoute,
  });
  const {
    closeAfterGoto,
    consumeImportPick,
    drawer,
    importPickPending,
    requestImportPick,
    toggleDrawer,
  } = useExamWorkspaceDrawerState({ isExamOpen: deps.isExamOpen, layout: deps.layout });
  const lineageId = computed(() => deps.summary.value?.lineage_id ?? null);
  const {
    importOpen,
    isPhone,
    listOpen,
    previewBlocked,
    previewLoading,
    previewMessage,
    previewOpen,
    previewPages,
    previewQuestionPages,
    togglePreview,
  } = useExamWorkspaceSideColumns({
    drawer,
    historyCursor: deps.historyCursor,
    historyPosition: deps.historyPosition,
    layout: deps.layout,
    lineageId,
    savedRevision: deps.savedRevision,
    selectedItemId: deps.selectedItemId,
    store: deps.store,
    onLineage: () => {
      deps.dismissSignInPrompt();
    },
  });
  /**
   * The width owner's side state and the remembered column widths (TASK-SKRIPT-41-02-04),
   * owned by `useExamWorkspaceColumnLayout`: on desktop the root carries the widths
   * as inline custom properties and the list state as `data-list`; tablet and
   * phone render without either.
   */
  const {
    isDesktop,
    listRailCollapsed,
    resetWidth,
    rootColumnStyle,
    rootListState,
    setListWidth,
    setWidth,
    side,
    toggleListCollapsed,
  } = useExamWorkspaceColumnLayout(deps.layout, {
    drawer,
    isPhone,
    previewOpen,
    store: deps.store,
    workspaceDocument: deps.workspaceDocument,
  });

  return {
    closeAfterGoto,
    consumeImportPick,
    drawer,
    importOpen,
    importPickPending,
    isDesktop,
    isPhone,
    listOpen,
    listRailCollapsed,
    /** Submit the drawer-opened lineage as a route intent through the coordinator. */
    openRoutedDocument: (lineageId: string) => deps.submitRoute(lineageId),
    previewBlocked,
    previewLoading,
    previewMessage,
    previewOpen,
    previewPages,
    previewQuestionPages,
    requestImportPick,
    resetWidth,
    rootColumnStyle,
    rootListState,
    setListWidth,
    setWidth,
    side,
    toggleDrawer,
    toggleListCollapsed,
    togglePreview,
  };
}
