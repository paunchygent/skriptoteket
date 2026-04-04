<script setup lang="ts">
/**
 * Klassrumskartan entry shell.
 *
 * This wrapper lets the authenticated and public curated-app host routes share
 * one app-specific shell contract while the public browser-workspace behavior
 * is implemented in later EPIC-32 slices.
 */

import { computed } from "vue";
import { RouterLink } from "vue-router";

import { useLoginModal } from "../../composables/useLoginModal";
import { CLASSROOM_PLANNER_APP_ID } from "./classroomPlannerNavigation";
import { useClassroomPlannerGuestSnapshotStatus } from "./useClassroomPlannerGuestSnapshotStatus";
import { useClassroomPlannerGuestUpgrade } from "./useClassroomPlannerGuestUpgrade";
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

const authenticatedRoute = computed(() => `/apps/${encodeURIComponent(CLASSROOM_PLANNER_APP_ID)}`);
const loginModal = useLoginModal();
const guestSnapshot = useClassroomPlannerGuestSnapshotStatus({
  enabled: props.hostMode === "public",
});
const guestSnapshotStatus = guestSnapshot.status;
const guestSnapshotSummary = guestSnapshot.summary;
const guestSnapshotErrorMessage = guestSnapshot.errorMessage;
const guestSnapshotIsWorking = guestSnapshot.isWorking;
const authenticatedGuestUpgrade = useClassroomPlannerGuestUpgrade({
  enabled: props.hostMode === "authenticated",
});
const authenticatedGuestUpgradeErrorMessage = authenticatedGuestUpgrade.errorMessage;
const authenticatedGuestUpgradePreviewReceipt = authenticatedGuestUpgrade.previewReceipt;
const authenticatedGuestUpgradeSummary = authenticatedGuestUpgrade.summary;
const authenticatedGuestUpgradeIsBlocking = authenticatedGuestUpgrade.isBlocking;
const authenticatedGuestUpgradeShouldShowPrompt = authenticatedGuestUpgrade.shouldShowPrompt;

function openLoginModal(): void {
  loginModal.open(authenticatedRoute.value);
}
</script>

