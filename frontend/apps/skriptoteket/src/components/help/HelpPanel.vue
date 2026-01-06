<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute } from "vue-router";

import { useAuthStore } from "../../stores/auth";
import { resolveHelpTopic, useHelp, type HelpTopicId } from "./useHelp";

type IndexItem = {
  topic: HelpTopicId;
  title: string;
  description?: string;
};

const auth = useAuthStore();
const route = useRoute();
const { isOpen, activeTopic, close, showIndex, showTopic } = useHelp();

const isAuthenticated = computed(() => auth.isAuthenticated);
const canSeeContributor = computed(() => auth.hasAtLeastRole("contributor"));
const canSeeAdmin = computed(() => auth.hasAtLeastRole("admin"));

const starterIndexItems: IndexItem[] = [
  {
    topic: "home",
    title: "Start",
    description: "Se vad du har tillgång till.",
  },
  {
    topic: "browse_professions",
    title: "Katalog",
    description: "Hitta verktyg via yrke → kategori.",
  },
  {
    topic: "tools_run",
    title: "Kör ett verktyg",
    description: "Ladda upp fil och klicka Kör.",
  },
];

const contributorIndexItems: IndexItem[] = [
  {
    topic: "my_tools",
    title: "Mina verktyg",
    description: "Öppna verktyg du underhåller.",
  },
  {
    topic: "suggestions_new",
    title: "Föreslå skript",
    description: "Skicka in idéer och behov.",
  },
];

const adminIndexItems: IndexItem[] = [
  {
    topic: "admin_suggestions",
    title: "Förslag",
    description: "Granska och fatta beslut.",
  },
  {
    topic: "admin_tools",
    title: "Testyta",
    description: "Publicera/avpublicera och testa.",
  },
  {
    topic: "admin_editor",
    title: "Skripteditorn",
    description: "Redigera skript och versioner.",
  },
];

const loggedOutIndexItems: IndexItem[] = [
  {
    topic: "login",
    title: "Logga in",
  },
];

const routeTopic = computed(() => resolveHelpTopic(route.name));

function syncToRoute(): void {
  if (routeTopic.value) {
    showTopic(routeTopic.value);
  } else {
    showIndex();
  }
}

watch(
  () => isOpen.value,
  (open) => {
    if (open) {
      syncToRoute();
    }
  },
);

watch(
  () => route.fullPath,
  () => {
    if (isOpen.value) {
      syncToRoute();
    }
  },
);
</script>

