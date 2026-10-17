/**
 * Purpose:
 *     Map each shared semantic glyph meaning to exactly one glyph.
 *
 * Relationships:
 *     - Rendered by UiGlyph; UiSymbol maps its legacy names onto these meanings.
 *     - Lucide glyphs come from the `@lucide/vue` 1.47.0 peer dependency.
 *     - Custom glyphs keep the HuleEdu workbench geometry the user chose to retain.
 *     - Meaning-to-glyph provenance lives in assets/icons/README.md.
 */

import {
  ArrowDown,
  ArrowLeft,
  Bold,
  ArrowRight,
  ArrowUp,
  Bookmark,
  BookOpen,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ChevronUp,
  CircleAlert,
  CircleCheck,
  ClipboardCheck,
  CirclePlus,
  CircleQuestionMark,
  CircleUserRound,
  Code,
  Copy,
  Download,
  EllipsisVertical,
  Eye,
  EyeOff,
  FileArchive,
  FileHeadphone,
  FileMinus,
  FileSpreadsheet,
  FileText,
  Folder,
  FolderInput,
  FolderOpen,
  Fullscreen,
  Globe,
  Heading1,
  Heading2,
  Heading3,
  History,
  Image,
  Info,
  Italic,
  LayoutDashboard,
  Library,
  Lightbulb,
  Link2,
  List,
  ListChecks,
  LoaderCircle,
  LogOut,
  Maximize2,
  Menu,
  Minus,
  OctagonAlert,
  PanelLeft,
  Pencil,
  PencilLine,
  Play,
  Plus,
  Power,
  Redo2,
  RefreshCw,
  Replace,
  RotateCw,
  Save,
  Search,
  SendHorizontal,
  Settings,
  Shuffle,
  SlidersHorizontal,
  Sparkles,
  Square,
  SquareCheck,
  Subscript,
  Superscript,
  TextAlignCenter,
  TextAlignStart,
  Trash2,
  TriangleAlert,
  Underline,
  Undo2,
  Upload,
  UserMinus,
  Users,
  Wrench,
  X,
  ZoomIn,
  ZoomOut,
} from "@lucide/vue";
import type { LucideIcon } from "@lucide/vue";

export type UiGlyphNavigationMeaning =
  | "home"
  | "assessments"
  | "raters"
  | "continue"
  | "back"
  | "previous"
  | "next"
  | "log-out"
  | "navigation-menu"
  | "first-page"
  | "last-page"
  | "open-detail"
  | "nav-files"
  | "nav-my-tools"
  | "nav-suggest-tool"
  | "nav-review-suggestions"
  | "nav-users";

export type UiGlyphActionMeaning =
  | "upload"
  | "add"
  | "add-entity"
  | "edit"
  | "download"
  | "document"
  | "delete"
  | "archive-batch"
  | "remove-rater"
  | "remove-essay"
  | "choose-from-catalogue"
  | "confirm"
  | "close"
  | "retry"
  | "move-up"
  | "move-down"
  | "increment"
  | "decrement"
  | "remove-item"
  | "copy"
  | "save"
  | "save-to-files"
  | "undo"
  | "redo"
  | "restore"
  | "start"
  | "refresh"
  | "search"
  | "share-link"
  | "bookmark"
  | "shuffle"
  | "show-password"
  | "hide-password"
  | "audio-file"
  | "spreadsheet-file"
  | "archive-file"
  | "image-file"
  | "code-file"
  | "open-files"
  | "convert-type"
  | "export-checklist"
  | "send";

export type UiGlyphUtilityMeaning =
  | "info"
  | "collapse"
  | "expand"
  | "open-list"
  | "more-below"
  | "minimize-panel"
  | "restore-panel"
  | "dismiss-coach"
  | "interface-language"
  | "account-menu"
  | "tutorial-pointer"
  | "status-success"
  | "status-warning"
  | "status-failure"
  | "selected"
  | "busy"
  | "completed"
  | "status-modified"
  | "ai-assist"
  | "help"
  | "settings"
  | "configure"
  | "history"
  | "preview"
  | "zoom-in"
  | "zoom-out"
  | "fit-view"
  | "toggle-sidebar"
  | "instruction"
  | "blocker"
  | "checkbox-on"
  | "checkbox-off"
  | "focus-mode"
  | "overview";

export type UiGlyphEditorToolbarMeaning =
  | "bold"
  | "italic"
  | "bulleted-list"
  | "align-left"
  | "align-center"
  | "info-box"
  | "more-actions"
  | "underline"
  | "subscript"
  | "superscript"
  | "heading-1"
  | "heading-2"
  | "heading-3";

export type UiGlyphMeaning =
  | UiGlyphNavigationMeaning
  | UiGlyphActionMeaning
  | UiGlyphUtilityMeaning
  | UiGlyphEditorToolbarMeaning;

export type UiGlyphCustomGeometry = {
  rects: readonly { x: number; y: number; width: number; height: number; rx: number }[];
  paths: readonly string[];
};

export type UiGlyphSource =
  | { kind: "lucide"; icon: LucideIcon }
  | { kind: "custom"; geometry: UiGlyphCustomGeometry };

const lucide = (icon: LucideIcon): UiGlyphSource => ({ kind: "lucide", icon });
const custom = (geometry: UiGlyphCustomGeometry): UiGlyphSource => ({ kind: "custom", geometry });

