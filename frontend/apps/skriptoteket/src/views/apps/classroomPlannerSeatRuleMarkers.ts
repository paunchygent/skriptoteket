/**
 * Seat-level smart-rule marker evaluation.
 *
 * Purpose:
 *   Derive symbolic rule markers for classroom-map seats from the visible
 *   planner state without introducing a separate persistence contract.
 *
 * Relationships:
 *   - consumed by phone and desktop rules-map seat renderers
 *   - uses room template geometry only for presentation-state marker tone
 */

import type {
  FixedSeatRule,
  RelationshipRule,
  RoomFixture,
  RoomTemplate,
  Seat,
  SeatAssignment,
  Student,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";
import { formatSeatDisplayLabel } from "./classroomPlannerSmartRulePresentation";
import { ROOM_GRID_UNIT } from "./roomFixtureLayout";

export type SmartRuleMarkerKind = "fixed-seat" | "keep-apart" | "keep-near" | "near-teacher";
export type SmartRuleMarkerTone = "success" | "warning" | "error";

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
  pendingFixedSeatStudentId?: string | null;
  pendingFixedSeatSeatId?: string | null;
};
type TeachingEdge = "top" | "bottom" | "left" | "right";
type TeachingAnchor = {
  edge: TeachingEdge;
  x: number;
  y: number;
};
type SeatTopology = {
  frontRankBySeat: Record<string, number>;
  lateralRankBySeat: Record<string, number>;
  actualLateralDistanceBySeat: Record<string, number>;
};
type RoomBounds = {
  maxX: number;
  maxY: number;
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
  const nearTeacherSeatIds = buildNearTeacherSeatIds(
    input.template,
    countNearTeacherPreferences(input.seatingPreferences),
  );

  appendFixedSeatMarkers(input, markers, studentIdBySeatId, studentsById);
  appendNearTeacherMarkers(input, markers, seatIdByStudentId, nearTeacherSeatIds, studentsById);
  appendRelationshipMarkers(input, markers, seatIdByStudentId, studentsById);

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
  nearTeacherSeatIds: ReadonlySet<string>,
  studentsById: Readonly<Record<string, Student | undefined>>,
): void {
  for (const preference of input.seatingPreferences ?? []) {
    if (!preference.near_teacher) {
      continue;
    }
    const seatId = seatIdByStudentId[preference.student_id];
    if (!seatId) {
      continue;
    }
    markers[seatId]?.push({
      id: `near-teacher-${preference.student_id}`,
      kind: "near-teacher",
      label: nearTeacherMarkerLabel(preference.student_id, seatId, nearTeacherSeatIds, studentsById),
      tone: nearTeacherSeatIds.has(seatId) ? "success" : "warning",
    });
  }
}

