<script setup lang="ts">
/**
 * Link management section for Klassrumskartan share/export surfaces.
 *
 * Relationships:
 * - rendered by `PlannerShareExportPanel` in modal and inline overview modes
 * - owns active-link filtering, copy/revoke rows, and stable link-state
 *   transitions while the parent owns share/export intent routing
 */

import { computed } from "vue";

import { IconCopy, IconLink2, IconTrash } from "../../../components/icons";
import { UiDenseActionButton, UiDenseSpinner } from "../../../components/ui";
import type { ClassroomPlannerShareArtifact } from "../classroomPlannerShareApi";

const props = withDefaults(
  defineProps<{
    shares?: ClassroomPlannerShareArtifact[];
    revokingShareId?: string | null;
    shareLoading?: boolean;
    shareBusy?: boolean;
    shareStatusLabel?: string | null;
    shareErrorMessage?: string | null;
    showRevokeAction?: boolean;
    visualVariant?: "default" | "desktop-overview";
    createShareTestId: string;
    createShareMobileTestId: string;
  }>(),
  {
    shares: () => [],
    revokingShareId: null,
    shareLoading: false,
    shareBusy: false,
    shareStatusLabel: null,
    shareErrorMessage: null,
    showRevokeAction: true,
    visualVariant: "default",
  },
);

const emit = defineEmits<{
  (e: "create-share"): void;
  (e: "copy-share", share: ClassroomPlannerShareArtifact): void;
  (e: "revoke-share", share: ClassroomPlannerShareArtifact): void;
}>();

const dateFormatter = new Intl.DateTimeFormat("sv-SE", {
  day: "numeric",
  month: "short",
  year: "numeric",
});
const activeShares = computed(() => props.shares.filter((share) => !share.revoked_at));
const activeShareCount = computed(() => activeShares.value.length);
const isCreateActionBusy = computed(() => {
  return props.shareBusy && !props.shareLoading && props.revokingShareId === null;
});

function formatDate(value: string): string {
  return dateFormatter.format(new Date(value));
}

function formatActiveMeta(share: ClassroomPlannerShareArtifact): string {
  return `Skapad ${formatDate(share.created_at)}`;
}
</script>

