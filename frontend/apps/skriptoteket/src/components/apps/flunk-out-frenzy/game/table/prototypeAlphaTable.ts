/**
 * Typed prototype-alpha table definition for Flunk-Out Frenzy.
 *
 * The first playable slice keeps the table authored directly in TypeScript so
 * physics, rules, and host rendering can share one stable source of geometry
 * without introducing a JSON content pipeline yet.
 */

import type {
  TableBumperDefinition,
  TableFlipperDefinition,
  TableGateDefinition,
  TablePopupTargetDefinition,
  TableRolloverDefinition,
  TableSlingDefinition,
  TableStandupTargetDefinition,
  TableTripwireDefinition,
  TableWallDefinition,
} from "./tableDefinitionTypes";

export const PROTOTYPE_ALPHA_TABLE = {
  id: "prototype-alpha",
  board: {
    width: 600,
    height: 1200,
    displayAspectRatio: 0.76,
  },
  ballsPerGame: 3,
  gravity: {
    x: 0,
    y: 981,
  },
  ball: {
    radius: 12,
    spawn: {
      x: 528,
      y: 1044,
    },
    mass: 1,
    launchImpulseMin: 980,
    launchImpulseMax: 1820,
    launchAssistX: -110,
  },
  flippers: {
    left: {
      side: "left",
      pivot: { x: 220, y: 1045 },
      length: 96,
      thickness: 20,
      restAngleDeg: 18,
      activeAngleDeg: -24,
      assistImpulse: { x: 320, y: -760 },
    },
    right: {
      side: "right",
      pivot: { x: 380, y: 1045 },
      length: 96,
      thickness: 20,
      restAngleDeg: 162,
      activeAngleDeg: 204,
      assistImpulse: { x: -320, y: -760 },
    },
  } satisfies Record<"left" | "right", TableFlipperDefinition>,
  bumpers: [
    {
      tag: "bumper/pop-top",
      x: 300,
      y: 350,
      radius: 30,
      sensorRadius: 40,
      impulse: 420,
    },
    {
      tag: "bumper/pop-left",
      x: 220,
      y: 450,
      radius: 30,
      sensorRadius: 40,
      impulse: 420,
    },
    {
      tag: "bumper/pop-right",
      x: 380,
      y: 450,
      radius: 30,
      sensorRadius: 40,
      impulse: 420,
    },
  ] satisfies TableBumperDefinition[],
  slings: [
    {
      tag: "sling/left",
      side: "left",
      vertices: [
        { x: 160, y: 860 },
        { x: 242, y: 962 },
        { x: 160, y: 962 },
      ],
      impulse: { x: 260, y: -460 },
    },
    {
      tag: "sling/right",
      side: "right",
      vertices: [
        { x: 440, y: 860 },
        { x: 358, y: 962 },
        { x: 440, y: 962 },
      ],
      impulse: { x: -260, y: -460 },
    },
  ] satisfies TableSlingDefinition[],
  rollovers: [
    { tag: "lane/top-l", label: "L", x: 180, y: 150, width: 28, height: 28, bankTag: "bank/late-top" },
    { tag: "lane/top-a", label: "A", x: 260, y: 130, width: 28, height: 28, bankTag: "bank/late-top" },
    { tag: "lane/top-t", label: "T", x: 340, y: 130, width: 28, height: 28, bankTag: "bank/late-top" },
    { tag: "lane/top-e", label: "E", x: 420, y: 150, width: 28, height: 28, bankTag: "bank/late-top" },
  ] satisfies TableRolloverDefinition[],
  tripwires: [
    {
      tag: "tripwire/right-orbit-return",
      x: 518,
      y: 438,
      width: 24,
      height: 132,
      laneTag: "lane/right-orbit-return",
    },
  ] satisfies TableTripwireDefinition[],
  gates: [
    {
      tag: "gate/launch-lane-exit",
      x: 518,
      y: 792,
      width: 22,
      height: 120,
      laneTag: "lane/launch-exit",
    },
  ] satisfies TableGateDefinition[],
  standupTargets: [
    {
      tag: "target/jock-left",
      x: 188,
      y: 612,
      width: 18,
      height: 64,
      angleDeg: -8,
      bankTag: "bank/jocks",
    },
    {
      tag: "target/jock-center",
      x: 300,
      y: 568,
      width: 18,
      height: 68,
      bankTag: "bank/jocks",
    },
    {
      tag: "target/jock-right",
      x: 412,
      y: 612,
      width: 18,
      height: 64,
      angleDeg: 8,
      bankTag: "bank/jocks",
    },
  ] satisfies TableStandupTargetDefinition[],
  popupTargets: [
    {
      tag: "target/pop-study",
      x: 300,
      y: 250,
      radius: 18,
      sensorRadius: 26,
      bankTag: "bank/study-pop",
    },
  ] satisfies TablePopupTargetDefinition[],
  drain: {
    tag: "drain/main",
    x: 300,
    y: 1164,
    width: 136,
    height: 44,
  },
  walls: [
    { from: { x: 108, y: 112 }, to: { x: 492, y: 112 } },
    { from: { x: 108, y: 112 }, to: { x: 72, y: 930 } },
    { from: { x: 492, y: 112 }, to: { x: 528, y: 912 } },
    { from: { x: 474, y: 112 }, to: { x: 474, y: 1090 } },
    { from: { x: 562, y: 112 }, to: { x: 562, y: 1116 } },
    { from: { x: 474, y: 1100 }, to: { x: 562, y: 1100 } },
    { from: { x: 72, y: 930 }, to: { x: 188, y: 1088 } },
    { from: { x: 528, y: 912 }, to: { x: 412, y: 1088 } },
    { from: { x: 56, y: 1112 }, to: { x: 176, y: 1112 } },
    { from: { x: 424, y: 1112 }, to: { x: 562, y: 1112 } },
    { from: { x: 244, y: 1056 }, to: { x: 300, y: 1138 } },
    { from: { x: 356, y: 1056 }, to: { x: 300, y: 1138 } },
  ] satisfies TableWallDefinition[],
} as const;

export const PROTOTYPE_ALPHA_LATE_TAGS = PROTOTYPE_ALPHA_TABLE.rollovers.map(
  (rollover) => rollover.tag,
);

export type PrototypeAlphaTable = typeof PROTOTYPE_ALPHA_TABLE;
