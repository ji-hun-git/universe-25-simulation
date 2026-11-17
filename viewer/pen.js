// Top-down view of the pen: walls, cells, nest boxes, hoppers, the playground and its objects,
// and the mice. World units are inches with y up (wall 0 at the bottom, world/geometry.py).

const TAU = Math.PI * 2;
// action -> group: rest/nest, forage/drink, social/mate/nurse, aggress, locomote, object, withdraw
export const ACTION_GROUP = [0, 1, 1, 0, 2, 4, 5, 3, 2, 2, 6, 4, 4, 5, 5];
export const ACTION_GROUP_NAMES = ["rest, nest", "forage, drink", "social, mate, nurse",
  "aggress", "explore, run on, turn back", "manipulate, back off, circle", "withdraw"];
const STRESS_STEPS = 8;

export function tokens() {
  const cs = getComputedStyle(document.documentElement);
  const g = (k) => cs.getPropertyValue(k).trim();
  return {
    paper: g("--paper"), paper2: g("--paper-2"), paper3: g("--paper-3"), floor: g("--floor"),
    ink: g("--ink"), ink2: g("--ink-2"), ink3: g("--ink-3"), rule: g("--rule"),
    rule2: g("--rule-2"), stress: g("--stress"), nest: g("--nest"), nest2: g("--nest-2"),
    ochre: g("--ochre"), slate: g("--slate"), umber: g("--umber"), sand: g("--sand"),
  };
}

