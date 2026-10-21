/**
 * Exam workspace rich-text schema.
 *
 * Domain purpose:
 *   The ProseMirror schema every exam text field edits on (question text, a
 *   part instruction, the exam instruction, a choice option, a Kategorisera
 *   entry, an ordering step), composed extension by extension so it admits
 *   exactly the native body vocabulary: paragraphs and headings of level 1
 *   to 3, hard breaks, the five kept marks, one kept-gap link mark, and two
 *   inline atoms — a gap and
 *   a picture. No StarterKit bundle, so no list, quote, code, link or rule
 *   enters the schema.
 *
 *   There is no editor-local undo history: Ctrl/Cmd+Z and Ctrl/Cmd+Shift+Z or
 *   Ctrl+Y reach the workspace's Ångra and Gör om through the options, and are
 *   always swallowed so the browser's own contenteditable undo never runs.
 *   Only the workspace history restores gap and picture records together
 *   with the text (TASK-SKRIPT-40-04-06 D2).
 *
 *   Ctrl+Alt+G (Cmd+Option+G on macOS) reaches the gap tool toggle through
 *   the options, in either letter case so Caps Lock keeps working, and is
 *   left alone when this editor has no gap tool.
 *
 *   A drag over a surface that accepts pictures shows the drop line a
 *   dropped file lands on (`@tiptap/pm/dropcursor`, class `xw-dropcursor`),
 *   through the options; a surface without pictures has no drop line.
 *
 *   Neither atom parses from HTML, so a paste or a drop never carries a gap
 *   or a picture, even one cut from the same editor: a gap id must stay
 *   placed once and its record leaves the item with the cut, and only the
 *   importer places pictures. The kept-gap mark defines no parse rule either,
 *   so a paste never carries that link. A gap reads its visible and accessible label
 *   and a picture its URL through the options getters, drawn as node
 *   decorations, so the owning component redraws both by dispatching a
 *   transaction with `ATOM_STATE_KEY` meta, without a document change.
 *
 * Relationships:
 *   - `examWorkspaceRichTextDocument` maps the stored body to and from this
 *     schema's JSON; nothing else reads its node names.
 *   - `ExamWorkspaceRichTextEditor` builds its editor from
 *     `examRichTextExtensions`.
 */

import { Extension, Mark, Node } from "@tiptap/core";
import Bold from "@tiptap/extension-bold";
import Document from "@tiptap/extension-document";
import HardBreak from "@tiptap/extension-hard-break";
import Heading from "@tiptap/extension-heading";
import Italic from "@tiptap/extension-italic";
import Paragraph from "@tiptap/extension-paragraph";
import Subscript from "@tiptap/extension-subscript";
import Superscript from "@tiptap/extension-superscript";
import Text from "@tiptap/extension-text";
import Underline from "@tiptap/extension-underline";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { dropCursor } from "@tiptap/pm/dropcursor";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";

export const EXAM_GAP_NODE = "examGap";
export const EXAM_PICTURE_NODE = "examPicture";
/** The editor mark a kept gap id maps to; stored text keeps it as `kept_gap_id`, never as a mark name. */
export const EXAM_KEPT_GAP_MARK = "examKeptGap";

/** Dispatch a transaction with this meta key to redraw gap labels and picture URLs. */
export const ATOM_STATE_KEY = new PluginKey<DecorationSet>("examAtomState");

/** A gap's visible label ("Lucka 2" or its accepted answers), accessible name, and whether it lacks answers. */
export type ExamGapState = { label: string; accessibleLabel: string; empty: boolean };

export type ExamRichTextOptions = {
  /** How one gap is drawn, read on every redraw. */
  gapState: (gapId: string) => ExamGapState;
  /** The protected URL of one picture, or undefined while it is not loaded. */
  pictureUrl: (assetId: string) => string | undefined;
  /** While true, words that keep hidden answers show their dotted underline. */
  keptGapToolOn: () => boolean;
  /** Ctrl/Cmd+Z: the workspace's Ångra. */
  onUndo: () => void;
  /** Ctrl/Cmd+Shift+Z or Ctrl+Y: the workspace's Gör om. */
  onRedo: () => void;
  /** Ctrl+Alt+G, Cmd+Option+G on macOS: turn the gap tool on or off; false when this editor has no gap tool, so the key is left alone. */
  onToggleGapTool: () => boolean;
  /** While true, a drag over the surface shows the drop line a dropped picture lands on. */
  dropCursor?: boolean;
};

