/**
 * Exam workspace autosave and server-stored undo history.
 *
 * Domain purpose:
 *   Each autosave is one undo step stored on the server (TASK-SKRIPT-39-04-08,
 *   TASK-SKRIPT-40-04-03 W5, W8): typing becomes a step after a 900 ms pause,
 *   a structural edit becomes a step at once. The server keeps at most 10
 *   steps after the import baseline, so undo survives reload, reopening and
 *   Spara. Undo and redo move between stored steps and install the step's
 *   document; a new edit after an undo branches after the current step,
 *   which drops the redo steps. Undo first stores any pending edit, so the
 *   pending edit itself can be redone; if that store fails, undo stops and
 *   the pending edit stays in front of the teacher.
 *
 *   The history cursor is only a concurrency token: it rotates on every
 *   write, Spara included, and need not name a step. The step the editor
 *   stands on is the server's `position_step_id`, the baseline or a step;
 *   Spara sends it, and the server keeps the saved copy retained there, so
 *   history stays navigable after any Spara. While undo or redo reads a
 *   step, editing is locked through the document owner's `replaceCopy`, so
 *   no edit is typed into a copy the read is about to replace, and AI
 *   arrivals that land meanwhile run again on the step.
 *
 * Relationships:
 *   - Reads the working copy and the cursor the document composable installs;
 *     every response that carries a cursor this composable did not write
 *     (open, reload, Spara som, parent and change-type commands) reloads
 *     the step list.
 *   - Spara and the structural commands call `flush` first, so the server's
 *     newest step is the editor's document; `flush` resolves false when that
 *     could not be established, and a replacing command must then not run.
 *   - Reports a failed undo or redo through the shared toast store, and an
 *     autosave the server could not store; a draft the save rules refuse
 *     shows its reason inline in the editor instead, never as a toast.
 */

import { computed, onScopeDispose, ref, shallowRef, watch } from "vue";
import type { Ref } from "vue";

import { isApiError } from "../../../api/client";
import {
  getExamWorkspaceHistory,
  getExamWorkspaceHistoryStep,
  storeExamWorkspaceUndoStep,
} from "../../../api/examWorkspace";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { sameDocument } from "./examWorkspaceConversionMerge";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";

export const EXAM_WORKSPACE_TYPING_PAUSE_MS = 900;

const UNDO_FAILURE_COPY = "Det gick inte att ångra. Försök igen.";
const REDO_FAILURE_COPY = "Det gick inte att göra om. Försök igen.";
const AUTOSAVE_FAILURE_COPY = "Ändringen kunde inte sparas som utkast. Försök igen.";

export type ExamWorkspaceHistoryDeps = {
  workspaceDocument: Ref<NativeExamDocument | null>;
  /** The server's working copy from the last response; the step the cursor names. */
  serverDocument: Ref<NativeExamDocument | null>;
  historyCursor: Ref<string | null>;
  lineageId: () => string | null;
  savedRevision: () => number | null;
  /** True while an import or a save may not be interleaved with a step write; excludes the replacing lock. */
  isBlocked: () => boolean;
  /** Another undo, redo or server command is replacing the copy; undo and redo wait for it. */
  isReplacing: () => boolean;
  /** Run a read that replaces the copy: locks editing and keeps arrivals that land meanwhile. */
  replaceCopy: <T>(run: () => Promise<T>) => Promise<T>;
  /** Put a stored step's document in front of the teacher. */
  install: (document: NativeExamDocument) => void;
  /** Another tab moved the history; reload the exam. */
  onConflict: () => Promise<void>;
};

/** Steps compare without the revision: a step stored before a Spara carries the older one. */
function sameContent(a: NativeExamDocument | null, b: NativeExamDocument | null): boolean {
  if (a === null || b === null) {
    return a === b;
  }
  return sameDocument({ ...a, revision: 1 }, { ...b, revision: 1 });
}

