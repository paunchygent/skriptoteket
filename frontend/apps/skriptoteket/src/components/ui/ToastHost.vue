<script setup lang="ts">
import type { ToastVariant } from "../../stores/toast";
import { useToast } from "../../composables/useToast";

const toast = useToast();

function dismiss(id: string): void {
  toast.dismiss(id);
}

function variantLabel(variant: ToastVariant): string {
  switch (variant) {
    case "success":
      return "Lyckades";
    case "warning":
      return "Varning";
    case "failure":
      return "Misslyckades";
    case "info":
    default:
      return "Info";
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup
        name="toast"
        tag="div"
        class="toast-stack"
      >
        <div
          v-for="item in toast.toasts"
          :key="item.id"
          class="toast"
          :class="`toast-${item.variant}`"
          :role="item.variant === 'failure' ? 'alert' : 'status'"
          aria-atomic="true"
        >
          <span
            class="toast-icon"
            aria-hidden="true"
          >
            <svg
              v-if="item.variant === 'success'"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="square"
              stroke-linejoin="miter"
            >
              <path d="M20 6 9 17l-5-5" />
            </svg>
            <svg
              v-else-if="item.variant === 'warning'"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="square"
              stroke-linejoin="miter"
            >
              <path d="M12 3 22 21H2L12 3Z" />
              <path d="M12 9v5" />
              <circle
                cx="12"
                cy="17"
                r="1"
                fill="currentColor"
                stroke="none"
              />
            </svg>
            <svg
              v-else-if="item.variant === 'failure'"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="square"
              stroke-linejoin="miter"
            >
              <path d="M8 8l8 8M16 8l-8 8" />
            </svg>
            <svg
              v-else
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="square"
              stroke-linejoin="miter"
            >
              <circle
                cx="12"
                cy="12"
                r="9"
              />
              <path d="M12 10v6" />
              <circle
                cx="12"
                cy="7.5"
                r="1"
                fill="currentColor"
                stroke="none"
              />
            </svg>
          </span>

          <p class="toast-message">
            <span class="sr-only">{{ variantLabel(item.variant) }}: </span>
            {{ item.message }}
          </p>

          <button
            type="button"
            class="toast-close"
            aria-label="Stäng"
            @click="dismiss(item.id)"
          >
            &times;
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
