import { beforeEach, describe, expect, it, vi } from "vitest";
import { EditorState } from "@codemirror/state";
import { EditorView } from "@codemirror/view";
import { python } from "@codemirror/lang-python";
import { forceLinting, forEachDiagnostic, type Diagnostic } from "@codemirror/lint";

import { skriptoteketLinter } from "./skriptoteketLinter";

async function flushMicrotasks(): Promise<void> {
  await new Promise<void>((resolve) => queueMicrotask(() => resolve()));
}

async function collectDiagnostics(view: EditorView): Promise<Diagnostic[]> {
  forceLinting(view);
  await flushMicrotasks();
  await flushMicrotasks();

  const diagnostics: Diagnostic[] = [];
  forEachDiagnostic(view.state, (diagnostic) => {
    diagnostics.push(diagnostic);
  });
  return diagnostics;
}

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
    return await collectDiagnostics(view);
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
        (diagnostic) =>
          diagnostic.source === "ST_CONTRACT_OUTPUT_KIND_INVALID" && diagnostic.message.includes("Ogiltigt kind"),
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

  it("supports quick fix: add ToolUserError import", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);

    const view = new EditorView({
      state: EditorState.create({
        doc: `
def run_tool(input_dir, output_dir):
    raise ToolUserError("nope")
`,
        extensions: [python(), skriptoteketLinter({ entrypointName: "run_tool" })],
      }),
      parent,
    });

    try {
      const diagnostics = await collectDiagnostics(view);
      const diagnostic = diagnostics.find((entry) => entry.source === "ST_BESTPRACTICE_TOOLUSERERROR_IMPORT");
      expect(diagnostic?.actions?.some((action) => action.name === "Lägg till import")).toBe(true);

      const action = diagnostic?.actions?.find((entry) => entry.name === "Lägg till import");
      expect(action).toBeTruthy();

      action?.apply(view, diagnostic?.from ?? 0, diagnostic?.to ?? 0);
      const afterFirst = view.state.doc.toString();
      expect(afterFirst).toContain("from tool_errors import ToolUserError");

      action?.apply(view, diagnostic?.from ?? 0, diagnostic?.to ?? 0);
      expect(view.state.doc.toString()).toBe(afterFirst);

      const afterDiagnostics = await collectDiagnostics(view);
      expect(afterDiagnostics.some((entry) => entry.source === "ST_BESTPRACTICE_TOOLUSERERROR_IMPORT")).toBe(false);
    } finally {
      view.destroy();
      parent.remove();
    }
  });

  it("inserts ToolUserError import after docstring and __future__ imports", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);

    const view = new EditorView({
      state: EditorState.create({
        doc: `#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Docstring."""
from __future__ import annotations

import os

def run_tool(input_dir, output_dir):
    raise ToolUserError("nope")
`,
        extensions: [python(), skriptoteketLinter({ entrypointName: "run_tool" })],
      }),
      parent,
    });

    try {
      const diagnostics = await collectDiagnostics(view);
      const diagnostic = diagnostics.find((entry) => entry.source === "ST_BESTPRACTICE_TOOLUSERERROR_IMPORT");
      const action = diagnostic?.actions?.find((entry) => entry.name === "Lägg till import");
      expect(action).toBeTruthy();

      action?.apply(view, diagnostic?.from ?? 0, diagnostic?.to ?? 0);
      const afterFirst = view.state.doc.toString();

      const importIndex = afterFirst.indexOf("from tool_errors import ToolUserError");
      expect(importIndex).toBeGreaterThan(-1);

      expect(afterFirst.indexOf('r"""Docstring."""')).toBeLessThan(importIndex);
      expect(afterFirst.indexOf("from __future__ import annotations")).toBeLessThan(importIndex);
    } finally {
      view.destroy();
      parent.remove();
    }
  });

  it("supports quick fix: add encoding", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);

    const view = new EditorView({
      state: EditorState.create({
        doc: `
from pathlib import Path

def run_tool(input_dir, output_dir):
    Path("x.txt").read_text()
    return {"outputs": [], "next_actions": [], "state": {}}
`,
        extensions: [python(), skriptoteketLinter({ entrypointName: "run_tool" })],
      }),
      parent,
    });

    try {
      const diagnostics = await collectDiagnostics(view);
      const diagnostic = diagnostics.find((entry) => entry.source === "ST_BESTPRACTICE_ENCODING");
      expect(diagnostic?.actions?.some((action) => action.name === "Lägg till encoding")).toBe(true);

      const action = diagnostic?.actions?.find((entry) => entry.name === "Lägg till encoding");
      expect(action).toBeTruthy();

      action?.apply(view, diagnostic?.from ?? 0, diagnostic?.to ?? 0);
      const afterFirst = view.state.doc.toString();
      expect(afterFirst).toContain('read_text(encoding="utf-8")');

      action?.apply(view, diagnostic?.from ?? 0, diagnostic?.to ?? 0);
      expect(view.state.doc.toString()).toBe(afterFirst);

      const afterDiagnostics = await collectDiagnostics(view);
      expect(afterDiagnostics.some((entry) => entry.source === "ST_BESTPRACTICE_ENCODING")).toBe(false);
    } finally {
      view.destroy();
      parent.remove();
    }
  });

  it("supports quick fix: create entrypoint stub", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);

    const view = new EditorView({
      state: EditorState.create({
        doc: `
def other(input_dir, output_dir):
    return {}
`,
        extensions: [python(), skriptoteketLinter({ entrypointName: "run_tool" })],
      }),
      parent,
    });

    try {
      const diagnostics = await collectDiagnostics(view);
      const diagnostic = diagnostics.find((entry) => entry.source === "ST_ENTRYPOINT_MISSING");
      expect(diagnostic?.actions?.some((action) => action.name === "Skapa startfunktion")).toBe(true);

      const action = diagnostic?.actions?.find((entry) => entry.name === "Skapa startfunktion");
      expect(action).toBeTruthy();

      action?.apply(view, diagnostic?.from ?? 0, diagnostic?.to ?? 0);
      const afterFirst = view.state.doc.toString();
      expect(afterFirst).toContain("def run_tool(input_dir, output_dir):");
      expect(afterFirst).toContain('"next_actions": []');

      action?.apply(view, diagnostic?.from ?? 0, diagnostic?.to ?? 0);
      expect(view.state.doc.toString()).toBe(afterFirst);

      const afterDiagnostics = await collectDiagnostics(view);
      expect(afterDiagnostics.some((entry) => entry.source === "ST_ENTRYPOINT_MISSING")).toBe(false);
    } finally {
      view.destroy();
      parent.remove();
    }
  });

  it("supports quick fix: add missing contract keys", async () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);

    const view = new EditorView({
      state: EditorState.create({
        doc: `
def run_tool(input_dir, output_dir):
    return {"outputs": []}
`,
        extensions: [python(), skriptoteketLinter({ entrypointName: "run_tool" })],
      }),
      parent,
    });

    try {
      const diagnostics = await collectDiagnostics(view);
      const diagnostic = diagnostics.find((entry) => entry.source === "ST_CONTRACT_KEYS_MISSING");
      expect(diagnostic?.actions?.some((action) => action.name === "Lägg till nycklar")).toBe(true);

      const action = diagnostic?.actions?.find((entry) => entry.name === "Lägg till nycklar");
      expect(action).toBeTruthy();

      action?.apply(view, diagnostic?.from ?? 0, diagnostic?.to ?? 0);
      const afterFirst = view.state.doc.toString();
      expect(afterFirst).toContain('"next_actions": []');
      expect(afterFirst).toContain('"state": {}');

      action?.apply(view, diagnostic?.from ?? 0, diagnostic?.to ?? 0);
      expect(view.state.doc.toString()).toBe(afterFirst);

      const afterDiagnostics = await collectDiagnostics(view);
      expect(afterDiagnostics.some((entry) => entry.source === "ST_CONTRACT_KEYS_MISSING")).toBe(false);
    } finally {
      view.destroy();
      parent.remove();
    }
  });

  it("hides diagnostic source row in lint tooltip for error/warning only", () => {
    const parent = document.createElement("div");
    document.body.appendChild(parent);

    const view = new EditorView({
      state: EditorState.create({
        doc: "print('x')\n",
        extensions: [python(), skriptoteketLinter({ entrypointName: "run_tool" })],
      }),
      parent,
    });

    function createTooltipSource(severity: "error" | "warning" | "info" | "hint") {
      const tooltip = document.createElement("div");
      tooltip.className = "cm-tooltip cm-tooltip-lint";

      const diagnostic = document.createElement("div");
      diagnostic.className = `cm-diagnostic cm-diagnostic-${severity}`;

      const source = document.createElement("div");
      source.className = "cm-diagnosticSource";
      source.textContent = `ST_TEST_${severity.toUpperCase()}`;

      diagnostic.appendChild(source);
      tooltip.appendChild(diagnostic);
      view.dom.appendChild(tooltip);

      return { tooltip, source };
    }

    try {
      const error = createTooltipSource("error");
      expect(getComputedStyle(error.source).display).toBe("none");
      error.tooltip.remove();

      const warning = createTooltipSource("warning");
      expect(getComputedStyle(warning.source).display).toBe("none");
      warning.tooltip.remove();

      const info = createTooltipSource("info");
      expect(getComputedStyle(info.source).display).not.toBe("none");
      info.tooltip.remove();

      const hint = createTooltipSource("hint");
      expect(getComputedStyle(hint.source).display).not.toBe("none");
      hint.tooltip.remove();
    } finally {
      view.destroy();
      parent.remove();
    }
  });
});
