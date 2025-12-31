import type { Extension } from "@codemirror/state";
import { EditorState, Prec, StateEffect, StateField } from "@codemirror/state";
import {
  Decoration,
  EditorView,
  ViewPlugin,
  type DecorationSet,
  type ViewUpdate,
  WidgetType,
  keymap,
} from "@codemirror/view";

import { apiFetch } from "../../api/client";
import type { SkriptoteketIntelligenceConfig } from "./skriptoteketIntelligence";

type GhostTextConfig = {
  enabled: boolean;
  autoTrigger: boolean;
  debounceMs: number;
};

type GhostTextState = {
  text: string | null;
  from: number | null;
  decorations: DecorationSet;
};

const DEFAULT_CONFIG: GhostTextConfig = {
  enabled: true,
  autoTrigger: true,
  debounceMs: 1500,
};

const setGhostTextEffect = StateEffect.define<{ text: string; from: number } | null>();
const manualTriggerEffect = StateEffect.define<null>();

class GhostTextWidget extends WidgetType {
  public constructor(private readonly text: string) {
    super();
  }

  public override eq(other: GhostTextWidget): boolean {
    return this.text === other.text;
  }

  public override toDOM(): HTMLElement {
    const element = document.createElement("span");
    element.className = "cm-skriptoteket-ghost-text";
    element.textContent = this.text;
    return element;
  }

  public override ignoreEvent(): boolean {
    return true;
  }
}

function buildDecorations({ text, from }: { text: string; from: number }): DecorationSet {
  const widget = Decoration.widget({
    widget: new GhostTextWidget(text),
    side: 1,
  });
  return Decoration.set([widget.range(from)]);
}

const ghostTextField = StateField.define<GhostTextState>({
  create(): GhostTextState {
    return { text: null, from: null, decorations: Decoration.none };
  },
  update(value, tr): GhostTextState {
    let next = value;

    if (tr.docChanged) {
      next = { text: null, from: null, decorations: Decoration.none };
    }

    for (const effect of tr.effects) {
      if (!effect.is(setGhostTextEffect)) continue;

      if (effect.value === null) {
        next = { text: null, from: null, decorations: Decoration.none };
      } else {
        next = {
          text: effect.value.text,
          from: effect.value.from,
          decorations: buildDecorations(effect.value),
        };
      }
    }

    return next;
  },
  provide(field) {
    return EditorView.decorations.from(field, (state) => state.decorations);
  },
});

function clearGhostText(view: EditorView): boolean {
  const current = view.state.field(ghostTextField, false);
  if (!current || !current.text) return false;
  view.dispatch({ effects: setGhostTextEffect.of(null) });
  return true;
}

function acceptGhostText(view: EditorView): boolean {
  const current = view.state.field(ghostTextField, false);
  if (!current || !current.text || current.from === null) return false;

  const selection = view.state.selection.main;
  if (!selection.empty || selection.head !== current.from) return false;

  const insertText = current.text;
  view.dispatch({
    changes: { from: current.from, to: current.from, insert: insertText },
    selection: { anchor: current.from + insertText.length },
    effects: setGhostTextEffect.of(null),
  });
  return true;
}

function triggerManualCompletion(view: EditorView): boolean {
  view.dispatch({ effects: manualTriggerEffect.of(null) });
  return true;
}

type CompletionResponse = { completion: string; enabled: boolean };

function getPrefixSuffix(state: EditorState): { prefix: string; suffix: string; from: number } | null {
  const selection = state.selection.main;
  if (!selection.empty) return null;
  const from = selection.head;

  const prefixMax = 8000;
  const suffixMax = 4000;

  const prefixFrom = Math.max(0, from - prefixMax);
  const prefix = state.doc.sliceString(prefixFrom, from);
  const suffixTo = Math.min(state.doc.length, from + suffixMax);
  const suffix = state.doc.sliceString(from, suffixTo);
  return { prefix, suffix, from };
}

class GhostTextController {
  private timer: number | null = null;
  private abortController: AbortController | null = null;
  private requestSeq = 0;
  private disabledByServer = false;

