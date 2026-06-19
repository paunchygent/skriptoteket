<script setup lang="ts">
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
</script>

<template>
  <HelpTopicLayout
    title="Mina filer"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>
        Här ligger sparade filer och exporter, till exempel körresultat eller
        dokument du använder ofta.
      </li>
      <li>Du kan öppna, ladda ner eller ta bort filer. Tar du bort en fil är den borta för gott.</li>
      <li>Utrymmet är begränsat. När du närmar dig gränsen syns en varning högst upp.</li>
    </ul>
  </HelpTopicLayout>
</template>
