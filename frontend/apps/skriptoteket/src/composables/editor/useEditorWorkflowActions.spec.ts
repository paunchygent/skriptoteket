import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, reactive, ref, type EffectScope } from "vue";

import { useEditorWorkflowActions } from "./useEditorWorkflowActions";
import type { UiNotifier } from "../notify";

type AuthMock = {
  hasAtLeastRole: ReturnType<typeof vi.fn>;
};

const clientMocks = vi.hoisted(() => ({
  apiPost: vi.fn(),
  isApiError: vi.fn(),
}));

const authState = vi.hoisted(() => ({
  value: null as AuthMock | null,
}));

vi.mock("../../api/client", () => ({
  apiPost: clientMocks.apiPost,
  isApiError: clientMocks.isApiError,
}));

vi.mock("../../stores/auth", () => ({
  useAuthStore: () => authState.value,
}));

type NotifyMock = {
  info: ReturnType<typeof vi.fn<(message: string) => void>>;
  success: ReturnType<typeof vi.fn<(message: string) => void>>;
  warning: ReturnType<typeof vi.fn<(message: string) => void>>;
  failure: ReturnType<typeof vi.fn<(message: string) => void>>;
};

function createNotify(): NotifyMock {
  return {
    info: vi.fn<(message: string) => void>(),
    success: vi.fn<(message: string) => void>(),
    warning: vi.fn<(message: string) => void>(),
    failure: vi.fn<(message: string) => void>(),
  };
}

function createAuth(overrides: Partial<AuthMock> = {}): AuthMock {
  return {
    hasAtLeastRole: overrides.hasAtLeastRole ?? vi.fn().mockReturnValue(false),
  };
}

function createWorkflow(selectedVersion: ReturnType<typeof ref>) {
  const route = reactive({
    path: "/admin/tools/1",
    fullPath: "/admin/tools/1",
    query: {},
  });
  const router = {
    push: vi.fn().mockResolvedValue(undefined),
  };
  const reloadEditor = vi.fn().mockResolvedValue(undefined);
  const notify = createNotify();

  let workflow!: ReturnType<typeof useEditorWorkflowActions>;
  const scope: EffectScope = effectScope();
  scope.run(() => {
    workflow = useEditorWorkflowActions({
      selectedVersion: selectedVersion as never,
      route: route as never,
      router: router as never,
      reloadEditor,
      notify: notify as UiNotifier,
    });
  });

  return { scope, workflow, router, reloadEditor, notify };
}

beforeEach(() => {
  clientMocks.apiPost.mockReset();
  clientMocks.isApiError.mockReset();
});

describe("useEditorWorkflowActions", () => {
  it("exposes review actions based on role + state", () => {
    authState.value = createAuth({ hasAtLeastRole: vi.fn().mockReturnValue(true) });
    const selectedVersion = ref({ id: "ver-1", state: "in_review" } as never);
    const { scope, workflow } = createWorkflow(selectedVersion);

    expect(workflow.actionItems.value.map((item) => item.id)).toEqual([
      "publish",
      "request_changes",
    ]);

    scope.stop();
  });

  it("submits publish actions and navigates to redirect", async () => {
    authState.value = createAuth({ hasAtLeastRole: vi.fn().mockReturnValue(true) });
    const selectedVersion = ref({ id: "ver-1", state: "in_review" } as never);
    const { scope, workflow, router, notify } = createWorkflow(selectedVersion);

    clientMocks.apiPost.mockResolvedValueOnce({ redirect_url: "/admin/tools/1/versions" });

    workflow.openAction("publish");
    workflow.note.value = "Updated summary";

    await workflow.submitAction();

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/editor/tool-versions/ver-1/publish",
      { change_summary: "Updated summary" },
    );
    expect(notify.success).toHaveBeenCalledWith("Version publicerad.");
    expect(router.push).toHaveBeenCalledWith("/admin/tools/1/versions");
    expect(workflow.isModalOpen.value).toBe(false);

    scope.stop();
  });

  it("surfaces API errors during workflow actions", async () => {
    authState.value = createAuth({ hasAtLeastRole: vi.fn().mockReturnValue(true) });
    const selectedVersion = ref({ id: "ver-1", state: "draft" } as never);
    const { scope, workflow } = createWorkflow(selectedVersion);

    clientMocks.apiPost.mockRejectedValueOnce({ status: 500, message: "Boom" });
    clientMocks.isApiError.mockReturnValue(true);

    workflow.openAction("submit_review");
    await workflow.submitAction();

    expect(workflow.workflowError.value).toBe("Boom");
    expect(workflow.isSubmitting.value).toBe(false);

    scope.stop();
  });
});
