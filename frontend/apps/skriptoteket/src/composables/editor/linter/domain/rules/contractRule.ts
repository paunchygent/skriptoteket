import {
  SKRIPTOTEKET_CONTRACT_KEYS,
  SKRIPTOTEKET_NOTICE_LEVELS,
  SKRIPTOTEKET_OUTPUT_KINDS,
} from "../../../skriptoteketMetadata";

import type { DomainDiagnostic } from "../diagnostics";
import type { LintRule } from "../lintRule";
import type { LinterContext } from "../linterContext";
import { stringLiteralValue } from "../utils/pythonStringLiterals";

const ST_CONTRACT_KEYS_MISSING = "ST_CONTRACT_KEYS_MISSING";

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
        diagnostics.push({
          from: dictNode.from,
          to: Math.min(dictNode.from + 1, ctx.text.length),
          severity: "info",
          source: ST_CONTRACT_KEYS_MISSING,
          message: `Retur-dict saknar nycklar: ${missingKeys.join(" / ")}.`,
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
