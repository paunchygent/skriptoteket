<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import { useLoginModal } from "../composables/useLoginModal";
import { useAuthStore } from "../stores/auth";

type ListMyRunsResponse = components["schemas"]["ListMyRunsResponse"];
type ListMyToolsResponse = components["schemas"]["ListMyToolsResponse"];
type ListAdminToolsResponse = components["schemas"]["ListAdminToolsResponse"];

const auth = useAuthStore();
const loginModal = useLoginModal();

const isAuthenticated = computed(() => auth.isAuthenticated);
const canSeeContributor = computed(() => auth.hasAtLeastRole("contributor"));
const canSeeAdmin = computed(() => auth.hasAtLeastRole("admin"));
const userName = computed(() => {
  if (!auth.user) return null;
  return auth.user.email.split("@")[0];
});

// Dashboard data
const runsCount = ref(0);
const runsLoading = ref(false);

const toolsTotal = ref(0);
const toolsPublished = ref(0);
const toolsLoading = ref(false);

const adminToolsTotal = ref(0);
const adminToolsPublished = ref(0);
const adminPendingReview = ref(0);
const adminLoading = ref(false);

const dashboardError = ref<string | null>(null);

async function loadUserDashboard(): Promise<void> {
  runsLoading.value = true;
  try {
    const response = await apiGet<ListMyRunsResponse>("/api/v1/my-runs");
    runsCount.value = response.runs.length;
  } catch (error: unknown) {
    if (isApiError(error)) {
      dashboardError.value = error.message;
    }
  } finally {
    runsLoading.value = false;
  }
}

async function loadContributorDashboard(): Promise<void> {
  toolsLoading.value = true;
  try {
    const response = await apiGet<ListMyToolsResponse>("/api/v1/my-tools");
    toolsTotal.value = response.tools.length;
    toolsPublished.value = response.tools.filter((t) => t.is_published).length;
  } catch (error: unknown) {
    if (isApiError(error)) {
      dashboardError.value = error.message;
    }
  } finally {
    toolsLoading.value = false;
  }
}

async function loadAdminDashboard(): Promise<void> {
  adminLoading.value = true;
  try {
    const response = await apiGet<ListAdminToolsResponse>("/api/v1/admin/tools");
    adminToolsTotal.value = response.tools.length;
    adminToolsPublished.value = response.tools.filter((t) => t.is_published).length;
    adminPendingReview.value = response.tools.filter((t) => t.has_pending_review).length;
  } catch (error: unknown) {
    if (isApiError(error)) {
      dashboardError.value = error.message;
    }
  } finally {
    adminLoading.value = false;
  }
}

onMounted(async () => {
  if (!isAuthenticated.value) return;

  // Load dashboard data based on role
  await loadUserDashboard();

  if (canSeeContributor.value) {
    await loadContributorDashboard();
  }

  if (canSeeAdmin.value) {
    await loadAdminDashboard();
  }
});
</script>

