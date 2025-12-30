import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, nextTick, ref } from "vue";
import { mount } from "@vue/test-utils";

import { useDraftLock } from "./useDraftLock";

const clientMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  isApiError: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  apiFetch: clientMocks.apiFetch,
  isApiError: clientMocks.isApiError,
}));

async function flushPromises(): Promise<void> {
  await nextTick();
  await Promise.resolve();
}

type DraftLockResponse = {
  tool_id: string;
  draft_head_id: string;
  locked_by_user_id: string;
  expires_at: string;
  is_owner: boolean;
};

function mountDraftLock({
  toolIdValue = "tool-1",
  draftHeadIdValue = "draft-1",
  initialLockValue = null,
  heartbeatMs = 1_000,
}: {
  toolIdValue?: string;
  draftHeadIdValue?: string;
  initialLockValue?: DraftLockResponse | null;
  heartbeatMs?: number;
} = {}) {
  const toolId = ref(toolIdValue);
  const draftHeadId = ref(draftHeadIdValue);
  const initialLock = ref(initialLockValue);

  const TestComponent = defineComponent({
    name: "TestDraftLock",
    setup() {
      return useDraftLock({
        toolId,
        draftHeadId,
        initialLock,
        heartbeatMs,
      });
    },
    template: "<div />",
  });

  const wrapper = mount(TestComponent);
  return { wrapper };
}

beforeEach(() => {
  clientMocks.apiFetch.mockReset();
  clientMocks.isApiError.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useDraftLock", () => {
  it("acquires the lock and marks the user as owner", async () => {
    clientMocks.apiFetch.mockResolvedValueOnce({
      tool_id: "tool-1",
      draft_head_id: "draft-1",
      locked_by_user_id: "user-1",
      expires_at: "2030-01-01T00:00:00Z",
      is_owner: true,
    });

    const { wrapper } = mountDraftLock();
    await flushPromises();

    const vm = wrapper.vm as unknown as ReturnType<typeof useDraftLock>;
    expect(vm.state).toBe("owner");
    expect(vm.isReadOnly).toBe(false);
    expect(vm.statusMessage).toContain("redigeringslåset");

    wrapper.unmount();
  });

  it("hydrates locked state from API error details", async () => {
    clientMocks.apiFetch.mockRejectedValueOnce({
      status: 409,
      message: "Locked",
      details: {
        locked_by_user_id: "user-2",
        expires_at: "2030-01-01T00:00:00Z",
      },
    });
    clientMocks.isApiError.mockReturnValue(true);

    const { wrapper } = mountDraftLock();
    await flushPromises();

    const vm = wrapper.vm as unknown as ReturnType<typeof useDraftLock>;
    expect(vm.state).toBe("locked");
    expect(vm.lockError).toBeNull();

    wrapper.unmount();
  });

  it("reacquires the lock on heartbeat", async () => {
    vi.useFakeTimers();
    clientMocks.apiFetch.mockResolvedValue({
      tool_id: "tool-1",
      draft_head_id: "draft-1",
      locked_by_user_id: "user-1",
      expires_at: "2030-01-01T00:00:00Z",
      is_owner: true,
    });

    const { wrapper } = mountDraftLock({ heartbeatMs: 500 });
    await flushPromises();

    expect(clientMocks.apiFetch).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(500);
    await flushPromises();

    expect(clientMocks.apiFetch).toHaveBeenCalledTimes(2);

    wrapper.unmount();
  });
});
