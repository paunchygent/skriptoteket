<script setup lang="ts">
import { ref } from "vue";

import SystemMessage from "../../components/ui/SystemMessage.vue";
import { useAppAvailability } from "../../composables/useAppAvailability";

const props = defineProps<{
  appTitle: string;
}>();

const { unavailableMessage } = useAppAvailability();
const message = ref<string | null>(unavailableMessage(props.appTitle));
</script>

<template>
  <section class="mx-auto max-w-[40rem] space-y-6">
    <SystemMessage
      v-model="message"
      variant="info"
      :dismissible="false"
    />
    <RouterLink
      to="/"
      class="btn-ghost"
    >
      Gå till startsidan
    </RouterLink>
  </section>
</template>
