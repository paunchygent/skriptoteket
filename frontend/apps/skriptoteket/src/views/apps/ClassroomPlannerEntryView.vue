<script setup lang="ts">
/**
 * Klassrumskartan entry shell.
 *
 * This wrapper lets the authenticated and public curated-app host routes share
 * one app-specific shell contract while keeping authenticated upgrade
 * orchestration separate from the public browser-owned guest overview lane.
 */

import { computed, unref } from "vue";

import { useClassroomPlannerGuestUpgrade } from "./useClassroomPlannerGuestUpgrade";
import { hasClassroomPlannerGuestUpgradeReceiptEffects } from "./classroomPlannerGuestUpgradeOutcome";
import ClassroomPlannerGuestOverviewView from "./ClassroomPlannerGuestOverviewView.vue";
import ClassroomPlannerGuestUpgradePrompt from "./ClassroomPlannerGuestUpgradePrompt.vue";
import ClassroomPlannerView from "./ClassroomPlannerView.vue";

const props = withDefaults(
  defineProps<{
    hostMode?: "authenticated" | "public";
  }>(),
  {
    hostMode: "authenticated",
  },
);

const authenticatedGuestUpgrade = useClassroomPlannerGuestUpgrade({
  enabled: props.hostMode === "authenticated",
});
const authenticatedGuestUpgradeErrorMessage = authenticatedGuestUpgrade.errorMessage;
const authenticatedGuestUpgradePreviewReceipt = authenticatedGuestUpgrade.previewReceipt;
const authenticatedGuestUpgradeLastReceipt = authenticatedGuestUpgrade.lastReceipt;
const authenticatedGuestUpgradeSummary = authenticatedGuestUpgrade.summary;
const authenticatedGuestUpgradeIsBlocking = authenticatedGuestUpgrade.isBlocking;
const authenticatedGuestUpgradeShouldShowPrompt = authenticatedGuestUpgrade.shouldShowPrompt;
const authenticatedPlannerRefreshKey = authenticatedGuestUpgrade.plannerRefreshKey;
const authenticatedGuestUpgradeCompletedReceipt = computed(() => {
  const receipt = unref(authenticatedGuestUpgradeLastReceipt);
  return hasClassroomPlannerGuestUpgradeReceiptEffects(receipt) ? receipt : null;
});
</script>

<template>
  <section
    v-if="props.hostMode === 'authenticated'"
    class="flex flex-col gap-6"
  >
    <section
      v-if="authenticatedGuestUpgradeCompletedReceipt"
      data-test="guest-upgrade-result-summary"
      class="mx-auto w-full max-w-4xl border border-success/30 bg-canvas p-6 shadow-brutal-md"
    >
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-2">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-success">
            Inloggad import klar
          </p>
          <div class="space-y-1">
            <h2 class="font-serif text-2xl text-navy">
              Gästarbetsytan importerades till ditt konto
            </h2>
            <p class="text-sm leading-6 text-navy/80">
              Snapshot <span class="font-mono text-xs">{{ authenticatedGuestUpgradeCompletedReceipt.snapshot_id }}</span>
              är nu överförd. Sammanfattningen nedan visar vad som skapades eller återanvändes.
            </p>
          </div>
        </div>
        <button
          type="button"
          class="btn-ghost"
          data-test="guest-upgrade-result-dismiss"
          @click="authenticatedGuestUpgrade.dismissLastReceiptSummary"
        >
          Stäng sammanfattning
        </button>
      </div>

      <div class="mt-4 grid gap-4 md:grid-cols-4">
        <article class="border border-success/30 bg-white p-4 shadow-brutal-sm">
          <h3 class="font-serif text-lg text-navy">
            Skapades
          </h3>
          <p class="mt-2 text-2xl text-navy">
            {{ authenticatedGuestUpgradeCompletedReceipt.created.length }}
          </p>
        </article>
        <article class="border border-navy/20 bg-white p-4 shadow-brutal-sm">
          <h3 class="font-serif text-lg text-navy">
            Återanvändes
          </h3>
          <p class="mt-2 text-2xl text-navy">
            {{ authenticatedGuestUpgradeCompletedReceipt.reused.length }}
          </p>
        </article>
        <article class="border border-burgundy/20 bg-white p-4 shadow-brutal-sm">
          <h3 class="font-serif text-lg text-navy">
            Hoppades över
          </h3>
          <p class="mt-2 text-2xl text-navy">
            {{ authenticatedGuestUpgradeCompletedReceipt.skipped.length }}
          </p>
        </article>
        <article class="border border-error/20 bg-white p-4 shadow-brutal-sm">
          <h3 class="font-serif text-lg text-navy">
            Konflikter
          </h3>
          <p class="mt-2 text-2xl text-navy">
            {{ authenticatedGuestUpgradeCompletedReceipt.conflicted.length }}
          </p>
        </article>
      </div>
    </section>

    <ClassroomPlannerView :key="authenticatedPlannerRefreshKey" />

    <div
      v-if="authenticatedGuestUpgradeIsBlocking"
      class="fixed inset-0 z-50 flex items-center justify-center bg-navy/30 p-4 backdrop-blur-[1px]"
      data-test="guest-upgrade-blocking-modal"
    >
      <div class="w-full max-w-[28rem] border border-navy bg-white px-6 py-5 text-sm text-navy/80 shadow-brutal-md">
        Kontrollerar om det finns tidigare arbete i den här webbläsaren...
      </div>
    </div>

    <ClassroomPlannerGuestUpgradePrompt
      v-else-if="authenticatedGuestUpgradeShouldShowPrompt"
      :error-message="authenticatedGuestUpgradeErrorMessage"
      :preview-receipt="authenticatedGuestUpgradePreviewReceipt"
      :summary="authenticatedGuestUpgradeSummary"
      @discard="authenticatedGuestUpgrade.discardGuestWorkspace"
      @import="authenticatedGuestUpgrade.importGuestWorkspace"
      @postpone="authenticatedGuestUpgrade.postponeGuestWorkspace"
    />
  </section>

  <section
    v-else
    class="flex flex-col"
  >
    <ClassroomPlannerGuestOverviewView />
  </section>
</template>
