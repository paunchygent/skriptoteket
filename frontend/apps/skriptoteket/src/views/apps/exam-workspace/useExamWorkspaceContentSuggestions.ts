/**
 * Exam workspace Centralt innehåll suggestions.
 *
 * Domain purpose:
 *   "Föreslå innehåll" asks the server which parts of the course's central
 *   content the saved exam covers, waits for the job, and ticks each
 *   suggestion with the questions that cite it. A suggestion the teacher
 *   already ticked keeps its origin and gains the cited questions. The
 *   ticks are one edit, so Ångra takes them back.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView`; reads the saved exam through the
 *     content-suggestions routes and writes `header.tags` through `setTags`.
 */

import { onScopeDispose, ref } from "vue";

import type {
  ExamWorkspaceContentSuggestions,
  NativeExamDocument,
  NativeExamHeader,
} from "../../../api/examWorkspace";
import { isApiError } from "../../../api/client";
import { useAiAccess } from "../../../composables/useAiAccess";
import { useToast } from "../../../composables/useToast";
import {
  AI_DAILY_LIMIT_NOTE,
  hasAiDailyLimit,
  isAiDailyLimitError,
  markAiDailyLimit,
} from "./aiDailyLimit";
import type { ExamWorkspaceTeacherServices } from "./examWorkspaceStore";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";

export const EXAM_WORKSPACE_CONTENT_POLL_MS = 1500;
const FAILURE_COPY = "Det gick inte att föreslå innehåll. Försök igen.";

type Tags = NativeExamHeader["tags"];

/** Tick every suggestion; a tag already ticked keeps its origin and gains the cited questions. */
export function withSuggestedTags(tags: Tags, suggestions: Tags): Tags {
  const next = tags.map((tag) => ({ ...tag }));
  for (const suggestion of suggestions) {
    const current = next.find((tag) => tag.id === suggestion.id);
    if (current) {
      current.question_ids = [...new Set([...current.question_ids, ...suggestion.question_ids])];
    } else {
      next.push({ ...suggestion, origin: "suggested" });
    }
  }
  return next;
}

const STALE_COPY = "Provet ändrades medan innehållet föreslogs. Föreslå innehåll igen.";

/** What the job was asked about; the result applies only while all of it still holds. */
type Request = {
  readonly opening: ExamWorkspaceOpening;
  readonly courseKey: string | null;
};

export function useExamWorkspaceContentSuggestions(deps: {
  openExam: () => ExamWorkspaceOpening | null;
  isOpen: (opening: ExamWorkspaceOpening) => boolean;
  document: () => NativeExamDocument | null;
  savedRevision: () => number | null;
  setTags: (tags: Tags) => void;
  /** The teacher services the content-suggestion jobs run through; null in guest mode. */
  teacher: ExamWorkspaceTeacherServices | null;
}) {
  const toast = useToast();
  // The paid content suggestion is admin-only until the spend cap ships (TASK-SKRIPT-REP-0044 L3).
  const { canUseAi } = useAiAccess();
  const busy = ref(false);
  /** Said in the drawer when the job ticked nothing; toasts report failures only. */
  const message = ref<string | null>(null);
  let timer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;

  function stop(): void {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  }

  /** Keep the suggestions that still cite a question of the open copy. */
  function citedPresent(suggestions: Tags, document: NativeExamDocument): Tags {
    const present = new Set(document.items.map((item) => item.item_id));
    return suggestions
      .map((suggestion) => ({
        ...suggestion,
        question_ids: suggestion.question_ids.filter((id) => present.has(id)),
      }))
      .filter((suggestion) => suggestion.question_ids.length > 0);
  }

  function settle(request: Request, response: ExamWorkspaceContentSuggestions): void {
    busy.value = false;
    if (!deps.isOpen(request.opening)) return;
    // The door's daily limit disables the control for the page session and
    // says so in the drawer; unlike other failures it never toasts.
    if (hasAiDailyLimit(response)) {
      markAiDailyLimit();
    }
    if (response.state === "failed") {
      if (hasAiDailyLimit(response)) {
        message.value = AI_DAILY_LIMIT_NOTE;
        return;
      }
      toast.failure(response.message ?? FAILURE_COPY);
      return;
    }
    const document = deps.document();
    if (
      !document ||
      response.document_revision !== deps.savedRevision() ||
      response.course_key !== (document.header.course?.key ?? null) ||
      request.courseKey !== response.course_key
    ) {
      message.value = STALE_COPY;
      return;
    }
    const suggestions = citedPresent(response.suggestions, document);
    if (suggestions.length === 0) {
      message.value = response.message ?? "Inget centralt innehåll kunde föreslås för provets frågor.";
      return;
    }
    deps.setTags(withSuggestedTags(document.header.tags, suggestions));
  }

  function follow(request: Request, response: ExamWorkspaceContentSuggestions): void {
    if (disposed) return;
    if (!deps.isOpen(request.opening)) {
      busy.value = false;
      return;
    }
    if (response.state === "succeeded" || response.state === "failed") {
      settle(request, response);
      return;
    }
    const lineageId = request.opening.lineageId;
    timer = setTimeout(() => {
      const teacher = deps.teacher;
      if (!teacher) {
        busy.value = false;
        return;
      }
      void teacher.getExamWorkspaceContentSuggestions(lineageId, response.job_id)
        .then((next) => follow(request, next))
        .catch((error: unknown) => {
          busy.value = false;
          if (!disposed && deps.isOpen(request.opening)) {
            if (isAiDailyLimitError(error)) {
              markAiDailyLimit();
              message.value = AI_DAILY_LIMIT_NOTE;
              return;
            }
            toast.failure(FAILURE_COPY);
          }
        });
    }, EXAM_WORKSPACE_CONTENT_POLL_MS);
  }

  async function suggest(): Promise<void> {
    const opening = deps.openExam();
    const teacher = deps.teacher;
    if (!canUseAi.value || !opening || !teacher || busy.value) return;
    const request: Request = {
      opening,
      courseKey: deps.document()?.header.course?.key ?? null,
    };
    busy.value = true;
    message.value = null;
    try {
      const started = await teacher.requestExamWorkspaceContentSuggestions(opening.lineageId);
      follow(request, started);
    } catch (error) {
      busy.value = false;
      if (!deps.isOpen(opening)) return;
      if (isAiDailyLimitError(error)) {
        markAiDailyLimit();
        message.value = AI_DAILY_LIMIT_NOTE;
        return;
      }
      toast.failure(isApiError(error) && error.status === 422 ? error.message : FAILURE_COPY);
    }
  }

  onScopeDispose(() => {
    disposed = true;
    stop();
  });

  return { busy, message, suggest };
}
