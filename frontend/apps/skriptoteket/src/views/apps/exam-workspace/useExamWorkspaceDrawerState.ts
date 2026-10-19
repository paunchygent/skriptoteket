/**
 * Exam workspace drawer state (view seam).
 *
 * Domain purpose:
 *   Own which drawer (Öppna, Exportera, Provets uppgifter) is open, that Öppna
 *   is open on arrival without an exam, how the header toggles it, when
 *   selecting a question closes it, and the one-shot
 *   request that Importera in the header makes to the Öppna drawer: open it
 *   and show its file picker.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView`, which passes `importPickPending` down to
 *     the Öppna drawer and calls `consumeImportPick` when the drawer reports
 *     that it has acted on the request. The drawer decides whether the import
 *     gates allow the picker.
 *   - `useExamWorkspaceSideColumns` receives the `drawer` ref to keep it
 *     exclusive with the preview.
 */

import { onMounted, ref } from "vue";
import type { Ref } from "vue";

import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";
import type { ExamWorkspaceSideDrawer } from "./useExamWorkspaceSideColumns";

export function useExamWorkspaceDrawerState(deps: { isExamOpen: () => boolean; layout: Ref<ExamWorkspaceLayout> }) {
  const drawer = ref<ExamWorkspaceSideDrawer | null>(null);
  const importPickPending = ref(false);

  onMounted(() => {
    if (!deps.isExamOpen()) drawer.value = "open";
  });

  function toggleDrawer(name: ExamWorkspaceSideDrawer): void {
    drawer.value = drawer.value === name ? null : name;
  }

  /** Selecting a question closes the drawer, except the docked Exportera drawer on tablet and desktop. */
  function closeAfterGoto(): void {
    if (deps.layout.value !== "phone" && drawer.value === "export") return;
    drawer.value = null;
  }

  function requestImportPick(): void {
    drawer.value = "open";
    importPickPending.value = true;
  }

  function consumeImportPick(): void {
    importPickPending.value = false;
  }

  return { closeAfterGoto, consumeImportPick, drawer, importPickPending, requestImportPick, toggleDrawer };
}
