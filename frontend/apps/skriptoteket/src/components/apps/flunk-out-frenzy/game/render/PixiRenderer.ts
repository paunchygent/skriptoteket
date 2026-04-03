/**
 * Pixi-powered renderer for Flunk-Out Frenzy.
 *
 * This adapter owns the canvas, draws the live board state, and reacts to
 * semantic effect events with lightweight pulses and lamp updates. Vue never
 * owns the playfield rendering itself.
 */

import {
  Application,
  BlurFilter,
  Container,
  Graphics,
  Text,
} from "pixi.js";

import type { GameHudSnapshot, GameViewSnapshot } from "../core/runtimeTypes";
import type { GameEffectEvent } from "../presentation/gameEffectTypes";
import { PROTOTYPE_ALPHA_TABLE } from "../table/prototypeAlphaTable";
import type { TableTriggerShapeDefinition } from "../table/tableDefinitionTypes";
import type { RuntimeRenderer } from "./renderTypes";
import { buildStaticBoardUnderlay } from "./staticBoardUnderlay";

interface RolloverNode {
  container: Container;
  ring: Graphics;
  label: Text;
}

export class PixiRenderer implements RuntimeRenderer {
  private readonly app = new Application();
  private readonly scene = new Container();
  private readonly underlay = new Container();
  private readonly pulseLayer = new Container();
  private readonly rolloverLayer = new Container();
  private readonly ballGraphic = new Graphics();
  private readonly plungerGraphic = new Graphics();
  private readonly leftFlipperGraphic = new Graphics();
  private readonly rightFlipperGraphic = new Graphics();
  private readonly rolloverNodes = new Map<string, RolloverNode>();
  private hostElement: HTMLElement | null = null;
  private lastCanvasWidth = 0;
  private lastCanvasHeight = 0;

  static async create(): Promise<PixiRenderer> {
    const renderer = new PixiRenderer();
    await renderer.init();
    return renderer;
  }

  private async init(): Promise<void> {
    await this.app.init({
      width: PROTOTYPE_ALPHA_TABLE.board.width,
      height: PROTOTYPE_ALPHA_TABLE.board.height,
      antialias: true,
      autoDensity: true,
      backgroundAlpha: 0,
      preference: "webgl",
      sharedTicker: true,
      autoStart: true,
    });

    this.app.canvas.dataset.test = "runtime-renderer-canvas";
    this.app.canvas.className = "fof-host__canvas";
    this.app.canvas.setAttribute("aria-hidden", "true");
    this.app.canvas.style.position = "absolute";
    this.app.canvas.style.inset = "0";
    this.app.canvas.style.width = "100%";
    this.app.canvas.style.height = "100%";
    this.app.canvas.style.pointerEvents = "none";

    this.scene.eventMode = "none";
    this.app.stage.addChild(this.scene);
    this.scene.addChild(this.underlay);
    this.scene.addChild(this.pulseLayer);
    this.scene.addChild(this.rolloverLayer);
    this.scene.addChild(this.plungerGraphic);
    this.scene.addChild(this.leftFlipperGraphic);
    this.scene.addChild(this.rightFlipperGraphic);
    this.scene.addChild(this.ballGraphic);

    this.drawStaticUnderlay();
    this.buildRolloverNodes();
    this.drawFlipper(this.leftFlipperGraphic, "left");
    this.drawFlipper(this.rightFlipperGraphic, "right");
    this.ballGraphic.visible = false;
    this.plungerGraphic.visible = false;
  }

  attach(hostElement: HTMLElement): void {
    if (this.hostElement === hostElement && this.app.canvas.parentElement === hostElement) {
      this.syncViewport();
      return;
    }

    if (this.app.canvas.parentElement && this.app.canvas.parentElement !== hostElement) {
      this.app.canvas.parentElement.removeChild(this.app.canvas);
    }

    this.hostElement = hostElement;
    hostElement.appendChild(this.app.canvas);
    this.syncViewport();
  }

  render(view: GameViewSnapshot, hud: GameHudSnapshot, effects: GameEffectEvent[]): void {
    this.syncViewport();
    this.syncRollovers(view);
    this.syncPlunger(view);
    this.syncBall(view);
    this.syncFlippers(view);
    this.applyEffects(effects, hud);
  }

