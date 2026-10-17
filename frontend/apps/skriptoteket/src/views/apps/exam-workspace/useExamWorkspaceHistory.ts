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
 *   pending edit itself can be redone.
 *
 * Relationships:
 *   - Reads the working copy and the cursor the document composable installs;
 *     every response that carries a cursor this composable did not write
 *     (open, reload, Spara som, parent and change-type commands) reloads
 *     the step list.
 *   - Spara and the structural commands call `flush` first, so the server's
 *     newest step is the editor's document.
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
  /** True while an import or a save may not be interleaved with a step write. */
  isBlocked: () => boolean;
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
  /** The stored step the editor stands on. */
  const position = ref<string | null>(null);
  /** That step's document; a working copy that differs from it is a pending edit. */
  const stepDocument = shallowRef<NativeExamDocument | null>(null);
  const navigating = ref(false);
  const storing = ref(false);
  let ownCursor: string | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let chain: Promise<void> = Promise.resolve();
  let loadToken = 0;

  const ids = computed(() => (baselineId.value ? [baselineId.value, ...stepIds.value] : []));
  const index = computed(() => (position.value ? ids.value.indexOf(position.value) : -1));
  const pending = computed(
    () =>
      deps.workspaceDocument.value !== null &&
      stepDocument.value !== null &&
      !sameContent(deps.workspaceDocument.value, stepDocument.value),
  );
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

  async function load(lineageId: string, cursor: string): Promise<void> {
    const token = ++loadToken;
    const base = deps.serverDocument.value;
    try {
      const history = await getExamWorkspaceHistory(lineageId);
      if (token !== loadToken || deps.lineageId() !== lineageId) {
        return;
      }
      baselineId.value = history.baseline_step_id;
      stepIds.value = [...history.step_ids];
      position.value = cursor;
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
      void load(lineageId, cursor);
    },
    { immediate: true },
  );

  async function store(settle = false, snapshot: NativeExamDocument | null = null): Promise<void> {
    clearTimer();
    const lineageId = deps.lineageId();
    const cursor = deps.historyCursor.value;
    if (lineageId && cursor && position.value === null) {
      // The step list failed to load earlier; without it no step can be stored.
      await load(lineageId, cursor);
    }
    const document = snapshot ?? deps.workspaceDocument.value;
    const undone = position.value !== null && position.value !== cursor;
    if (!lineageId || !cursor || !document || position.value === null) {
      return;
    }
    if (sameContent(document, stepDocument.value) && !(settle && undone)) {
      return;
    }
    if (deps.isBlocked()) {
      schedule();
      return;
    }
    storing.value = true;
    try {
      const response = await storeExamWorkspaceUndoStep(lineageId, {
        afterStepId: position.value === cursor ? null : position.value,
        document,
        expectedCursor: cursor,
      });
      if (deps.lineageId() !== lineageId) {
        return;
      }
      ownCursor = response.history.cursor;
      deps.historyCursor.value = response.history.cursor;
      baselineId.value = response.history.baseline_step_id;
      stepIds.value = [...response.history.step_ids];
      position.value = response.history.cursor;
      stepDocument.value = document;
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
    } finally {
      storing.value = false;
    }
  }

  /**
   * Store the pending edit now; resolves after every earlier write. `settle`
   * also stores an undone step as the newest one, because the server's
   * commands (parents, Byt frågetyp) apply to its newest step.
   */
  function flush(settle = false, snapshot: NativeExamDocument | null = null): Promise<void> {
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

  async function goTo(stepId: string, failureCopy: string): Promise<void> {
    const lineageId = deps.lineageId();
    if (!lineageId) {
      return;
    }
    navigating.value = true;
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
    } finally {
      navigating.value = false;
    }
  }

  async function undo(): Promise<void> {
    if (!canUndo.value || deps.isBlocked()) {
      return;
    }
    await flush();
    const at = index.value;
    const target = at > 0 ? ids.value[at - 1] : undefined;
    if (target) {
      await goTo(target, UNDO_FAILURE_COPY);
    }
  }

  async function redo(): Promise<void> {
    if (!canRedo.value || deps.isBlocked()) {
      return;
    }
    const target = ids.value[index.value + 1];
    if (target) {
      await goTo(target, REDO_FAILURE_COPY);
    }
  }

  onScopeDispose(clearTimer);

  return {
    canRedo,
    canUndo,
    flush,
    noteEdit,
    pending,
    redo,
    storing: computed(() => storing.value),
    undo,
  };
}