<template>
  <section
    class="border-b border-navy/15"
    aria-labelledby="planner-share-export-link-heading"
  >
    <div
      v-if="visualVariant === 'desktop-overview'"
      class="planner-share-export-link-actions px-3.5 py-3 md:px-4"
    >
      <h3
        id="planner-share-export-link-heading"
        class="mb-2 text-[11px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)] text-navy/65"
      >
        Länk
      </h3>
      <button
        type="button"
        class="planner-share-export-link-create-button grid w-full grid-cols-[auto_minmax(0,1fr)] items-center gap-2 rounded-[4px] border border-action/60 bg-canvas/40 px-2.5 text-left text-action transition-colors hover:border-action hover:bg-action/5 disabled:cursor-not-allowed disabled:opacity-55"
        :disabled="isCreateActionBusy"
        :data-test="createShareTestId"
        :aria-busy="isCreateActionBusy ? 'true' : undefined"
        :aria-label="isCreateActionBusy ? 'Skapar länk' : undefined"
        @click="emit('create-share')"
      >
        <UiDenseSpinner
          v-if="isCreateActionBusy"
          :size="12"
        />
        <IconLink2
          v-else
          :size="13"
        />
        <span class="truncate text-[11px] font-semibold leading-none">
          Skapa länk
        </span>
      </button>
    </div>
    <div
      v-else
      class="planner-share-export-link-actions grid gap-3 px-3.5 py-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-start md:px-4"
    >
      <div>
        <h3
          id="planner-share-export-link-heading"
          class="text-[11px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)] text-navy/65"
        >
          Länk
        </h3>
      </div>
      <div class="hidden md:block">
        <UiDenseActionButton
          label="Skapa länk"
          :disabled="isCreateActionBusy"
          :busy="isCreateActionBusy"
          busy-label="Skapar länk"
          tone="secondary"
          class="min-w-[8.5rem]"
          :data-test="createShareTestId"
          @click="emit('create-share')"
        >
          <template #leading>
            <IconLink2 :size="10" />
          </template>
        </UiDenseActionButton>
      </div>
    </div>

    <div class="border-t border-navy/10 px-3.5 py-2 md:hidden">
      <button
        type="button"
        class="inline-flex h-10 w-full items-center justify-center gap-2 rounded-[4px] border border-action/60 bg-canvas/40 px-3 text-[11px] font-semibold uppercase leading-none tracking-[var(--huleedu-tracking-label)] text-action transition-colors hover:border-action hover:bg-action/5 disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="isCreateActionBusy"
        :data-test="createShareMobileTestId"
        :aria-busy="isCreateActionBusy ? 'true' : undefined"
        :aria-label="isCreateActionBusy ? 'Skapar länk' : undefined"
        @click="emit('create-share')"
      >
        <UiDenseSpinner
          v-if="isCreateActionBusy"
          :size="12"
        />
        <IconLink2
          v-else
          :size="12"
        />
        Skapa länk
      </button>
    </div>

    <div
      class="planner-share-export-link-state border-t border-navy/10"
      data-test="planner-share-export-link-state"
    >
      <div
        class="planner-share-export-link-state-content"
        data-test="planner-share-export-link-state-content"
      >
        <p
          v-if="shareStatusLabel"
          class="border-b border-navy/10 px-3.5 py-2 text-[11px] font-semibold text-navy/65"
          data-test="planner-share-status"
        >
          {{ shareStatusLabel }}
        </p>
        <p
          v-if="shareErrorMessage"
          class="border-b border-critical/20 bg-critical/5 px-3.5 py-2 text-[11px] font-semibold text-critical"
          data-test="planner-share-error"
        >
          {{ shareErrorMessage }}
        </p>

        <p
          v-if="shareLoading && activeShareCount === 0"
          class="px-3.5 py-3 text-sm font-semibold text-navy/65"
        >
          Hämtar länkar...
        </p>
        <p
          v-else-if="activeShareCount === 0"
          class="px-3.5 py-3 text-sm text-navy/65"
          data-test="planner-share-links-empty"
        >
          Inga aktiva delade länkar.
        </p>

        <ul
          v-else
          class="divide-y divide-navy/10"
        >
          <li
            v-for="share in activeShares"
            :key="share.id"
            class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-3.5 py-3"
            :data-test="`planner-share-link-${share.id}`"
          >
            <div class="min-w-0">
              <p class="truncate text-sm font-semibold leading-tight text-navy">
                {{ share.title }}
              </p>
              <p class="mt-0.5 truncate font-mono text-[10px] text-navy/50">
                {{ formatActiveMeta(share) }}
              </p>
            </div>
            <div class="flex min-w-max items-center justify-end gap-1.5">
              <button
                type="button"
                class="inline-flex h-8 w-8 items-center justify-center rounded-[4px] border border-navy/20 bg-canvas/40 text-navy transition-colors hover:border-action/45 hover:bg-action/5 disabled:cursor-not-allowed disabled:opacity-40 md:h-[26px] md:w-auto md:gap-1 md:px-2 md:text-[10px] md:font-semibold md:uppercase md:tracking-[var(--huleedu-tracking-label)]"
                :disabled="!share.public_url"
                :data-test="`planner-share-copy-${share.id}`"
                title="Kopiera länk till urklipp"
                @click="emit('copy-share', share)"
              >
                <IconCopy
                  :size="12"
                />
                <span class="sr-only md:not-sr-only">Kopiera</span>
              </button>
              <button
                v-if="showRevokeAction"
                type="button"
                class="inline-flex h-8 w-8 items-center justify-center rounded-[4px] border border-critical/30 bg-canvas/40 text-critical transition-colors hover:bg-critical/5 disabled:cursor-not-allowed disabled:opacity-40 md:h-[26px] md:w-auto md:gap-1 md:px-2 md:text-[10px] md:font-semibold md:uppercase md:tracking-[var(--huleedu-tracking-label)]"
                :disabled="revokingShareId === share.id"
                :data-test="`planner-share-revoke-${share.id}`"
                title="Återkalla länken"
                :aria-busy="revokingShareId === share.id ? 'true' : undefined"
                :aria-label="revokingShareId === share.id ? 'Återkallar länken' : undefined"
                @click="emit('revoke-share', share)"
              >
                <UiDenseSpinner
                  v-if="revokingShareId === share.id"
                  :size="12"
                />
                <IconTrash
                  v-else
                  :size="12"
                />
                <span class="sr-only md:not-sr-only">
                  Återkalla
                </span>
              </button>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
