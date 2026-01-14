<script setup lang="ts">
import { computed } from "vue";

import type { RemoteFallbackPreference } from "../../stores/ai";

const props = defineProps<{
  remoteFallbackPreference: RemoteFallbackPreference;
}>();

const emit = defineEmits<{
  edit: [];
}>();

const preferenceLabel = computed(() => {
  switch (props.remoteFallbackPreference) {
    case "allow":
      return "Aktiverat";
    case "deny":
      return "Avstängt";
    default:
      return "Inte inställt";
  }
});

const preferenceHint = computed(() => {
  if (props.remoteFallbackPreference === "allow") {
    return "Kodassistenten kan använda externa AI-API:er vid behov.";
  }

  if (props.remoteFallbackPreference === "deny") {
    return "Kodassistenten använder endast lokala modeller.";
  }

  return "Aktivera eller stäng av externa AI-API:er.";
});

const actionLabel = computed(() => {
  return props.remoteFallbackPreference === "unset" ? "Välj" : "Ändra";
});
</script>

<template>
  <section class="border border-navy bg-white shadow-brutal-sm">
    <div class="flex items-center justify-between border-b border-navy px-4 py-3">
      <div>
        <h3 class="text-sm font-semibold text-navy">AI-inställningar</h3>
        <p class="text-xs text-navy/70">Kodassistenten och externa AI-API:er</p>
      </div>
      <button
        type="button"
        class="btn-ghost px-3 py-1 text-xs"
        @click="emit('edit')"
      >
        {{ actionLabel }}
      </button>
    </div>

    <dl class="divide-y divide-navy/20 px-4 text-sm">
      <div class="grid gap-1 pt-3 pb-1 sm:gap-4 sm:items-baseline sm:grid-cols-[10rem_1fr]">
        <dt class="text-xs font-semibold uppercase tracking-wide text-navy/70">Externa AI-API:er</dt>
        <dd class="text-navy">
          <span class="font-semibold">{{ preferenceLabel }}</span>
          <span class="block text-xs text-navy/70">{{ preferenceHint }}</span>
        </dd>
      </div>
      <div class="grid gap-1 pt-3 pb-1 sm:gap-4 sm:items-baseline sm:grid-cols-[10rem_1fr]">
        <dt class="text-xs font-semibold uppercase tracking-wide text-navy/70">Integritet</dt>
        <dd class="text-xs text-navy/70">
          Externa AI-API:er kan skicka innehåll utanför servern. Välj vad som passar din miljö.
        </dd>
      </div>
    </dl>
  </section>
</template>