  dispose(): void {
    this.rolloverNodes.clear();
    this.hostElement = null;
    this.app.destroy({ removeView: true }, true);
  }

  private drawStaticUnderlay(): void {
    buildStaticBoardUnderlay(this.underlay);
  }

  private buildRolloverNodes(): void {
    for (const rollover of PROTOTYPE_ALPHA_TABLE.rollovers) {
      const ring = new Graphics();
      const label = new Text({
        text: rollover.label,
        style: {
          fill: 0xffee8d,
          fontFamily: '"IBM Plex Sans", sans-serif',
          fontSize: 20,
          fontWeight: "800",
          letterSpacing: 1,
        },
      });

      label.anchor.set(0.5);

      const container = new Container();
      container.position.set(rollover.x, rollover.y);
      container.addChild(ring);
      container.addChild(label);
      this.rolloverLayer.addChild(container);
      this.rolloverNodes.set(rollover.tag, { container, ring, label });
    }
  }

  private syncRollovers(view: GameViewSnapshot): void {
    for (const rollover of view.rollovers) {
      const node = this.rolloverNodes.get(rollover.tag);
      if (!node) {
        continue;
      }

      node.container.position.set(rollover.x, rollover.y);
      node.label.text = rollover.label;
      this.drawRollover(node.ring, rollover.lit);
    }
  }

  private drawRollover(graphic: Graphics, lit: boolean): void {
    graphic.clear();
    graphic.circle(0, 0, 21);
    graphic.fill({
      color: lit ? 0xffee8d : 0x191a15,
      alpha: lit ? 0.78 : 0.36,
    });
    graphic.stroke({
      color: 0xffee8d,
      alpha: lit ? 0.92 : 0.22,
      width: lit ? 2 : 1,
    });

    if (lit) {
      graphic.circle(0, 0, 27);
      graphic.stroke({
        color: 0xffee8d,
        alpha: 0.22,
        width: 7,
      });
    }
  }

  private syncBall(view: GameViewSnapshot): void {
    if (!view.ball) {
      this.ballGraphic.visible = false;
      return;
    }

    this.ballGraphic.visible = true;
    this.ballGraphic.clear();
    this.ballGraphic.circle(0, 0, view.ball.radius);
    this.ballGraphic.fill({
      color: 0xe2e8f0,
    });
    this.ballGraphic.stroke({
      color: 0xffffff,
      alpha: 0.3,
      width: 1.2,
    });
    this.ballGraphic.position.set(view.ball.x, view.ball.y);
  }

  private syncPlunger(view: GameViewSnapshot): void {
    if (!view.plunger) {
      this.plungerGraphic.visible = false;
      return;
    }

    this.plungerGraphic.visible = true;
    this.plungerGraphic.clear();
    this.plungerGraphic.roundRect(
      -view.plunger.width / 2,
      -view.plunger.height / 2,
      view.plunger.width,
      view.plunger.height,
      999,
    );
    this.plungerGraphic.fill({
      color: 0x8c526b,
      alpha: 0.92,
    });
    this.plungerGraphic.stroke({
      color: 0xffd7e8,
      alpha: 0.42,
      width: 1.4,
    });
    this.plungerGraphic.position.set(view.plunger.x, view.plunger.y);
  }

  private syncFlippers(view: GameViewSnapshot): void {
    this.leftFlipperGraphic.position.set(
      view.flippers.left.pivotX,
      view.flippers.left.pivotY,
    );
    this.leftFlipperGraphic.rotation = degreesToRadians(view.flippers.left.angleDeg);

    this.rightFlipperGraphic.position.set(
      view.flippers.right.pivotX,
      view.flippers.right.pivotY,
    );
    this.rightFlipperGraphic.rotation = degreesToRadians(view.flippers.right.angleDeg);
  }

  private drawFlipper(graphic: Graphics, side: "left" | "right"): void {
    const flipper = PROTOTYPE_ALPHA_TABLE.flippers[side];
    const x = side === "left" ? 0 : -flipper.length;

    graphic.clear();
    graphic.roundRect(x, -flipper.thickness / 2, flipper.length, flipper.thickness, 999);
    graphic.fill({ color: 0xff4f96 });
    graphic.stroke({
      color: 0xffd3e5,
      alpha: 0.3,
      width: 1.4,
    });
  }

