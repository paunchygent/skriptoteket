import type { Extension } from "@codemirror/state";
import { hoverTooltip } from "@codemirror/view";

import type { SkriptoteketIntelligenceConfig } from "./skriptoteketIntelligence";
import { SKRIPTOTEKET_HELPER_DOCS } from "./skriptoteketMetadata";
import { isInNonCodeContext, resolvePythonIdentifierNode } from "./skriptoteketPythonTree";

export function skriptoteketHover(_config: SkriptoteketIntelligenceConfig): Extension {
  const docsByExportId = new Map<string, { signature: string; swedishDoc: string }>(
    SKRIPTOTEKET_HELPER_DOCS.map((doc) => [
      doc.exportId,
      { signature: doc.signature, swedishDoc: doc.swedishDoc },
    ]),
  );

  return hoverTooltip((view, pos, side) => {
    if (isInNonCodeContext(view.state, pos)) return null;

    const identifier = resolvePythonIdentifierNode(view.state, pos, side);
    if (!identifier) return null;

    const doc = docsByExportId.get(identifier.name);
    if (!doc) return null;

    return {
      pos: identifier.from,
      end: identifier.to,
      above: true,
      create: () => {
        const dom = document.createElement("div");

        const title = document.createElement("div");
        title.textContent = doc.signature;
        title.style.fontFamily = "var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace)";
        title.style.fontSize = "12px";
        title.style.fontWeight = "600";

        const body = document.createElement("div");
        body.textContent = doc.swedishDoc;
        body.style.marginTop = "6px";
        body.style.fontSize = "12px";
        body.style.maxWidth = "420px";

        dom.appendChild(title);
        dom.appendChild(body);

        return { dom };
      },
    };
  });
}
