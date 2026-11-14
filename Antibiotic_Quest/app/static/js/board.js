/* global Phaser */
// The game board: a 30-square snakes-and-ladders "culture slide" drawn with Phaser.
// Superbug colonies sit on gate squares; answering a gate's question clears it (ladder)
// or lets it escape (snake).

const W = 720, H = 608;
const COLS = 6, ROWS = 5, X0 = 24, Y0 = 24, CW = 112, CH = 112;
const C = {
  violet: 0x4a2c7a, violetInk: 0x241640, lilac: 0xefeaf7, lilac2: 0xf8f6fb, white: 0xffffff,
  safranin: 0xd6457a, iodine: 0xe2a12b, malachite: 0x1f8a5b, muted: 0x8d82a3,
};
const REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const dur = (ms) => (REDUCED ? 0 : ms);

export function cellXY(n) {
  const i = n - 1;
  const row = Math.floor(i / COLS);
  let col = i % COLS;
  if (row % 2 === 1) col = COLS - 1 - col;
  return { x: X0 + col * CW + CW / 2, y: Y0 + (ROWS - 1 - row) * CH + CH / 2 };
}

class BoardScene extends Phaser.Scene {
  constructor() { super("board"); }

  create() {
    this.makeTextures();
    this.layerCells = this.add.container(0, 0);
    this.layerPaths = this.add.graphics();
    this.layerBugs = this.add.container(0, 0);
    this.token = this.add.image(0, 0, "token").setDepth(10);
    this.bugs = {};
    this.events.emit("ready-internal");
  }

  makeTextures() {
    const g = this.make.graphics({ x: 0, y: 0, add: false });
    // superbug colony: spiky safranin blob with eyes
    const R = 24, S = 64;
    g.fillStyle(C.safranin, 1);
    for (let k = 0; k < 12; k++) {
      const a = (Math.PI * 2 * k) / 12;
      g.fillCircle(S / 2 + Math.cos(a) * (R + 3), S / 2 + Math.sin(a) * (R + 3), 6);
    }
    g.fillCircle(S / 2, S / 2, R);
    g.fillStyle(C.white, 1);
    g.fillCircle(S / 2 - 8, S / 2 - 4, 6);
    g.fillCircle(S / 2 + 8, S / 2 - 4, 6);
    g.fillStyle(C.violetInk, 1);
    g.fillCircle(S / 2 - 7, S / 2 - 2, 3);
    g.fillCircle(S / 2 + 9, S / 2 - 2, 3);
    g.lineStyle(3, C.violetInk, 1);
    g.beginPath();
    g.arc(S / 2, S / 2 + 6, 7, Math.PI * 0.15, Math.PI * 0.85, false);
    g.strokePath();
    g.generateTexture("bug", S, S);
    g.clear();
    // cleared colony: malachite disc with a check
    g.fillStyle(C.malachite, 1);
    g.fillCircle(S / 2, S / 2, 22);
    g.lineStyle(6, C.white, 1);
    g.beginPath();
    g.moveTo(S / 2 - 10, S / 2 + 1);
    g.lineTo(S / 2 - 2, S / 2 + 9);
    g.lineTo(S / 2 + 12, S / 2 - 8);
    g.strokePath();
    g.generateTexture("cleared", S, S);
    g.clear();
    // player token: an immune cell (white cell, violet membrane, lilac nucleus)
    const T = 48;
    g.fillStyle(C.violet, 1);
    g.fillCircle(T / 2, T / 2, 21);
    g.fillStyle(C.white, 1);
    g.fillCircle(T / 2, T / 2, 16);
    g.fillStyle(0xb9a6dc, 1);
    g.fillCircle(T / 2 - 4, T / 2 - 2, 6);
    g.fillCircle(T / 2 + 4, T / 2 + 3, 6);
    g.generateTexture("token", T, T);
    g.destroy();
  }

  drawLevel(cfg) {
    this.layerCells.removeAll(true);
    this.layerBugs.removeAll(true);
    this.layerPaths.clear();
    this.bugs = {};
    const frame = this.add.graphics();
    frame.fillStyle(C.white, 1);
    frame.fillRoundedRect(X0 - 12, Y0 - 12, COLS * CW + 24, ROWS * CH + 24, 18);
    frame.lineStyle(3, C.violet, 1);
    frame.strokeRoundedRect(X0 - 12, Y0 - 12, COLS * CW + 24, ROWS * CH + 24, 18);
    this.layerCells.add(frame);
    const gates = new Set(cfg.gates);
    for (let n = 1; n <= cfg.cells; n++) {
      const { x, y } = cellXY(n);
      const g = this.add.graphics();
      const isGate = gates.has(n);
      const fill = isGate ? 0xfbe3ec : (n % 2 ? C.lilac : C.lilac2);
      g.fillStyle(fill, 1);
      g.fillRoundedRect(x - CW / 2 + 2, y - CH / 2 + 2, CW - 4, CH - 4, 10);
      if (n === cfg.cells) {
        g.fillStyle(C.iodine, 1);
        g.fillRoundedRect(x - CW / 2 + 2, y - CH / 2 + 2, CW - 4, CH - 4, 10);
      }
      this.layerCells.add(g);
      const label = n === 1 ? (cfg.startLabel || "Start") : n === cfg.cells ? (cfg.exitLabel || "Exit") : String(n);
      const txt = this.add.text(x - CW / 2 + 10, y - CH / 2 + 6, label, {
        fontFamily: '"Baloo 2", system-ui, sans-serif', fontSize: n === 1 || n === cfg.cells ? "20px" : "18px",
        fontStyle: "600", color: n === cfg.cells ? "#241640" : "#6f6490",
      });
      this.layerCells.add(txt);
      if (isGate) {
        const bug = this.add.image(x + 14, y + 10, "bug").setScale(0.95);
        this.layerBugs.add(bug);
        this.bugs[n] = bug;
        if (!REDUCED) {
          this.tweens.add({ targets: bug, scale: 1.04, duration: 900 + Math.random() * 400, yoyo: true,
            repeat: -1, ease: "Sine.easeInOut" });
        }
      }
    }
    this.placeToken(1);
  }

