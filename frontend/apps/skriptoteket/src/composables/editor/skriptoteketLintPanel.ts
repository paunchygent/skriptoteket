import {
  closeLintPanel,
  diagnosticCount,
  lintKeymap,
  nextDiagnostic,
  openLintPanel,
  previousDiagnostic,
} from "@codemirror/lint";
import type { Extension } from "@codemirror/state";
import { keymap } from "@codemirror/view";

export { closeLintPanel, diagnosticCount, openLintPanel };

export function skriptoteketLintPanel(): Extension {
  return keymap.of([
    ...lintKeymap,
    { key: "Shift-F8", run: previousDiagnostic, preventDefault: true },
    { key: "Mod-Alt-n", run: nextDiagnostic, preventDefault: true },
    { key: "Mod-Alt-p", run: previousDiagnostic, preventDefault: true },
  ]);
}