/** Visible label of a picture whose protected URL is not loaded. */
export const PICTURE_PLACEHOLDER_LABEL = "Bild";

/** A gap is a fixed inline atom: selectable as a whole, never split, never parsed from a paste. */
const ExamGap = Node.create({
  name: EXAM_GAP_NODE,
  group: "inline",
  inline: true,
  atom: true,
  selectable: true,
  draggable: false,

  addAttributes() {
    return { gapId: { default: null, rendered: false } };
  },

  renderHTML({ node }) {
    return [
      "span",
      {
        "data-atom": "gap",
        "data-gap-id": String(node.attrs.gapId),
        "aria-haspopup": "dialog",
        "aria-expanded": "false",
        role: "button",
        class: "xw-gap",
      },
    ];
  },
});

/**
 * A picture is a fixed inline atom. Its node view re-reads the URL on every
 * redraw, so a URL that arrives, changes or goes away is applied in place.
 */
function examPictureNode(options: ExamRichTextOptions) {
  return Node.create({
    name: EXAM_PICTURE_NODE,
    group: "inline",
    inline: true,
    atom: true,
    selectable: true,
    draggable: false,

    addAttributes() {
      return { assetId: { default: null, rendered: false } };
    },

    renderHTML({ node }) {
      return ["span", { "data-atom": "asset", "data-asset-id": String(node.attrs.assetId) }];
    },

    addNodeView() {
      return ({ node }) => {
        const dom = document.createElement("span");
        dom.setAttribute("data-atom", "asset");
        dom.setAttribute("data-asset-id", String(node.attrs.assetId));
        dom.setAttribute("role", "img");
        dom.setAttribute("aria-label", PICTURE_PLACEHOLDER_LABEL);
        dom.className = "xw-picture";
        let shownUrl: string | undefined;
        const draw = (current: ProseMirrorNode): void => {
          const url = options.pictureUrl(String(current.attrs.assetId));
          if (url === shownUrl) {
            return;
          }
          shownUrl = url;
          dom.replaceChildren();
          if (url) {
            const image = document.createElement("img");
            image.src = url;
            image.alt = "";
            image.draggable = false;
            image.className = "xw-picture__image";
            dom.append(image);
          }
        };
        draw(node);
        return {
          dom,
          update: (updated) => {
            if (updated.type.name !== EXAM_PICTURE_NODE || updated.attrs.assetId !== node.attrs.assetId) {
              return false;
            }
            draw(updated);
            return true;
          },
          ignoreMutation: () => true,
        };
      };
    },
  });
}

/** The tooltip of a word that keeps hidden answers while the gap tool is on. */
export const KEPT_GAP_TOOLTIP = "Har sparade svar för en lucka";

/**
 * Gap labels and picture URL state as node decorations. CSS draws
 * `data-label`, so copied text never carries a label; a changed decoration
 * makes the picture node view re-read its URL. While the gap tool is on,
 * every kept word also carries an inline decoration with the kept underline
 * class and tooltip; with the tool off it renders as plain text.
 */
