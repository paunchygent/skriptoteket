export type SkriptoteketHelperModuleId = "pdf_helper" | "tool_errors" | "skriptoteket_toolkit";

export type SkriptoteketHelperExportId =
  | "save_as_pdf"
  | "ToolUserError"
  | "ActionPayload"
  | "JsonValue"
  | "ManifestFile"
  | "get_action_parts"
  | "list_input_files"
  | "read_action"
  | "read_input_manifest"
  | "read_inputs"
  | "read_memory"
  | "read_settings";

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
  {
    moduleId: "skriptoteket_toolkit",
    exportId: "read_inputs",
    signature: "read_inputs() -> dict[str, JsonValue]",
    swedishDoc:
      "Läser och parsar `SKRIPTOTEKET_INPUTS` (JSON dict). Returnerar `{}` om den saknas eller är trasig JSON.",
  },
  {
    moduleId: "skriptoteket_toolkit",
    exportId: "read_input_manifest",
    signature: 'read_input_manifest() -> dict[str, JsonValue]  # {"files": [...]}',
    swedishDoc:
      "Läser `SKRIPTOTEKET_INPUT_MANIFEST` (JSON). Returnerar `{\"files\": []}` om den saknas eller är trasig JSON.",
  },
  {
    moduleId: "skriptoteket_toolkit",
    exportId: "list_input_files",
    signature: "list_input_files() -> list[ManifestFile]",
    swedishDoc:
      "Returnerar validerade uppladdade filer från input-manifestet. Varje post har `{name, path, bytes}`. Returnerar `[]` vid fel.",
  },
  {
    moduleId: "skriptoteket_toolkit",
    exportId: "read_action",
    signature: "read_action() -> ActionPayload | None",
    swedishDoc:
      "Läser `SKRIPTOTEKET_ACTION` (för next_actions-körningar). Returnerar `None` om den saknas eller är felaktig.",
  },
  {
    moduleId: "skriptoteket_toolkit",
    exportId: "get_action_parts",
    signature: "get_action_parts() -> (action_id, input, state)",
    swedishDoc:
      "Returnerar `(action_id, input, state)` med säkra defaultvärden. Om inte en action-körning: `(None, {}, {})`.",
  },
  {
    moduleId: "skriptoteket_toolkit",
    exportId: "read_memory",
    signature: "read_memory() -> dict[str, JsonValue]",
    swedishDoc:
      "Läser memory JSON från filen som pekas ut av `SKRIPTOTEKET_MEMORY_PATH`. Returnerar `{}` om filen saknas eller innehållet är felaktigt.",
  },
  {
    moduleId: "skriptoteket_toolkit",
    exportId: "read_settings",
    signature: "read_settings() -> dict[str, JsonValue]",
    swedishDoc: "Returnerar `memory['settings']` som dict, annars `{}`.",
  },
  {
    moduleId: "skriptoteket_toolkit",
    exportId: "ManifestFile",
    signature: "ManifestFile: TypedDict  # {name: str, path: str, bytes: int}",
    swedishDoc:
      "Typ för en uppladdad fil i input-manifestet (validerad): `{name, path, bytes}`.",
  },
  {
    moduleId: "skriptoteket_toolkit",
    exportId: "ActionPayload",
    signature: "ActionPayload: TypedDict  # {action_id: str, input: dict, state: dict}",
    swedishDoc:
      "Typ för action-körningar (när user klickar på en next_action): `{action_id, input, state}`.",
  },
  {
    moduleId: "skriptoteket_toolkit",
    exportId: "JsonValue",
    signature: "JsonValue: JSON (str/int/float/bool/None/dict/list)",
    swedishDoc:
      "Typalias för JSON-värden (rekursivt) som används av toolkit-hjälparna.",
  },
];
