export type EditorSaveMode = "snapshot" | "create_draft";

export type EditorBootPayload = {
  tool_id: string;
  selected_version_id: string | null;
  save_mode: EditorSaveMode;
  derived_from_version_id: string | null;
  entrypoint: string;
  source_code: string;
};

export type SaveResult = {
  version_id: string;
  redirect_url: string;
};
