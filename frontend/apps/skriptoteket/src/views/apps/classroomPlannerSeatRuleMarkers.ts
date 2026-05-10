/**
 * Seat-level smart-rule marker presentation.
 *
 * Purpose:
 *   Derive symbolic rule participation markers for classroom-map seats while
 *   keeping solver-owned soft-rule fulfillment outside frontend presentation.
 *
 * Relationships:
 *   - consumed by phone and desktop rules-map seat renderers
 *   - keeps fixed-seat hard-rule markers local because they compare exact
 *     student and seat ids
 */

import type {
  FixedSeatRule,
  RelationshipRule,
  RoomTemplate,
  SeatAssignment,
  SmartRuleDiagnostic,
  SmartRuleDiagnosticStatus,
  Student,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";
import { formatSeatDisplayLabel } from "./classroomPlannerSmartRulePresentation";

export type SmartRuleMarkerKind = "fixed-seat" | "keep-apart" | "keep-near" | "near-teacher";
export type SmartRuleMarkerTone = "success" | "warning" | "error" | "neutral";

export type SmartRuleSymbolMarker = {
  id: string;
  kind: SmartRuleMarkerKind;
  label: string;
  tone: SmartRuleMarkerTone;
};

type SeatRuleMarkerInput = {
  template?: RoomTemplate | null;
  studentsById?: Readonly<Record<string, Student | undefined>>;
  seatAssignments?: readonly SeatAssignment[];
  fixedSeatRules?: readonly FixedSeatRule[];
  relationshipRules?: readonly RelationshipRule[];
  seatingPreferences?: readonly StudentSeatingPreference[];
  ruleDiagnostics?: readonly SmartRuleDiagnostic[];
  pendingFixedSeatStudentId?: string | null;
  pendingFixedSeatSeatId?: string | null;
};

type CurrentDiagnosticsByRule = {
  nearTeacherByStudentId: Map<string, SmartRuleDiagnostic>;
  relationshipByRuleId: Map<string, SmartRuleDiagnostic>;
};

export function buildSeatRuleMarkersBySeatId(
  input: SeatRuleMarkerInput,
): Record<string, SmartRuleSymbolMarker[]> {
  const markers: Record<string, SmartRuleSymbolMarker[]> = {};
  for (const seat of input.template?.seats ?? []) {
    markers[seat.id] = [];
  }

  const studentsById = input.studentsById ?? {};
  const studentIdBySeatId = buildStudentIdBySeatId(input);
  const seatIdByStudentId = buildSeatIdByStudentId(input);
  const currentDiagnostics = buildCurrentDiagnostics(input, seatIdByStudentId);

  appendFixedSeatMarkers(input, markers, studentIdBySeatId, studentsById);
  appendNearTeacherMarkers(input, markers, seatIdByStudentId, studentsById, currentDiagnostics);
  appendRelationshipMarkers(input, markers, seatIdByStudentId, studentsById, currentDiagnostics);

  return markers;
}

function appendFixedSeatMarkers(
  input: SeatRuleMarkerInput,
  markers: Record<string, SmartRuleSymbolMarker[]>,
  studentIdBySeatId: Readonly<Record<string, string | null>>,
  studentsById: Readonly<Record<string, Student | undefined>>,
): void {
  for (const rule of input.fixedSeatRules ?? []) {
    const actualStudentId = studentIdBySeatId[rule.seat_id] ?? null;
    markers[rule.seat_id]?.push({
      id: `fixed-${rule.id}`,
      kind: "fixed-seat",
      label: fixedSeatMarkerLabel(rule, actualStudentId, studentsById),
      tone: fixedSeatMarkerTone(rule, actualStudentId),
    });
  }

  if (input.pendingFixedSeatSeatId) {
    markers[input.pendingFixedSeatSeatId]?.push({
      id: `pending-fixed-${input.pendingFixedSeatSeatId}`,
      kind: "fixed-seat",
      label: pendingFixedSeatMarkerLabel(input.pendingFixedSeatStudentId, studentsById),
      tone: "warning",
    });
  }
}

function appendNearTeacherMarkers(
  input: SeatRuleMarkerInput,
  markers: Record<string, SmartRuleSymbolMarker[]>,
  seatIdByStudentId: Readonly<Record<string, string | undefined>>,
  studentsById: Readonly<Record<string, Student | undefined>>,
  diagnosticsByRule: CurrentDiagnosticsByRule,
): void {
  for (const preference of input.seatingPreferences ?? []) {
    if (!preference.near_teacher) {
      continue;
    }
    const seatId = seatIdByStudentId[preference.student_id];
    if (!seatId) {
      continue;
    }
    const diagnostic = diagnosticsByRule.nearTeacherByStudentId.get(preference.student_id);
    markers[seatId]?.push({
      id: `near-teacher-${preference.student_id}`,
      kind: "near-teacher",
      label: nearTeacherMarkerLabel(preference.student_id, studentsById, diagnostic),
      tone: diagnostic ? markerToneForDiagnosticStatus(diagnostic.status) : "neutral",
    });
  }
}

function appendRelationshipMarkers(
  input: SeatRuleMarkerInput,
  markers: Record<string, SmartRuleSymbolMarker[]>,
  seatIdByStudentId: Readonly<Record<string, string | undefined>>,
  studentsById: Readonly<Record<string, Student | undefined>>,
  diagnosticsByRule: CurrentDiagnosticsByRule,
): void {
  for (const rule of input.relationshipRules ?? []) {
    const placedSeatIds = rule.student_ids
      .map((studentId) => seatIdByStudentId[studentId])
      .filter((seatId): seatId is string => typeof seatId === "string" && seatId.length > 0);
    if (placedSeatIds.length === 0) {
      continue;
    }
    const diagnostic = diagnosticsByRule.relationshipByRuleId.get(rule.id);
    const seatIds = diagnostic?.seat_ids.length ? diagnostic.seat_ids : placedSeatIds;
    for (const seatId of seatIds) {
      markers[seatId]?.push({
        id: `${rule.id}-${seatId}`,
        kind: rule.kind === "keep_near" ? "keep-near" : "keep-apart",
        label: relationshipMarkerLabel(rule, studentsById, diagnostic),
        tone: diagnostic ? markerToneForDiagnosticStatus(diagnostic.status) : "neutral",
      });
    }
  }
}

function buildCurrentDiagnostics(
  input: SeatRuleMarkerInput,
  seatIdByStudentId: Readonly<Record<string, string | undefined>>,
): CurrentDiagnosticsByRule {
  const diagnosticsByRule: CurrentDiagnosticsByRule = {
    nearTeacherByStudentId: new Map(),
    relationshipByRuleId: new Map(),
  };
  for (const diagnostic of input.ruleDiagnostics ?? []) {
    if (diagnostic.rule_kind === "fixed_seat") {
      continue;
    }
    if (!diagnosticMatchesCurrentAssignment(diagnostic, seatIdByStudentId)) {
      continue;
    }
    if (diagnostic.rule_kind === "near_teacher") {
      const [studentId] = diagnostic.student_ids;
      if (studentId) {
        diagnosticsByRule.nearTeacherByStudentId.set(studentId, diagnostic);
      }
      continue;
    }
    if (diagnostic.rule_id) {
      diagnosticsByRule.relationshipByRuleId.set(diagnostic.rule_id, diagnostic);
    }
  }
  return diagnosticsByRule;
}

function diagnosticMatchesCurrentAssignment(
  diagnostic: SmartRuleDiagnostic,
  seatIdByStudentId: Readonly<Record<string, string | undefined>>,
): boolean {
  if (diagnostic.student_ids.length === 0 || diagnostic.seat_ids.length === 0) {
    return false;
  }
  const currentSeatIds = diagnostic.student_ids.map((studentId) => seatIdByStudentId[studentId]);
  if (currentSeatIds.some((seatId) => !seatId)) {
    return false;
  }
  return sameStringSet(currentSeatIds as string[], diagnostic.seat_ids);
}

function sameStringSet(leftValues: readonly string[], rightValues: readonly string[]): boolean {
  if (leftValues.length !== rightValues.length) {
    return false;
  }
  const rightSet = new Set(rightValues);
  return leftValues.every((value) => rightSet.has(value));
}

function markerToneForDiagnosticStatus(status: SmartRuleDiagnosticStatus): SmartRuleMarkerTone {
  if (status === "satisfied") {
    return "success";
  }
  if (status === "failed") {
    return "error";
  }
  return "warning";
}

function buildStudentIdBySeatId(input: SeatRuleMarkerInput): Record<string, string | null> {
  const bySeatId: Record<string, string | null> = {};
  for (const seat of input.template?.seats ?? []) {
    bySeatId[seat.id] = null;
  }
  for (const assignment of input.seatAssignments ?? []) {
    if (bySeatId[assignment.seat_id] !== undefined) {
      bySeatId[assignment.seat_id] = assignment.student_id;
    }
  }
  return bySeatId;
}

function buildSeatIdByStudentId(input: SeatRuleMarkerInput): Record<string, string | undefined> {
  return Object.fromEntries(
    (input.seatAssignments ?? []).map((assignment) => [assignment.student_id, assignment.seat_id]),
  );
}

function studentName(
  studentId: string,
  studentsById: Readonly<Record<string, Student | undefined>>,
): string {
  return studentsById[studentId]?.display_name ?? "Okänd elev";
}

function fixedSeatMarkerLabel(
  rule: FixedSeatRule,
  actualStudentId: string | null,
  studentsById: Readonly<Record<string, Student | undefined>>,
): string {
  const target = `${studentName(rule.student_id, studentsById)} ska sitta på ${
    formatSeatDisplayLabel(rule.seat_id)
  }.`;
  if (!actualStudentId) {
    return `${target} Platsen är tom.`;
  }
  if (actualStudentId === rule.student_id) {
    return `${target} Regeln är uppfylld.`;
  }
  return `${target} Nu sitter ${studentName(actualStudentId, studentsById)} där.`;
}

function fixedSeatMarkerTone(
  rule: FixedSeatRule,
  actualStudentId: string | null,
): SmartRuleMarkerTone {
  if (!actualStudentId) {
    return "warning";
  }
  return actualStudentId === rule.student_id ? "success" : "error";
}

function pendingFixedSeatMarkerLabel(
  studentId: string | null | undefined,
  studentsById: Readonly<Record<string, Student | undefined>>,
): string {
  if (!studentId) {
    return "Vald plats för fast plats.";
  }
  return `Vald plats för ${studentName(studentId, studentsById)}.`;
}

function nearTeacherMarkerLabel(
  studentId: string,
  studentsById: Readonly<Record<string, Student | undefined>>,
  diagnostic: SmartRuleDiagnostic | undefined,
): string {
  return withDiagnosticStatus(
    `Nära läraren: ${studentName(studentId, studentsById)} har regeln nära läraren.`,
    diagnostic,
  );
}

function relationshipMarkerLabel(
  rule: RelationshipRule,
  studentsById: Readonly<Record<string, Student | undefined>>,
  diagnostic: SmartRuleDiagnostic | undefined,
): string {
  const ruleLabel = rule.kind === "keep_near" ? "Håll nära" : "Håll isär";
  const names = rule.student_ids.map((studentId) => studentName(studentId, studentsById));
  return withDiagnosticStatus(`${ruleLabel}: ${formatNameList(names)}.`, diagnostic);
}

function withDiagnosticStatus(
  label: string,
  diagnostic: SmartRuleDiagnostic | undefined,
): string {
  if (!diagnostic) {
    return label;
  }
  return `${label} ${diagnosticStatusLabel(diagnostic.status)}`;
}

function diagnosticStatusLabel(status: SmartRuleDiagnosticStatus): string {
  if (status === "satisfied") {
    return "Smart bedömer regeln som uppfylld.";
  }
  if (status === "degraded") {
    return "Smart bedömer placeringen som en acceptabel kompromiss.";
  }
  if (status === "failed") {
    return "Smart bedömer placeringen som utanför regelns accepterade läge.";
  }
  return "Smart väntar på att regeln ska kunna bedömas.";
}

function formatNameList(names: readonly string[]): string {
  if (names.length <= 1) {
    return names[0] ?? "Okänd elev";
  }
  if (names.length === 2) {
    return `${names[0]} och ${names[1]}`;
  }
  return `${names.slice(0, -1).join(", ")} och ${names[names.length - 1]}`;
}
