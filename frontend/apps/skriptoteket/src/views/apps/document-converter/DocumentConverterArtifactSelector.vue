<script setup lang="ts">
/**
 * Output artifact selector for the Document Converter route.
 *
 * Domain purpose:
 *   Let teachers choose among generated converter outputs inside the
 *   middle-column file-operations flow.
 *
 * Relationships:
 *   - Used by `DocumentConverterView.vue`.
 *   - Receives artifact filenames from project-preview or single-file history
 *     state.
 *   - Emits artifact-selection intent back to the route host.
 */
import { IconFileText } from "../../../components/icons";

type ArtifactOption = {
  artifactId: string;
  filename: string;
};

defineProps<{
  activeArtifactId: string | null;
  artifactOptions: ArtifactOption[];
}>();

const emit = defineEmits<{
  selectArtifact: [artifactId: string];
}>();
</script>

<template>
  <section
    v-if="artifactOptions.length > 1"
    class="dc-artifact-selector"
    aria-label="Skapade filer"
    data-testid="document-converter-artifact-selector"
  >
    <button
      v-for="artifact in artifactOptions"
      :key="artifact.artifactId"
      class="dc-artifact-selector__item"
      :class="{ 'dc-artifact-selector__item--active': artifact.artifactId === activeArtifactId }"
      type="button"
      @click="emit('selectArtifact', artifact.artifactId)"
    >
      <IconFileText :size="16" />
      <span>{{ artifact.filename }}</span>
    </button>
  </section>
</template>