  public constructor(
    private readonly view: EditorView,
    private readonly config: GhostTextConfig,
  ) {}

  public update(update: ViewUpdate): void {
    const manualTriggered = update.transactions.some((tr) =>
      tr.effects.some((effect) => effect.is(manualTriggerEffect)),
    );

    if (update.docChanged) {
      clearGhostText(update.view);
      this.cancelPendingRequest();

      const isUserTyping = update.transactions.some(
        (tr) => tr.isUserEvent("input") || tr.isUserEvent("delete"),
      );
      if (isUserTyping) {
        this.scheduleAutoTrigger();
      }
      return;
    }

    if (update.selectionSet) {
      clearGhostText(update.view);
      this.cancelPendingRequest();
    }

    if (manualTriggered) {
      clearGhostText(update.view);
      this.cancelPendingRequest();
      void this.requestCompletion(update.view.state);
    }
  }

  public destroy(): void {
    this.cancelTimer();
    this.cancelPendingRequest();
  }

  private scheduleAutoTrigger(): void {
    if (!this.config.enabled || !this.config.autoTrigger) return;
    if (this.disabledByServer) return;

    this.cancelTimer();
    this.timer = window.setTimeout(() => {
      this.timer = null;
      void this.requestCompletion(this.view.state);
    }, this.config.debounceMs);
  }

  private cancelTimer(): void {
    if (this.timer === null) return;
    window.clearTimeout(this.timer);
    this.timer = null;
  }

  private cancelPendingRequest(): void {
    this.abortController?.abort();
    this.abortController = null;
  }

  private async requestCompletion(state: EditorState): Promise<void> {
    if (!this.config.enabled) return;
    if (this.disabledByServer) return;
    if (!this.view.hasFocus) return;

    const slice = getPrefixSuffix(state);
    if (!slice) return;

    const expectedDoc = state.doc;
    const expectedFrom = slice.from;
    const requestId = ++this.requestSeq;

    this.cancelPendingRequest();
    const abortController = new AbortController();
    this.abortController = abortController;

    let response: CompletionResponse;
    try {
      response = await apiFetch<CompletionResponse>("/api/v1/editor/completions", {
        method: "POST",
        body: { prefix: slice.prefix, suffix: slice.suffix },
        signal: abortController.signal,
      });
    } catch {
      if (abortController.signal.aborted) return;
      return;
    } finally {
      if (this.abortController === abortController) {
        this.abortController = null;
      }
    }

    if (requestId !== this.requestSeq) return;
    if (this.view.state.doc !== expectedDoc) return;

    const selection = this.view.state.selection.main;
    if (!selection.empty || selection.head !== expectedFrom) return;

    if (!response.enabled) {
      this.disabledByServer = true;
      clearGhostText(this.view);
      return;
    }

    if (!response.completion) {
      clearGhostText(this.view);
      return;
    }

    this.view.dispatch({
      effects: setGhostTextEffect.of({ text: response.completion, from: expectedFrom }),
    });
  }
}

export function skriptoteketGhostText(config: SkriptoteketIntelligenceConfig): Extension {
  const ghostConfig = { ...DEFAULT_CONFIG, ...(config.ghostText ?? {}) };

  if (!ghostConfig.enabled) return [];

  return [
    ghostTextField,
    EditorView.baseTheme({
      ".cm-skriptoteket-ghost-text": {
        color: "var(--color-navy, #0b1b3a)",
        opacity: "0.45",
        fontStyle: "italic",
        whiteSpace: "pre",
        pointerEvents: "none",
      },
    }),
    ViewPlugin.fromClass(
      class extends GhostTextController {
        public constructor(view: EditorView) {
          super(view, ghostConfig);
        }
      },
    ),
    Prec.highest(
      keymap.of([
        { key: "Tab", run: acceptGhostText, preventDefault: true },
        { key: "Escape", run: clearGhostText, preventDefault: true },
        { key: "Alt-\\", run: triggerManualCompletion, preventDefault: true },
      ]),
    ),
  ];
}
