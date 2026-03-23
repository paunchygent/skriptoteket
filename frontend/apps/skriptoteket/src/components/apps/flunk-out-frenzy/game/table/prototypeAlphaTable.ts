/**
 * Typed prototype-alpha table definition for Flunk-Out Frenzy.
 *
 * The first playable slice keeps the table authored directly in TypeScript so
 * physics, rules, and host rendering can share one stable source of geometry
 * without introducing a JSON content pipeline yet.
 */

export interface TablePoint {
  x: number;
  y: number;
}

export interface TableWallDefinition {
  from: TablePoint;
  to: TablePoint;
}

export interface TableBumperDefinition {
  tag: string;
  x: number;
  y: number;
  radius: number;
  sensorRadius: number;
  impulse: number;
}

export interface TableSlingDefinition {
  tag: string;
  side: "left" | "right";
  vertices: [TablePoint, TablePoint, TablePoint];
  impulse: TablePoint;
}

export interface TableRolloverDefinition {
  tag: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface TableFlipperDefinition {
  side: "left" | "right";
  pivot: TablePoint;
  length: number;
  thickness: number;
  restAngleDeg: number;
  activeAngleDeg: number;
  assistImpulse: TablePoint;
}

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
    { tag: "lane/top-l", label: "L", x: 180, y: 150, width: 28, height: 28 },
    { tag: "lane/top-a", label: "A", x: 260, y: 130, width: 28, height: 28 },
    { tag: "lane/top-t", label: "T", x: 340, y: 130, width: 28, height: 28 },
    { tag: "lane/top-e", label: "E", x: 420, y: 150, width: 28, height: 28 },
  ] satisfies TableRolloverDefinition[],
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
