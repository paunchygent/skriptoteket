<script setup lang="ts">
/**
 * Purpose:
 *     Draw the simplified pinball board on the theme sample page.
 *
 * Relationships:
 *     - Used by ThemeSampleWorkspaces.vue under its "Flipperspel" subheading.
 *     - Draws the playfield, bumpers, flippers, ball and lamps from the shared
 *       --huleedu-playfield-* tokens, so a theme choice restyles the board.
 *     - Static sample markup: no props, no state and no data flow.
 */
</script>

<template>
  <div class="pinball">
    <svg
      class="pinball-board"
      viewBox="0 0 320 420"
      role="img"
      aria-label="Förenklad flipperspelsplan med tre kuddar, två flipprar, en kula och tända lampor."
    >
      <rect
        x="0"
        y="0"
        width="320"
        height="420"
        rx="20"
        fill="var(--huleedu-playfield-board)"
      />
      <rect
        x="10"
        y="10"
        width="300"
        height="400"
        rx="14"
        fill="none"
        stroke="var(--huleedu-playfield-rail)"
        stroke-width="6"
      />
      <path
        d="M160 74 L244 158 L160 242 L76 158 Z"
        fill="var(--huleedu-playfield-inlay)"
      />
      <circle
        cx="84"
        cy="272"
        r="13"
        fill="var(--huleedu-playfield-inlay)"
      />
      <circle
        cx="236"
        cy="272"
        r="13"
        fill="var(--huleedu-playfield-inlay)"
      />
      <rect
        x="128"
        y="384"
        width="64"
        height="16"
        rx="8"
        fill="var(--huleedu-playfield-inlay)"
      />
      <circle
        cx="40"
        cy="64"
        r="6"
        fill="var(--huleedu-playfield-light)"
      />
      <circle
        cx="280"
        cy="64"
        r="6"
        fill="var(--huleedu-playfield-light)"
      />
      <circle
        cx="40"
        cy="236"
        r="6"
        fill="var(--huleedu-playfield-light)"
      />
      <circle
        cx="280"
        cy="236"
        r="6"
        fill="var(--huleedu-playfield-light)"
      />
      <circle
        cx="40"
        cy="292"
        r="6"
        fill="var(--huleedu-playfield-light)"
      />
      <circle
        cx="280"
        cy="292"
        r="6"
        fill="var(--huleedu-playfield-light)"
      />
      <circle
        cx="108"
        cy="158"
        r="24"
        fill="var(--huleedu-playfield-bumper)"
      />
      <circle
        cx="108"
        cy="158"
        r="11"
        fill="var(--huleedu-playfield-bumper-cap)"
      />
      <circle
        cx="212"
        cy="158"
        r="24"
        fill="var(--huleedu-playfield-bumper)"
      />
      <circle
        cx="212"
        cy="158"
        r="11"
        fill="var(--huleedu-playfield-bumper-cap)"
      />
      <circle
        cx="160"
        cy="222"
        r="26"
        fill="var(--huleedu-playfield-bumper)"
      />
      <circle
        cx="160"
        cy="222"
        r="12"
        fill="var(--huleedu-playfield-bumper-cap)"
      />
      <rect
        x="66"
        y="330"
        width="82"
        height="16"
        rx="8"
        fill="var(--huleedu-playfield-flipper)"
        transform="rotate(-20 66 338)"
      />
      <rect
        x="172"
        y="330"
        width="82"
        height="16"
        rx="8"
        fill="var(--huleedu-playfield-flipper)"
        transform="rotate(20 254 338)"
      />
      <circle
        cx="200"
        cy="292"
        r="9"
        fill="var(--huleedu-playfield-ball)"
      />
    </svg>
  </div>
</template>

<style scoped>
.pinball {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
}

.pinball-board {
  display: block;
  width: 100%;
  max-width: var(--huleedu-max-width-sm);
  height: auto;
}
</style>
