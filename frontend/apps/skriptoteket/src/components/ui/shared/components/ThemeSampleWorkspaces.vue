<script setup lang="ts">
/**
 * Purpose:
 *     Show the shared workspace surfaces on the theme sample page: the room
 *     canvas, a code editor and a pinball board.
 *
 * Relationships:
 *     - Composed by ThemeSamplePage.vue as the "Arbetsytor" section, between
 *       the controls and the share sections.
 *     - Draws every colour, spacing, type and radius value from the shared
 *       --huleedu-* tokens, including the grid, editor and syntax roles, so a
 *       theme choice restyles the section through the tokens.
 *     - Renders the pinball board through ThemeSamplePinball.vue, which owns
 *       the playfield drawing and its playfield-token styles.
 *     - Static sample markup: no props, no state and no data flow.
 */

import ThemeSamplePinball from "./ThemeSamplePinball.vue";

type EditorTokenKind = "keyword" | "string" | "number" | "function" | "comment";

type EditorToken = {
  text: string;
  kind?: EditorTokenKind;
  selected?: boolean;
};

type EditorLine = {
  tokens: readonly EditorToken[];
  active?: boolean;
};

const EDITOR_LINE_NUMBERS: readonly number[] = [1, 2, 3, 4, 5, 6, 7, 8];

const EDITOR_LINES: readonly EditorLine[] = [
  {
    tokens: [{ text: "# Rita en rumslig yta", kind: "comment" }],
  },
  {
    tokens: [
      { text: "from ", kind: "keyword" },
      { text: "huleedu" },
      { text: " import ", kind: "keyword" },
      { text: "panel" },
    ],
  },
  {
    tokens: [{ text: " " }],
  },
  {
    tokens: [
      { text: "def ", kind: "keyword" },
      { text: "rita_rum", kind: "function" },
      { text: "(bredd: " },
      { text: "int", kind: "keyword" },
      { text: " = " },
      { text: "24", kind: "number" },
      { text: ") -> " },
      { text: "str", kind: "keyword" },
      { text: ":" },
    ],
  },
  {
    tokens: [{ text: '    """Rita rutnätet på duken."""', kind: "string" }],
  },
  {
    tokens: [
      { text: "    yta = " },
      { text: "panel", kind: "function" },
      { text: "(" },
      { text: 'ton="rum"', kind: "string", selected: true },
      { text: ", kant=" },
      { text: "True", kind: "keyword" },
      { text: ")" },
    ],
    active: true,
  },
  {
    tokens: [
      { text: "    " },
      { text: "return", kind: "keyword" },
      { text: " yta." },
      { text: "rita", kind: "function" },
      { text: "(bredd)" },
    ],
  },
  {
    tokens: [{ text: "# Klar", kind: "comment" }],
  },
];

function tokenClass(token: EditorToken): string[] {
  const classes = ["editor-token"];
  if (token.kind !== undefined) {
    classes.push(`editor-token-${token.kind}`);
  }
  if (token.selected === true) {
    classes.push("editor-token-selected");
  }
  return classes;
}
</script>

<template>
  <section
    class="workspaces"
    aria-labelledby="theme-sample-workspaces-heading"
  >
    <h2
      id="theme-sample-workspaces-heading"
      class="workspaces-heading"
    >
      Arbetsytor
    </h2>

    <article class="workspace">
      <header class="workspace-header">
        <h3 class="workspace-heading">Rum</h3>
        <p class="workspace-note">Duken med rutnät och en panel som släpper igenom den.</p>
      </header>

      <div class="room">
        <div class="room-panel">
          <h4 class="room-panel-heading">Ritning</h4>
          <p class="room-panel-text">En genomskinlig panel ovanpå dukens rutnät.</p>
        </div>
      </div>
    </article>

    <article class="workspace">
      <header class="workspace-header">
        <h3 class="workspace-heading">Kodredigerare</h3>
        <p class="workspace-note">Åtta rader Python med aktiv rad, markering och markör.</p>
      </header>

      <div
        class="editor"
        role="img"
        aria-label="Förenklad kodredigerare med åtta rader Python, en aktiv rad och en markerad text."
      >
        <div class="editor-inner">
          <div
            class="editor-gutter"
            aria-hidden="true"
          >
            <span
              v-for="number in EDITOR_LINE_NUMBERS"
              :key="number"
              class="editor-line-number"
              >{{ number }}</span
            >
          </div>
          <div
            class="editor-code"
            aria-hidden="true"
          >
            <div
              v-for="(line, lineIndex) in EDITOR_LINES"
              :key="lineIndex"
              class="editor-line"
              :class="{ 'editor-line-active': line.active }"
            >
              <span
                v-for="(token, tokenIndex) in line.tokens"
                :key="tokenIndex"
                :class="tokenClass(token)"
                >{{ token.text }}</span
              >
              <span
                v-if="line.active"
                class="editor-cursor"
              ></span>
            </div>
          </div>
        </div>
      </div>
    </article>

    <article class="workspace">
      <header class="workspace-header">
        <h3 class="workspace-heading">Flipperspel</h3>
        <p class="workspace-note">Plan, kuddar och flipprar i spelplanens färger.</p>
      </header>

      <ThemeSamplePinball />
    </article>
  </section>
