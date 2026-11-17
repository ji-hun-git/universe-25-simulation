// Dashboard: six small multiples on one time axis (days), a shared hover cursor, Calhoun's
// phases A-D shaded on the record's days, and the current moment as a red rule. uPlot draws the
// line charts (HANDOFF §8); the cell strip is a plain canvas.
import { mix, palette, rgba, tokens } from "./pen.js";

const SYNC = "u25";
const ROLE_ORDER = [0, 1, 4, 5, 2, 3, 6]; // stacked from the bottom: young, females, males, withdrawn

function fmtInt(v) { return v == null ? "–" : Math.round(v).toLocaleString("en-US"); }
function fmt(v, d = 2) { return v == null || Number.isNaN(v) ? "–" : v.toFixed(d); }

export class Dash {
  constructor(root, { onSeek }) {
    this.root = root;
    this.onSeek = onSeek;
    this.plots = {};
    this.t = 0;
    this.store = null;
    this.world = null;
    this.data = null;
    this.hover = null;
    this.heatCv = root.querySelector("#cCells canvas.heat");
    this.heatImg = document.createElement("canvas");
    this.ro = new ResizeObserver(() => this.resize());
    for (const fig of root.querySelectorAll(".chart .plot")) this.ro.observe(fig);
    this._heatInput();
  }

  get ok() { return typeof window.uPlot === "function"; }

  build(world) {
    this.world = world;
    for (const u of Object.values(this.plots)) u.destroy();
    this.plots = {};
    this.tok = tokens();
    this.pal = palette(this.tok);
    if (!this.ok) {
      for (const p of this.root.querySelectorAll(".chart .plot")) {
        if (!p.querySelector("canvas.heat")) p.textContent = "Charts need uPlot from cdn.jsdelivr.net.";
      }
      return;
    }
    const t = this.tok, pal = this.pal;
    const line = (stroke, extra = {}) => ({ stroke, width: 1.4, points: { show: false }, ...extra });
    this._make("cPop", [line(t.ink, { label: "N" })], { yRange: (u, lo, hi) => [0, Math.max(hi || 0, 2200) * 1.08] }, true);
    this._make("cRoles", ROLE_ORDER.slice().reverse().map((r) => ({
      label: world.roles[r], stroke: pal.role[r], width: 0, fill: pal.role[r], points: { show: false },
    })), { yRange: (u, lo, hi) => [0, Math.max(10, hi || 0) * 1.05] });
    this._make("cVital", [line(t.nest, { label: "births" }), line(t.stress, { label: "deaths" })],
      { yRange: (u, lo, hi) => [0, Math.max(1, hi || 0) * 1.1] });
    this._make("cStress", [line(t.stress, { label: "stress", scale: "y" }),
      line(t.ink2, { label: "withdrawn %", scale: "pct", dash: [4, 3], width: 1.2 })],
    { yRange: (u, lo, hi) => [0, Math.max(0.2, hi || 0) * 1.1], pct: true });
    this._make("cPg", [line(t.umber, { label: "inside %" }), line(t.ink2, { label: "V %", dash: [4, 3], width: 1.2 }),
      line(t.ink3, { label: "G %", width: 1.1 })], { yRange: () => [0, 100] });
    if (this.store) this.update(this.store);
  }

