import { v } from "../pinballTableMath";
import {
  VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC,
  VPW_LEFT_DROP_BANK_SPECS,
  VPW_POPUP_TARGET_SPECS,
  VPW_RIGHT_RETURN_TRIGGER_SPEC,
  VPW_TOP_ROLLOVER_SPECS,
} from "../prototypeAlphaVpwDonorDevices";
import type {
  TableCaptureDeviceDefinition,
  TableGateDefinition,
  TablePopupTargetDefinition,
  TableRolloverDefinition,
  TableSaveDeviceDefinition,
  TableStandupTargetDefinition,
  TableTripwireDefinition,
} from "../tableDefinitionTypes";

export const ALPHA_ROLLOVERS: readonly TableRolloverDefinition[] = [
  {
    tag: "lane/top-l",
    label: "L",
    x: VPW_TOP_ROLLOVER_SPECS.leftOrbit.center.x,
    y: VPW_TOP_ROLLOVER_SPECS.leftOrbit.center.y,
    width: VPW_TOP_ROLLOVER_SPECS.leftOrbit.width,
    height: VPW_TOP_ROLLOVER_SPECS.leftOrbit.height,
    bankTag: "bank/late-top",
  },
  {
    tag: "lane/top-a",
    label: "A",
    x: VPW_TOP_ROLLOVER_SPECS.topLeft.center.x,
    y: VPW_TOP_ROLLOVER_SPECS.topLeft.center.y,
    width: VPW_TOP_ROLLOVER_SPECS.topLeft.width,
    height: VPW_TOP_ROLLOVER_SPECS.topLeft.height,
    bankTag: "bank/late-top",
  },
  {
    tag: "lane/top-t",
    label: "T",
    x: VPW_TOP_ROLLOVER_SPECS.topMiddle.center.x,
    y: VPW_TOP_ROLLOVER_SPECS.topMiddle.center.y,
    width: VPW_TOP_ROLLOVER_SPECS.topMiddle.width,
    height: VPW_TOP_ROLLOVER_SPECS.topMiddle.height,
    bankTag: "bank/late-top",
  },
  {
    tag: "lane/top-e",
    label: "E",
    x: VPW_TOP_ROLLOVER_SPECS.topRight.center.x,
    y: VPW_TOP_ROLLOVER_SPECS.topRight.center.y,
    width: VPW_TOP_ROLLOVER_SPECS.topRight.width,
    height: VPW_TOP_ROLLOVER_SPECS.topRight.height,
    bankTag: "bank/late-top",
  },
];

export const ALPHA_TRIPWIRES: readonly TableTripwireDefinition[] = [
  {
    tag: "tripwire/right-orbit-return",
    shape: VPW_RIGHT_RETURN_TRIGGER_SPEC.shape,
    triggerPhase: VPW_RIGHT_RETURN_TRIGGER_SPEC.triggerPhase,
    laneTag: "lane/right-orbit-return",
  },
];

export const ALPHA_GATES: readonly TableGateDefinition[] = [
  {
    tag: "gate/launch-lane-exit",
    shape: VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.shape,
    triggerPhase: VPW_LAUNCH_LANE_EXIT_TRIGGER_SPEC.triggerPhase,
    laneTag: "lane/launch-exit",
  },
];

export const ALPHA_STANDUP_TARGETS: readonly TableStandupTargetDefinition[] = [
  {
    tag: "target/jock-left",
    x: VPW_LEFT_DROP_BANK_SPECS.left.center.x,
    y: VPW_LEFT_DROP_BANK_SPECS.left.center.y,
    width: VPW_LEFT_DROP_BANK_SPECS.left.width,
    height: VPW_LEFT_DROP_BANK_SPECS.left.height,
    angleDeg: VPW_LEFT_DROP_BANK_SPECS.left.angleDeg,
    bankTag: "bank/jocks",
  },
  {
    tag: "target/jock-center",
    x: VPW_LEFT_DROP_BANK_SPECS.center.center.x,
    y: VPW_LEFT_DROP_BANK_SPECS.center.center.y,
    width: VPW_LEFT_DROP_BANK_SPECS.center.width,
    height: VPW_LEFT_DROP_BANK_SPECS.center.height,
    angleDeg: VPW_LEFT_DROP_BANK_SPECS.center.angleDeg,
    bankTag: "bank/jocks",
  },
  {
    tag: "target/jock-right",
    x: VPW_LEFT_DROP_BANK_SPECS.right.center.x,
    y: VPW_LEFT_DROP_BANK_SPECS.right.center.y,
    width: VPW_LEFT_DROP_BANK_SPECS.right.width,
    height: VPW_LEFT_DROP_BANK_SPECS.right.height,
    angleDeg: VPW_LEFT_DROP_BANK_SPECS.right.angleDeg,
    bankTag: "bank/jocks",
  },
];

export const ALPHA_POPUP_TARGETS: readonly TablePopupTargetDefinition[] = [
  {
    tag: "target/pop-study",
    x: VPW_POPUP_TARGET_SPECS.middleScoop.center.x,
    y: VPW_POPUP_TARGET_SPECS.middleScoop.center.y,
    radius: VPW_POPUP_TARGET_SPECS.middleScoop.radius,
    sensorRadius: VPW_POPUP_TARGET_SPECS.middleScoop.sensorRadius,
    bankTag: "bank/study-pop",
  },
];

export const ALPHA_CAPTURE_DEVICES: readonly TableCaptureDeviceDefinition[] = [
  {
    tag: "capture/scoop-study",
    kind: "hole",
    x: VPW_POPUP_TARGET_SPECS.middleScoop.center.x,
    y: VPW_POPUP_TARGET_SPECS.middleScoop.center.y,
    width: 56,
    height: 56,
    holdMs: 560,
    cooldownMs: 900,
    ejectImpulse: v(-120, -1120),
  },
];

export const ALPHA_SAVE_DEVICES: readonly TableSaveDeviceDefinition[] = [
  {
    tag: "save/right-kickback",
    kind: "kickback",
    x: 462,
    y: 1018,
    width: 62,
    height: 38,
    cooldownMs: 650,
    saveImpulse: v(-420, -560),
  },
];