export function useExamWorkspaceHistory(deps: ExamWorkspaceHistoryDeps) {
  const toast = useToast();
  const baselineId = ref<string | null>(null);
  const stepIds = ref<string[]>([]);
  /** The stored snapshot the editor stands on; null until the step list is loaded. */
  const position = ref<string | null>(null);
  /** That step's document; a working copy that differs from it is a pending edit. */
  const stepDocument = shallowRef<NativeExamDocument | null>(null);
  const navigating = ref(false);
  const storing = ref(false);
  let ownCursor: string | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let chain: Promise<boolean> = Promise.resolve(true);
  let loadToken = 0;

  const ids = computed(() => (baselineId.value ? [baselineId.value, ...stepIds.value] : []));
  const index = computed(() => (position.value ? ids.value.indexOf(position.value) : -1));
  const pending = computed(
    () =>
      deps.workspaceDocument.value !== null &&
      stepDocument.value !== null &&
      !sameContent(deps.workspaceDocument.value, stepDocument.value),
  );
  const newestId = computed(() => ids.value[ids.value.length - 1] ?? null);
  const ready = computed(() => position.value !== null && !navigating.value);
  const canUndo = computed(() => ready.value && (pending.value || index.value > 0));
  const canRedo = computed(
    () => ready.value && !pending.value && index.value >= 0 && index.value < ids.value.length - 1,
  );

  function clearTimer(): void {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function reset(): void {
    clearTimer();
    baselineId.value = null;
    stepIds.value = [];
    position.value = null;
    stepDocument.value = null;
  }

  async function load(lineageId: string): Promise<void> {
    const token = ++loadToken;
    const base = deps.serverDocument.value;
    try {
      const history = await getExamWorkspaceHistory(lineageId);
      if (token !== loadToken || deps.lineageId() !== lineageId) {
        return;
      }
      baselineId.value = history.baseline_step_id;
      stepIds.value = [...history.step_ids];
      position.value = history.position_step_id;
      stepDocument.value = base;
    } catch {
      if (token === loadToken) {
        reset();
      }
    }
  }

  watch(
    [() => deps.lineageId(), deps.historyCursor],
    ([lineageId, cursor], previous) => {
      const [previousLineage] = previous ?? [null, null];
      if (lineageId !== previousLineage) {
        reset();
      }
      if (!lineageId || !cursor) {
        return;
      }
      if (cursor === ownCursor && lineageId === previousLineage) {
        return;
      }
      if (lineageId === previousLineage && ownCursor !== null && ids.value.includes(cursor)) {
        // A read that started before this tab's last step write echoes an older cursor.
        deps.historyCursor.value = ownCursor;
        return;
      }
      void load(lineageId);
    },
    { immediate: true },
  );

  /** Resolves whether the server's newest step now holds `document` (or nothing needed storing). */
  async function store(settle = false, snapshot: NativeExamDocument | null = null): Promise<boolean> {
    clearTimer();
    const lineageId = deps.lineageId();
    const cursor = deps.historyCursor.value;
    if (lineageId && cursor && position.value === null) {
      // The step list failed to load earlier; without it no step can be stored.
      await load(lineageId);
    }
    const document = snapshot ?? deps.workspaceDocument.value;
    const after = position.value;
    if (!lineageId || !cursor || !document || after === null) {
      return false;
    }
    const undone = after !== newestId.value;
    if (sameContent(document, stepDocument.value) && !(settle && undone)) {
      return true;
    }
    if (deps.isBlocked()) {
      schedule();
      return false;
    }
    storing.value = true;
    try {
      const response = await storeExamWorkspaceUndoStep(lineageId, {
        afterStepId: after,
        document,
        expectedCursor: cursor,
      });
      if (deps.lineageId() !== lineageId) {
        return false;
      }
      ownCursor = response.history.cursor;
      deps.historyCursor.value = response.history.cursor;
      baselineId.value = response.history.baseline_step_id;
      stepIds.value = [...response.history.step_ids];
      position.value = response.history.position_step_id;
      stepDocument.value = document;
      return true;
    } catch (error) {
      if (isApiError(error) && error.status === 409) {
        await deps.onConflict();
      } else if (isApiError(error) && error.status === 422) {
        // A draft the save rules refuse already shows why inline in the editor; the
        // server's request-shape rejection carries no Swedish copy of its own.
        if (examWorkspaceSaveRefusalCopy(document.items) === null) {
          toast.failure(error.code === "VALIDATION_ERROR" ? AUTOSAVE_FAILURE_COPY : error.message);
        }
      } else {
        toast.failure(AUTOSAVE_FAILURE_COPY);
      }
      return false;
    } finally {
      storing.value = false;
    }
  }

  /**
   * Store the pending edit now; resolves after every earlier write, with
   * whether the server's newest step holds the editor's document. `settle`
   * also stores an undone step as the newest one, because the server's
   * commands (parents, Byt frågetyp) apply to its newest step.
   */
  function flush(settle = false, snapshot: NativeExamDocument | null = null): Promise<boolean> {
    const run = () => store(settle, snapshot);
    chain = chain.then(run, run);
    return chain;
  }

  function schedule(): void {
    clearTimer();
    timer = setTimeout(() => {
      timer = null;
      void flush();
    }, EXAM_WORKSPACE_TYPING_PAUSE_MS);
  }

  /**
   * A teacher edit happened: typing waits for a pause; a structural edit is a
   * step now, holding the document as it was right after that edit, so two
   * quick structural edits stay two steps.
   */
  function noteEdit(structural = false): void {
    if (structural) {
      void flush(false, deps.workspaceDocument.value);
    } else {
      schedule();
    }
  }

  /** Read and install one step; the caller holds `navigating` and the replacing lock. */
  async function goTo(stepId: string, failureCopy: string): Promise<void> {
    const lineageId = deps.lineageId();
    if (!lineageId) {
      return;
    }
    try {
      const response = await getExamWorkspaceHistoryStep(lineageId, stepId);
      if (deps.lineageId() !== lineageId) {
        return;
      }
      const revision = deps.savedRevision() ?? response.document.revision;
      const document = { ...response.document, revision };
      deps.install(document);
      stepDocument.value = document;
      position.value = stepId;
    } catch {
      toast.failure(failureCopy);
    }
  }

  async function undo(): Promise<void> {
    if (!canUndo.value || deps.isBlocked() || deps.isReplacing()) {
      return;
    }
    // Locked from before the pending edit is stored, so nothing typed meanwhile is replaced.
    navigating.value = true;
    try {
      await deps.replaceCopy(async () => {
        if (!(await flush())) {
          return;
        }
        const at = index.value;
        const target = at > 0 ? ids.value[at - 1] : undefined;
        if (target) {
          await goTo(target, UNDO_FAILURE_COPY);
        }
      });
    } finally {
      navigating.value = false;
    }
  }

  async function redo(): Promise<void> {
    if (!canRedo.value || deps.isBlocked() || deps.isReplacing()) {
      return;
    }
    const target = ids.value[index.value + 1];
    if (!target) {
      return;
    }
    navigating.value = true;
    try {
      await deps.replaceCopy(() => goTo(target, REDO_FAILURE_COPY));
    } finally {
      navigating.value = false;
    }
  }

  onScopeDispose(clearTimer);

  return {
    canRedo,
    canUndo,
    flush,
    navigating: computed(() => navigating.value),
    /** The snapshot Spara keeps the saved copy at; null until the step list is loaded. */
    position: computed(() => position.value),
    noteEdit,
    pending,
    redo,
    storing: computed(() => storing.value),
    undo,
  };
}
