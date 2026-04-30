<script setup lang="ts">
/**
 * Owned Klassrumskartan share-link panel.
 *
 * Relationships:
 * - receives owner-scoped share metadata from the authenticated route shell
 * - emits copy/revoke intents back to the share-flow composable
 * - stays out of the public guest shell until PR-0273 owns that route
 */

import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";

const props = withDefaults(
  defineProps<{
    shares?: ClassroomPlannerShareArtifact[];
    copiedShareId?: string | null;
    revokingShareId?: string | null;
    loading?: boolean;
  }>(),
  {
    shares: () => [],
    copiedShareId: null,
    revokingShareId: null,
    loading: false,
  },
);

const emit = defineEmits<{
  (e: "copy-share", share: ClassroomPlannerShareArtifact): void;
  (e: "revoke-share", share: ClassroomPlannerShareArtifact): void;
}>();

const dateFormatter = new Intl.DateTimeFormat("sv-SE", {
  dateStyle: "short",
  timeStyle: "short",
});

function formatCreatedAt(value: string): string {
  return dateFormatter.format(new Date(value));
}
</script>

<template>
  <section
    class="border-t border-navy/15 pt-3"
    data-test="planner-share-links-panel"
  >
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-sm font-semibold text-navy">
        Delade länkar
      </h2>
      <span
        v-if="loading"
        class="text-xs font-semibold text-navy/60"
      >
        Hämtar länkar…
      </span>
    </div>

    <p
      v-if="!loading && props.shares.length === 0"
      class="mt-2 text-xs text-navy/65"
      data-test="planner-share-links-empty"
    >
      Inga delade länkar för det här utkastet ännu.
    </p>

    <ul
      v-else
      class="mt-2 divide-y divide-navy/10 border border-navy/15 bg-white"
    >
      <li
        v-for="share in props.shares"
        :key="share.id"
        class="grid gap-2 px-3 py-2 md:grid-cols-[minmax(0,1fr)_auto]"
        :data-test="`planner-share-link-${share.id}`"
      >
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <p class="truncate text-sm font-semibold text-navy">
              {{ share.title }}
            </p>
            <span
              v-if="share.revoked_at"
              class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-burgundy"
            >
              Återkallad
            </span>
            <span
              v-else-if="copiedShareId === share.id"
              class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-success"
            >
              Kopierad
            </span>
          </div>
          <p class="truncate text-xs text-navy/60">
            {{ share.public_url ?? "Länken saknar kopierbar adress." }}
          </p>
          <p class="text-[11px] text-navy/50">
            Skapad {{ formatCreatedAt(share.created_at) }}
          </p>
        </div>
        <div class="flex items-center gap-2 md:justify-end">
          <button
            type="button"
            class="btn-ghost planner-btn-ghost"
            :disabled="!share.public_url"
            :data-test="`planner-share-copy-${share.id}`"
            @click="emit('copy-share', share)"
          >
            Kopiera
          </button>
          <button
            type="button"
            class="btn-ghost planner-btn-ghost"
            :disabled="Boolean(share.revoked_at) || revokingShareId === share.id"
            :data-test="`planner-share-revoke-${share.id}`"
            @click="emit('revoke-share', share)"
          >
            {{ revokingShareId === share.id ? "Återkallar…" : "Återkalla" }}
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>
