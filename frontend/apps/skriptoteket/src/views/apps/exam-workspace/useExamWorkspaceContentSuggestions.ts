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

import {
  getExamWorkspaceContentSuggestions,
  requestExamWorkspaceContentSuggestions,
} from "../../../api/examWorkspace";
import type { ExamWorkspaceContentSuggestions, NativeExamHeader } from "../../../api/examWorkspace";
import { isApiError } from "../../../api/client";
import { useToast } from "../../../composables/useToast";

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

export function useExamWorkspaceContentSuggestions(deps: {
  lineageId: () => string | null;
  tags: () => Tags | null;
  setTags: (tags: Tags) => void;
}) {
  const toast = useToast();
  const busy = ref(false);
  /** Said in the drawer when the job ticked nothing; toasts report failures only. */
  const message = ref<string | null>(null);
  let timer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;

  function stop(): void {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  }

  function settle(lineageId: string, response: ExamWorkspaceContentSuggestions): void {
    busy.value = false;
    if (deps.lineageId() !== lineageId) return;
    if (response.state === "failed") {
      toast.failure(response.message ?? FAILURE_COPY);
      return;
    }
    const tags = deps.tags();
    if (tags && response.suggestions.length > 0) {
      deps.setTags(withSuggestedTags(tags, response.suggestions));
    } else if (response.suggestions.length === 0) {
      message.value = response.message ?? "Inget centralt innehåll kunde föreslås för provets frågor.";
    }
  }

  function follow(lineageId: string, response: ExamWorkspaceContentSuggestions): void {
    if (disposed) return;
    if (response.state === "succeeded" || response.state === "failed") {
      settle(lineageId, response);
      return;
    }
    timer = setTimeout(() => {
      void getExamWorkspaceContentSuggestions(lineageId, response.job_id)
        .then((next) => follow(lineageId, next))
        .catch(() => {
          busy.value = false;
          if (!disposed) toast.failure(FAILURE_COPY);
        });
    }, EXAM_WORKSPACE_CONTENT_POLL_MS);
  }

  async function suggest(): Promise<void> {
    const lineageId = deps.lineageId();
    if (!lineageId || busy.value) return;
    busy.value = true;
    message.value = null;
    try {
      follow(lineageId, await requestExamWorkspaceContentSuggestions(lineageId));
    } catch (error) {
      busy.value = false;
      toast.failure(isApiError(error) && error.status === 422 ? error.message : FAILURE_COPY);
    }
  }

  onScopeDispose(() => {
    disposed = true;
    stop();
  });

  return { busy, message, suggest };
}
