import {
  SKRIPTOTEKET_CONTRACT_KEYS,
  SKRIPTOTEKET_NOTICE_LEVELS,
  SKRIPTOTEKET_OUTPUT_KINDS,
} from "../../../skriptoteketMetadata";

import type { DomainDiagnostic } from "../diagnostics";
import type { FixIntent } from "../fixIntents";
import type { LintRule } from "../lintRule";
import type { LinterContext } from "../linterContext";
import { stringLiteralValue } from "../utils/pythonStringLiterals";

const ST_CONTRACT_KEYS_MISSING = "ST_CONTRACT_KEYS_MISSING";

const FIX_ADD_CONTRACT_KEYS = "Lägg till nycklar";

function contractKeyDefaultValue(key: string): string {
  if (key === "outputs") return "[]";
  if (key === "next_actions") return "[]";
  if (key === "state") return "{}";
  return "None";
}

function safeQuoteForDictKeys(ctx: LinterContext, dictRange: { from: number; to: number }): "'" | '"' {
  const entries = ctx.pythonLiterals.dictionaryEntries(dictRange);
  const first = entries[0] ?? null;
  if (!first) return '"';

  const raw = ctx.text.slice(first.keyFrom, first.keyTo);
  return raw.startsWith("'") ? "'" : '"';
}

function addContractKeysFix(
  ctx: LinterContext,
  dictRange: { from: number; to: number },
  missingKeys: readonly string[],
): FixIntent | null {
  const closeBracePos = dictRange.to - 1;
  const quote = safeQuoteForDictKeys(ctx, dictRange);

  let lastNonWhitespace = closeBracePos - 1;
  while (lastNonWhitespace > dictRange.from && /\s/.test(ctx.text[lastNonWhitespace] ?? "")) {
    lastNonWhitespace -= 1;
  }

  const lastChar = ctx.text[lastNonWhitespace] ?? "";
  const insertAt = lastNonWhitespace + 1;
  const isEmpty = lastChar === "{";
  const hasTrailingComma = lastChar === ",";

  const dictText = ctx.text.slice(dictRange.from, dictRange.to);
  const isMultiLine = dictText.includes("\n");

  const segments = missingKeys.map((key) => `${quote}${key}${quote}: ${contractKeyDefaultValue(key)}`);

  let text = "";

  if (!isMultiLine) {
    const separator = isEmpty ? "" : hasTrailingComma ? " " : ", ";
    text = `${separator}${segments.join(", ")}`;
  } else {
    const lineStartClose = ctx.text.lastIndexOf("\n", closeBracePos - 1) + 1;
    const closeIndent = ctx.text.slice(lineStartClose, closeBracePos).match(/^[ \t]*/)?.[0] ?? "";

    const firstEntry = ctx.pythonLiterals.dictionaryEntries(dictRange)[0] ?? null;
    let entryIndent = `${closeIndent}    `;
    if (firstEntry) {
      const lineStartEntry = ctx.text.lastIndexOf("\n", firstEntry.keyFrom - 1) + 1;
      entryIndent = ctx.text.slice(lineStartEntry, firstEntry.keyFrom).match(/^[ \t]*/)?.[0] ?? entryIndent;
    }

    const lines = segments.map((segment) => `${entryIndent}${segment},`);
    const prefix = isEmpty || hasTrailingComma ? "" : ",";
    text = `${prefix}\n${lines.join("\n")}`;
  }

  if (text === "") return null;
  return { kind: "insertText", label: FIX_ADD_CONTRACT_KEYS, at: insertAt, text };
}

