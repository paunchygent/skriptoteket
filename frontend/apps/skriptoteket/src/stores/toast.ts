import { defineStore } from "pinia";
import { ref } from "vue";

export type ToastVariant = "info" | "success" | "warning" | "failure";

export type ToastItem = {
  id: string;
  variant: ToastVariant;
  message: string;
  durationMs: number;
};

type ShowToastOptions = {
  durationMs?: number;
};

function defaultDurationMs(variant: ToastVariant): number {
  switch (variant) {
    case "warning":
      return 10_000;
    case "failure":
      return 12_000;
    case "info":
    case "success":
    default:
      return 6_000;
  }
}

function createToastId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export const useToastStore = defineStore("toast", () => {
  const toasts = ref<ToastItem[]>([]);
  const timers = new Map<string, number>();

  const maxToasts = 3;

  function clearTimer(id: string): void {
    const timerId = timers.get(id);
    if (timerId !== undefined) {
      window.clearTimeout(timerId);
      timers.delete(id);
    }
  }

  function dismiss(id: string): void {
    clearTimer(id);
    toasts.value = toasts.value.filter((toast) => toast.id !== id);
  }

  function show(variant: ToastVariant, message: string, options: ShowToastOptions = {}): string {
    const normalizedMessage = message.trim();
    const durationMs = Math.max(0, options.durationMs ?? defaultDurationMs(variant));

    if (toasts.value.length >= maxToasts) {
      dismiss(toasts.value[0].id);
    }

    const id = createToastId();
    toasts.value.push({ id, variant, message: normalizedMessage, durationMs });

    if (durationMs > 0) {
      const timerId = window.setTimeout(() => dismiss(id), durationMs);
      timers.set(id, timerId);
    }

    return id;
  }

  function info(message: string, options?: ShowToastOptions): string {
    return show("info", message, options);
  }

  function success(message: string, options?: ShowToastOptions): string {
    return show("success", message, options);
  }

  function warning(message: string, options?: ShowToastOptions): string {
    return show("warning", message, options);
  }

  function failure(message: string, options?: ShowToastOptions): string {
    return show("failure", message, options);
  }

  function dismissAll(): void {
    for (const toast of toasts.value) {
      clearTimer(toast.id);
    }
    toasts.value = [];
  }

  return {
    toasts,
    dismiss,
    dismissAll,
    show,
    info,
    success,
    warning,
    failure,
  };
});
