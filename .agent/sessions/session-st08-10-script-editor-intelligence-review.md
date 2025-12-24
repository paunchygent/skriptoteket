# Session: ST-08-10 Script Editor Intelligence — Technical Review

## Session Scope

**Objective**: Review the proposed CodeMirror 6 script editor intelligence feature and validate the technical design before implementation begins.

**Deliverables**:

1. Validate ADR-0035 architecture decisions (Lezer vs regex, extension composition)
2. Review lint rule specifications for completeness and feasibility
3. Identify implementation risks or gaps
4. Confirm phased story breakdown is appropriate
5. Update documentation with any findings

**Out of scope**: Actual implementation of the extensions (that's a future sprint).

---

## Role

You are the **lead frontend developer and architect** of Skriptoteket.

The scope of this session is **reviewing the ST-08-10/11/12 script editor intelligence feature design** — a CodeMirror 6 extension suite that adds autocomplete, linting, and hover docs for tool script authors.

---

## Before Touching Code

### From repo root, read these files to understand conventions:

```
CLAUDE.md                                    # Project overview, commands, patterns
.agent/rules/000-rule-index.md               # Index of all rules
```

### Rules relevant to this session:

This is a frontend feature, but review these for context on the runner contract the linter will validate:

- Review the KB that defines what the linter must check: `docs/reference/ref-ai-script-generation-kb.md`

### Read these files to understand current scope:

**Architecture decision:**

- `docs/adr/adr-0035-script-editor-intelligence-architecture.md` — Core technical decisions

**Stories (phased):**

- `docs/backlog/stories/story-08-10-script-editor-intelligence.md` — Phase 1: Discoverability MVP
- `docs/backlog/stories/story-08-11-script-editor-intelligence-phase2.md` — Phase 2: Contract + security
- `docs/backlog/stories/story-08-12-script-editor-intelligence-phase3.md` — Phase 3: Best practices

**Epic context:**

- `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md` — Parent epic

**Existing editor implementation:**

- `frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue` — Current CM6 setup
- `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue` — Editor view
- `frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts` — Editor state

**Runner contract (what linter validates):**

- `runner/_runner.py` — Runner contract implementation
- `runner/pdf_helper.py` — Helper the linter should suggest
- `runner/tool_errors.py` — Helper the linter should suggest

**Architect's technical design:**

- `.claude/repomix_packages/TASK-st08-10-architect-review.md` — Research questions and design doc

---

## Review Checklist

Work through these items, stopping at each major decision point to confirm with the user.

### 1. Validate ADR-0035 Decisions

Review the architecture decisions and confirm they are sound:

- [ ] **Lezer-based analysis**: Is using the Python syntax tree (already bundled) the right choice vs regex?
- [ ] **Extension composition**: Is the proposed file layout (`skriptoteketIntelligence.ts`, `skriptoteketLinter.ts`, etc.) appropriate?
- [ ] **State sharing**: Is the Facet + StateField approach for config/caching reasonable?
- [ ] **Performance model**: Is 750ms debounce + linear scanning sufficient for 500+ line scripts?

**Stop and confirm**: Present your assessment of each decision with pros/cons. If you disagree with any decision, explain why and propose alternatives.

### 2. Validate Lint Rules

Review the lint rule specifications across all three phases:

| Phase | Rules | Focus |
|-------|-------|-------|
| Phase 1 | 2 | Entrypoint detection |
| Phase 2 | 9 | Contract + security |
| Phase 3 | 4 | Best practices |

For each rule category:

- [ ] Are the detection patterns feasible with Lezer syntax tree?
- [ ] Are the Swedish error messages clear and actionable?
- [ ] Are severity levels appropriate (error/warning/info)?
- [ ] Are there edge cases that could cause false positives?

**Stop and confirm**: If any rules seem problematic or need refinement, discuss with the user before proceeding.

### 3. Validate Completion Sources

Review the autocomplete design:

- [ ] Import completions on `from ` prefix — feasible with `matchBefore`?
- [ ] Contract key completions inside dict literals — requires syntax tree context detection
- [ ] Automatic trigger via `startCompletion` — UX appropriate?

**Stop and confirm**: If the completion trigger behavior seems intrusive or the context detection too complex, propose alternatives.

### 4. Validate Hover Documentation

Review the hover tooltip design:

- [ ] Word detection via `wordAt` + dotted name expansion — sufficient?
- [ ] Swedish documentation content — clear and helpful?
- [ ] Tooltip styling — consistent with brutalist design system?

### 5. Identify Risks and Gaps

Document any concerns:

- [ ] Are there missing lint rules that should be added?
- [ ] Are there rules that should be removed or deferred?
- [ ] Are there dependencies not captured (npm packages, etc.)?
- [ ] Is the phased breakdown appropriate, or should stories be combined/split differently?

**Stop and confirm**: Present a risk summary with recommendations before finalizing.

### 6. Review CodeMirror 6 Integration Point

The ADR proposes adding `extensions?: Extension[]` prop to `CodeMirrorEditor.vue`.

- [ ] Is this the right integration pattern?
- [ ] Should the extensions be composed inside the component instead?
- [ ] Are there existing patterns in the codebase to follow?

**Stop and confirm**: If you recommend a different integration approach, explain with code examples.

---

## Key CodeMirror 6 Idioms

For your reference when reviewing the design:

### Completion Source

```typescript
import { autocompletion, CompletionContext } from "@codemirror/autocomplete";

const skriptoteketCompletions = autocompletion({
  override: [
    (context: CompletionContext) => {
      const word = context.matchBefore(/from\s+\w*/);
      if (!word) return null;
      return {
        from: word.from,
        options: [
          { label: "pdf_helper", type: "module", detail: "PDF-rendering" },
          { label: "tool_errors", type: "module", detail: "Felhantering" },
        ],
      };
    },
  ],
});
```

### Linter

```typescript
import { linter, Diagnostic } from "@codemirror/lint";

const skriptoteketLinter = linter((view) => {
  const diagnostics: Diagnostic[] = [];
  const doc = view.state.doc.toString();

  if (!doc.includes("def run_tool")) {
    diagnostics.push({
      from: 0,
      to: 0,
      severity: "warning",
      message: "Saknar startfunktion: def run_tool(input_path, output_dir)",
    });
  }

  return diagnostics;
});
```

### Hover Tooltip

```typescript
import { hoverTooltip } from "@codemirror/view";

const skriptoteketHover = hoverTooltip((view, pos) => {
  const word = view.state.wordAt(pos);
  if (!word) return null;

  const text = view.state.sliceDoc(word.from, word.to);
  if (text === "save_as_pdf") {
    return {
      pos: word.from,
      end: word.to,
      above: true,
      create: () => {
        const dom = document.createElement("div");
        dom.className = "cm-tooltip-docs";
        dom.innerHTML = `<strong>save_as_pdf(html, output_dir, filename)</strong><br>
          Renderar HTML till PDF och sparar som artefakt.`;
        return { dom };
      },
    };
  }
  return null;
});
```

### Syntax Tree Access

```typescript
import { syntaxTree } from "@codemirror/language";

function findFunctionDefs(view: EditorView) {
  const tree = syntaxTree(view.state);
  const functions: { name: string; from: number; to: number }[] = [];

  tree.iterate({
    enter: (node) => {
      if (node.type.name === "FunctionDefinition") {
        // Extract function name from child nodes
      }
    },
  });

  return functions;
}
```

---

## Decision Points Requiring User Input

When you encounter these situations, **stop and ask the user**:

1. **Architecture changes**: Any modification to ADR-0035 decisions
2. **Rule additions/removals**: Adding or removing lint rules from the specification
3. **Severity changes**: Changing error → warning or warning → info
4. **Phase reassignment**: Moving rules between phases
5. **New dependencies**: Any npm packages not already in the project
6. **Breaking changes**: Anything that would change the existing editor behavior

For each decision:

1. Describe the situation
2. List options with pros/cons
3. Provide your recommendation
4. Wait for user confirmation before proceeding

---

## At the End of Your Session

When you are done with the review, you **MUST**:

1. **Update documentation** if any changes were made:
   - `docs/adr/adr-0035-script-editor-intelligence-architecture.md`
   - `docs/backlog/stories/story-08-10-script-editor-intelligence.md`
   - `docs/backlog/stories/story-08-11-script-editor-intelligence-phase2.md`
   - `docs/backlog/stories/story-08-12-script-editor-intelligence-phase3.md`

2. **Update handoff** with review findings:
   - `.agent/handoff.md` — Add summary of review decisions

3. **Validate documentation**:
   ```bash
   pdm run docs-validate
   ```

4. **Summarize for user**:
   - List all decisions made
   - List any open questions for future sessions
   - Confirm documentation is up-to-date

---

## Entry Point

Start by reading the files listed above, then work through the review checklist. Your first action should be:

1. Read `docs/adr/adr-0035-script-editor-intelligence-architecture.md`
2. Read `docs/backlog/stories/story-08-10-script-editor-intelligence.md`
3. Present your initial assessment of the Lezer-based architecture decision

**Do not make any changes** until you have discussed your findings with the user.
