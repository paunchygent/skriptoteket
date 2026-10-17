<script setup lang="ts">
import { ref, useId } from "vue";

import { IconX } from "../../../components/icons";
import { SystemMessage, UiDenseIconButton, UiMarkdown } from "../../../components/ui";
import { useDialogFocus } from "../../../composables/useDialogFocus";

const props = withDefaults(defineProps<{
  isOpen: boolean;
  title: string;
  provider?: string | null;
  revision?: string | null;
  markdown?: string | null;
  pdfUrl?: string | null;
  isLoading?: boolean;
}>(), {
  provider: null,
  revision: null,
  markdown: null,
  pdfUrl: null,
  isLoading: false,
});

const emit = defineEmits<{
  close: [];
}>();

const titleId = useId();
const dialog = ref<HTMLElement | null>(null);

useDialogFocus(dialog, {
  modal: () => true,
  takesFocus: () => true,
  onClose: () => emit("close"),
});
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="props.isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40"
        @click.self="emit('close')"
      >
        <div
          ref="dialog"
          class="relative w-full max-w-4xl mx-4 p-6 rounded-[var(--huleedu-panel-radius)] bg-modal border border-navy/20 shadow-md"
          role="dialog"
          tabindex="-1"
          aria-modal="true"
          :aria-labelledby="titleId"
        >
          <UiDenseIconButton
            class="absolute top-3 right-3"
            label="Stäng SDS"
            @click="emit('close')"
          >
            <IconX :size="16" />
          </UiDenseIconButton>

          <div class="flex flex-wrap items-start justify-between gap-3 pr-8">
            <div class="space-y-1">
              <h2
                :id="titleId"
                class="text-xl font-semibold text-navy"
              >
                {{ props.title }}
              </h2>
              <p class="text-xs text-navy/70">
                Leverantör: {{ props.provider || "—" }} · Revision: {{ props.revision || "—" }}
              </p>
            </div>

            <a
              v-if="props.pdfUrl"
              class="btn-ghost"
              :href="props.pdfUrl"
              target="_blank"
              rel="noopener"
            >
              Öppna PDF
            </a>
          </div>

          <div class="mt-4 rounded-[var(--huleedu-panel-radius)] border border-navy/20 bg-panel max-h-[70vh] overflow-auto p-4">
            <SystemMessage v-if="props.isLoading">
              Laddar SDS…
            </SystemMessage>
            <SystemMessage v-else-if="!props.markdown">
              SDS saknas.
            </SystemMessage>
            <UiMarkdown
              v-else
              :markdown="props.markdown"
            />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