const navigationGlyphs: Record<UiGlyphNavigationMeaning, UiGlyphSource> = {
  home: custom({
    rects: [],
    paths: ["M3 11l9-8 9 8M5 10v10a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V10"],
  }),
  assessments: custom({
    rects: [{ x: 8, y: 2, width: 8, height: 4, rx: 1 }],
    paths: [
      "M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2M9 12h6M9 16h6",
    ],
  }),
  raters: lucide(Users),
  continue: lucide(ArrowRight),
  back: lucide(ArrowLeft),
  previous: lucide(ChevronLeft),
  next: lucide(ChevronRight),
  "log-out": lucide(LogOut),
  "navigation-menu": lucide(Menu),
  "first-page": lucide(ChevronsLeft),
  "last-page": lucide(ChevronsRight),
  "open-detail": lucide(ChevronRight),
  "nav-files": lucide(Folder),
  "nav-my-tools": lucide(Wrench),
  "nav-suggest-tool": lucide(Lightbulb),
  "nav-review-suggestions": lucide(ClipboardCheck),
  "nav-users": lucide(Users),
};

const actionGlyphs: Record<UiGlyphActionMeaning, UiGlyphSource> = {
  upload: lucide(Upload),
  add: lucide(Plus),
  "add-entity": lucide(CirclePlus),
  edit: lucide(Pencil),
  download: lucide(Download),
  document: lucide(FileText),
  delete: lucide(Trash2),
  "archive-batch": custom({
    rects: [{ x: 3, y: 3, width: 18, height: 5, rx: 1 }],
    paths: ["M5 8v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8M10 12h4"],
  }),
  "remove-rater": lucide(UserMinus),
  "remove-essay": lucide(FileMinus),
  "choose-from-catalogue": lucide(Library),
  confirm: lucide(Check),
  close: lucide(X),
  retry: lucide(RotateCw),
  "move-up": lucide(ArrowUp),
  "move-down": lucide(ArrowDown),
  increment: lucide(Plus),
  decrement: lucide(Minus),
  "remove-item": lucide(X),
  copy: lucide(Copy),
  save: lucide(Save),
  "save-to-files": lucide(FolderInput),
  undo: lucide(Undo2),
  redo: lucide(Redo2),
  restore: lucide(Undo2),
  start: lucide(Play),
  refresh: lucide(RefreshCw),
  search: lucide(Search),
  "share-link": lucide(Link2),
  bookmark: lucide(Bookmark),
  shuffle: lucide(Shuffle),
  "show-password": lucide(Eye),
  "hide-password": lucide(EyeOff),
  "audio-file": lucide(FileHeadphone),
  "spreadsheet-file": lucide(FileSpreadsheet),
  "archive-file": lucide(FileArchive),
  "image-file": lucide(Image),
  "code-file": lucide(Code),
  "open-files": lucide(FolderOpen),
  "convert-type": lucide(Replace),
  "export-checklist": lucide(ListChecks),
  send: lucide(SendHorizontal),
};

const utilityGlyphs: Record<UiGlyphUtilityMeaning, UiGlyphSource> = {
  info: lucide(Info),
  collapse: lucide(ChevronDown),
  expand: lucide(ChevronRight),
  "open-list": lucide(ChevronDown),
  "more-below": lucide(ChevronDown),
  "minimize-panel": lucide(ChevronDown),
  "restore-panel": lucide(ChevronUp),
  "dismiss-coach": lucide(Power),
  "interface-language": lucide(Globe),
  "account-menu": lucide(CircleUserRound),
  "tutorial-pointer": lucide(ArrowUp),
  "status-success": lucide(CircleCheck),
  "status-warning": lucide(TriangleAlert),
  "status-failure": lucide(OctagonAlert),
  selected: lucide(Check),
  busy: lucide(LoaderCircle),
  completed: lucide(Check),
  "status-modified": lucide(PencilLine),
  "ai-assist": lucide(Sparkles),
  help: lucide(CircleQuestionMark),
  settings: lucide(Settings),
  configure: lucide(SlidersHorizontal),
  history: lucide(History),
  preview: lucide(Eye),
  "zoom-in": lucide(ZoomIn),
  "zoom-out": lucide(ZoomOut),
  "fit-view": lucide(Fullscreen),
  "toggle-sidebar": lucide(PanelLeft),
  instruction: lucide(BookOpen),
  blocker: lucide(CircleAlert),
  "checkbox-on": lucide(SquareCheck),
  "checkbox-off": lucide(Square),
  "focus-mode": lucide(Maximize2),
  overview: lucide(LayoutDashboard),
};

const editorToolbarGlyphs: Record<UiGlyphEditorToolbarMeaning, UiGlyphSource> = {
  bold: lucide(Bold),
  italic: lucide(Italic),
  "bulleted-list": lucide(List),
  "align-left": lucide(TextAlignStart),
  "align-center": lucide(TextAlignCenter),
  "info-box": custom({
    rects: [{ x: 3, y: 5, width: 18, height: 14, rx: 2 }],
    paths: ["M7 10h10M7 14h6"],
  }),
  "more-actions": lucide(EllipsisVertical),
  underline: lucide(Underline),
  subscript: lucide(Subscript),
  superscript: lucide(Superscript),
  "heading-1": lucide(Heading1),
  "heading-2": lucide(Heading2),
  "heading-3": lucide(Heading3),
};

export const UI_GLYPHS: Readonly<Record<UiGlyphMeaning, UiGlyphSource>> = {
  ...navigationGlyphs,
  ...actionGlyphs,
  ...utilityGlyphs,
  ...editorToolbarGlyphs,
};
