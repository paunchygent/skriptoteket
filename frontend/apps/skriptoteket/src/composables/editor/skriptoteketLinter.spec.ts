import { beforeEach, describe, expect, it, vi } from "vitest";
import { EditorState } from "@codemirror/state";
import { EditorView } from "@codemirror/view";
import { python } from "@codemirror/lang-python";
import { forceLinting, forEachDiagnostic, type Diagnostic } from "@codemirror/lint";

import { skriptoteketLinter } from "./skriptoteketLinter";

async function runLinter(doc: string, entrypointName = "run_tool"): Promise<Diagnostic[]> {
  const parent = document.createElement("div");
  document.body.appendChild(parent);

  const view = new EditorView({
    state: EditorState.create({
      doc,
      extensions: [python(), skriptoteketLinter({ entrypointName })],
    }),
    parent,
  });

  try {
    forceLinting(view);
    await new Promise<void>((resolve) => queueMicrotask(() => resolve()));
    await new Promise<void>((resolve) => queueMicrotask(() => resolve()));

    const diagnostics: Diagnostic[] = [];
    forEachDiagnostic(view.state, (diagnostic) => {
      diagnostics.push(diagnostic);
    });
    return diagnostics;
  } finally {
    view.destroy();
    parent.remove();
  }
}

describe("skriptoteketLinter", () => {
  beforeEach(() => {
    vi.useRealTimers();
  });

  it("warns when entrypoint is missing", async () => {
    const diagnostics = await runLinter(
      `
def other(input_dir, output_dir):
    return {}
`,
    );

    const entrypoint = diagnostics.find((diagnostic) => diagnostic.source === "ST_ENTRYPOINT_MISSING");
    expect(entrypoint).toBeTruthy();
    expect(entrypoint?.severity).toBe("warning");
  });

  it("reports contract issues for invalid output kinds", async () => {
    const diagnostics = await runLinter(
      `
def run_tool(input_dir, output_dir):
    return {"outputs": [{"kind": "bad", "level": "info", "message": "x"}]}
`,
    );

    expect(diagnostics.some((diagnostic) => diagnostic.source === "ST_CONTRACT_KEYS_MISSING")).toBe(true);
    expect(
      diagnostics.some(
        (diagnostic) => diagnostic.source === "ST_CONTRACT" && diagnostic.message.includes("Ogiltigt kind"),
      ),
    ).toBe(true);
  });

  it("flags ToolUserError without imports", async () => {
    const diagnostics = await runLinter(
      `
def run_tool(input_dir, output_dir):
    raise ToolUserError("nope")
`,
    );

    const diagnostic = diagnostics.find(
      (entry) => entry.source === "ST_BESTPRACTICE_TOOLUSERERROR_IMPORT",
    );
    expect(diagnostic?.severity).toBe("error");
    expect(diagnostic?.message).toContain("ToolUserError");
  });

  it("blocks sandboxed network libraries", async () => {
    const diagnostics = await runLinter(
      `
import requests

def run_tool(input_dir, output_dir):
    return {"outputs": [], "next_actions": [], "state": {}}
`,
    );

    const diagnostic = diagnostics.find((entry) => entry.source === "ST_SECURITY");
    expect(diagnostic?.severity).toBe("error");
    expect(diagnostic?.message).toContain("sandbox");
  });

  it("short-circuits to syntax diagnostics when syntax errors exist", async () => {
    const diagnostics = await runLinter(
      `
import requests

def run_tool(input_dir, output_dir)
    return {"outputs": []}
`,
    );

    expect(diagnostics.length).toBeGreaterThan(0);
    expect(diagnostics.every((diagnostic) => diagnostic.source === "ST_SYNTAX_ERROR")).toBe(true);
  });
});
