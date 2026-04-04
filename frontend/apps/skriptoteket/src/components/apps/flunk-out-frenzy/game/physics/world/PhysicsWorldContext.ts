import RAPIER3D from "@dimforge/rapier3d-compat";
import type { PrototypeAlphaTable } from "../../table/prototypeAlphaTable";
import type {
  TableCaptureDeviceDefinition,
  TableSaveDeviceDefinition,
} from "../../table/tableDefinitionTypes";
import type { ColliderMeta } from "../colliderMeta";
import type { CaptureLifecycleState } from "../captureDeviceLifecycle";
import type { MachineEvent } from "../physicsTypes";
import type { PlungerLaneState } from "../plungerLaneState";
import type { LauncherChain3D } from "../launcherChain3d";

export interface PhysicsWorldContext {
  readonly table: PrototypeAlphaTable;
  readonly world: RAPIER3D.World;
  readonly eventQueue: RAPIER3D.EventQueue;
  launcherChain: LauncherChain3D | null;

  // Rigid Bodies
  ballBody: RAPIER3D.RigidBody | null;
  ballColliderHandle: number | null;
  leftFlipper: RAPIER3D.RigidBody;
  rightFlipper: RAPIER3D.RigidBody;

  // Input State
  leftPressed: boolean;
  rightPressed: boolean;
  launchPressed: boolean;
  wasLeftPressed: boolean;
  wasRightPressed: boolean;

  // Simulation State
  leftFlipperAngleRad: number;
  rightFlipperAngleRad: number;
  plungerLaneState: PlungerLaneState;
  currentPlungerCenterY: number;
  traceStepIndex: number;
  lastStepDtMs: number;
  lastStepEvents: MachineEvent[];
  lastHandoffToBoardStep: number | null;
  firstBoardCollisionStep: number | null;
  boardCollisionStartedThisStep: boolean;

  // Metadata/Indices
  readonly cooldowns: Map<string, number>;
  readonly captureDevicesByTag: ReadonlyMap<string, TableCaptureDeviceDefinition>;
  readonly saveDevicesByTag: ReadonlyMap<string, TableSaveDeviceDefinition>;
  readonly colliderMetaByHandle: Map<number, ColliderMeta>;
  readonly captureLifecycleState: CaptureLifecycleState;
}
