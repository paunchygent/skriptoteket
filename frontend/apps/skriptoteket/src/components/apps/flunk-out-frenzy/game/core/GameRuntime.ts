/**
 * Browser-owned runtime core for Flunk-Out Frenzy.
 *
 * The runtime owns session lifecycle, command draining, and the authoritative
 * HUD plus playfield view projections for the current game slice. Vue only
 * subscribes to published snapshots while the composed prototype-alpha engine
 * owns physics and rules behind a narrower simulation boundary.
 */

import { PrototypeAlphaGameEngine } from "../engine/PrototypeAlphaGameEngine";
import type { MachineEvent } from "../physics/physicsTypes";
import { CommandQueue } from "./CommandQueue";
import { FixedStepRunner } from "./FixedStepRunner";
import type { RuntimeEngine, RuntimeEngineState } from "./runtimeEngineTypes";
import {
  createBrowserAnimationScheduler,
  createInitialHudSnapshot,
  createInitialInputState,
  describeRuntimeCommand,
  type AnimationScheduler,
  type GameHudSnapshot,
  type GameViewSnapshot,
  type RuntimeCommand,
} from "./runtimeTypes";

export interface GameRuntimeOptions {
  stepHz?: number;
  scheduler?: AnimationScheduler;
  engine?: RuntimeEngine;
}

export class GameRuntime {
  private readonly hudListeners = new Set<(hud: GameHudSnapshot) => void>();
  private readonly viewListeners = new Set<(view: GameViewSnapshot) => void>();
  private readonly commandQueue = new CommandQueue<RuntimeCommand>();
  private readonly runner: FixedStepRunner;
  private readonly engine: RuntimeEngine;
  private hostElement: HTMLElement | null = null;
  private hudSnapshot: GameHudSnapshot;
  private viewSnapshot: GameViewSnapshot;
  private inputState = createInitialInputState();

  static async create(options: Omit<GameRuntimeOptions, "engine"> = {}): Promise<GameRuntime> {
    return new GameRuntime({
      ...options,
      engine: await PrototypeAlphaGameEngine.create(),
    });
  }

  constructor(options: GameRuntimeOptions = {}) {
    const stepHz = options.stepHz ?? 120;
    const scheduler = options.scheduler ?? createBrowserAnimationScheduler();

    if (!options.engine) {
      throw new Error("GameRuntime requires an engine. Use GameRuntime.create() for the default runtime.");
    }

    this.engine = options.engine;

    const initialState = this.engine.currentState();
    this.hudSnapshot = this.stateToHudSnapshot(initialState, "ready");
    this.viewSnapshot = initialState.view;

    this.runner = new FixedStepRunner(1000 / stepHz, this.onFixedStep, scheduler);
  }

  mount(hostElement: HTMLElement): void {
    this.hostElement = hostElement;
    this.applyHostState();
  }

  start(): void {
    const nextState = this.engine.startGame();
    this.inputState = createInitialInputState();
    this.commandQueue.clear();
    this.applyEngineState(nextState, "running");
    this.runner.start();
  }

  pause(): void {
    if (this.hudSnapshot.status !== "running") {
      return;
    }

    this.hudSnapshot = {
      ...this.hudSnapshot,
      status: "paused",
    };
    this.runner.stop();
    this.publishHud();
    this.applyHostState();
  }

  resume(): void {
    if (this.hudSnapshot.status !== "paused") {
      return;
    }

    this.hudSnapshot = {
      ...this.hudSnapshot,
      status: "running",
    };
    this.runner.start();
    this.publishHud();
    this.applyHostState();
  }

  restart(): void {
    const nextState = this.engine.restartGame();
    this.inputState = createInitialInputState();
    this.commandQueue.clear();
    this.applyEngineState(nextState, "running");
    this.runner.start();
  }

  setMuted(muted: boolean): void {
    if (this.hudSnapshot.muted === muted) {
      return;
    }

    this.hudSnapshot = {
      ...this.hudSnapshot,
      muted,
    };
    this.publishHud();
    this.applyHostState();
  }

  enqueueCommand(command: RuntimeCommand): void {
    this.commandQueue.push(command);

    if (!this.runner.isRunning()) {
      this.processPendingCommands();
    }
  }

  subscribeHud(listener: (hud: GameHudSnapshot) => void): () => void {
    this.hudListeners.add(listener);
    listener(this.hudSnapshot);
    return () => {
      this.hudListeners.delete(listener);
    };
  }