  _make(id, series, o, census = false) {
    const fig = this.root.querySelector(`#${id}`), el = fig.querySelector(".plot");
    el.textContent = "";
    const t = this.tok, dpr = () => window.uPlot.pxRatio || 1;
    const axis = (extra) => ({
      stroke: t.ink3, font: '10px "IBM Plex Mono", monospace', grid: { stroke: t.rule, width: 1 },
      ticks: { stroke: t.rule, width: 1, size: 3 }, gap: 3, ...extra,
    });
    const scales = { x: { time: false, range: () => this._xRange() }, y: { range: o.yRange } };
    const axes = [axis({ size: 20, space: 54, values: (u, v) => v.map((d) => fmtInt(d)) }),
      axis({ size: 38, space: 22, values: (u, v) => v.map((d) => (Math.abs(d) >= 1000 ? `${(d / 1000).toFixed(1)}k` : d < 10 && d % 1 ? d.toFixed(1) : String(Math.round(d)))) })];
    if (o.pct) {
      scales.pct = { range: (u, lo, hi) => [0, Math.max(5, hi || 0) * 1.1] };
      axes.push(axis({ scale: "pct", side: 1, size: 30, grid: { show: false }, values: (u, v) => v.map((d) => `${Math.round(d)}%`) }));
    }
    const self = this;
    const opts = {
      width: Math.max(80, el.clientWidth), height: Math.max(60, el.clientHeight),
      legend: { show: false },
      cursor: { sync: { key: SYNC }, drag: { x: false, y: false, setScale: false }, points: { show: false }, y: false },
      scales, axes,
      series: [{}, ...series],
      hooks: {
        drawClear: [(u) => self._phases(u, dpr())],
        draw: [(u) => { if (census) self._census(u, dpr()); self._now(u, dpr()); }],
        setCursor: [(u) => self._read(id, u.cursor.idx)],
      },
    };
    const u = new window.uPlot(opts, [[]], el);
    u.over.addEventListener("pointerdown", (e) => { this.onSeek(u.posToVal(e.offsetX, "x")); });
    u.over.addEventListener("pointermove", (e) => { if (e.buttons & 1) this.onSeek(u.posToVal(e.offsetX, "x")); });
    u.over.addEventListener("pointerleave", () => { this.hover = null; this._readAll(); });
    this.plots[id] = u;
  }

  _xRange() {
    const s = this.store;
    const end = Math.max(s ? s.t1 : 1, this.span || 0, 1);
    return [s ? s.t0 : 0, end];
  }

  // Calhoun's phases on the record's days, alternately tinted, lettered at the top
  _phases(u, k) {
    const ph = this.world?.landmarks?.phases;
    if (!ph) return;
    const ctx = u.ctx, { left, top, width, height } = u.bbox;
    ctx.save();
    ctx.font = `${10 * k}px "IBM Plex Mono", monospace`;
    ctx.textBaseline = "top";
    ph.forEach((p, i) => {
      const x0 = Math.max(left, u.valToPos(p.from, "x", true));
      const x1 = Math.min(left + width, u.valToPos(p.to ?? u.scales.x.max, "x", true));
      if (x1 <= x0 + 1) return;
      if (i % 2 === 0) { ctx.fillStyle = rgba(this.tok.ink, 0.045); ctx.fillRect(x0, top, x1 - x0, height); }
      if (x1 - x0 > 14 * k) { ctx.fillStyle = this.tok.ink3; ctx.fillText(p.name, x0 + 3 * k, top + 2 * k); }
    });
    ctx.restore();
  }

  _census(u, k) {
    const pts = this.world?.landmarks?.census || [];
    const ctx = u.ctx, { left, top, width, height } = u.bbox;
    ctx.save();
    ctx.strokeStyle = this.tok.stress; ctx.lineWidth = 1.4 * k;
    for (const [d, n] of pts) {
      const x = u.valToPos(d, "x", true), y = u.valToPos(n, "y", true);
      if (x < left || x > left + width || y < top || y > top + height) continue;
      const r = 3.5 * k;
      ctx.beginPath(); ctx.moveTo(x - r, y); ctx.lineTo(x + r, y); ctx.moveTo(x, y - r); ctx.lineTo(x, y + r); ctx.stroke();
    }
    ctx.restore();
  }

  _now(u, k) {
    const ctx = u.ctx, { left, top, width, height } = u.bbox;
    const x = u.valToPos(this.t, "x", true);
    if (x < left - 1 || x > left + width + 1) return;
    ctx.save();
    ctx.strokeStyle = this.tok.stress; ctx.lineWidth = k;
    ctx.beginPath(); ctx.moveTo(Math.round(x) + 0.5, top); ctx.lineTo(Math.round(x) + 0.5, top + height); ctx.stroke();
    ctx.restore();
  }