function atomState(options: ExamRichTextOptions) {
  return Extension.create({
    name: "examAtomState",

    addProseMirrorPlugins() {
      const build = (doc: ProseMirrorNode): DecorationSet => {
        const decorations: Decoration[] = [];
        const showKept = options.keptGapToolOn();
        doc.descendants((node, pos) => {
          if (node.type.name === EXAM_GAP_NODE) {
            const gap = options.gapState(String(node.attrs.gapId));
            decorations.push(
              Decoration.node(pos, pos + node.nodeSize, {
                "data-label": gap.label,
                "aria-label": gap.accessibleLabel,
                ...(gap.empty ? { "data-empty": "true" } : {}),
              }),
            );
          } else if (node.type.name === EXAM_PICTURE_NODE) {
            const url = options.pictureUrl(String(node.attrs.assetId));
            decorations.push(
              Decoration.node(
                pos,
                pos + node.nodeSize,
                url ? { "data-picture-url": url } : { "data-label": PICTURE_PLACEHOLDER_LABEL },
              ),
            );
          } else if (showKept && node.isText) {
            const kept = node.marks.find((mark) => mark.type.name === EXAM_KEPT_GAP_MARK);
            if (kept && typeof kept.attrs.keptGapId === "string") {
              decorations.push(
                Decoration.inline(pos, pos + node.nodeSize, {
                  class: "xw-kept-gap",
                  title: KEPT_GAP_TOOLTIP,
                }),
              );
            }
          }
        });
        return DecorationSet.create(doc, decorations);
      };
      return [
        new Plugin<DecorationSet>({
          key: ATOM_STATE_KEY,
          state: {
            init: (_, state) => build(state.doc),
            apply: (tr, previous, _, state) =>
              tr.docChanged || tr.getMeta(ATOM_STATE_KEY) ? build(state.doc) : previous,
          },
          props: {
            decorations: (state) => ATOM_STATE_KEY.getState(state),
          },
        }),
      ];
    },
  });
}

/** Undo and redo go to the workspace history and never to the browser. */
function workspaceHistoryKeys(options: ExamRichTextOptions) {
  return Extension.create({
    name: "examWorkspaceHistoryKeys",

    addKeyboardShortcuts() {
      const undo = () => {
        options.onUndo();
        return true;
      };
      const redo = () => {
        options.onRedo();
        return true;
      };
      return { "Mod-z": undo, "Mod-Z": undo, "Shift-Mod-z": redo, "Shift-Mod-Z": redo, "Mod-y": redo, "Mod-Y": redo };
    },
  });
}

/** Ctrl+Alt+G (Cmd+Option+G on macOS) toggles the gap tool, and is left alone without one. */
function gapToolKeys(options: ExamRichTextOptions) {
  return Extension.create({
    name: "examWorkspaceGapToolKeys",

    addKeyboardShortcuts() {
      return { "Mod-Alt-g": () => options.onToggleGapTool(), "Mod-Alt-G": () => options.onToggleGapTool() };
    },
  });
}

/**
 * The drop line a dragged picture lands on. Only a surface that accepts
 * pictures draws it, and CSS gives it the action colour through its class.
 */
function pictureDropCursor(options: ExamRichTextOptions) {
  return Extension.create({
    name: "examPictureDropCursor",

    addProseMirrorPlugins() {
      if (!options.dropCursor) {
        return [];
      }
      return [dropCursor({ class: "xw-dropcursor", width: 2, color: false })];
    },
  });
}

/** One glyph cannot sit both above and below the baseline, so the two marks exclude each other. */
const ExamSuperscript = Superscript.extend({ excludes: "subscript" });
const ExamSubscript = Subscript.extend({ excludes: "superscript" });

/**
 * A reverted word's link to its hidden kept gap. The mark is not inclusive,
 * so typing at the word's edges does not join the link, while typing inside
 * the word keeps it. It defines no parse rule and renders no identifying
 * attribute, so a paste or a drop never carries the link, even one cut from
 * the same editor — the same route that keeps gaps and pictures out of a
 * paste. While the gap tool is on, the atom state's inline decoration draws
 * the word with the kept underline and tooltip.
 */
const ExamKeptGap = Mark.create({
  name: EXAM_KEPT_GAP_MARK,
  inclusive: false,

  addAttributes() {
    return { keptGapId: { default: null } };
  },

  renderHTML() {
    return ["span", { "data-kept-gap": "true" }];
  },
});

/** The extension set an exam text editor is built with, in schema order. */
export function examRichTextExtensions(options: ExamRichTextOptions) {
  return [
    Document,
    Paragraph,
    Text,
    Heading.configure({ levels: [1, 2, 3] }),
    HardBreak,
    Bold,
    Italic,
    Underline,
    ExamSuperscript,
    ExamSubscript,
    ExamKeptGap,
    ExamGap,
    examPictureNode(options),
    atomState(options),
    workspaceHistoryKeys(options),
    gapToolKeys(options),
    pictureDropCursor(options),
  ];
}
