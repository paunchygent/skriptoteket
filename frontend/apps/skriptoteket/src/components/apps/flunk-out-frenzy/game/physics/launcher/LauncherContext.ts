import RAPIER3D from "@dimforge/rapier3d-compat";
import type {
  TableBallDefinition,
  TableLauncherDefinition,
  TableLauncherObservationSpine3DDefinition,
  TablePoint3D,
} from "../../table/tableDefinitionTypes";
import type { CompiledLauncherWorldPlan } from "../../table/pinballTablePlanTypes";
import type {
  LauncherRouteCaptureDecision,
  LauncherRouteCaptureRejectReason,
  PhysicsLauncherSeamTransitionSnapshot,
} from "../physicsTypes";

export interface ActiveTravelRoute {
  route: TableLauncherObservationSpine3DDefinition;
  cumulativeDistances: readonly number[];
  totalDistance: number;
  distance: number;
  speed: number;
}

export interface LauncherContext {
  readonly world: RAPIER3D.World;
  readonly launcher: TableLauncherDefinition;
  readonly launcherWorld: CompiledLauncherWorldPlan;
  readonly ball: TableBallDefinition;
  readonly plungerBody: RAPIER3D.RigidBody;
  ballBody: RAPIER3D.RigidBody | null;
  readonly parkCenter: TablePoint3D;
  readonly releasePlaneY: number;

  // Mutable State
  currentPlungerCenterY: number;
  currentPlungerVelocityY: number;
  currentPlungerTargetY: number;
  exitInside: boolean;
  feedInside: boolean;
  boardHandoffArmed: boolean;
  activeTravelRoute: ActiveTravelRoute | null;
  pendingReleaseChargeRatio: number | null;
  pendingReleaseNeedsSw16Exit: boolean;
  routeCaptureWindowMsRemaining: number;
  stepCounter: number;
  lastSw16ExitStep: number | null;
  lastRouteCaptureDecision: LauncherRouteCaptureDecision;
  lastRouteCaptureRejectReason: LauncherRouteCaptureRejectReason;
  plungerBallContactActive: boolean;
  contactEnteredThisStep: boolean;
  contactExitedThisStep: boolean;
  separationPx: number | null;
  overlapPx: number;
  relativeVyAtContact: number | null;
  lastContactAtStep: number | null;
  impulseTransferMarker: number;
  releaseIntegrationWindowMsRemaining: number;
  seamTransition: PhysicsLauncherSeamTransitionSnapshot | null;
}