<template>
  <section
    v-if="props.hostMode === 'authenticated'"
    class="mx-auto flex max-w-4xl flex-col gap-6"
  >
    <div
      v-if="authenticatedGuestUpgradeIsBlocking"
      class="border border-navy bg-white px-6 py-5 text-sm text-navy/80 shadow-brutal-md"
    >
      Kontrollerar lokal gästarbetsyta för möjlig inloggad import...
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

    <ClassroomPlannerView v-else />
  </section>

  <section
    v-else
    class="mx-auto flex max-w-4xl flex-col gap-6 border border-navy bg-white p-6 shadow-brutal-md md:p-8"
  >
    <div class="space-y-3">
      <p class="text-xs font-semibold uppercase tracking-[0.22em] text-burgundy">
        Publik apphost
      </p>
      <div class="space-y-2">
        <h1 class="font-serif text-3xl text-navy md:text-4xl">
          Klassrumskartan
        </h1>
        <p class="max-w-2xl text-sm leading-6 text-navy/80 md:text-base">
          Den separata publika värdytan är nu på plats. I den här bounded slicen landar den
          godkända browser-ägda snapshot-grunden för lokal gästarbetsyta, medan publik redigering,
          import, export och inloggad uppgradering följer i senare EPIC-32-steg.
        </p>
      </div>
    </div>

    <div class="grid gap-4 md:grid-cols-2">
      <article class="border border-navy/20 bg-canvas p-4 shadow-brutal-sm">
        <h2 class="font-serif text-xl text-navy">
          Det här är klart nu
        </h2>
        <p class="mt-2 text-sm leading-6 text-navy/80">
          Klassrumskartan kan nu ha en dedikerad publik route och publik bootstrap utan att
          försvaga den befintliga autentiserade hosten eller de ägarstyrda API-sömmarna.
        </p>
      </article>

      <article class="border border-navy/20 bg-canvas p-4 shadow-brutal-sm">
        <h2 class="font-serif text-xl text-navy">
          Nästa steg i demo-paketet
        </h2>
        <p class="mt-2 text-sm leading-6 text-navy/80">
          Gästredigering för roster, mallar, smarta regler, checkpoints och senare inloggad import
          är medvetet utanför just den här implementeringsslicen även om den lokala snapshot-sömmen
          nu finns på plats.
        </p>
      </article>
    </div>

    <article class="space-y-4 border border-navy/20 bg-canvas p-4 shadow-brutal-sm">
      <div class="space-y-2">
        <h2 class="font-serif text-xl text-navy">
          Browser-agd gästarbetsyta
        </h2>
        <p class="text-sm leading-6 text-navy/80">
          Den här bounded slicen lägger den versionerade snapshot-sömmen för lokal gästarbetsyta
          i webbläsaren. Servern skapar fortfarande inga gäst-roster, mallar, regler eller utkast
          innan inloggning.
        </p>
      </div>

      <div
        v-if="guestSnapshotStatus === 'loading'"
        class="border border-navy/15 bg-white px-4 py-3 text-sm text-navy/70"
      >
        Kontrollerar lokal gästarbetsyta...
      </div>

      <div
        v-else-if="guestSnapshotStatus === 'error'"
        class="border border-error/30 bg-white px-4 py-3 text-sm text-error"
      >
        {{ guestSnapshotErrorMessage ?? "Det gick inte att läsa den lokala gästarbetsytan." }}
      </div>

      <div
        v-else-if="guestSnapshotStatus === 'missing'"
        class="space-y-3 border border-navy/15 bg-white p-4"
      >
        <p class="text-sm leading-6 text-navy/80">
          Ingen lokal gästarbetsyta finns sparad i den här webbläsaren ännu.
        </p>
        <button
          type="button"
          class="btn-primary"
          :disabled="guestSnapshotIsWorking"
          @click="guestSnapshot.initializeGuestWorkspace"
        >
          Initiera lokal gästarbetsyta
        </button>
      </div>

      <div
        v-else-if="guestSnapshotStatus === 'expired'"
        class="space-y-3 border border-burgundy/25 bg-white p-4"
      >
        <p class="text-sm leading-6 text-navy/80">
          Den tidigare lokala gästarbetsytan har gått ut och behöver startas om innan senare
          demo-steg kan använda den.
        </p>
        <p
          v-if="guestSnapshotSummary"
          class="text-xs uppercase tracking-[0.18em] text-burgundy"
        >
          Senast uppdaterad {{ guestSnapshotSummary.updated_at }}
        </p>
        <button
          type="button"
          class="btn-primary"
          :disabled="guestSnapshotIsWorking"
          @click="guestSnapshot.initializeGuestWorkspace"
        >
          Starta ny lokal gästarbetsyta
        </button>
      </div>

      <div
        v-else-if="guestSnapshotStatus === 'ready' && guestSnapshotSummary"
        class="space-y-4 border border-navy/15 bg-white p-4"
      >
        <p class="text-sm leading-6 text-navy/80">
          Lokal gästarbetsyta är nu etablerad i den här webbläsaren med versionssatt snapshot-id,
          TTL och fingeravtryck för framtida uppgradering efter riktig inloggning.
        </p>

        <dl class="grid gap-3 text-sm text-navy/80 md:grid-cols-2">
          <div>
            <dt class="font-semibold text-navy">
              Snapshot-id
            </dt>
            <dd class="break-all font-mono text-xs">
              {{ guestSnapshotSummary.snapshot_id }}
            </dd>
          </div>
          <div>
            <dt class="font-semibold text-navy">
              Går ut
            </dt>
            <dd>{{ guestSnapshotSummary.expires_at }}</dd>
          </div>
          <div>
            <dt class="font-semibold text-navy">
              Roster / mallar
            </dt>
            <dd>{{ guestSnapshotSummary.roster_count }} / {{ guestSnapshotSummary.template_count }}</dd>
          </div>
          <div>
            <dt class="font-semibold text-navy">
              Regler / checkpoints
            </dt>
            <dd>
              {{ guestSnapshotSummary.smart_rule_set_count }} / {{
                guestSnapshotSummary.checkpoint_count
              }}
            </dd>
          </div>
          <div>
            <dt class="font-semibold text-navy">
              Grupputkast
            </dt>
            <dd>{{ guestSnapshotSummary.has_grouping_draft ? "Ja" : "Nej" }}</dd>
          </div>
          <div>
            <dt class="font-semibold text-navy">
              Sittutkast
            </dt>
            <dd>{{ guestSnapshotSummary.has_seating_draft ? "Ja" : "Nej" }}</dd>
          </div>
        </dl>

        <button
          type="button"
          class="btn-ghost"
          :disabled="guestSnapshotIsWorking"
          @click="guestSnapshot.clearGuestWorkspace"
        >
          Rensa lokal gästarbetsyta
        </button>
      </div>
    </article>

    <div class="flex flex-wrap gap-3">
      <button
        type="button"
        class="btn-primary"
        @click="openLoginModal"
      >
        Logga in till full version
      </button>
      <RouterLink
        to="/register"
        class="btn-ghost"
      >
        Skapa konto
      </RouterLink>
    </div>
  </section>
</template>
