<script setup lang="ts">
import type { ToastVariant } from "../../stores/toast";
import { useToast } from "../../composables/useToast";
import { IconCheck, IconWarning, IconX, IconInfo } from "../icons";

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
            <IconCheck
              v-if="item.variant === 'success'"
              :size="16"
            />
            <IconWarning
              v-else-if="item.variant === 'warning'"
              :size="16"
            />
            <IconX
              v-else-if="item.variant === 'failure'"
              :size="16"
            />
            <IconInfo
              v-else
              :size="16"
            />
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
