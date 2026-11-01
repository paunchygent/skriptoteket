// @ts-check

const HEX_COLOUR =
  /(?<![\w&])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9a-zA-Z_-])/;
const COLOUR_FUNCTION = /\b(?:rgba?|hsla?)\(/i;
const TAILWIND_PALETTE_CLASS =
  /(?<![\w-])(?:[a-z0-9-]+:)*(?:scrollbar-thumb|scrollbar-track|border-bs|border-be|border-[trblxyse]|border|inset-shadow|inset-ring|ring-offset|drop-shadow|text-shadow|shadow|ring|accent|bg|caret|decoration|divide|fill|from|outline|placeholder|stroke|text|to|via)-(?:(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}|white|black)(?:\/\d{1,3})?(?![\w-])/;

const PATTERN = new RegExp(
  [HEX_COLOUR.source, COLOUR_FUNCTION.source, TAILWIND_PALETTE_CLASS.source].join(
    "|",
  ),
  "gi",
);

/** @type {import("eslint").Rule.RuleModule} */
const rule = {
  meta: {
    type: "problem",
    docs: {
      description:
        "Disallow hardcoded colours; use var(--huleedu-*) tokens.",
    },
    schema: [],
    messages: {
      noHardcodedColour:
        "Hardcoded colour `{{value}}`. Use a var(--huleedu-*) design token.",
    },
  },
  create(context) {
    const sourceCode = context.sourceCode;
    const text = sourceCode.text;

    /** @param {number} index */
    function positionAt(index) {
      if (typeof sourceCode.getLocFromIndex === "function") {
        return sourceCode.getLocFromIndex(index);
      }
      let line = 1;
      let lastLineStart = 0;
      for (let i = 0; i < index; i += 1) {
        if (text.charCodeAt(i) === 10) {
          line += 1;
          lastLineStart = i + 1;
        }
      }
      return { line, column: index - lastLineStart };
    }

    /** @param {import("eslint").Rule.Node} node */
    function scan(node) {
      PATTERN.lastIndex = 0;
      let match;
      while ((match = PATTERN.exec(text)) !== null) {
        context.report({
          node,
          loc: {
            start: positionAt(match.index),
            end: positionAt(match.index + match[0].length),
          },
          messageId: "noHardcodedColour",
          data: { value: match[0] },
        });
      }
    }

    return {
      Program(node) {
        scan(node);
      },
      StyleSheet(node) {
        scan(node);
      },
    };
  },
};

export default rule;