  private applyEffects(effects: GameEffectEvent[], hud: GameHudSnapshot): void {
    this.app.canvas.dataset.runtimeStatus = hud.status;
    this.app.canvas.dataset.runtimeMuted = String(hud.muted);

    for (const effect of effects) {
      switch (effect.type) {
        case "bumper-hit": {
          const bumper = PROTOTYPE_ALPHA_TABLE.bumpers.find((item) => item.tag === effect.tag);
          if (bumper) {
            this.spawnPulse(bumper.x, bumper.y, 32, 0x69ff7d, 170);
          }
          break;
        }
        case "sling-hit": {
          const sling = PROTOTYPE_ALPHA_TABLE.slings.find((item) => item.tag === effect.tag);
          if (sling) {
            const centroidX =
              (sling.vertices[0].x + sling.vertices[1].x + sling.vertices[2].x) / 3;
            const centroidY =
              (sling.vertices[0].y + sling.vertices[1].y + sling.vertices[2].y) / 3;
            this.spawnPulse(centroidX, centroidY, 26, 0xff8a47, 150);
          }
          break;
        }
        case "rollover-lit": {
          const rollover = PROTOTYPE_ALPHA_TABLE.rollovers.find((item) => item.tag === effect.tag);
          if (rollover) {
            this.spawnPulse(rollover.x, rollover.y, 22, 0xffee8d, 130);
          }
          break;
        }
        case "tripwire-crossed": {
          const tripwire = PROTOTYPE_ALPHA_TABLE.tripwires.find((item) => item.tag === effect.tag);
          if (tripwire) {
            const center = resolveTriggerEffectCenter(tripwire);
            this.spawnPulse(center.x, center.y, 28, 0x6be9ff, 140);
          }
          break;
        }
        case "standup-target-hit": {
          const target = PROTOTYPE_ALPHA_TABLE.standupTargets.find((item) => item.tag === effect.tag);
          if (target) {
            this.spawnPulse(target.x, target.y, 24, 0xffc769, 155);
          }
          break;
        }
        case "popup-target-hit": {
          const target = PROTOTYPE_ALPHA_TABLE.popupTargets.find((item) => item.tag === effect.tag);
          if (target) {
            this.spawnPulse(target.x, target.y, target.radius + 10, 0xff8df0, 165);
          }
          break;
        }
        case "gate-passed": {
          const gate = PROTOTYPE_ALPHA_TABLE.gates.find((item) => item.tag === effect.tag);
          if (gate) {
            const center = resolveTriggerEffectCenter(gate);
            this.spawnPulse(center.x, center.y, 22, 0x9ee081, 130);
          }
          break;
        }
        case "ball-captured": {
          const captureDevice = PROTOTYPE_ALPHA_TABLE.captureDevices.find(
            (item) => item.tag === effect.tag,
          );
          if (captureDevice) {
            this.spawnPulse(
              captureDevice.x,
              captureDevice.y,
              Math.max(captureDevice.width, captureDevice.height) * 0.62,
              0x66f0ff,
              170,
            );
          }
          break;
        }
        case "ball-ejected": {
          const captureDevice = PROTOTYPE_ALPHA_TABLE.captureDevices.find(
            (item) => item.tag === effect.tag,
          );
          if (captureDevice) {
            this.spawnPulse(
              captureDevice.x,
              captureDevice.y,
              Math.max(captureDevice.width, captureDevice.height) * 0.82,
              0xffbf72,
              180,
            );
          }
          break;
        }
        case "ball-saved": {
          const saveDevice = PROTOTYPE_ALPHA_TABLE.saveDevices.find((item) => item.tag === effect.tag);
          if (saveDevice) {
            this.spawnPulse(
              saveDevice.x,
              saveDevice.y,
              Math.max(saveDevice.width, saveDevice.height) * 0.7,
              0x91ffc6,
              175,
            );
          }
          break;
        }
        case "late-bank-complete":
          this.spawnPulse(300, 146, 110, 0xffee8d, 280);
          break;
        case "bonus-awarded":
          this.spawnPulse(300, 1030, 72, 0xffcf7c, 240);
          break;
        case "jackpot-lit":
          this.spawnPulse(300, 250, 48, 0xff8df0, 200);
          break;
        case "jackpot-awarded":
          this.spawnPulse(300, 420, 126, 0xff8df0, 300);
          break;
        case "capture-awarded":
          this.spawnPulse(300, 980, 62, 0x66f0ff, 240);
          break;
        case "eject-awarded":
          this.spawnPulse(300, 900, 56, 0xffbf72, 220);
          break;
        case "save-awarded":
          this.spawnPulse(300, 850, 64, 0x91ffc6, 250);
          break;
        case "shoot-again-lit":
          this.spawnPulse(PROTOTYPE_ALPHA_TABLE.ball.spawn.x, 930, 42, 0x8dffcf, 220);
          break;
        case "ball-drained":
          this.spawnPulse(300, 1136, 54, 0xff5d92, 200);
          break;
        case "ball-spawned":
          this.spawnPulse(PROTOTYPE_ALPHA_TABLE.ball.spawn.x, PROTOTYPE_ALPHA_TABLE.ball.spawn.y, 24, 0xb8c5ff, 150);
          break;
        case "game-over":
          this.spawnPulse(300, 680, 150, 0xff5d92, 360);
          break;
        case "round-started":
        case "flipper-fired":
        case "launch-released":
          break;
      }
    }
  }

