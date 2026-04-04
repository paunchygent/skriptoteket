<script setup lang="ts">
import type { GameHudSnapshot } from "../../../components/apps/flunk-out-frenzy/gameHostTypes";

defineProps<{
  hud: GameHudSnapshot;
  sessionStatusLabel: string;
}>();
</script>

<template>
  <aside class="fof-status-cluster">
    <div class="fof-plaque">
      <span>Status</span>
      <strong>{{ sessionStatusLabel }}</strong>
    </div>
    <div class="fof-plaque">
      <span>Poäng</span>
      <strong>{{ hud.score.toLocaleString("sv-SE") }}</strong>
    </div>
    <div class="fof-plaque">
      <span>Bollar kvar</span>
      <strong>{{ hud.ballsRemaining }}</strong>
    </div>
    <div class="fof-plaque">
      <span>Multiplikator</span>
      <strong>x{{ hud.multiplier }}</strong>
    </div>
    <div class="fof-plaque">
      <span>Bonus</span>
      <strong>{{ hud.bonus.points.toLocaleString("sv-SE") }}</strong>
    </div>
    <div class="fof-plaque">
      <span>Jackpot</span>
      <strong>
        {{ hud.jackpot.points.toLocaleString("sv-SE") }}
        {{ hud.jackpot.lit ? "• Tänd" : "• Släckt" }}
      </strong>
    </div>
    <div class="fof-plaque">
      <span>Shoot again</span>
      <strong>{{ hud.ballLifecycle.shootAgainLit ? "Tänd" : "Släckt" }}</strong>
    </div>
  </aside>
</template>
