import { CompletionContext, type CompletionSource } from "@codemirror/autocomplete";
import { python } from "@codemirror/lang-python";
import { EditorState } from "@codemirror/state";
import { describe, expect, it } from "vitest";

import { skriptoteketCompletions } from "./skriptoteketCompletions";
import { SKRIPTOTEKET_HELPER_DOCS } from "./skriptoteketMetadata";

async function collectCompletionLabels(doc: string): Promise<Set<string>> {
  const state = EditorState.create({
    doc,
    extensions: [python(), skriptoteketCompletions({ entrypointName: "run_tool" })],
  });
  const pos = state.doc.length;

  const sources = state.languageDataAt<CompletionSource>("autocomplete", pos);
  const context = new CompletionContext(state, pos, true);

  const labels = new Set<string>();
  for (const source of sources) {
    const result = await source(context);
    if (!result) continue;
    for (const option of result.options) labels.add(option.label);
  }

  return labels;
}

describe("skriptoteketCompletions (helper imports)", () => {
  it("suggests skriptoteket_toolkit in module completions", async () => {
    const labels = await collectCompletionLabels("from skr");
    expect(labels.has("skriptoteket_toolkit")).toBe(true);
  });

  it("suggests toolkit exports after from-import", async () => {
    const labels = await collectCompletionLabels("from skriptoteket_toolkit import ");
    expect(labels.has("read_inputs")).toBe(true);
    expect(labels.has("read_settings")).toBe(true);
  });

  it("includes Swedish docs for toolkit exports", () => {
    const doc = SKRIPTOTEKET_HELPER_DOCS.find(
      (entry) => entry.moduleId === "skriptoteket_toolkit" && entry.exportId === "read_inputs",
    );
    expect(doc?.swedishDoc).toContain("SKRIPTOTEKET_INPUTS");
  });
});