export const ContractRule: LintRule = {
  id: "ST_CONTRACT",
  check(ctx: LinterContext): DomainDiagnostic[] {
    const match = ctx.facts.entrypoint;
    if (!match) return [];

    const returns = ctx.facts.returns;
    if (returns.length === 0) return [];

    const literalDictReturns = returns.filter((stmt) => stmt.expression?.name === "DictionaryExpression");
    const literalStringReturns = returns.filter((stmt) => stmt.expression?.name === "String");

    if (literalDictReturns.length === 0 && literalStringReturns.length === 0) {
      return [
        {
          from: match.nameFrom,
          to: match.nameTo,
          severity: "hint",
          source: "ST_CONTRACT",
          message:
            "Kunde inte verifiera Contract v2 eftersom returvärdet byggs dynamiskt. Kontrollera att du returnerar dict med outputs/next_actions/state.",
        },
      ];
    }

    const diagnostics: DomainDiagnostic[] = [];

    for (const stmt of literalDictReturns) {
      const dictNode = stmt.expression;
      if (!dictNode) continue;

      const entries = ctx.pythonLiterals.dictionaryEntries({ from: dictNode.from, to: dictNode.to });
      const byKey = new Map(entries.map((entry) => [entry.key, entry]));

      const missingKeys = SKRIPTOTEKET_CONTRACT_KEYS.filter((key) => !byKey.has(key));
      if (missingKeys.length > 0) {
        const fix = addContractKeysFix(ctx, { from: dictNode.from, to: dictNode.to }, missingKeys);
        diagnostics.push({
          from: dictNode.from,
          to: Math.min(dictNode.from + 1, ctx.text.length),
          severity: "info",
          source: ST_CONTRACT_KEYS_MISSING,
          message: `Retur-dict saknar nycklar: ${missingKeys.join(" / ")}.`,
          fixes: fix ? [fix] : undefined,
        });
      }

      const outputsEntry = byKey.get("outputs") ?? null;
      if (!outputsEntry) continue;

      const outputsValue = outputsEntry.value;
      if (!outputsValue || outputsValue.name !== "ArrayExpression") {
        diagnostics.push({
          from: outputsEntry.keyFrom,
          to: outputsEntry.keyTo,
          severity: "error",
          source: "ST_CONTRACT",
          message: "`outputs` måste vara en lista (`[...]`).",
        });
        continue;
      }

      const outputEntries = ctx.pythonLiterals
        .arrayElements({ from: outputsValue.from, to: outputsValue.to })
        .filter((node) => node.name === "DictionaryExpression");

      for (const outputDict of outputEntries) {
        const outputFields = ctx.pythonLiterals.dictionaryEntries({ from: outputDict.from, to: outputDict.to });
        const outputByKey = new Map(outputFields.map((entry) => [entry.key, entry]));

        const kindEntry = outputByKey.get("kind") ?? null;
        const kindValue = stringLiteralValue(ctx, kindEntry?.value ?? null);
        if (!kindEntry || !kindValue) {
          diagnostics.push({
            from: outputDict.from,
            to: Math.min(outputDict.from + 1, ctx.text.length),
            severity: "warning",
            source: "ST_CONTRACT",
            message: 'Ett output-objekt saknar "kind".',
          });
          continue;
        }

        if (!SKRIPTOTEKET_OUTPUT_KINDS.includes(kindValue as (typeof SKRIPTOTEKET_OUTPUT_KINDS)[number])) {
          diagnostics.push({
            from: kindEntry.value?.from ?? outputDict.from,
            to: kindEntry.value?.to ?? Math.min(outputDict.from + 1, ctx.text.length),
            severity: "warning",
            source: "ST_CONTRACT",
            message: `Ogiltigt kind: "${kindValue}". Tillåtna: ${SKRIPTOTEKET_OUTPUT_KINDS.join(", ")}.`,
          });
          continue;
        }

        if (kindValue !== "notice") continue;

        const levelEntry = outputByKey.get("level") ?? null;
        const messageEntry = outputByKey.get("message") ?? null;
        if (!levelEntry || !messageEntry) {
          diagnostics.push({
            from: outputDict.from,
            to: Math.min(outputDict.from + 1, ctx.text.length),
            severity: "warning",
            source: "ST_CONTRACT",
            message: 'Notice saknar "level" eller "message".',
          });
          continue;
        }

        const levelValue = stringLiteralValue(ctx, levelEntry.value);
        if (
          levelValue &&
          !SKRIPTOTEKET_NOTICE_LEVELS.includes(levelValue as (typeof SKRIPTOTEKET_NOTICE_LEVELS)[number])
        ) {
          diagnostics.push({
            from: levelEntry.value?.from ?? outputDict.from,
            to: levelEntry.value?.to ?? Math.min(outputDict.from + 1, ctx.text.length),
            severity: "warning",
            source: "ST_CONTRACT",
            message: "Notice level måste vara info/warning/error.",
          });
        }
      }
    }

    return diagnostics;
  },
};