<template>
  <div>
    <!-- ═══════════════════════════════════════════════════════════════════════
         PRE-LOGIN: Hero + Features
         ═══════════════════════════════════════════════════════════════════════ -->
    <template v-if="!isAuthenticated">
      <!-- Hero Section -->
      <section class="py-16 text-center">
        <h1
          class="font-serif text-4xl md:text-5xl font-bold text-navy tracking-tighter leading-tight"
        >
          Verktyg för lärare
        </h1>
        <p class="mt-4 text-lg text-navy/70 max-w-xl mx-auto">
          Ladda upp en fil, välj ett verktyg, ladda ned resultatet.
        </p>
        <p class="mt-10">
          <button
            type="button"
            class="px-8 py-4 bg-navy text-canvas border border-navy shadow-brutal font-semibold uppercase tracking-wide hover:bg-burgundy transition-colors"
            @click="loginModal.open()"
          >
            Logga in
          </button>
        </p>
      </section>

      <!-- Features Section -->
      <section class="py-16 border-t border-navy/10">
        <div class="grid gap-12 md:grid-cols-3 max-w-5xl mx-auto">
          <!-- Card 1 -->
          <div class="relative">
            <div
              class="absolute -top-3 -left-2 w-8 h-8 bg-burgundy border border-navy flex items-center justify-center"
            >
              <span class="text-canvas font-bold text-sm">1</span>
            </div>
            <div class="pt-6 pl-5 border-l-2 border-navy min-h-[120px]">
              <h3 class="font-semibold text-navy text-lg">Dela och återanvänd</h3>
              <p class="mt-2 text-sm text-navy/70 leading-relaxed">
                Slipp skriva samma skript om och om igen. Hitta färdiga verktyg
                eller bidra med egna idéer.
              </p>
            </div>
          </div>

          <!-- Card 2 -->
          <div class="relative">
            <div
              class="absolute -top-3 -left-2 w-8 h-8 bg-burgundy border border-navy flex items-center justify-center"
            >
              <span class="text-canvas font-bold text-sm">2</span>
            </div>
            <div class="pt-6 pl-5 border-l-2 border-navy min-h-[120px]">
              <h3 class="font-semibold text-navy text-lg">Enkel uppladdning</h3>
              <p class="mt-2 text-sm text-navy/70 leading-relaxed">
                Ladda upp en fil, kör, ladda ner resultatet. Ingen IDE, ingen
                terminal, ingen installation.
              </p>
            </div>
          </div>

          <!-- Card 3 -->
          <div class="relative">
            <div
              class="absolute -top-3 -left-2 w-8 h-8 bg-burgundy border border-navy flex items-center justify-center"
            >
              <span class="text-canvas font-bold text-sm">3</span>
            </div>
            <div class="pt-6 pl-5 border-l-2 border-navy min-h-[120px]">
              <h3 class="font-semibold text-navy text-lg">Tryggt och lokalt</h3>
              <p class="mt-2 text-sm text-navy/70 leading-relaxed">
                Alla filer behandlas säkert på vår server. Verktyg granskas
                innan publicering.
              </p>
            </div>
          </div>
        </div>
      </section>
    </template>

    <!-- ═══════════════════════════════════════════════════════════════════════
         POST-LOGIN: Role-guarded Dashboard
         ═══════════════════════════════════════════════════════════════════════ -->
    <template v-else>
      <div class="max-w-4xl space-y-10">
        <!-- Error message -->
        <div
          v-if="dashboardError"
          class="p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
        >
          {{ dashboardError }}
        </div>

        <!-- Greeting -->
        <section>
          <h1 class="text-3xl font-semibold text-navy">
            Välkommen<template v-if="userName">, {{ userName }}</template>
          </h1>
          <p class="mt-2 text-navy/60">Vad vill du göra?</p>
        </section>

        <!-- ═══════════════════════════════════════════════════════════════════
             USER SECTION: All authenticated users
             ═══════════════════════════════════════════════════════════════════ -->
        <section class="space-y-4">
          <div class="grid gap-5 sm:grid-cols-2">
            <!-- Senaste körningar -->
            <RouterLink
              to="/my-runs"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Senaste körningar</span>
                <span class="card-arrow">&rarr;</span>
              </div>
              <div class="card-stats">
                <span
                  v-if="runsLoading"
                  class="text-navy/40"
                >...</span>
                <span
                  v-else
                  class="stat-number"
                >{{ runsCount }}</span>
                <span class="stat-label">körningar totalt</span>
              </div>
              <p class="card-description">
                Se resultat från tidigare körningar.
              </p>
            </RouterLink>

            <!-- Hitta verktyg -->
            <RouterLink
              to="/browse"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Hitta verktyg</span>
                <span class="card-arrow">&rarr;</span>
              </div>
              <p class="card-description mt-4">
                Bläddra i katalogen och kör det du behöver.
              </p>
            </RouterLink>
          </div>
        </section>

        <!-- ═══════════════════════════════════════════════════════════════════
             CONTRIBUTOR SECTION: contributor+ only
             ═══════════════════════════════════════════════════════════════════ -->
        <section
          v-if="canSeeContributor"
          class="space-y-4"
        >
          <h2 class="section-label">Bidragsgivare</h2>
          <div class="grid gap-5 sm:grid-cols-2">
            <!-- Mina verktyg -->
            <RouterLink
              to="/my-tools"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Mina verktyg</span>
                <span class="card-arrow">&rarr;</span>
              </div>
              <div class="card-stats">
                <span
                  v-if="toolsLoading"
                  class="text-navy/40"
                >...</span>
                <template v-else>
                  <span class="stat-number">{{ toolsTotal }}</span>
                  <span class="stat-label">
                    verktyg
                    <span
                      v-if="toolsPublished > 0"
                      class="text-success"
                    >
                      ({{ toolsPublished }} publicerade)
                    </span>
                  </span>
                </template>
              </div>
              <p class="card-description">
                Hantera verktyg du ansvarar för.
              </p>
            </RouterLink>

            <!-- Föreslå verktyg -->
            <RouterLink
              to="/suggestions/new"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Föreslå verktyg</span>
                <span class="card-arrow">&rarr;</span>
              </div>
              <p class="card-description mt-4">
                Har du en idé? Skicka in ett förslag.
              </p>
            </RouterLink>
          </div>
        </section>

        <!-- ═══════════════════════════════════════════════════════════════════
             ADMIN SECTION: admin+ only
             ═══════════════════════════════════════════════════════════════════ -->
        <section
          v-if="canSeeAdmin"
          class="space-y-4"
        >
          <h2 class="section-label">Administration</h2>
          <div class="grid gap-5 sm:grid-cols-2">
            <!-- Att granska -->
            <RouterLink
              to="/admin/tools"
              class="dashboard-card group"
              :class="{ 'border-warning': adminPendingReview > 0 }"
            >
              <div class="card-header">
                <span class="card-label">Att granska</span>
                <span class="card-arrow">&rarr;</span>
              </div>
              <div class="card-stats">
                <span
                  v-if="adminLoading"
                  class="text-navy/40"
                >...</span>
                <template v-else>
                  <span
                    class="stat-number"
                    :class="{ 'text-warning': adminPendingReview > 0 }"
                  >
                    {{ adminPendingReview }}
                  </span>
                  <span class="stat-label">väntar på granskning</span>
                </template>
              </div>
              <p class="card-description">
                Granska och publicera verktyg.
              </p>
            </RouterLink>

            <!-- Alla verktyg -->
            <RouterLink
              to="/admin/tools"
              class="dashboard-card group"
            >
              <div class="card-header">
                <span class="card-label">Alla verktyg</span>
                <span class="card-arrow">&rarr;</span>
              </div>
              <div class="card-stats">
                <span
                  v-if="adminLoading"
                  class="text-navy/40"
                >...</span>
                <template v-else>
                  <span class="stat-number">{{ adminToolsTotal }}</span>
                  <span class="stat-label">
                    totalt
                    <span
                      v-if="adminToolsPublished > 0"
                      class="text-success"
                    >
                      ({{ adminToolsPublished }} publicerade)
                    </span>
                  </span>
                </template>
              </div>
              <p class="card-description">
                Administrera verktyg i systemet.
              </p>
            </RouterLink>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* Section label */