<template>
  <Teleport to="body">
    <Transition name="help-backdrop">
      <div
        v-if="isOpen"
        class="help-backdrop fixed inset-0 bg-navy/40"
        @click="close"
      />
    </Transition>

    <Transition name="help-panel">
      <aside
        v-if="isOpen"
        id="help-panel"
        class="help-panel border border-navy bg-canvas shadow-brutal flex flex-col text-navy"
        role="dialog"
        aria-modal="false"
        aria-labelledby="help-panel-title"
      >
        <header class="flex items-center justify-between gap-3 p-4 border-b border-navy/20">
          <h2
            id="help-panel-title"
            class="text-lg font-semibold text-navy"
          >
            Hjälp
          </h2>
          <button
            type="button"
            class="w-10 h-10 border border-navy text-navy text-xl leading-none flex items-center justify-center hover:bg-navy hover:text-canvas transition-colors"
            aria-label="Stäng"
            @click="close"
          >
            &times;
          </button>
        </header>

        <div class="flex-1 overflow-y-auto p-6 space-y-6">
          <template v-if="!activeTopic">
            <div class="space-y-3">
              <h3 class="text-lg font-semibold text-navy">Hjälpindex</h3>
              <p
                v-if="!isAuthenticated"
                class="text-sm text-navy/60"
              >
                Välj ett ämne för att komma igång.
              </p>
            </div>

            <div
              v-if="isAuthenticated"
              class="space-y-6"
            >
              <section class="space-y-3">
                <h4 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                  Kom igång
                </h4>
                <ul class="border border-navy/20 bg-white shadow-brutal-sm divide-y divide-navy/20">
                  <li
                    v-for="item in starterIndexItems"
                    :key="item.topic"
                  >
                    <button
                      type="button"
                      class="w-full text-left flex items-start justify-between gap-4 px-4 py-3 hover:bg-canvas transition-colors"
                      @click="showTopic(item.topic)"
                    >
                      <span class="flex flex-col gap-1">
                        <span class="text-sm font-semibold text-navy">{{ item.title }}</span>
                        <span class="text-xs text-navy/60">{{ item.description }}</span>
                      </span>
                      <span class="text-navy/40">→</span>
                    </button>
                  </li>
                </ul>
              </section>

              <section
                v-if="canSeeContributor"
                class="space-y-3"
              >
                <h4 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                  Bidra
                </h4>
                <ul class="border border-navy/20 bg-white shadow-brutal-sm divide-y divide-navy/20">
                  <li
                    v-for="item in contributorIndexItems"
                    :key="item.topic"
                  >
                    <button
                      type="button"
                      class="w-full text-left flex items-start justify-between gap-4 px-4 py-3 hover:bg-canvas transition-colors"
                      @click="showTopic(item.topic)"
                    >
                      <span class="flex flex-col gap-1">
                        <span class="text-sm font-semibold text-navy">{{ item.title }}</span>
                        <span class="text-xs text-navy/60">{{ item.description }}</span>
                      </span>
                      <span class="text-navy/40">→</span>
                    </button>
                  </li>
                </ul>
              </section>

              <section
                v-if="canSeeAdmin"
                class="space-y-3"
              >
                <h4 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                  Admin
                </h4>
                <ul class="border border-navy/20 bg-white shadow-brutal-sm divide-y divide-navy/20">
                  <li
                    v-for="item in adminIndexItems"
                    :key="item.topic"
                  >
                    <button
                      type="button"
                      class="w-full text-left flex items-start justify-between gap-4 px-4 py-3 hover:bg-canvas transition-colors"
                      @click="showTopic(item.topic)"
                    >
                      <span class="flex flex-col gap-1">
                        <span class="text-sm font-semibold text-navy">{{ item.title }}</span>
                        <span class="text-xs text-navy/60">{{ item.description }}</span>
                      </span>
                      <span class="text-navy/40">→</span>
                    </button>
                  </li>
                </ul>
              </section>
            </div>

            <section
              v-else
              class="space-y-3"
            >
              <ul class="border border-navy/20 bg-white shadow-brutal-sm divide-y divide-navy/20">
                <li
                  v-for="item in loggedOutIndexItems"
                  :key="item.topic"
                >
                  <button
                    type="button"
                    class="w-full text-left flex items-center justify-between gap-4 px-4 py-3 hover:bg-canvas transition-colors"
                    @click="showTopic(item.topic)"
                  >
                    <span class="text-sm font-semibold text-navy">{{ item.title }}</span>
                    <span class="text-navy/40">→</span>
                  </button>
                </li>
              </ul>
            </section>
          </template>

          <template v-else>
            <section
              v-if="activeTopic === 'login'"
              class="space-y-3"
            >
              <button
                type="button"
                class="text-sm text-navy/70 underline hover:text-burgundy"
                @click="showIndex"
              >
                ← Till hjälpindex
              </button>
              <h3 class="text-lg font-semibold text-navy">Logga in</h3>
              <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
                <li>Logga in för att komma till startsidan.</li>
                <li>Använd din skol-/arbets-e-post.</li>
                <li>Om det inte går: kontrollera stavning och Caps Lock.</li>
                <li>Glömt lösenord? Kontakta en admin (ingen återställning i systemet än).</li>
              </ul>
              <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
            </section>

            <section
              v-if="activeTopic === 'home'"
              class="space-y-3"
            >
              <button
                type="button"
                class="text-sm text-navy/70 underline hover:text-burgundy"
                @click="showIndex"
              >
                ← Till hjälpindex
              </button>
              <h3 class="text-lg font-semibold text-navy">Start</h3>
              <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
                <li>
                  <strong>Katalog</strong>: hitta verktyg via yrke → kategori → verktyg,
                  och kör dem när du behöver.
                </li>
                <li>
                  <strong>Kör ett verktyg</strong>: ladda upp fil när verktyget ber om det
                  och klicka Kör. Om verktyget behöver fler saker, visas de under resultatet.
                </li>
                <li v-if="canSeeContributor">
                  <strong>Mina verktyg</strong>: se och öppna verktyg du underhåller.
                </li>
                <li v-if="canSeeContributor">
                  <strong>Föreslå skript</strong>: skicka in idéer och behov (välj yrke/kategori).
                </li>
                <li v-if="canSeeAdmin">
                  <strong>Förslag</strong>: granska inkomna förslag och fatta beslut.
                </li>
                <li v-if="canSeeAdmin">
                  <strong>Testyta</strong>: publicera/avpublicera och testa verktyg.
                </li>
                <li v-if="canSeeAdmin">
                  <strong>Skripteditorn</strong>: redigera skript och spara versioner.
                </li>
              </ul>
              <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
            </section>

            <section
              v-if="activeTopic === 'browse_professions'"
              class="space-y-3"
            >
              <button
                type="button"
                class="text-sm text-navy/70 underline hover:text-burgundy"
                @click="showIndex"
              >
                ← Till hjälpindex
              </button>
              <h3 class="text-lg font-semibold text-navy">Katalog: välj yrke</h3>
              <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
                <li>Välj det yrke som passar bäst för att se relevanta kategorier.</li>
              </ul>
              <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
            </section>

            <section
              v-if="activeTopic === 'browse_categories'"
              class="space-y-3"
            >
              <button
                type="button"
                class="text-sm text-navy/70 underline hover:text-burgundy"
                @click="showIndex"
              >
                ← Till hjälpindex
              </button>
              <h3 class="text-lg font-semibold text-navy">Katalog: välj kategori</h3>
              <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
                <li>Välj en kategori för att se appar och verktyg.</li>
              </ul>
              <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
            </section>

            <section
              v-if="activeTopic === 'browse_tools'"
              class="space-y-3"
            >
              <button
                type="button"
                class="text-sm text-navy/70 underline hover:text-burgundy"
                @click="showIndex"
              >
                ← Till hjälpindex
              </button>
              <h3 class="text-lg font-semibold text-navy">Katalog: verktyg och appar</h3>
              <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
                <li>
                  Klicka <strong>Öppna</strong> för en app eller <strong>Kör</strong> för ett
                  verktyg.
                </li>
                <li>Om inget finns ännu: prova en annan kategori.</li>
              </ul>
              <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
            </section>

            <section
              v-if="activeTopic === 'tools_run'"
              class="space-y-3"
            >
              <button
                type="button"
                class="text-sm text-navy/70 underline hover:text-burgundy"
                @click="showIndex"
              >
                ← Till hjälpindex
              </button>
              <h3 class="text-lg font-semibold text-navy">Kör ett verktyg</h3>
              <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
                <li>Ladda upp en fil och klicka <strong>Kör</strong>.</li>
                <li>Resultatet visas under formuläret när körningen är klar.</li>
              </ul>
              <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
            </section>

            <section
              v-if="activeTopic === 'tools_result'"
              class="space-y-3"
            >
              <button
                type="button"
                class="text-sm text-navy/70 underline hover:text-burgundy"
                @click="showIndex"
              >
                ← Till hjälpindex
              </button>
              <h3 class="text-lg font-semibold text-navy">Resultat</h3>
              <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
                <li>Här ser du utdata och eventuella filer från körningen.</li>
                <li>Om du får fel: prova igen eller kontrollera att filen är rätt.</li>
              </ul>
              <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
            </section>

            <section
              v-if="activeTopic === 'my_tools'"
              class="space-y-3"
            >
              <button
                type="button"
                class="text-sm text-navy/70 underline hover:text-burgundy"
                @click="showIndex"
              >
                ← Till hjälpindex
              </button>
              <h3 class="text-lg font-semibold text-navy">Mina verktyg</h3>
              <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
                <li>Här ser du verktyg du underhåller.</li>
                <li>Klicka <strong>Redigera</strong> för att öppna skripteditorn.</li>
              </ul>
              <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
            </section>

            <section
              v-if="activeTopic === 'apps_detail'"
              class="space-y-3"
            >
              <button
                type="button"
                class="text-sm text-navy/70 underline hover:text-burgundy"
                @click="showIndex"
              >
                ← Till hjälpindex
              </button>
              <h3 class="text-lg font-semibold text-navy">App</h3>
              <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
                <li>Klicka <strong>Starta</strong> för att köra appen.</li>
                <li>Resultat och nästa steg visas under.</li>
              </ul>
              <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
            </section>

            <section
              v-if="activeTopic === 'suggestions_new'"
              class="space-y-3"
            >
              <button
                type="button"
                class="text-sm text-navy/70 underline hover:text-burgundy"
                @click="showIndex"
              >
                ← Till hjälpindex
              </button>
              <h3 class="text-lg font-semibold text-navy">Föreslå skript</h3>
              <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
                <li>Skriv en tydlig titel och en kort beskrivning av vad skriptet ska göra.</li>
                <li>Välj relevanta yrken och kategorier så att andra hittar det.</li>
                <li>Klicka <strong>Skicka förslag</strong> när du är klar.</li>
              </ul>
              <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
            </section>

            <section
              v-if="activeTopic === 'admin_suggestions'"
              class="space-y-3"
            >
              <button
                type="button"
                class="text-sm text-navy/70 underline hover:text-burgundy"
                @click="showIndex"
              >
                ← Till hjälpindex
              </button>
              <h3 class="text-lg font-semibold text-navy">Förslag (admin)</h3>
              <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
                <li>
                  Öppna ett förslag och läs igenom titel, beskrivning, yrken och kategorier.
                </li>
                <li>Fatta beslut och skriv en kort motivering.</li>
              </ul>
              <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
            </section>

            <section
              v-if="activeTopic === 'admin_tools'"
              class="space-y-3"
            >
              <button
                type="button"
                class="text-sm text-navy/70 underline hover:text-burgundy"
                @click="showIndex"
              >
                ← Till hjälpindex
              </button>
              <h3 class="text-lg font-semibold text-navy">Testyta (admin)</h3>
              <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
                <li>
                  Här hanterar du verktyg: publicera, avpublicera och öppna för redigering.
                </li>
                <li>Verktyg måste ha en aktiv version för att kunna publiceras.</li>
              </ul>
              <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
            </section>

            <section
              v-if="activeTopic === 'admin_editor'"
              class="space-y-3"
            >
              <button
                type="button"
                class="text-sm text-navy/70 underline hover:text-burgundy"
                @click="showIndex"
              >
                ← Till hjälpindex
              </button>
              <h3 class="text-lg font-semibold text-navy">Skripteditorn</h3>
              <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
                <li>Spara som utkast, testkör och granska resultatet.</li>
                <li>När du är nöjd: skicka för granskning och publicera.</li>
                <li>
                  <strong>Krav för begäran</strong>: URL-namnet får inte börja med
                  <span class="font-mono">draft-</span> och minst ett yrke + en kategori
                  måste vara valda.
                </li>
                <li>
                  Ändra URL-namn och taxonomi under <strong>Metadata</strong>-panelen.
                </li>
              </ul>
              <p class="text-sm text-navy/60">Mer hjälp kommer snart.</p>
            </section>
          </template>
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.help-backdrop {
  z-index: var(--huleedu-z-overlay);
}

