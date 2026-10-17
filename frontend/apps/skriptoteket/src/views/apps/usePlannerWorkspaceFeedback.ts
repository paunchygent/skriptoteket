import { ref, watch } from "vue";

import { useToast } from "../../composables/useToast";
import type { useClassroomState } from "./useClassroomState";

/** Announces workspace notices and smart-run outcomes once per distinct result. */
export function usePlannerWorkspaceFeedback(
  plannerState: ReturnType<typeof useClassroomState>,
  workspaceNotice?: { message: () => string | null; dismiss: () => void },
): void {
  const toast = useToast();
  const lastGroupingSmartRunToast = ref<string | null>(null);
  const lastSeatingSmartRunToast = ref<string | null>(null);

  if (workspaceNotice) {
    const lastWorkspaceNotice = ref<string | null>(null);
    watch(workspaceNotice.message, (nextNotice) => {
      if (!nextNotice) {
        lastWorkspaceNotice.value = null;
        return;
      }
      if (nextNotice === lastWorkspaceNotice.value) {
        return;
      }
      toast.info(nextNotice);
      lastWorkspaceNotice.value = nextNotice;
      workspaceNotice.dismiss();
    }, { immediate: true });
  }

  function showSmartRunToast(options: {
    message: string | null;
    tone: "neutral" | "success" | "warning";
    lastToastRef: { value: string | null };
  }): void {
    const { message, tone, lastToastRef } = options;
    if (!message) {
      lastToastRef.value = null;
      return;
    }

    const toastKey = `${tone}:${message}`;
    if (toastKey === lastToastRef.value) {
      return;
    }

    if (tone === "success") {
      toast.success(message);
    } else if (tone === "warning") {
      toast.warning(message);
    } else {
      toast.info(message);
    }
    lastToastRef.value = toastKey;
  }

  watch(
    () => ({
      message: plannerState.smartGroupingRunMessage,
      tone: plannerState.smartGroupingRunTone,
    }),
    ({ message, tone }) => {
      showSmartRunToast({
        message,
        tone,
        lastToastRef: lastGroupingSmartRunToast,
      });
    },
  );

  watch(
    () => ({
      message: plannerState.smartSeatingRunMessage,
      tone: plannerState.smartSeatingRunTone,
    }),
    ({ message, tone }) => {
      showSmartRunToast({
        message,
        tone,
        lastToastRef: lastSeatingSmartRunToast,
      });
    },
  );
}
