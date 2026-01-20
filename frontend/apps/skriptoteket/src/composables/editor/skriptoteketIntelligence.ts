import type { Extension } from "@codemirror/state";

import { skriptoteketCompletions } from "./skriptoteketCompletions";
import { skriptoteketGhostText } from "./skriptoteketGhostText";
import { skriptoteketHover } from "./skriptoteketHover";
import { skriptoteketLintPanel } from "./skriptoteketLintPanel";
import { skriptoteketLinter } from "./skriptoteketLinter";

export type SkriptoteketIntelligenceConfig = {
  entrypointName: string;
  ghostText?: {
    enabled: boolean;
    autoTrigger: boolean;
    debounceMs: number;
    onNotice?: (params: { message: string; variant: "info" | "warning"; code?: string | null }) => void;
  };
};

export function skriptoteketIntelligence(config: SkriptoteketIntelligenceConfig): Extension {
  return [
    skriptoteketCompletions(config),
    skriptoteketHover(config),
    skriptoteketLinter(config),
    skriptoteketLintPanel(),
    skriptoteketGhostText(config),
  ];
}
