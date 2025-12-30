import type { Extension } from "@codemirror/state";

import type { SkriptoteketIntelligenceConfig } from "./skriptoteketIntelligence";
import { skriptoteketLinterAdapter } from "./linter/adapters/codemirror/skriptoteketLinterAdapter";

export function skriptoteketLinter(config: SkriptoteketIntelligenceConfig): Extension {
  return skriptoteketLinterAdapter(config);
}
