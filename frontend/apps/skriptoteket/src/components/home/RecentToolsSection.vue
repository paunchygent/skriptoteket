<script setup lang="ts">
import { computed, toRef } from "vue";

import type { CatalogItem } from "../../types/catalog";
import { useEqualHeightGrid } from "../../composables/useEqualHeightGrid";
import CatalogItemCard from "../catalog/CatalogItemCard.vue";
import SectionHeader from "./SectionHeader.vue";

type Props = {
  items: CatalogItem[];
  isToggling?: (id: string) => boolean;
};

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "favorite-toggled", payload: { id: string; isFavorite: boolean }): void;
}>();

const hasItems = computed(() => props.items.length > 0);
const { gridRef } = useEqualHeightGrid(toRef(props, "items"));

function isItemToggling(id: string): boolean {
  return props.isToggling ? props.isToggling(id) : false;
}

function handleFavoriteToggled(payload: { id: string; isFavorite: boolean }): void {
  emit("favorite-toggled", payload);
}
</script>

<template>
  <section
    v-if="hasItems"
    class="space-y-3"
  >
    <SectionHeader title="Senast använda" />
    <div
      ref="gridRef"
      class="grid items-stretch gap-3 sm:grid-cols-2 xl:grid-cols-3"
    >
      <CatalogItemCard
        v-for="item in items"
        :key="`${item.kind}-${item.id}`"
        :item="item"
        variant="compact"
        :is-toggling="isItemToggling(item.id)"
        @favorite-toggled="handleFavoriteToggled"
      />
    </div>
  </section>
</template>
