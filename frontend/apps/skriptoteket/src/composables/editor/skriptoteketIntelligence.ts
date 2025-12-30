import type { Extension } from "@codemirror/state";

import { skriptoteketCompletions } from "./skriptoteketCompletions";
import { skriptoteketHover } from "./skriptoteketHover";
import { skriptoteketLintPanel } from "./skriptoteketLintPanel";
import { skriptoteketLinter } from "./skriptoteketLinter";

export type SkriptoteketIntelligenceConfig = {
  entrypointName: string;
};

export function skriptoteketIntelligence(config: SkriptoteketIntelligenceConfig): Extension {
  return [
    skriptoteketCompletions(config),
    skriptoteketHover(config),
    skriptoteketLinter(config),
    skriptoteketLintPanel(),
  ];
}
