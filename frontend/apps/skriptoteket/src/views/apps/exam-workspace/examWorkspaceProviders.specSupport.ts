/**
 * Exam workspace provider plugin for specs.
 *
 * Purpose:
 *   One plugin that provides the required `EXAM_WORKSPACE_STORE_KEY` and
 *   `EXAM_WORKSPACE_SIGN_IN_KEY` injections to the component under test, so
 *   specs mount through `global.plugins` with typed `app.provide` instead of
 *   casting the injection keys in `global.provide`.
 */

import type { Plugin } from "vue";

import { EXAM_WORKSPACE_SIGN_IN_KEY } from "./examWorkspaceSignIn";
import { EXAM_WORKSPACE_STORE_KEY, serverExamWorkspaceStore } from "./examWorkspaceStore";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";

/** Provide the exam-workspace store and sign-in request to the component under test. */
export function examWorkspaceProvidersPlugin(options?: {
  store?: ExamWorkspaceStore;
  requestSignIn?: (message: string) => void;
}): Plugin {
  const store = options?.store ?? serverExamWorkspaceStore;
  const requestSignIn = options?.requestSignIn ?? (() => undefined);
  return {
    install(app) {
      app.provide(EXAM_WORKSPACE_STORE_KEY, store);
      app.provide(EXAM_WORKSPACE_SIGN_IN_KEY, requestSignIn);
    },
  };
}
