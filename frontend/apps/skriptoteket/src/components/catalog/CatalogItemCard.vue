<script setup lang="ts">
import { computed } from "vue";

import type { CatalogItem } from "../../types/catalog";
import { IconBookmark } from "../icons";

type Variant = "default" | "compact" | "list";

type Props = {
  item: CatalogItem;
  isToggling?: boolean;
  variant?: Variant;
};

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "favorite-toggled", payload: { id: string; isFavorite: boolean }): void;
}>();

const isCuratedApp = computed(() => props.item.kind === "curated_app");
const isCompact = computed(() => props.variant === "compact");
const isList = computed(() => props.variant === "list");
const actionLabel = computed(() => (isCuratedApp.value ? "Öppna" : "Välj"));

const actionTarget = computed(() => {
  if (props.item.kind === "curated_app") {
    return { name: "app-detail", params: { appId: props.item.app_id } };
  }
  return { name: "tool-run", params: { slug: props.item.slug } };
});

function handleToggle(): void {
  emit("favorite-toggled", { id: props.item.id, isFavorite: props.item.is_favorite });
}
</script>

<template>
  <article
    :class="[
      'relative',
      isList ? 'px-4 py-3' : 'border border-navy bg-white shadow-brutal-sm',
      isCompact ? 'flex flex-col h-full p-3' : (!isList && 'p-4'),
    ]"
  >
    <div
      v-if="isCompact"
      class="grid h-full grid-cols-[minmax(0,1fr)_auto_auto] grid-rows-[auto_auto_1fr_auto] gap-x-3 gap-y-2"
    >
      <h3 class="min-w-0 text-sm font-semibold text-navy clamp-2 compact-title col-start-1 row-start-1">
        {{ item.title }}
      </h3>
      <span
        v-if="isCuratedApp"
        class="inline-flex items-center justify-self-end self-start h-5 px-2 py-0 text-[10px] uppercase tracking-wide border border-navy/60 bg-canvas text-navy leading-none sm:text-xs col-start-2 row-start-1"
      >
        Kurerad app
      </span>
      <button
        type="button"
        :disabled="isToggling"
        :aria-label="item.is_favorite ? 'Ta bort favorit' : 'Lägg till favorit'"
        :aria-pressed="item.is_favorite"
        :class="[
          'inline-flex items-center justify-center justify-self-end self-start -mt-1 col-start-3 row-start-1',
          'focus-visible:outline focus-visible:outline-2',
          'focus-visible:outline-burgundy/40 focus-visible:outline-offset-2',
          'transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
          item.is_favorite ? 'text-burgundy' : 'text-burgundy/70 hover:text-burgundy',
          'h-6 w-6',
        ]"
        @click="handleToggle"
      >
        <IconBookmark
          class="h-full w-full"
          :filled="item.is_favorite"
        />
      </button>
      <p
        v-if="item.summary"
        class="min-w-0 text-xs text-navy/60 break-words clamp-4 compact-summary col-span-3 row-start-2"
      >
        {{ item.summary }}
      </p>
      <p
        v-else
        class="compact-summary col-span-3 row-start-2"
        aria-hidden="true"
      />
      <div class="col-start-3 row-start-4 justify-self-end">
        <RouterLink
          :to="actionTarget"
          class="btn-ghost w-full sm:w-auto sm:min-w-24 text-center no-underline"
        >
          {{ actionLabel }}
        </RouterLink>
      </div>
    </div>

    <div
      v-else
      :class="[
        'flex flex-col sm:flex-row sm:items-center sm:justify-between',
        isList ? 'gap-2 sm:gap-4' : 'gap-3 sm:gap-6 sm:items-stretch',
      ]"
    >
      <button
        v-if="!isList"
        type="button"
        :disabled="isToggling"
        :aria-label="item.is_favorite ? 'Ta bort favorit' : 'Lägg till favorit'"
        :aria-pressed="item.is_favorite"
        :class="[
          'absolute top-0 inline-flex items-center justify-center',
          'focus-visible:outline focus-visible:outline-2',
          'focus-visible:outline-burgundy/40 focus-visible:outline-offset-2',
          'transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
          item.is_favorite ? 'text-burgundy' : 'text-burgundy/70 hover:text-burgundy',
          'right-3 h-6 w-6 sm:right-4 sm:h-7 sm:w-7',
        ]"
        @click="handleToggle"
      >
        <IconBookmark
          class="h-full w-full"
          :filled="item.is_favorite"
        />
      </button>
      <div :class="['min-w-0', isList ? 'space-y-0.5' : 'space-y-1 pr-12 sm:pr-14']">
        <div class="flex flex-wrap items-center gap-2">
          <h3 :class="['font-semibold text-navy', isList ? 'text-sm' : 'text-base']">
            {{ item.title }}
          </h3>
          <span
            v-if="isCuratedApp"
            :class="[
              'inline-flex items-center self-center px-2 py-0 uppercase tracking-wide border border-navy/60 bg-canvas text-navy leading-none',
              isList ? 'h-4 text-[9px]' : 'h-5 text-[10px] sm:text-xs',
            ]"
          >
            Kurerad app
          </span>
        </div>
        <p
          v-if="item.summary"
          :class="['text-navy/60 break-words', isList ? 'text-xs line-clamp-1' : 'text-sm']"
        >
          {{ item.summary }}
        </p>
      </div>

      <div
        :class="[
          'flex shrink-0 items-center gap-3',
          isList ? '' : 'flex-col gap-2 items-end sm:self-stretch sm:justify-end pt-6 sm:pt-7',
        ]"
      >
        <RouterLink
          :to="actionTarget"
          :class="[
            'text-center no-underline',
            isList ? 'btn-ghost text-xs py-1.5 px-3' : 'btn-ghost w-full sm:w-auto sm:min-w-24',
          ]"
        >
          {{ actionLabel }}
        </RouterLink>
        <button
          v-if="isList"
          type="button"
          :disabled="isToggling"
          :aria-label="item.is_favorite ? 'Ta bort favorit' : 'Lägg till favorit'"
          :aria-pressed="item.is_favorite"
          :class="[
            'inline-flex items-center justify-center h-5 w-5',
            'focus-visible:outline focus-visible:outline-2',
            'focus-visible:outline-burgundy/40 focus-visible:outline-offset-2',
            'transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
            item.is_favorite ? 'text-burgundy' : 'text-burgundy/70 hover:text-burgundy',
          ]"
          @click="handleToggle"
        >
          <IconBookmark
            class="h-full w-full"
            :filled="item.is_favorite"
          />
        </button>
      </div>
    </div>
  </article>
</template>

<style scoped>
.clamp-2,
.clamp-4 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.compact-title {
  min-height: 2.4em;
}

.compact-summary {
  min-height: 5.6em;
}

.clamp-2 {
  -webkit-line-clamp: 2;
}

.clamp-4 {
  -webkit-line-clamp: 4;
}
</style>