export function rgb(hex) {
  let h = hex.replace("#", "");
  if (h.length === 3) h = [...h].map((c) => c + c).join("");
  const v = parseInt(h, 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
}
export const rgba = (hex, a) => { const [r, g, b] = rgb(hex); return `rgba(${r},${g},${b},${a})`; };
export function mix(a, b, f) {
  const A = rgb(a), B = rgb(b);
  return `rgb(${A.map((v, k) => Math.round(v + (B[k] - v) * f)).join(",")})`;
}

export function palette(tok) {
  const stress = [];
  for (let k = 0; k < STRESS_STEPS; k++) stress.push(mix(tok.ink3, tok.stress, k / (STRESS_STEPS - 1)));
  return {
    role: [tok.sand, tok.ochre, tok.ink, tok.slate, tok.nest, tok.nest2, tok.umber],
    sex: [tok.nest, tok.ink],
    action: [tok.sand, tok.ochre, tok.nest, tok.stress, tok.slate, tok.umber, tok.ink3],
    stress,
  };
}

export class Pen {
  constructor(canvas, { onSelect, onView }) {
    this.c = canvas;
    this.ctx = canvas.getContext("2d");
    this.onSelect = onSelect;
    this.onView = onView;
    this.world = null;
    this.layers = { cells: true, nests: true, hoppers: true, playground: true, density: false, trails: false };
    this.colorBy = "role";
    this.hidden = new Set();
    this.zoom = 1;
    this.cx = 50;
    this.cy = 50;
    this.sel = null; // {slot, born}
    this.selPos = null;
    this.followSel = false;
    this.hoverCell = -1;
    this.w = 1; this.h = 1; this.dpr = 1;
    this.layer = document.createElement("canvas");
    this.layerKey = "";
    this.trail = document.createElement("canvas");
    this.trailKey = "";
    this.slotMap = new Int32Array(65536).fill(-1);
    this.drawn = { n: 0, x: new Float32Array(4096), y: new Float32Array(4096), i: new Int32Array(4096) };
    this.retheme();
    this._input();
  }

  retheme() { this.tok = tokens(); this.pal = palette(this.tok); this.layerKey = ""; this.trailKey = ""; }

  setWorld(world) {
    this.world = world;
    this.W = world.width; this.H = world.height;
    this.reset();
  }

  reset() {
    this.zoom = 1; this.followSel = false;
    if (this.world) { this.cx = this.W / 2; this.cy = this.H / 2; }
    this.onView?.();
  }

  get s() { return this.base * this.zoom; }
  X(x) { return this.w / 2 + (x - this.cx) * this.s; }
  Y(y) { return this.h / 2 - (y - this.cy) * this.s; }
  wx(px) { return this.cx + (px - this.w / 2) / this.s; }
  wy(py) { return this.cy - (py - this.h / 2) / this.s; }

  _size() {
    const r = this.c.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    if (r.width !== this.w || r.height !== this.h || dpr !== this.dpr) {
      this.w = Math.max(1, r.width); this.h = Math.max(1, r.height); this.dpr = dpr;
      for (const cv of [this.c, this.layer, this.trail]) {
        cv.width = Math.round(this.w * dpr); cv.height = Math.round(this.h * dpr);
      }
      this.layerKey = ""; this.trailKey = "";
    }
    this.base = this.world ? Math.min(this.w, this.h) * 0.92 / Math.max(this.W, this.H) : 1;
  }

  // ------------------------------------------------------------------ static layer
  _drawLayer() {
    const key = [this.w, this.h, this.dpr, this.zoom, this.cx, this.cy, this.layers.cells,
      this.layers.hoppers, this.layers.nests, this.layers.playground, this.tok.ink].join("|");
    if (key === this.layerKey) return;
    this.layerKey = key;
    const ctx = this.layer.getContext("2d"), t = this.tok, w = this.world, s = this.s;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.w, this.h);
    const X = (v) => this.X(v), Y = (v) => this.Y(v);
    // cells
    if (this.layers.cells) {
      ctx.strokeStyle = t.rule2; ctx.lineWidth = 1;
      for (const c of w.cells) {
        ctx.beginPath();
        c.poly.forEach(([px, py], k) => (k ? ctx.lineTo(X(px), Y(py)) : ctx.moveTo(X(px), Y(py))));
        ctx.closePath(); ctx.stroke();
      }
      ctx.fillStyle = t.ink3;
      ctx.font = `${Math.max(9, Math.min(12, s * 1.4))}px "IBM Plex Mono", monospace`;
      ctx.textBaseline = "top";
      for (const c of w.cells) {
        const [lx, ly] = this._labelAt(c);
        ctx.fillText(String(c.id), X(lx), Y(ly));
      }
    }
    // ring stands (Calhoun layout)
    if (this.layers.cells && w.rings.length) {
      ctx.strokeStyle = t.ink3; ctx.lineWidth = 1;
      for (const [rx, ry] of w.rings) { ctx.beginPath(); ctx.arc(X(rx), Y(ry), Math.max(2, 1.4 * s), 0, TAU); ctx.stroke(); }
    }
    // nest box outlines
    if (this.layers.nests) {
      ctx.strokeStyle = rgba(t.nest, 0.55); ctx.lineWidth = 1;
      const b = Math.max(2.5, 1.5 * s);
      for (const nb of this._nestXY()) ctx.strokeRect(X(nb[0]) - b / 2, Y(nb[1]) - b / 2, b, b);
    }
    // food hoppers and water
    if (this.layers.hoppers) {
      const f = Math.max(3.5, 2.2 * s), r = Math.max(2, 1.1 * s);
      for (const c of w.cells) {
        ctx.fillStyle = t.ochre; ctx.fillRect(X(c.food[0]) - f / 2, Y(c.food[1]) - f / 2, f, f);
        ctx.fillStyle = t.slate; ctx.beginPath(); ctx.arc(X(c.water[0]), Y(c.water[1]), r, 0, TAU); ctx.fill();
      }
    }
    // playground box
    if (this.layers.playground && w.playground.enabled) {
      const [x0, y0, x1, y1] = w.playground.bounds;
      ctx.strokeStyle = t.ink2; ctx.lineWidth = 1; ctx.setLineDash([5, 4]);
      ctx.strokeRect(X(x0), Y(y1), (x1 - x0) * s, (y1 - y0) * s);
      ctx.setLineDash([]);
      ctx.fillStyle = t.ink3; ctx.textBaseline = "bottom";
      ctx.font = `10px "IBM Plex Mono", monospace`;
      ctx.fillText("playground", X(x0), Y(y1) - 3);
    }
    // walls
    ctx.strokeStyle = t.ink; ctx.lineWidth = 1.6;
    ctx.strokeRect(X(0), Y(this.H), this.W * s, this.H * s);
  }

  _labelAt(c) {
    if (this.world.layout !== "calhoun") {
      const xs = c.poly.map((p) => p[0]), ys = c.poly.map((p) => p[1]);
      return [Math.min(...xs) + 0.9, Math.max(...ys) - 0.9];
    }
    const [a, b, m] = c.poly; // wall segment a-b, apex m at the centre
    const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
    return [mx + (m[0] - mx) * 0.22, my + (m[1] - my) * 0.22];
  }

  // nest positions, with the Calhoun layout's four box levels drawn inward from the wall
  _nestXY() {
    if (this._nests) return this._nests;
    const w = this.world, cxm = this.W / 2, cym = this.H / 2;
    this._nests = w.nests.map((n) => {
      if (!n.level) return [n.x, n.y];
      const dx = cxm - n.x, dy = cym - n.y, L = Math.hypot(dx, dy) || 1;
      return [n.x + (dx / L) * 1.7 * n.level, n.y + (dy / L) * 1.7 * n.level];
    });
    return this._nests;
  }

  // ------------------------------------------------------------------ frame
  draw(st) {
    this._size();
    const ctx = this.ctx, t = this.tok;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.fillStyle = t.paper; ctx.fillRect(0, 0, this.w, this.h);
    if (!this.world) return;
    const w = this.world, s = this.s;
    if (this.followSel && this.selPos) { this.cx = this.selPos[0]; this.cy = this.selPos[1]; }
    const X = (v) => this.X(v), Y = (v) => this.Y(v);
    // floor
    ctx.fillStyle = t.floor; ctx.fillRect(X(0), Y(this.H), this.W * s, this.H * s);
    const ma = st.ma;
    // cell density shading
    if (this.layers.density && ma) {
      const cap = w.cell_capacity;
      for (const c of w.cells) {
        const v = Math.min(1, (ma.cells[c.id] || 0) / cap);
        const a = 0.55 * Math.pow(v, 1.6); // faint below half the design capacity
        if (a < 0.02) continue;
        ctx.fillStyle = rgba(t.stress, a);
        ctx.beginPath();
        c.poly.forEach(([px, py], k) => (k ? ctx.lineTo(X(px), Y(py)) : ctx.moveTo(X(px), Y(py))));
        ctx.closePath(); ctx.fill();
      }
    }
    if (this.hoverCell >= 0) {
      const c = w.cells[this.hoverCell];
      ctx.fillStyle = rgba(t.ink, 0.06);
      ctx.beginPath();
      c.poly.forEach(([px, py], k) => (k ? ctx.lineTo(X(px), Y(py)) : ctx.moveTo(X(px), Y(py))));
      ctx.closePath(); ctx.fill();
    }
    this._drawLayer();
    ctx.drawImage(this.layer, 0, 0, this.w, this.h);
    const fa = st.fa;
    // nest residents
    if (this.layers.nests && fa) {
      const cnt = this._nestCount || (this._nestCount = new Uint16Array(w.nests.length));
      cnt.fill(0);
      for (let i = 0; i < fa.n; i++) { const k = fa.nest[i]; if (k >= 0 && k < cnt.length) cnt[k]++; }
      const b = Math.max(2.5, 1.5 * s), xy = this._nestXY();
      for (let k = 0; k < cnt.length; k++) {
        if (!cnt[k]) continue;
        ctx.fillStyle = rgba(t.nest, 0.25 + 0.65 * Math.min(1, cnt[k] / (w.nests[k].cap || 15)));
        ctx.fillRect(X(xy[k][0]) - b / 2, Y(xy[k][1]) - b / 2, b, b);
      }
    }
    // objects
    if (this.layers.playground && w.playground.enabled) this._objects(ctx, st);
    if (!fa) return;
    // mice
    const pos = this._positions(st);
    if (this.layers.trails) this._trails(pos, fa.n);
    const r = Math.min(6, Math.max(1.3, 0.48 * s));
    const groups = new Map(), rings = new Path2D();
    const pal = this.pal, mode = this.colorBy;
    const d = this.drawn;
    let nd = 0, selI = -1;
    for (let i = 0; i < fa.n; i++) {
      const role = fa.role[i];
      if (this.hidden.has(role)) continue;
      const px = X(pos.x[i]), py = Y(pos.y[i]);
      d.x[nd] = px; d.y[nd] = py; d.i[nd] = i; nd++;
      if (this.sel && fa.slot[i] === this.sel.slot) selI = i;
      if (mode === "role" && role === 6) { rings.moveTo(px + r, py); rings.arc(px, py, r, 0, TAU); continue; }
      let col;
      if (mode === "role") col = pal.role[role];
      else if (mode === "sex") col = pal.sex[fa.flags[i] & 1];
      else if (mode === "action") col = pal.action[ACTION_GROUP[fa.action[i]] ?? 0];
      else col = pal.stress[Math.min(STRESS_STEPS - 1, Math.floor((fa.stress[i] * 1.5 / 255) * STRESS_STEPS))];
      let p = groups.get(col);
      if (!p) { p = new Path2D(); groups.set(col, p); }
      p.moveTo(px + r, py); p.arc(px, py, r, 0, TAU);
    }
    d.n = nd;
    for (const [col, p] of groups) { ctx.fillStyle = col; ctx.fill(p); }
    ctx.strokeStyle = pal.role[6]; ctx.lineWidth = Math.max(1, r * 0.55); ctx.stroke(rings);
    // selection
    if (this.sel) {
      const ok = selI >= 0 && Math.abs((st.t - fa.age[selI]) - this.sel.born) < 2.5;
      if (ok) {
        const px = X(pos.x[selI]), py = Y(pos.y[selI]);
        this.selPos = [pos.x[selI], pos.y[selI]];
        ctx.strokeStyle = t.stress; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(px, py, r + 5, 0, TAU); ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(px - r - 12, py); ctx.lineTo(px - r - 6, py);
        ctx.moveTo(px + r + 6, py); ctx.lineTo(px + r + 12, py);
        ctx.moveTo(px, py - r - 12); ctx.lineTo(px, py - r - 6);
        ctx.moveTo(px, py + r + 6); ctx.lineTo(px, py + r + 12);
        ctx.stroke();
        this.selIndex = selI;
      } else {
        this.selIndex = -1;
      }
    }
  }

  _positions(st) {
    const fa = st.fa, fb = st.fb, a = st.alpha;
    const n = fa.n;
    if (!this._px || this._px.length < n) { this._px = new Float32Array(4096); this._py = new Float32Array(4096); }
    const px = this._px, py = this._py;
    for (let i = 0; i < n; i++) { px[i] = fa.x[i] / 100; py[i] = fa.y[i] / 100; }
    if (fb && a > 0) {
      const map = this.slotMap;
      for (let j = 0; j < fb.n; j++) map[fb.slot[j]] = j;
      for (let i = 0; i < n; i++) {
        const j = map[fa.slot[i]];
        if (j < 0) continue;
        const dAge = fb.age[j] - fa.age[i];
        if (dAge < 0 || dAge > 2) continue; // a reused slot: another animal
        px[i] += (fb.x[j] / 100 - px[i]) * a;
        py[i] += (fb.y[j] / 100 - py[i]) * a;
      }
      for (let j = 0; j < fb.n; j++) map[fb.slot[j]] = -1;
    }
    return { x: px, y: py };
  }

  _objects(ctx, st) {
    const w = this.world, t = this.tok, s = this.s;
    const oa = st.ma?.obj, ob = st.mb?.obj, a = st.alpha || 0;
    w.objects.forEach((o, k) => {
      let x = o.x, y = o.y;
      if (oa && oa[k]) { x = oa[k][0]; y = oa[k][1]; }
      if (ob && ob[k] && a > 0) { x += (ob[k][0] - x) * a; y += (ob[k][1] - y) * a; }
      const X = this.X(x), Y = this.Y(y), r = Math.max(2, o.r * s);
      ctx.lineWidth = 1.2; ctx.strokeStyle = t.ink2; ctx.fillStyle = t.paper2;
      ctx.beginPath();
      if (o.kind === "ball") {
        ctx.arc(X, Y, r, 0, TAU); ctx.fill(); ctx.stroke();
        ctx.beginPath(); ctx.arc(X - r * 0.3, Y - r * 0.3, Math.max(0.8, r * 0.18), 0, TAU);
        ctx.fillStyle = t.ink3; ctx.fill();
      } else if (o.kind === "tunnel") {
        ctx.roundRect(X - r, Y - r * 0.45, 2 * r, r * 0.9, r * 0.45); ctx.fill(); ctx.stroke();
      } else {
        ctx.moveTo(X - r, Y + r * 0.6); ctx.lineTo(X + r, Y + r * 0.6); ctx.lineTo(X + r, Y - r * 0.6);
        ctx.closePath(); ctx.fill(); ctx.stroke();
      }
    });
  }

  // fading marks of the last positions; cleared whenever the view moves
  _trails(pos, n) {
    const key = [this.w, this.h, this.zoom, this.cx, this.cy, this.tok.ink].join("|");
    const tc = this.trail.getContext("2d");
    tc.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    if (key !== this.trailKey) { tc.clearRect(0, 0, this.w, this.h); this.trailKey = key; }
    tc.globalCompositeOperation = "destination-out";
    tc.fillStyle = "rgba(0,0,0,0.07)";
    tc.fillRect(0, 0, this.w, this.h);
    tc.globalCompositeOperation = "source-over";
    tc.fillStyle = rgba(this.tok.ink3, 0.4);
    const p = new Path2D();
    for (let i = 0; i < n; i++) p.rect(this.X(pos.x[i]) - 0.7, this.Y(pos.y[i]) - 0.7, 1.4, 1.4);
    tc.fill(p);
    this.ctx.drawImage(this.trail, 0, 0, this.w, this.h);
  }

  clearTrails() { this.trailKey = ""; }

  // ------------------------------------------------------------------ input
  _input() {
    const c = this.c;
    let drag = null;
    c.addEventListener("pointerdown", (e) => {
      c.setPointerCapture(e.pointerId);
      drag = { x: e.offsetX, y: e.offsetY, cx: this.cx, cy: this.cy, moved: false };
    });
    c.addEventListener("pointermove", (e) => {
      if (!drag) return;
      const dx = e.offsetX - drag.x, dy = e.offsetY - drag.y;
      if (!drag.moved && Math.hypot(dx, dy) < 4) return;
      drag.moved = true; c.classList.add("dragging");
      this.followSel = false;
      this.cx = drag.cx - dx / this.s; this.cy = drag.cy + dy / this.s;
      this.onView?.();
    });
    c.addEventListener("pointerup", (e) => {
      c.classList.remove("dragging");
      if (drag && !drag.moved) this._pick(e.offsetX, e.offsetY);
      drag = null;
    });
    c.addEventListener("wheel", (e) => {
      e.preventDefault();
      if (!this.world) return;
      const wx = this.wx(e.offsetX), wy = this.wy(e.offsetY);
      this.zoom = Math.min(40, Math.max(0.6, this.zoom * Math.exp(-e.deltaY * 0.0016)));
      if (!this.followSel) {
        this.cx = wx - (e.offsetX - this.w / 2) / this.s;
        this.cy = wy + (e.offsetY - this.h / 2) / this.s;
      }
      this.onView?.();
    }, { passive: false });
    c.addEventListener("dblclick", () => this.reset());
  }

  _pick(px, py) {
    const d = this.drawn;
    let best = -1, bd = 9 * 9;
    for (let k = 0; k < d.n; k++) {
      const dx = d.x[k] - px, dy = d.y[k] - py, q = dx * dx + dy * dy;
      if (q < bd) { bd = q; best = d.i[k]; }
    }
    this.onSelect?.(best);
  }
}