  // ------------------------------------------------------------------ data
  update(store) {
    this.store = store;
    const m = store.meta, L = m.length;
    const x = new Array(L), N = new Array(L), births = new Array(L), deaths = new Array(L);
    const ms = new Array(L), wd = new Array(L), pg = new Array(L), V = new Array(L), G = new Array(L);
    const stacks = ROLE_ORDER.map(() => new Array(L));
    let j = 0;
    for (let i = 0; i < L; i++) {
      const f = m[i];
      x[i] = f.t; N[i] = f.n;
      let acc = 0;
      ROLE_ORDER.forEach((r, k) => { acc += f.roles[r]; stacks[k][i] = acc; });
      while (j < i && m[j].t < f.t - 7) j++;
      const span = f.t - m[j].t;
      births[i] = span >= 0.5 ? (f.b - m[j].b) / span : null;
      deaths[i] = span >= 0.5 ? (f.d - m[j].d) / span : null;
      ms[i] = f.n ? f.ms : null;
      wd[i] = f.n ? (100 * f.roles[6]) / f.n : null;
      pg[i] = f.n ? (100 * f.pg) / f.n : null;
      V[i] = f.n ? 100 * f.V : null;
      G[i] = f.n ? 100 * f.G : null;
    }
    this.data = { x, N, births, deaths, ms, wd, pg, V, G, stacks };
    if (this.ok && this.plots.cPop) {
      this.plots.cPop.setData([x, N]);
      this.plots.cRoles.setData([x, ...stacks.slice().reverse()]);
      this.plots.cVital.setData([x, births, deaths]);
      this.plots.cStress.setData([x, ms, wd]);
      this.plots.cPg.setData([x, pg, V, G]);
    }
    this._heatBuild();
    this._readAll();
  }

  setTime(t) {
    this.t = t;
    for (const u of Object.values(this.plots)) u.redraw(false);
    this._heatDraw();
    if (!this.hover) this._readAll();
  }

  resize() {
    for (const [id, u] of Object.entries(this.plots)) {
      const el = this.root.querySelector(`#${id} .plot`);
      if (el.clientWidth > 0 && el.clientHeight > 0) u.setSize({ width: el.clientWidth, height: el.clientHeight });
    }
    this._heatBuild();
  }

  // ------------------------------------------------------------------ readouts
  _readAll() {
    if (!this.store || !this.store.length) return;
    const i = this.store.indexAt(this.t);
    for (const id of ["cPop", "cRoles", "cVital", "cStress", "cPg"]) this._read(id, i, true);
  }

  _read(id, i, quiet = false) {
    const d = this.data, fig = this.root.querySelector(`#${id} .read`);
    if (!d || !fig || i == null || i < 0 || i >= d.x.length) return;
    if (!quiet) this.hover = id;
    const day = `day ${fmt(d.x[i], d.x[i] % 1 ? 2 : 0)}`;
    let s = "";
    if (id === "cPop") s = `N ${fmtInt(d.N[i])}`;
    else if (id === "cRoles") {
      const m = this.store.meta[i];
      s = `young ${fmtInt(m.roles[0] + m.roles[1])} · F ${fmtInt(m.roles[4] + m.roles[5])} · M ${fmtInt(m.roles[2] + m.roles[3])} · wd ${fmtInt(m.roles[6])}`;
    } else if (id === "cVital") s = `b ${fmt(d.births[i], 1)} · d ${fmt(d.deaths[i], 1)}`;
    else if (id === "cStress") s = `stress ${fmt(d.ms[i])} · wd ${fmt(d.wd[i], 1)}%`;
    else if (id === "cPg") s = `${fmt(d.pg[i], 1)}% · V ${fmt(d.V[i], 0)} · G ${fmt(d.G[i], 0)}`;
    fig.textContent = `${day} · ${s}`;
  }

  // ------------------------------------------------------------------ cell strip
  _heatBuild() {
    const cv = this.heatCv, s = this.store;
    if (!cv) return;
    const r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    cv.width = Math.max(1, Math.round(r.width * dpr)); cv.height = Math.max(1, Math.round(r.height * dpr));
    this.heatGeom = { w: r.width, h: r.height, dpr, left: 38, right: 8, top: 4, bottom: 20 };
    if (!s || !s.length || !this.world) { this._heatDraw(); return; }
    const g = this.heatGeom, pw = Math.max(1, Math.round((g.w - g.left - g.right) * dpr));
    const nc = this.world.cells.length, cap = this.world.cell_capacity;
    const [t0, t1] = this._xRange();
    const img = new ImageData(pw, nc);
    const t = this.tok;
    const ramp = [];
    for (let k = 0; k <= 32; k++) {
      const v = k / 32;
      const c = v < 0.45 ? mix(t.paper3, t.ochre, v / 0.45) : mix(t.ochre, t.stress, Math.min(1, (v - 0.45) / 0.55));
      ramp.push(c.match(/\d+/g).map(Number));
    }
    for (let px = 0; px < pw; px++) {
      const tt = t0 + ((px + 0.5) / pw) * (t1 - t0);
      if (tt > s.t1 + 1e-9) continue;
      const cells = s.meta[s.indexAt(tt)].cells;
      for (let c = 0; c < nc; c++) {
        const v = Math.min(1, (cells[c] || 0) / cap);
        const col = ramp[Math.round(v * 32)], o = (c * pw + px) * 4;
        img.data[o] = col[0]; img.data[o + 1] = col[1]; img.data[o + 2] = col[2]; img.data[o + 3] = 255;
      }
    }
    this.heatImg.width = pw; this.heatImg.height = nc;
    this.heatImg.getContext("2d").putImageData(img, 0, 0);
    this._heatDraw();
  }