</template>

<style scoped>
.workspaces {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--huleedu-space-6);
}

.workspaces-heading {
  margin: 0;
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-sans);
  font-size: var(--huleedu-type-section-title-size);
  font-weight: var(--huleedu-type-section-title-weight);
  line-height: var(--huleedu-type-title-leading);
}

.workspace {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--huleedu-space-3);
}

.workspace-header {
  display: grid;
  gap: var(--huleedu-space-1);
}

.workspace-heading {
  margin: 0;
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-sans);
  font-size: var(--huleedu-type-nested-title-size);
  font-weight: var(--huleedu-type-nested-title-weight);
  line-height: var(--huleedu-type-title-leading);
}

.workspace-note {
  margin: 0;
  color: var(--huleedu-navy-70);
  font-family: var(--huleedu-font-sans);
  font-size: var(--huleedu-type-supporting-size);
  font-weight: var(--huleedu-type-supporting-weight);
  line-height: var(--huleedu-type-body-leading);
}

.room {
  position: relative;
  overflow: hidden;
  padding: var(--huleedu-space-5);
  border: var(--huleedu-border-width) solid var(--huleedu-panel-border);
  border-radius: var(--huleedu-radius-lg);
  background-color: var(--huleedu-canvas);
}

/* The grid is its own layer so --huleedu-grid-line-opacity tints the lines
   without tinting the canvas or the panel above it. */
.room::before {
  position: absolute;
  inset: 0;
  content: "";
  background-image:
    linear-gradient(
      to right,
      var(--huleedu-navy) var(--huleedu-border-width),
      transparent var(--huleedu-border-width)
    ),
    linear-gradient(
      to bottom,
      var(--huleedu-navy) var(--huleedu-border-width),
      transparent var(--huleedu-border-width)
    );
  background-size: var(--huleedu-grid-size) var(--huleedu-grid-size);
  opacity: var(--huleedu-grid-line-opacity);
  pointer-events: none;
}

.room-panel {
  position: relative;
  max-width: var(--huleedu-max-width-sm);
  padding: var(--huleedu-space-4);
  border: var(--huleedu-border-width) solid var(--huleedu-panel-border);
  border-radius: var(--huleedu-radius-lg);
  background-color: var(--huleedu-panel);
}

.room-panel-heading {
  margin: 0;
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-sans);
  font-size: var(--huleedu-type-field-label-size);
  font-weight: var(--huleedu-type-field-label-weight);
  line-height: var(--huleedu-type-title-leading);
}

.room-panel-text {
  margin: var(--huleedu-space-1) 0 0;
  color: var(--huleedu-navy-70);
  font-family: var(--huleedu-font-sans);
  font-size: var(--huleedu-type-supporting-size);
  font-weight: var(--huleedu-type-supporting-weight);
  line-height: var(--huleedu-type-body-leading);
}

.editor {
  overflow-x: auto;
  border: var(--huleedu-border-width) solid var(--huleedu-panel-border);
  border-radius: var(--huleedu-radius-lg);
  background-color: var(--huleedu-editor-bg);
  scrollbar-color: var(--huleedu-scrollbar-thumb) transparent;
}

.editor-inner {
  display: flex;
  width: max-content;
  min-width: 100%;
}

.editor,
.editor-inner {
  font-family: var(--huleedu-font-mono);
  font-size: var(--huleedu-text-sm);
  line-height: var(--huleedu-leading-normal);
}

.editor-gutter {
  flex: none;
  padding: var(--huleedu-space-2) var(--huleedu-space-3);
  background-color: var(--huleedu-editor-gutter-bg);
  color: var(--huleedu-editor-gutter-text);
  user-select: none;
}

.editor-line-number {
  display: block;
  text-align: right;
}

.editor-code {
  flex: 1 0 auto;
  padding: var(--huleedu-space-2) var(--huleedu-space-3);
  color: var(--huleedu-navy);
}

.editor-line {
  white-space: pre;
}

.editor-line-active {
  background-color: var(--huleedu-editor-active-line);
}

.editor-token-selected {
  background-color: var(--huleedu-editor-selection);
}

.editor-token-keyword {
  color: var(--huleedu-syntax-keyword);
}

.editor-token-string {
  color: var(--huleedu-syntax-string);
}

.editor-token-number {
  color: var(--huleedu-syntax-number);
}

.editor-token-function {
  color: var(--huleedu-syntax-function);
}

.editor-token-comment {
  color: var(--huleedu-syntax-comment);
}

.editor-cursor {
  display: inline-block;
  width: var(--huleedu-border-width-2);
  height: var(--huleedu-text-base);
  vertical-align: text-bottom;
  background-color: var(--huleedu-editor-cursor);
}
</style>
