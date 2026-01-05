import { onBeforeUnmount, ref } from "vue";

type UseToolRunPollingOptions = {
  poll: (runId: string) => Promise<void> | void;
  intervalMs?: number;
};

const DEFAULT_POLL_INTERVAL_MS = 2000;

export function useToolRunPolling(options: UseToolRunPollingOptions) {
  const isPolling = ref(false);
  let pollIntervalId: number | null = null;

  function stopPolling(): void {
    if (pollIntervalId !== null) {
      window.clearInterval(pollIntervalId);
      pollIntervalId = null;
      isPolling.value = false;
    }
  }

  function startPolling(runId: string): void {
    if (pollIntervalId !== null) return;

    const intervalMs = options.intervalMs ?? DEFAULT_POLL_INTERVAL_MS;
    isPolling.value = true;
    pollIntervalId = window.setInterval(() => {
      void Promise.resolve(options.poll(runId)).catch(() => {
        // Silent polling failure; main error handling happens elsewhere.
      });
    }, intervalMs);
  }

  onBeforeUnmount(() => {
    stopPolling();
  });

  return {
    isPolling,
    startPolling,
    stopPolling,
  };
}