function appendRelationshipMarkers(
  input: SeatRuleMarkerInput,
  markers: Record<string, SmartRuleSymbolMarker[]>,
  seatIdByStudentId: Readonly<Record<string, string | undefined>>,
  studentsById: Readonly<Record<string, Student | undefined>>,
): void {
  for (const rule of input.relationshipRules ?? []) {
    const [firstStudentId, secondStudentId] = rule.student_ids;
    if (!firstStudentId || !secondStudentId) {
      continue;
    }
    const firstSeatId = seatIdByStudentId[firstStudentId];
    const secondSeatId = seatIdByStudentId[secondStudentId];
    if (!firstSeatId || !secondSeatId) {
      continue;
    }
    const tone = relationshipRuleIsSatisfied(input.template, rule, firstSeatId, secondSeatId)
      ? "success"
      : "error";
    for (const seatId of [firstSeatId, secondSeatId]) {
      markers[seatId]?.push({
        id: `${rule.id}-${seatId}`,
        kind: rule.kind === "keep_near" ? "keep-near" : "keep-apart",
        label: relationshipMarkerLabel(rule, firstStudentId, secondStudentId, studentsById),
        tone,
      });
    }
  }
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

function countNearTeacherPreferences(
  seatingPreferences: readonly StudentSeatingPreference[] | undefined,
): number {
  return seatingPreferences?.filter((preference) => preference.near_teacher).length ?? 0;
}

function buildNearTeacherSeatIds(template: RoomTemplate | null | undefined, preferenceCount: number): Set<string> {
  const seats = template?.seats ?? [];
  if (!template || seats.length === 0 || preferenceCount <= 0) {
    return new Set();
  }
  return new Set(
    nearTeacherPool({
      seats,
      topology: buildSeatTopology(seats, inferTeachingAnchor(template)),
      seatCount: Math.min(seats.length, preferenceCount + 1),
    }),
  );
}

function buildSeatTopology(seats: readonly Seat[], anchor: TeachingAnchor): SeatTopology {
  const xStepByValue = axisStepPositions(seats.map((seat) => seat.x));
  const yStepByValue = axisStepPositions(seats.map((seat) => seat.y));
  const xStepBySeat = Object.fromEntries(seats.map((seat) => [seat.id, xStepByValue[seat.x] ?? 0]));
  const yStepBySeat = Object.fromEntries(seats.map((seat) => [seat.id, yStepByValue[seat.y] ?? 0]));
  const maxRowRank = Math.max(0, ...Object.values(yStepByValue));
  const maxColumnRank = Math.max(0, ...Object.values(xStepByValue));
  const frontRankBySeat: Record<string, number> = {};
  const lateralRankBySeat: Record<string, number> = {};
  const actualLateralDistanceBySeat: Record<string, number> = {};

  for (const seat of seats) {
    if (anchor.edge === "top" || anchor.edge === "bottom") {
      frontRankBySeat[seat.id] = anchor.edge === "top"
        ? yStepBySeat[seat.id] ?? 0
        : maxRowRank - (yStepBySeat[seat.id] ?? 0);
      lateralRankBySeat[seat.id] = xStepBySeat[seat.id] ?? 0;
      actualLateralDistanceBySeat[seat.id] = Math.abs(seat.x - anchor.x);
      continue;
    }
    frontRankBySeat[seat.id] = anchor.edge === "left"
      ? xStepBySeat[seat.id] ?? 0
      : maxColumnRank - (xStepBySeat[seat.id] ?? 0);
    lateralRankBySeat[seat.id] = yStepBySeat[seat.id] ?? 0;
    actualLateralDistanceBySeat[seat.id] = Math.abs(seat.y - anchor.y);
  }

  return { frontRankBySeat, lateralRankBySeat, actualLateralDistanceBySeat };
}

function nearTeacherPool(options: {
  seats: readonly Seat[];
  topology: SeatTopology;
  seatCount: number;
}): string[] {
  const rankedSeatIds = options.seats.map((seat) => seat.id).sort((left, right) => {
    return compareNumbers(options.topology.frontRankBySeat[left], options.topology.frontRankBySeat[right])
      || compareNumbers(
        options.topology.actualLateralDistanceBySeat[left],
        options.topology.actualLateralDistanceBySeat[right],
      )
      || compareNumbers(options.topology.lateralRankBySeat[left], options.topology.lateralRankBySeat[right])
      || left.localeCompare(right);
  });
  const expandedFrontBand = rankedSeatIds.filter((seatId) => options.topology.frontRankBySeat[seatId] <= 1);
  return (expandedFrontBand.length >= options.seatCount ? expandedFrontBand : rankedSeatIds)
    .slice(0, options.seatCount);
}

function inferTeachingAnchor(template: RoomTemplate): TeachingAnchor {
  const bounds = roomBounds(template);
  const whiteboards = template.fixtures.filter((fixture) => fixture.type === "whiteboard");
  if (whiteboards.length > 0) {
    return anchorFromFixtures(whiteboards, bounds, 0);
  }
  const teacherDesks = template.fixtures.filter((fixture) => fixture.type === "teacher_desk");
  if (teacherDesks.length > 0) {
    return anchorFromFixtures(teacherDesks, bounds, 0.65);
  }
  return { edge: "top", x: bounds.maxX / 2, y: 0 };
}

function roomBounds(template: RoomTemplate): RoomBounds {
  return {
    maxX: Math.max(
      template.grid_cols ?? 0,
      ...template.seats.map((seat) => seat.x),
      ...template.fixtures.map((fixture) => fixture.x + fixture.width),
    ),
    maxY: Math.max(
      template.grid_rows ?? 0,
      ...template.seats.map((seat) => seat.y),
      ...template.fixtures.map((fixture) => fixture.y + fixture.height),
    ),
  };
}

function anchorFromFixtures(fixtures: readonly RoomFixture[], bounds: RoomBounds, weightToCenter: number): TeachingAnchor {
  const edge = bestWall(fixtures, bounds);
  const averageCenterX = fixtures.reduce((sum, fixture) => sum + fixture.x + fixture.width / 2, 0) / fixtures.length;
  const averageCenterY = fixtures.reduce((sum, fixture) => sum + fixture.y + fixture.height / 2, 0) / fixtures.length;
  const roomCenterX = bounds.maxX / 2;
  const roomCenterY = bounds.maxY / 2;
  if (edge === "top") {
    return { edge, x: mix(roomCenterX, averageCenterX, 1 - weightToCenter), y: 0 };
  }
  if (edge === "bottom") {
    return { edge, x: mix(roomCenterX, averageCenterX, 1 - weightToCenter), y: bounds.maxY };
  }
  if (edge === "left") {
    return { edge, x: 0, y: mix(roomCenterY, averageCenterY, 1 - weightToCenter) };
  }
  return { edge, x: bounds.maxX, y: mix(roomCenterY, averageCenterY, 1 - weightToCenter) };
}

function bestWall(fixtures: readonly RoomFixture[], bounds: RoomBounds): TeachingEdge {
  const scores: Record<TeachingEdge, number> = { top: 0, bottom: 0, left: 0, right: 0 };
  const epsilon = 1e-6;
  for (const fixture of fixtures) {
    const distances: Record<TeachingEdge, number> = {
      top: fixture.y,
      bottom: Math.max(bounds.maxY - (fixture.y + fixture.height), 0),
      left: fixture.x,
      right: Math.max(bounds.maxX - (fixture.x + fixture.width), 0),
    };
    const nearestDistance = Math.min(...Object.values(distances));
    for (const edge of Object.keys(scores) as TeachingEdge[]) {
      if (Math.abs(distances[edge] - nearestDistance) <= epsilon) {
        scores[edge] += 1;
      }
      scores[edge] -= distances[edge] * 0.01;
    }
  }
  return (Object.keys(scores) as TeachingEdge[]).sort((left, right) => {
    return compareNumbers(scores[right], scores[left]) || right.localeCompare(left);
  })[0] ?? "top";
}

function axisStepPositions(values: number[]): Record<number, number> {
  const uniqueValues = [...new Set(values)].sort((left, right) => left - right);
  const stepUnit = axisStepUnit(uniqueValues);
  const origin = uniqueValues[0] ?? 0;
  return Object.fromEntries(uniqueValues.map((value) => [
    value,
    stepUnit > 0 ? Math.round((value - origin) / stepUnit) : 0,
  ]));
}

function axisStepUnit(values: number[]): number {
  const positiveGaps = values
    .slice(1)
    .map((value, index) => value - (values[index] ?? value))
    .filter((gap) => gap > 0);
  return Math.max(positiveGaps.reduce((stepUnit, gap) => greatestCommonDivisor(stepUnit, gap), positiveGaps[0] ?? 1), 1);
}

function greatestCommonDivisor(left: number, right: number): number {
  let a = Math.abs(Math.round(left));
  let b = Math.abs(Math.round(right));
  while (b > 0) {
    [a, b] = [b, a % b];
  }
  return a || 1;
}

function mix(centerValue: number, cueValue: number, cueWeight: number): number {
  return centerValue * (1 - cueWeight) + cueValue * cueWeight;
}

function compareNumbers(left: number | undefined, right: number | undefined): number {
  return (left ?? 0) - (right ?? 0);
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
  seatId: string,
  nearTeacherSeatIds: ReadonlySet<string>,
  studentsById: Readonly<Record<string, Student | undefined>>,
): string {
  const status = nearTeacherSeatIds.has(seatId) ? "uppfylld" : "inte nära läraren";
  return `Nära läraren: ${studentName(studentId, studentsById)} är ${status}.`;
}

function relationshipMarkerLabel(
  rule: RelationshipRule,
  firstStudentId: string,
  secondStudentId: string,
  studentsById: Readonly<Record<string, Student | undefined>>,
): string {
  const ruleLabel = rule.kind === "keep_near" ? "Håll nära" : "Håll isär";
  return `${ruleLabel}: ${studentName(firstStudentId, studentsById)} och ${
    studentName(secondStudentId, studentsById)
  }.`;
}

function relationshipRuleIsSatisfied(
  template: RoomTemplate | null | undefined,
  rule: RelationshipRule,
  firstSeatId: string,
  secondSeatId: string,
): boolean {
  const distance = seatGridDistance(template, firstSeatId, secondSeatId);
  if (distance === null) {
    return false;
  }
  if (rule.kind === "keep_near") {
    return distance.manhattan === 1;
  }
  return Math.max(distance.dx, distance.dy) > 1;
}

function seatGridDistance(
  template: RoomTemplate | null | undefined,
  firstSeatId: string,
  secondSeatId: string,
): { dx: number; dy: number; manhattan: number } | null {
  const first = template?.seats.find((seat) => seat.id === firstSeatId);
  const second = template?.seats.find((seat) => seat.id === secondSeatId);
  if (!first || !second) {
    return null;
  }
  const dx = Math.abs(gridStartFromCoordinate(first.x) - gridStartFromCoordinate(second.x));
  const dy = Math.abs(gridStartFromCoordinate(first.y) - gridStartFromCoordinate(second.y));
  return { dx, dy, manhattan: dx + dy };
}

function gridStartFromCoordinate(value: number): number {
  return Math.max(1, Math.round(value / ROOM_GRID_UNIT) + 1);
}
