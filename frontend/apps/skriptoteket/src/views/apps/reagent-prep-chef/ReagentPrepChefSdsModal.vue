<script setup lang="ts">
import UiMarkdown from "../../../components/ui/UiMarkdown.vue";

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
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="props.isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40"
        role="dialog"
        aria-modal="true"
        @click.self="emit('close')"
      >
        <div class="relative w-full max-w-4xl mx-4 p-6 bg-modal border border-navy shadow-brutal">
          <button
            type="button"
            class="absolute top-3 right-3 text-navy/60 hover:text-navy text-xl leading-none"
            @click="emit('close')"
          >
            &times;
          </button>

          <div class="flex flex-wrap items-start justify-between gap-3 pr-8">
            <div class="space-y-1">
              <h2 class="text-xl font-semibold text-navy">
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

          <div class="mt-4 border border-navy bg-panel shadow-none max-h-[70vh] overflow-auto p-4">
            <p
              v-if="props.isLoading"
              class="text-sm text-navy/70"
            >
              Laddar SDS…
            </p>
            <p
              v-else-if="!props.markdown"
              class="text-sm text-navy/70"
            >
              SDS saknas.
            </p>
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