  placeToken(n) {
    const { x, y } = cellXY(n);
    this.token.setPosition(x - 22, y + 22);
  }

  tween(cfg) {
    return new Promise((resolve) => {
      if (REDUCED) {
        Object.entries(cfg).forEach(([k, v]) => {
          if (typeof v === "number" && cfg.targets && k !== "duration") cfg.targets[k] = v;
        });
        resolve();
        return;
      }
      this.tweens.add({ ...cfg, onComplete: () => resolve() });
    });
  }

  async walk(path) {
    for (const n of path) {
      const { x, y } = cellXY(n);
      await this.tween({ targets: this.token, x: x - 22, y: y + 22, duration: dur(170), ease: "Quad.easeOut" });
    }
  }

  async ladder(from, to) {
    const a = cellXY(from), b = cellXY(to);
    const g = this.layerPaths;
    g.clear();
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
    const nx = (-dy / len) * 10, ny = (dx / len) * 10;
    g.lineStyle(5, C.iodine, 1);
    g.lineBetween(a.x - nx, a.y - ny, b.x - nx, b.y - ny);
    g.lineBetween(a.x + nx, a.y + ny, b.x + nx, b.y + ny);
    const rungs = Math.max(3, Math.round(len / 24));
    for (let i = 1; i < rungs; i++) {
      const t = i / rungs;
      g.lineBetween(a.x - nx + dx * t, a.y - ny + dy * t, a.x + nx + dx * t, a.y + ny + dy * t);
    }
    g.setAlpha(1);
    await this.tween({ targets: this.token, x: b.x - 22, y: b.y + 22, duration: dur(650), ease: "Cubic.easeInOut" });
    await this.tween({ targets: g, alpha: 0, duration: dur(500), delay: dur(250) });
    g.clear();
    g.setAlpha(1);
  }

  async snake(from, to) {
    const a = cellXY(from), b = cellXY(to);
    const g = this.layerPaths;
    g.clear();
    g.lineStyle(9, C.safranin, 0.9);
    const pts = [];
    const steps = 30, dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
    const nx = -dy / len, ny = dx / len;
    for (let i = 0; i <= steps; i++) {
      const t = i / steps, wave = Math.sin(t * Math.PI * 3) * 14 * (1 - t * 0.5);
      pts.push(new Phaser.Math.Vector2(a.x + dx * t + nx * wave, a.y + dy * t + ny * wave));
    }
    g.strokePoints(pts, false);
    g.fillStyle(C.safranin, 1);
    g.fillCircle(pts[0].x, pts[0].y, 9);
    g.setAlpha(1);
    const follower = { t: 0 };
    await this.tween({
      targets: follower, t: 1, duration: dur(800), ease: "Sine.easeIn",
      onUpdate: () => {
        const p = pts[Math.min(steps, Math.round(follower.t * steps))];
        this.token.setPosition(p.x - 22, p.y + 22);
      },
    });
    this.placeToken(to);
    await this.tween({ targets: g, alpha: 0, duration: dur(500), delay: dur(250) });
    g.clear();
    g.setAlpha(1);
  }

  async setGate(n, state) {
    const bug = this.bugs[n];
    if (!bug) return;
    this.tweens.killTweensOf(bug);
    if (state === "cleared") {
      await this.tween({ targets: bug, scale: 0.2, alpha: 0, duration: dur(300) });
      bug.setTexture("cleared").setAlpha(1);
      await this.tween({ targets: bug, scale: 0.8, duration: dur(250), ease: "Back.easeOut" });
      if (REDUCED) bug.setScale(0.8);
    } else {
      bug.setAlpha(0.4).setScale(0.8);
    }
  }
}

export class BoardView {
  constructor(parent) {
    this.ready = new Promise((resolve) => {
      this.game = new Phaser.Game({
        type: Phaser.AUTO, parent, width: W, height: H, transparent: true,
        scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_HORIZONTALLY },
        scene: [BoardScene], banner: false, render: { antialias: true },
      });
      this.game.events.once("ready", () => {
        this.scene = this.game.scene.getScene("board");
        if (this.scene.token) resolve();
        else this.scene.events.once("ready-internal", resolve);
      });
    });
  }
  async setLevel(cfg) { await this.ready; this.scene.drawLevel(cfg); }
  async walk(path) { await this.ready; return this.scene.walk(path); }
  async ladder(a, b) { await this.ready; return this.scene.ladder(a, b); }
  async snake(a, b) { await this.ready; return this.scene.snake(a, b); }
  async setGate(n, s) { await this.ready; return this.scene.setGate(n, s); }
  async place(n) { await this.ready; this.scene.placeToken(n); }
}
