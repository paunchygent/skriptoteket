export type FixIntent =
  | { kind: "replaceRange"; label: string; from: number; to: number; insert: string }
  | { kind: "insertText"; label: string; at: number; text: string }
  | { kind: "deleteRange"; label: string; from: number; to: number };