.section-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-navy);
  opacity: 0.5;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-navy);
  opacity: 0.2;
}

/* Dashboard card */
.dashboard-card {
  display: block;
  padding: 1.25rem;
  border: 1px solid var(--color-navy);
  background-color: white;
  box-shadow: 4px 4px 0 0 var(--color-navy);
  text-decoration: none;
  transition: all 0.15s ease;
}

.dashboard-card:hover {
  box-shadow: 6px 6px 0 0 var(--color-navy);
  transform: translate(-2px, -2px);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.card-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-navy);
  transition: color 0.15s ease;
}

.dashboard-card:hover .card-label {
  color: var(--color-burgundy);
}

.card-arrow {
  font-size: 1.125rem;
  color: var(--color-burgundy);
}

.card-stats {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.stat-number {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-navy);
  line-height: 1;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--color-navy);
  opacity: 0.6;
}

.card-description {
  margin-top: 0.5rem;
  font-size: 0.8125rem;
  color: var(--color-navy);
  opacity: 0.6;
  line-height: 1.4;
}

/* Success color for published counts */
.text-success {
  color: var(--huleedu-success);
}

/* Warning color for pending review */
.text-warning {
  color: var(--huleedu-warning);
}

.border-warning {
  border-color: var(--huleedu-warning);
}
</style>