  private spawnPulse(
    x: number,
    y: number,
    radius: number,
    color: number,
    durationMs: number,
  ): void {
    const pulse = new Graphics();
    pulse.position.set(x, y);
    pulse.circle(0, 0, radius);
    pulse.stroke({
      color,
      alpha: 0.72,
      width: 4,
    });
    pulse.filters = [new BlurFilter({ strength: 2 })];
    this.pulseLayer.addChild(pulse);

    let elapsedMs = 0;
    const tick = () => {
      elapsedMs += this.app.ticker.deltaMS;

      const progress = Math.min(elapsedMs / durationMs, 1);
      pulse.alpha = 1 - progress;
      pulse.scale.set(1 + progress * 0.92);

      if (progress >= 1) {
        this.app.ticker.remove(tick);
        pulse.destroy();
      }
    };

    this.app.ticker.add(tick);
  }

  private syncViewport(): void {
    if (!this.hostElement) {
      return;
    }

    const width = Math.max(Math.floor(this.hostElement.clientWidth), 1);
    const height = Math.max(Math.floor(this.hostElement.clientHeight), 1);

    if (width !== this.lastCanvasWidth || height !== this.lastCanvasHeight) {
      this.app.renderer.resize(width, height);
      this.lastCanvasWidth = width;
      this.lastCanvasHeight = height;
    }

    const scale = Math.min(
      width / PROTOTYPE_ALPHA_TABLE.board.width,
      height / PROTOTYPE_ALPHA_TABLE.board.height,
    );

    this.scene.scale.set(scale);
    this.scene.position.set(
      Math.round((width - PROTOTYPE_ALPHA_TABLE.board.width * scale) / 2),
      Math.round((height - PROTOTYPE_ALPHA_TABLE.board.height * scale) / 2),
    );
  }
}

function resolveTriggerEffectCenter(
  trigger:
    | (typeof PROTOTYPE_ALPHA_TABLE.tripwires)[number]
    | (typeof PROTOTYPE_ALPHA_TABLE.gates)[number],
): { x: number; y: number } {
  if ("shape" in trigger) {
    return centerForTriggerShape(trigger.shape);
  }

  return {
    x: trigger.x,
    y: trigger.y,
  };
}

function centerForTriggerShape(shape: TableTriggerShapeDefinition): {
  x: number;
  y: number;
} {
  switch (shape.kind) {
    case "rect":
    case "circle":
    case "capsule":
    case "donor-wire-rollover":
      return shape.center;
    case "polygon":
      return polygonCentroid(shape.points);
  }
}

function polygonCentroid(points: readonly { x: number; y: number }[]): { x: number; y: number } {
  const count = points.length || 1;
  return {
    x: points.reduce((sum, point) => sum + point.x, 0) / count,
    y: points.reduce((sum, point) => sum + point.y, 0) / count,
  };
}

function degreesToRadians(deg: number): number {
  return (deg * Math.PI) / 180;
}
