export type SkriptoteketHelperModuleId = "pdf_helper" | "tool_errors";

export type SkriptoteketHelperExportId =
  | "save_as_pdf"
  | "ToolUserError";

export const SKRIPTOTEKET_CONTRACT_KEYS = ["outputs", "next_actions", "state"] as const;
export type SkriptoteketContractKey = (typeof SKRIPTOTEKET_CONTRACT_KEYS)[number];

export const SKRIPTOTEKET_OUTPUT_KINDS = [
  "notice",
  "markdown",
  "table",
  "json",
  "html_sandboxed",
] as const;
export type SkriptoteketOutputKind = (typeof SKRIPTOTEKET_OUTPUT_KINDS)[number];

export const SKRIPTOTEKET_NOTICE_LEVELS = ["info", "warning", "error"] as const;
export type SkriptoteketNoticeLevel = (typeof SKRIPTOTEKET_NOTICE_LEVELS)[number];

export type SkriptoteketHelperDoc = {
  moduleId: SkriptoteketHelperModuleId;
  exportId: SkriptoteketHelperExportId;
  signature: string;
  swedishDoc: string;
};

export const SKRIPTOTEKET_HELPER_DOCS: SkriptoteketHelperDoc[] = [
  {
    moduleId: "pdf_helper",
    exportId: "save_as_pdf",
    signature: "save_as_pdf(html, output_dir, filename) -> str",
    swedishDoc:
      "Renderar HTML till PDF och sparar under output_dir så att filen blir en nedladdningsbar artefakt.",
  },
  {
    moduleId: "tool_errors",
    exportId: "ToolUserError",
    signature: "ToolUserError(message: str)",
    swedishDoc: "Använd för fel som ska visas för användaren utan stacktrace.",
  },
];
