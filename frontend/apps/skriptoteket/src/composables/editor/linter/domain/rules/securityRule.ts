import type { DomainDiagnostic } from "../diagnostics";
import type { LintRule } from "../lintRule";
import type { LinterContext } from "../linterContext";

export const SecurityRule: LintRule = {
  id: "ST_SECURITY",
  check(ctx: LinterContext): DomainDiagnostic[] {
    const diagnostics: DomainDiagnostic[] = [];

    const blockedNetworkModules = new Set(["aiohttp", "requests", "httpx", "urllib3"]);
    for (const entry of ctx.facts.importModules) {
      if (blockedNetworkModules.has(entry.modulePath) || entry.modulePath === "urllib.request") {
        diagnostics.push({
          from: entry.from,
          to: entry.to,
          severity: "error",
          source: "ST_SECURITY",
          message: "Nätverksbibliotek stöds inte i sandbox (ingen nätverksåtkomst).",
        });
      }
    }

    for (const call of ctx.facts.memberCalls) {
      const isSubprocessRun = call.objectName === "subprocess" && call.propertyName === "run";
      const isOsShell = call.objectName === "os" && (call.propertyName === "system" || call.propertyName === "popen");
      if (!isSubprocessRun && !isOsShell) continue;

      diagnostics.push({
        from: call.propertyFrom,
        to: call.propertyTo,
        severity: "warning",
        source: "ST_SECURITY",
        message: "Undvik subprocess/os.system i sandbox. Använd rena Python-lösningar.",
      });
    }

    return diagnostics;
  },
};
