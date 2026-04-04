import { v } from "../pinballTableMath";
import {
  VPW_BUMPER_CENTERS,
  VPW_LEFT_SLING_TRIANGLE,
  VPW_RIGHT_SLING_TRIANGLE,
} from "../prototypeAlphaVpwDonorMap";
import type {
  TableBumperDefinition,
  TableSlingDefinition,
} from "../tableDefinitionTypes";

export const ALPHA_BUMPERS: readonly TableBumperDefinition[] = [
  {
    tag: "bumper/pop-top",
    x: VPW_BUMPER_CENTERS.top.x,
    y: VPW_BUMPER_CENTERS.top.y,
    radius: 30,
    sensorRadius: 40,
    impulse: 420,
  },
  {
    tag: "bumper/pop-left",
    x: VPW_BUMPER_CENTERS.left.x,
    y: VPW_BUMPER_CENTERS.left.y,
    radius: 30,
    sensorRadius: 40,
    impulse: 420,
  },
  {
    tag: "bumper/pop-right",
    x: VPW_BUMPER_CENTERS.right.x,
    y: VPW_BUMPER_CENTERS.right.y,
    radius: 30,
    sensorRadius: 40,
    impulse: 420,
  },
];

export const ALPHA_SLINGS: readonly TableSlingDefinition[] = [
  {
    tag: "sling/left",
    side: "left",
    vertices: [...VPW_LEFT_SLING_TRIANGLE],
    impulse: v(260, -460),
  },
  {
    tag: "sling/right",
    side: "right",
    vertices: [...VPW_RIGHT_SLING_TRIANGLE],
    impulse: v(-260, -460),
  },
];