  subscribeView(listener: (view: GameViewSnapshot) => void): () => void {
    this.viewListeners.add(listener);
    listener(this.viewSnapshot);
    return () => {
      this.viewListeners.delete(listener);
    };
  }

  dispose(): void {
    this.runner.stop();
    this.commandQueue.clear();
    this.engine.dispose();

    if (this.hostElement) {
      delete this.hostElement.dataset.runtimeMounted;
      delete this.hostElement.dataset.runtimeStatus;
      delete this.hostElement.dataset.runtimeMuted;
      delete this.hostElement.dataset.leftFlipActive;
      delete this.hostElement.dataset.rightFlipActive;
      delete this.hostElement.dataset.launchActive;
      delete this.hostElement.dataset.lastCommand;
      delete this.hostElement.dataset.ballPresent;
      delete this.hostElement.dataset.runtimeScore;
      delete this.hostElement.dataset.runtimeBallsRemaining;
      delete this.hostElement.dataset.runtimeMultiplier;
    }

    this.hostElement = null;
  }

  injectMachineEventsForDebug(events: MachineEvent[]): void {
    if (typeof this.engine.injectMachineEventsForDebug !== "function") {
      throw new Error("Runtime engine does not support debug machine-event injection.");
    }

    const nextState = this.engine.injectMachineEventsForDebug(events);
    const nextStatus = nextState.roundFinished ? "game-over" : this.hudSnapshot.status;
    this.applyEngineState(nextState, nextStatus);
  }

  private readonly onFixedStep = (dtMs: number): void => {
    this.processPendingCommands();

    if (this.hudSnapshot.status !== "running") {
      this.applyHostState();
      return;
    }

    const nextState = this.engine.step(dtMs);
    const nextStatus = nextState.roundFinished ? "game-over" : "running";
    this.applyEngineState(nextState, nextStatus);

    if (nextState.roundFinished) {
      this.runner.stop();
    }
  };

  private processPendingCommands(): void {
    const pendingCommands = this.commandQueue.drain();

    if (pendingCommands.length === 0) {
      return;
    }

    for (const command of pendingCommands) {
      if (command.type === "left-flip") {
        this.inputState.leftFlipPressed = command.pressed;
      } else if (command.type === "right-flip") {
        this.inputState.rightFlipPressed = command.pressed;
      } else {
        this.inputState.launchPressed = command.pressed;
      }

      this.inputState.lastCommandLabel = describeRuntimeCommand(command);
      this.engine.applyCommand(command);
    }

    this.applyEngineState(this.engine.currentState(), this.hudSnapshot.status);
  }

  private applyEngineState(
    state: RuntimeEngineState,
    status: GameHudSnapshot["status"],
  ): void {
    this.hudSnapshot = this.stateToHudSnapshot(state, status);
    this.viewSnapshot = state.view;
    this.publishHud();
    this.publishView();
    this.applyHostState();
  }

  private stateToHudSnapshot(
    state: RuntimeEngineState,
    status: GameHudSnapshot["status"],
  ): GameHudSnapshot {
    return {
      ...createInitialHudSnapshot(),
      muted: this.hudSnapshot?.muted ?? false,
      score: state.score,
      ballsRemaining: state.ballsRemaining,
      multiplier: state.multiplier,
      status,
    };
  }

  private publishHud(): void {
    for (const listener of this.hudListeners) {
      listener(this.hudSnapshot);
    }
  }

  private publishView(): void {
    for (const listener of this.viewListeners) {
      listener(this.viewSnapshot);
    }
  }

  private applyHostState(): void {
    if (!this.hostElement) {
      return;
    }

    this.hostElement.dataset.runtimeMounted = "true";
    this.hostElement.dataset.runtimeStatus = this.hudSnapshot.status;
    this.hostElement.dataset.runtimeMuted = String(this.hudSnapshot.muted);
    this.hostElement.dataset.leftFlipActive = String(this.inputState.leftFlipPressed);
    this.hostElement.dataset.rightFlipActive = String(this.inputState.rightFlipPressed);
    this.hostElement.dataset.launchActive = String(this.inputState.launchPressed);
    this.hostElement.dataset.lastCommand = this.inputState.lastCommandLabel;
    this.hostElement.dataset.ballPresent = String(this.viewSnapshot.ball !== null);
    this.hostElement.dataset.runtimeScore = String(this.hudSnapshot.score);
    this.hostElement.dataset.runtimeBallsRemaining = String(this.hudSnapshot.ballsRemaining);
    this.hostElement.dataset.runtimeMultiplier = String(this.hudSnapshot.multiplier);
  }
}
