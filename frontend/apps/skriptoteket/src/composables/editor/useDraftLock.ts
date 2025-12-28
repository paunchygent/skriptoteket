import { computed, onBeforeUnmount, ref, watch, type Ref } from "vue";

import { apiFetch, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";

export type DraftLockState = "inactive" | "acquiring" | "owner" | "locked";

type DraftLockResponse = components["schemas"]["DraftLockResponse"];

type UseDraftLockOptions = {
  toolId: Readonly<Ref<string>>;
  draftHeadId: Readonly<Ref<string | null>>;
  initialLock: Readonly<Ref<DraftLockResponse | null>>;
  heartbeatMs?: number;
};

type AcquireLockOptions = {
  force?: boolean;
  silent?: boolean;
};

const DEFAULT_HEARTBEAT_MS = 60_000;

export function useDraftLock({
  toolId,
  draftHeadId,
  initialLock,
  heartbeatMs = DEFAULT_HEARTBEAT_MS,
}: UseDraftLockOptions) {
  const lock = ref<DraftLockResponse | null>(null);
  const isLocking = ref(false);
  const lockError = ref<string | null>(null);
  let heartbeatId: number | null = null;

  const hasDraftHead = computed(() => Boolean(draftHeadId.value));
  const isOwner = computed(() => lock.value?.is_owner ?? false);
  const isLockedByOther = computed(() => Boolean(lock.value) && !lock.value?.is_owner);

  const state = computed<DraftLockState>(() => {
    if (!hasDraftHead.value) return "inactive";
    if (isOwner.value) return "owner";
    if (isLockedByOther.value) return "locked";
    return "acquiring";
  });

  const isReadOnly = computed(() => hasDraftHead.value && !isOwner.value);
  const expiresAt = computed(() => lock.value?.expires_at ?? null);

  const statusMessage = computed(() => {
    if (!hasDraftHead.value) return null;
    if (state.value === "owner") {
      return "Du har redigeringslåset. Förnyas automatiskt.";
    }
    if (state.value === "locked") {
      return "Utkastet är låst av en annan användare. Du kan läsa men inte spara eller testköra.";
    }
    if (state.value === "acquiring") {
      return "Säkrar redigeringslås...";
    }
    return null;
  });

  function stopHeartbeat(): void {
    if (heartbeatId !== null) {
      window.clearInterval(heartbeatId);
      heartbeatId = null;
    }
  }

  function startHeartbeat(): void {
    stopHeartbeat();
    if (!hasDraftHead.value || !toolId.value) {
      return;
    }
    heartbeatId = window.setInterval(() => {
      void acquireLock({ silent: true });
    }, heartbeatMs);
  }

  function applyLockedStateFromError(error: unknown): void {
    if (!isApiError(error)) {
      return;
    }
    const details = error.details;
    if (!details || typeof details !== "object") {
      return;
    }
    const record = details as Record<string, unknown>;
    const lockedByUserId =
      typeof record.locked_by_user_id === "string" ? record.locked_by_user_id : null;
    const expiresAt = typeof record.expires_at === "string" ? record.expires_at : null;
    if (!lockedByUserId || !expiresAt || !toolId.value || !draftHeadId.value) {
      return;
    }
    lock.value = {
      tool_id: toolId.value,
      draft_head_id: draftHeadId.value,
      locked_by_user_id: lockedByUserId,
      expires_at: expiresAt,
      is_owner: false,
    };
  }

  async function acquireLock(options: AcquireLockOptions = {}): Promise<void> {
    if (!toolId.value || !draftHeadId.value) {
      return;
    }
    if (isLocking.value) {
      return;
    }

    const force = options.force ?? false;
    const silent = options.silent ?? false;

    isLocking.value = true;
    if (!silent) {
      lockError.value = null;
    }

    try {
      const response = await apiFetch<DraftLockResponse>(
        `/api/v1/editor/tools/${encodeURIComponent(toolId.value)}/draft-lock`,
        {
          method: "POST",
          body: {
            draft_head_id: draftHeadId.value,
            force,
          },
        },
      );
      lock.value = response;
      if (!silent) {
        lockError.value = null;
      }
    } catch (error: unknown) {
      applyLockedStateFromError(error);
      if (!silent) {
        if (isApiError(error)) {
          lockError.value = error.message;
        } else if (error instanceof Error) {
          lockError.value = error.message;
        } else {
          lockError.value = "Det gick inte att säkra redigeringslåset.";
        }
      }
    } finally {
      isLocking.value = false;
    }
  }

  function forceTakeover(): Promise<void> {
    return acquireLock({ force: true, silent: false });
  }

  watch(
    [toolId, draftHeadId, initialLock],
    ([toolIdValue, draftHeadValue, bootLock]) => {
      if (!toolIdValue || !draftHeadValue) {
        lock.value = null;
        lockError.value = null;
        stopHeartbeat();
        return;
      }

      if (bootLock && bootLock.draft_head_id === draftHeadValue) {
        lock.value = bootLock;
      } else {
        lock.value = null;
      }
      lockError.value = null;
      startHeartbeat();
      void acquireLock({ silent: true });
    },
    { immediate: true },
  );

  onBeforeUnmount(() => {
    stopHeartbeat();
  });

  return {
    state,
    isOwner,
    isReadOnly,
    isLocking,
    expiresAt,
    statusMessage,
    lockError,
    forceTakeover,
  };
}