  _heatDraw() {
    const cv = this.heatCv, g = this.heatGeom;
    if (!cv || !g) return;
    const ctx = cv.getContext("2d"), t = this.tok || tokens();
    ctx.setTransform(g.dpr, 0, 0, g.dpr, 0, 0);
    ctx.clearRect(0, 0, g.w, g.h);
    const pw = g.w - g.left - g.right, ph = g.h - g.top - g.bottom;
    if (pw <= 0 || ph <= 0) return;
    ctx.imageSmoothingEnabled = false;
    if (this.store && this.store.length) ctx.drawImage(this.heatImg, g.left, g.top, pw, ph);
    ctx.strokeStyle = t.rule2; ctx.lineWidth = 1;
    ctx.strokeRect(g.left + 0.5, g.top + 0.5, pw - 1, ph - 1);
    ctx.fillStyle = t.ink3; ctx.font = '10px "IBM Plex Mono", monospace';
    const nc = this.world ? this.world.cells.length : 16;
    ctx.textBaseline = "middle"; ctx.textAlign = "right";
    for (let c = 0; c < nc; c += 4) ctx.fillText(String(c), g.left - 5, g.top + ((c + 0.5) / nc) * ph);
    const [t0, t1] = this._xRange();
    const step = [10, 25, 50, 100, 200, 250, 500, 1000].find((s) => (t1 - t0) / s <= Math.max(2, pw / 70)) || 1000;
    ctx.textAlign = "center"; ctx.textBaseline = "top";
    for (let d = Math.ceil(t0 / step) * step; d <= t1; d += step) {
      const x = g.left + ((d - t0) / (t1 - t0 || 1)) * pw;
      ctx.fillText(fmtInt(d), x, g.top + ph + 4);
    }
    const x = g.left + ((this.t - t0) / (t1 - t0 || 1)) * pw;
    if (x >= g.left && x <= g.left + pw) {
      ctx.strokeStyle = t.stress; ctx.beginPath(); ctx.moveTo(Math.round(x) + 0.5, g.top); ctx.lineTo(Math.round(x) + 0.5, g.top + ph); ctx.stroke();
    }
  }

  _heatInput() {
    const cv = this.heatCv;
    if (!cv) return;
    const at = (e) => {
      const g = this.heatGeom, [t0, t1] = this._xRange();
      if (!g) return null;
      const pw = g.w - g.left - g.right, ph = g.h - g.top - g.bottom;
      const day = t0 + ((e.offsetX - g.left) / pw) * (t1 - t0);
      const cell = Math.floor(((e.offsetY - g.top) / ph) * (this.world?.cells.length || 16));
      return { day, cell };
    };
    cv.addEventListener("pointerdown", (e) => { const p = at(e); if (p) this.onSeek(p.day); });
    cv.addEventListener("pointermove", (e) => {
      const p = at(e), read = this.root.querySelector("#cCells .read");
      if (!p || !this.store || !this.store.length || !read) return;
      if (e.buttons & 1) this.onSeek(p.day);
      if (p.cell < 0 || p.cell >= (this.world?.cells.length || 16)) return;
      const m = this.store.meta[this.store.indexAt(p.day)];
      read.textContent = `day ${fmtInt(m.t)} · cell ${p.cell} · ${fmtInt(m.cells[p.cell])} (${fmt(m.cells[p.cell] / this.world.cell_capacity)})`;
    });
  }
}