.help-panel {
  position: fixed;
  top: calc(var(--huleedu-space-4) + var(--huleedu-header-height));
  right: var(--huleedu-space-4);
  bottom: var(--huleedu-space-4);
  width: min(420px, calc(100vw - var(--huleedu-space-8)));
  z-index: var(--huleedu-z-modal);
}

@media (max-width: 767px) {
  .help-panel {
    top: calc(
      var(--huleedu-header-height) + var(--huleedu-space-4) + env(safe-area-inset-top, 0px)
    );
    right: calc(var(--huleedu-space-4) + env(safe-area-inset-right, 0px));
    bottom: calc(var(--huleedu-space-4) + env(safe-area-inset-bottom, 0px));
    left: calc(var(--huleedu-space-4) + env(safe-area-inset-left, 0px));
    width: auto;
  }
}

.help-backdrop-enter-active,
.help-backdrop-leave-active {
  transition: opacity var(--huleedu-duration-slow) var(--huleedu-ease-default);
}
.help-backdrop-enter-from,
.help-backdrop-leave-to {
  opacity: 0;
}

.help-panel-enter-active,
.help-panel-leave-active {
  transition: transform var(--huleedu-duration-slow) var(--huleedu-ease-default),
    opacity var(--huleedu-duration-slow) var(--huleedu-ease-default);
}
.help-panel-enter-from,
.help-panel-leave-to {
  transform: translateY(8px);
  opacity: 0;
}
</style>
