// The pen in 3D (three.js, loaded on first use from cdn.jsdelivr.net): the pen as the model
// builds it (world/geometry.py) and every mouse at real scale as a procedural albino mouse. The
// founders were BALB/c (Calhoun 1973, docs/REPLICA_V2.md): white fur, pink skin, red eyes.
//
// The simulator is planar, so heights are drawn, not simulated:
// - a mouse at its own nest box's point is drawn inside that box, at the box's level;
// - in the Calhoun layout, a mouse at a hopper is drawn on the hopper's mesh face, and a mouse
//   at a water platform is drawn on the platform.
// Sizes the record gives (docs/REPLICA_V2.md) are used as given:
// - walls 54 in, the lower 37 in mesh;
// - tunnels 3 in across and 34 in tall;
// - boxes 8 x 5 x 4 in at 8, 16, 24 and 32 in;
// - hopper 6 x 10 in, halfway up the wall.
// Where the record is silent the drawing chooses:
// - the boxes sit behind the wall mesh, 4 in wide so four fit along the four tunnels;
// - hopper depth, platform height and depth, 1-in partitions, the ring stands' shape.
// The walls on the camera's side are drawn in outline (a cutaway), with the animals in them.
// The grid layout is the frozen colony's abstract pen: its boxes stand on the floor at their
// points, and its food and water are floor points.
// View state (layers, roles shown, selection, follow) is shared with the plan view through `ui`.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { ACTION_GROUP, mix, palette, rgb, tokens } from "./pen.js";

const TAU = Math.PI * 2;
const WALL_H = 54, MESH_H = 37, MESH_PITCH = 0.5;
const TUNNEL_R = 1.5, TUNNEL_H = 34;
const BOX_W = 4, BOX_H = 5, BOX_D = 8, BOX_LEVEL = [8, 16, 24, 32];
const HOPPER_W = 6, HOPPER_H = 10, HOPPER_D = 2.5, HOPPER_Y = 27;
const PLATFORM_Y = 35, PLATFORM_D = 3.5, PARTITION_H = 1, RING_H = 11;
const GRID_BOX = 4.6, GRID_BOX_H = 2.6;
const AT = 0.75; // inches: a mouse this close to a box, hopper or platform point is at it
const FUR = "#F1EEE7", SKIN = "#E2ABA2", EAR = "#E8BCB3", NOSE = "#D9928A", PUP = "#ECB7AD";
const EYE = "#701B20";
export const NATURAL = { fur: FUR, pup: PUP, eye: EYE }; // for the legend
const FLOOR = 0, BOX = 1, CLING = 2, SHELF = 3;
// wall k: inward normal n and counter-clockwise tangent t, in the model's plane (y up)
const NEAR = [0, 1, -1]; // a forager may use its own hopper or a wall neighbour's (replica M3)
const SIDES = [{ n: [0, 1], t: [1, 0] }, { n: [-1, 0], t: [0, 1] }, { n: [0, -1], t: [-1, 0] },
  { n: [1, 0], t: [0, -1] }];

// ------------------------------------------------------------------ helpers
function h01(n, salt) { // a stable number in [0, 1) per (n, salt)
  let x = (Math.imul(n | 0, 0x9e3779b1) ^ Math.imul(salt | 0, 0x85ebca6b)) >>> 0;
  x = Math.imul(x ^ (x >>> 15), 0x2c1b3c6d) >>> 0;
  x = Math.imul(x ^ (x >>> 12), 0x297a2d39) >>> 0;
  return ((x ^ (x >>> 15)) >>> 0) / 4294967296;
}
function lerpAngle(a, b, f) {
  let d = (b - a) % TAU;
  if (d > Math.PI) d -= TAU; else if (d < -Math.PI) d += TAU;
  return a + d * f;
}
function catmull(p0, p1, p2, p3, t) {
  const t2 = t * t, t3 = t2 * t;
  return 0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (3 * p1 - p0 - 3 * p2 + p3) * t3);
}
function rng(seed) { // mulberry32
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function disposeTree(obj) {
  obj.traverse((o) => {
    o.geometry?.dispose();
    const ms = Array.isArray(o.material) ? o.material : o.material ? [o.material] : [];
    for (const m of ms) { m.map?.dispose(); m.dispose(); }
  });
}
// concatenate indexed geometries (position, normal; colour, part and t when given)
function merge(parts) {
  let nv = 0, ni = 0;
  for (const p of parts) { nv += p.geo.attributes.position.count; ni += p.geo.index.count; }
  const pos = new Float32Array(nv * 3), nrm = new Float32Array(nv * 3), col = new Float32Array(nv * 3);
  const part = new Float32Array(nv), tt = new Float32Array(nv), idx = new Uint32Array(ni);
  let v = 0, k = 0;
  const c = new THREE.Color();
  for (const p of parts) {
    const g = p.geo, n = g.attributes.position.count;
    pos.set(g.attributes.position.array, v * 3);
    nrm.set(g.attributes.normal.array, v * 3);
    c.set(p.color || "#ffffff");
    for (let j = 0; j < n; j++) {
      col[(v + j) * 3] = c.r; col[(v + j) * 3 + 1] = c.g; col[(v + j) * 3 + 2] = c.b;
      part[v + j] = p.part || 0;
      tt[v + j] = p.t ? p.t[j] : 0;
    }
    const gi = g.index.array;
    for (let j = 0; j < gi.length; j++) idx[k + j] = gi[j] + v;
    v += n; k += gi.length;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  out.setAttribute("normal", new THREE.BufferAttribute(nrm, 3));
  out.setAttribute("color", new THREE.BufferAttribute(col, 3));
  out.setAttribute("aPart", new THREE.BufferAttribute(part, 1));
  out.setAttribute("aT", new THREE.BufferAttribute(tt, 1));
  out.setIndex(new THREE.BufferAttribute(idx, 1));
  return out;
}
function boxAt(sx, sy, sz, x, y, z) { const g = new THREE.BoxGeometry(sx, sy, sz); g.translate(x, y, z); return { geo: g }; }
// an open-topped box, width along x, depth along z, standing on y = 0
function trayGeometry(w, d, h, th) {
  return merge([boxAt(w, h, th, 0, h / 2, -d / 2 + th / 2), boxAt(w, h, th, 0, h / 2, d / 2 - th / 2),
    boxAt(th, h, d - 2 * th, -w / 2 + th / 2, h / 2, 0), boxAt(th, h, d - 2 * th, w / 2 - th / 2, h / 2, 0)]);
}
// a matrix with x along (tx, 0, tz), y up, z along (ox, 0, oz), at p
function basis(tx, tz, ox, oz, px, py, pz) {
  return new THREE.Matrix4().set(tx, 0, ox, px, 0, 1, 0, py, tz, 0, oz, pz, 0, 0, 0, 1);
}

// ------------------------------------------------------------------ the mouse
// An adult house mouse in inches, nose along +x, back up +y: head and body about 3.35 in, tail
// about 3.1 in. Rows: x, half-width, half-height, height of the axis.
const BODY = [[-1.56, 0, 0, 0.47], [-1.46, 0.3, 0.28, 0.49], [-1.22, 0.52, 0.5, 0.58],
  [-0.78, 0.63, 0.61, 0.66], [-0.25, 0.6, 0.58, 0.66], [0.25, 0.5, 0.51, 0.62],
  [0.66, 0.41, 0.44, 0.6], [0.9, 0.35, 0.39, 0.62], [1.13, 0.37, 0.37, 0.67],
  [1.38, 0.3, 0.3, 0.64], [1.6, 0.18, 0.18, 0.57], [1.74, 0.08, 0.08, 0.53], [1.79, 0, 0, 0.52]];

function bodyGeometry(segs = 18, sub = 2) {
  const P = BODY, rings = (P.length - 1) * sub + 1, pos = [], idx = [];
  for (let r = 0; r < rings; r++) {
    const s = r / sub, k = Math.min(P.length - 2, Math.floor(s)), t = s - k;
    const q = (o) => P[Math.min(P.length - 1, Math.max(0, k + o))];
    const [x, w, h, c] = [0, 1, 2, 3].map((j) => catmull(q(-1)[j], q(0)[j], q(1)[j], q(2)[j], t));
    for (let j = 0; j < segs; j++) {
      const a = (j / segs) * TAU, sa = Math.sin(a);
      pos.push(x, c + Math.max(0, h) * sa * (sa < 0 ? 0.8 : 1), Math.max(0, w) * Math.cos(a));
    }
  }
  for (let r = 0; r < rings - 1; r++) {
    for (let j = 0; j < segs; j++) {
      const a = r * segs + j, b = r * segs + ((j + 1) % segs);
      idx.push(a, a + segs, b, b, a + segs, b + segs);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  const nr = g.attributes.normal; // rump and nose tips point along the axis
  for (let j = 0; j < segs; j++) { nr.setXYZ(j, -1, 0, 0); nr.setXYZ((rings - 1) * segs + j, 1, 0, 0); }
  return g;
}

function tailGeometry() {
  const pts = [[-1.44, 0.42, 0], [-1.95, 0.2, 0.03], [-2.6, 0.075, 0.12], [-3.3, 0.055, 0.08],
    [-3.95, 0.05, -0.06], [-4.5, 0.05, -0.16]].map((p) => new THREE.Vector3(...p));
  const curve = new THREE.CatmullRomCurve3(pts), N = 18, M = 6, fr = curve.computeFrenetFrames(N, false);
  const pos = [], t = [], idx = [];
  for (let i = 0; i <= N; i++) {
    const u = i / N, p = curve.getPointAt(u), r = 0.085 + (0.02 - 0.085) * u, nn = fr.normals[i], bb = fr.binormals[i];
    for (let j = 0; j < M; j++) {
      const a = (j / M) * TAU, c = Math.cos(a) * r, s = Math.sin(a) * r;
      pos.push(p.x + nn.x * c + bb.x * s, p.y + nn.y * c + bb.y * s, p.z + nn.z * c + bb.z * s);
      t.push(u);
    }
  }
  for (let i = 0; i < N; i++) {
    for (let j = 0; j < M; j++) {
      const a = i * M + j, b = i * M + ((j + 1) % M);
      idx.push(a, b, a + M, b, b + M, a + M);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return { geo: g, t };
}

function ellipsoid(rx, ry, rz, ws = 10, hs = 7) { const g = new THREE.SphereGeometry(1, ws, hs); g.scale(rx, ry, rz); return g; }

// fur: head and body; skin: ears, nose, feet and tail (part 1 tail, 2-5 feet for the gait); eyes
function mouseGeometries() {
  const skin = [];
  for (const side of [1, -1]) {
    const ear = ellipsoid(0.05, 0.27, 0.24, 12, 8);
    ear.rotateZ(0.3); ear.rotateX(0.45 * side); ear.translate(0.98, 0.97, 0.24 * side);
    skin.push({ geo: ear, color: EAR });
  }
  const nose = ellipsoid(0.05, 0.045, 0.05, 8, 6);
  nose.translate(1.785, 0.525, 0);
  skin.push({ geo: nose, color: NOSE });
  for (const [rx, ry, rz, x, z, part] of [[0.14, 0.045, 0.085, 0.7, -0.27, 2], [0.14, 0.045, 0.085, 0.7, 0.27, 3],
    [0.27, 0.05, 0.11, -0.98, -0.4, 4], [0.27, 0.05, 0.11, -0.98, 0.4, 5]]) {
    const f = ellipsoid(rx, ry, rz, 8, 5);
    f.translate(x, ry, z);
    skin.push({ geo: f, color: SKIN, part });
  }
  const tail = tailGeometry();
  skin.push({ geo: tail.geo, color: SKIN, part: 1, t: tail.t });
  const eyes = [1, -1].map((side) => { const e = ellipsoid(0.062, 0.062, 0.062, 10, 8); e.translate(1.4, 0.75, 0.215 * side); return { geo: e }; });
  return { fur: bodyGeometry(), skin: merge(skin), eyes: merge(eyes) };
}

// ------------------------------------------------------------------ textures
function canvasTexture(c, renderer, srgb = true) {
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = renderer.capabilities.getMaxAnisotropy();
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
function wireTexture(renderer) { // one cell of woven wire: white wire, clear holes
  const c = document.createElement("canvas");
  c.width = c.height = 32;
  const g = c.getContext("2d");
  g.fillStyle = "#fff";
  g.fillRect(0, 0, 32, 3); g.fillRect(0, 0, 3, 32);
  return canvasTexture(c, renderer);
}
function beddingTexture(base, dark, renderer) { // wood-shaving flecks, the same every load
  const S = 256, c = document.createElement("canvas");
  c.width = c.height = S;
  const g = c.getContext("2d"), r = rng(25);
  g.fillStyle = base; g.fillRect(0, 0, S, S);
  for (let k = 0; k < 2600; k++) {
    const x = r() * S, y = r() * S, len = 2 + r() * 6, a = r() * Math.PI, light = r() < 0.5;
    g.strokeStyle = light ? `rgba(255,248,232,${(dark ? 0.04 : 0.1) + r() * 0.12})` : `rgba(${dark ? "0,0,0" : "70,45,10"},${0.05 + r() * 0.1})`;
    g.lineWidth = 0.8 + r() * 1.4;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * len, y + Math.sin(a) * len); g.stroke();
  }
  return canvasTexture(c, renderer);
}
function ballTexture(base, line, renderer) { // an equator and a meridian, so the roll shows
  const c = document.createElement("canvas");
  c.width = 128; c.height = 64;
  const g = c.getContext("2d");
  g.fillStyle = base; g.fillRect(0, 0, 128, 64);
  g.fillStyle = line; g.fillRect(0, 29, 128, 6); g.fillRect(29, 0, 6, 64); g.fillRect(93, 0, 6, 64);
  return canvasTexture(c, renderer);
}
function labelTexture(text, color, renderer) {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d");
  g.fillStyle = color;
  g.font = '500 36px "IBM Plex Mono", ui-monospace, monospace';
  g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText(text, 32, 34);
  return canvasTexture(c, renderer);
}
function uvScale(geo, su, sv) {
  const uv = geo.attributes.uv;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * su, uv.getY(i) * sv);
  return geo;
}

// ------------------------------------------------------------------ the view
export class Pen3D {
  constructor(canvas, ui, { onSelect, onFollow } = {}) {
    this.c = canvas;
    this.ui = ui;
    this.onSelect = onSelect;
    this.onFollow = onFollow; // told when a camera preset stops following
    this.colorBy = "natural";
    this.world = null;
    this.dirty = true;
    this.sig = "";
    this.layerKey = "";
    this.tween = null;
    this.placed = new WeakMap();
    this.slotMap = new Int32Array(65536).fill(-1);
    this.gx = new Float32Array(65536); this.gz = new Float32Array(65536);
    this.gph = new Float32Array(65536); this.gamp = new Float32Array(65536);
    this.gborn = new Float32Array(65536).fill(-1e9);
    this.ghosted = [null, null, null, null];
    this.w = 0; this.h = 0;
    const r = (this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" }));
    r.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    r.shadowMap.enabled = true;
    r.shadowMap.type = THREE.PCFSoftShadowMap;
    r.toneMapping = THREE.NeutralToneMapping;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(30, 1, 0.5, 4000);
    const ct = (this.controls = new OrbitControls(this.camera, canvas));
    Object.assign(ct, { enableDamping: true, dampingFactor: 0.14, screenSpacePanning: true, maxPolarAngle: Math.PI / 2 - 0.02, minDistance: 3, maxDistance: 900 });
    ct.addEventListener("change", () => { this.dirty = true; });
    ct.addEventListener("start", () => { this.tween = null; });
    this.hemi = new THREE.HemisphereLight(0xffffff, 0x8a7d66, 1.3);
    this.sun = new THREE.DirectionalLight(0xffffff, 2.3);
    this.sun.position.set(-60, 160, 70);
    this.sun.castShadow = true;
    Object.assign(this.sun.shadow.camera, { left: -92, right: 92, top: 92, bottom: -92, near: 20, far: 460 });
    this.sun.shadow.mapSize.set(4096, 4096);
    this.sun.shadow.bias = -0.0004;
    this.sun.shadow.normalBias = 0.03;
    this.fill = new THREE.DirectionalLight(0xffffff, 0.45);
    this.fill.position.set(80, 60, -70);
    this.scene.add(this.hemi, this.sun, this.sun.target, this.fill);
    this.pen = new THREE.Group();
    this.objs = new THREE.Group();
    this.scene.add(this.pen, this.objs);
    this._makeMice(4096);
    this._makeMarker();
    this._input();
    this.retheme();
    this.view("overview", true);
  }

  // ---------------------------------------------------------------- world and theme
  setWorld(world) {
    this.world = world;
    this.W = world.width; this.H = world.height;
    this.placed = new WeakMap();
    this.gborn.fill(-1e9);
    const cap = Math.max(4096, world.run?.max_agents || 0);
    if (cap > this.cap) this._makeMice(cap);
    this._build();
    this.view("overview", true);
    this.sig = ""; this.dirty = true;
  }

  retheme() {
    const t = (this.tok = tokens());
    this.pal = palette(t);
    const [pr, pg, pb] = rgb(t.paper);
    this.dark = (0.2126 * pr + 0.7152 * pg + 0.0722 * pb) / 255 < 0.4;
    this.scene.background = new THREE.Color(t.paper);
    const C = (s) => new THREE.Color(s);
    this.cRole = this.pal.role.map(C);
    this.cSex = this.pal.sex.map(C);
    this.cAction = this.pal.action.map(C);
    this.cStress = this.pal.stress.map(C);
    this.cFur = []; // natural: pink and hairless to about day 7, furred by day 12
    for (let a = 0; a <= 12; a++) this.cFur.push(C(PUP).lerp(C(FUR), Math.min(1, Math.max(0, (a - 7) / 5))));
    this.cEye = C(EYE); this.cEyeShut = C(PUP); // eyes open at about day 13
    this.cNest = C(t.nest);
    this.cStressCell = C(t.stress); this.cInk = C(t.ink);
    this.marker.material.color.set(t.stress);
    this.stalk.material.color.set(t.stress);
    this.hemi.groundColor.set(mix(t.paper, t.ochre, 0.45));
    this.hemi.intensity = this.dark ? 1.0 : 1.3;
    this.sun.intensity = this.dark ? 1.9 : 2.3;
    if (this.world) this._build();
    this.sig = ""; this.dirty = true;
  }

  _mats() { // matte: there is no environment for metal to reflect
    const t = this.tok, dark = this.dark;
    const std = (o) => new THREE.MeshStandardMaterial({ roughness: 0.85, metalness: 0, ...o });
    return {
      wire: std({ color: dark ? t.ink3 : t.ink2, map: this.wireTex, transparent: true, depthWrite: false, side: THREE.DoubleSide, roughness: 0.5, metalness: 0.2 }),
      metal: std({ color: mix(t.paper3, t.ink3, dark ? 0.2 : 0.3), roughness: 0.6, metalness: 0.1 }),
      stand: std({ color: mix(t.ink3, t.paper3, 0.35), roughness: 0.5, metalness: 0.15 }),
      partition: std({ color: mix(t.paper3, t.ink3, 0.25), roughness: 0.8 }),
      box: std({ color: mix(t.paper2, t.nest, dark ? 0.6 : 0.5) }),
      boxFloor: std({ color: "#ffffff" }),
      food: std({ color: t.ochre, roughness: 0.95 }),
      shelf: std({ color: mix(t.paper3, t.ink3, 0.3), roughness: 0.6, metalness: 0.1 }),
      bottle: std({ color: t.slate, roughness: 0.4 }),
      spout: std({ color: t.ink2, roughness: 0.45, metalness: 0.2 }),
    };
  }

  _build() {
    disposeTree(this.pen); this.pen.clear();
    disposeTree(this.objs); this.objs.clear();
    this.objMeshes = null;
    const w = this.world, t = this.tok, W = this.W, H = this.H, cal = w.layout === "calhoun";
    this.wireTex = wireTexture(this.renderer);
    const mt = (this.mats = this._mats());
    this.ghosted = [null, null, null, null];
    // every object: its layer (null: always), its wall side (-1: none) and whether it is the
    // outline of its side, shown instead of the solid side when the camera is behind that wall
    const add = (obj, layer = null, { cast = true, receive = true } = {}, side = -1) => {
      obj.traverse((o) => { if (o.isMesh) { o.castShadow = cast && o.material !== mt.wire; o.receiveShadow = receive; } });
      obj.userData.vis = { layer, side, outline: false };
      this.pen.add(obj);
      return obj;
    };
    const P = (x, y, h = 0) => new THREE.Vector3(x - W / 2, h, H / 2 - y);
    const place = (mesh, k, along, out, h) => { // k: side; along: point on the wall line
      const s = SIDES[k], q = P(along[0], along[1], h);
      const t3 = [s.t[0], -s.t[1]], o3 = [-s.n[0], s.n[1]];
      mesh.matrixAutoUpdate = false;
      mesh.matrix.copy(basis(t3[0], t3[1], o3[0], o3[1], q.x + o3[0] * out, q.y, q.z + o3[1] * out));
      return mesh;
    };
    // floor: bedding; and a catcher for the shadows outside the pen
    const bedding = mix(t.paper, t.ochre, this.dark ? 0.2 : 0.3);
    this.beddingColor = bedding;
    const fg = uvScale(new THREE.PlaneGeometry(W, H), W / 10, H / 10);
    fg.rotateX(-Math.PI / 2);
    add(new THREE.Mesh(fg, new THREE.MeshStandardMaterial({ map: beddingTexture(bedding, this.dark, this.renderer), roughness: 1 })), null, { cast: false });
    const gg = new THREE.PlaneGeometry(1200, 1200);
    gg.rotateX(-Math.PI / 2); gg.translate(0, -0.1, 0);
    add(new THREE.Mesh(gg, new THREE.ShadowMaterial({ opacity: this.dark ? 0.3 : 0.1 })), null, { cast: false });
    // walls: the lower 37 in woven wire, the upper 17 in sheet metal
    for (let k = 0; k < 4; k++) {
      const len = k % 2 ? H : W;
      const start = [[0, 0], [W, 0], [W, H], [0, H]][k];
      const s = SIDES[k], mid = [start[0] + s.t[0] * len / 2, start[1] + s.t[1] * len / 2];
      const mesh = new THREE.Mesh(uvScale(new THREE.PlaneGeometry(len, MESH_H), len / MESH_PITCH, MESH_H / MESH_PITCH), mt.wire);
      add(place(mesh, k, mid, 0, MESH_H / 2), null, { cast: false, receive: false }, k);
      add(place(new THREE.Mesh(new THREE.BoxGeometry(len + 0.5, WALL_H - MESH_H, 0.25), mt.metal), k, mid, 0.125, (WALL_H + MESH_H) / 2), null, { cast: false }, k);
    }
    // cells: grid lines or Calhoun's low partitions, labels, ring stands
    const lineCol = mix(bedding, t.ink, this.dark ? 0.35 : 0.3);
    if (cal) {
      const L = W / 4;
      for (let c = 0; c < 16; c++) {
        const k = c >> 2, s = SIDES[k], start = [[0, 0], [W, 0], [W, H], [0, H]][k];
        const a = [start[0] + s.t[0] * (c % 4) * L, start[1] + s.t[1] * (c % 4) * L];
        const dx = W / 2 - a[0], dy = H / 2 - a[1], len = Math.hypot(dx, dy);
        const g = new THREE.BoxGeometry(len, PARTITION_H, 0.15);
        g.translate(len / 2, PARTITION_H / 2, 0);
        const m = new THREE.Mesh(g, mt.partition), q = P(a[0], a[1]);
        m.position.copy(q); m.rotation.y = Math.atan2(dy, dx);
        add(m, "cells");
      }
      const metal = mt.stand;
      const tuft = new THREE.MeshStandardMaterial({ color: mix(t.sand, t.paper, 0.35), roughness: 1, flatShading: true });
      w.rings.forEach(([rx, ry], c) => {
        const g = new THREE.Group(), base = new THREE.Mesh(new THREE.BoxGeometry(2.8, 0.2, 1.9), metal);
        base.position.y = 0.1;
        const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.13, RING_H, 10), metal);
        rod.position.set(-1.1, RING_H / 2, 0);
        const ring = new THREE.Mesh(new THREE.TorusGeometry(1.5, 0.1, 8, 28), metal);
        ring.rotation.x = Math.PI / 2; ring.position.y = RING_H;
        const tg = new THREE.IcosahedronGeometry(1.45, 1), pa = tg.attributes.position, rr = rng(100 + c);
        for (let i = 0; i < pa.count; i++) { const f = 0.82 + r01(rr) * 0.3; pa.setXYZ(i, pa.getX(i) * f, pa.getY(i) * f * 0.5, pa.getZ(i) * f); }
        tg.computeVertexNormals();
        const nest = new THREE.Mesh(tg, tuft);
        nest.position.y = RING_H + 0.45;
        g.add(base, rod, ring, nest);
        g.position.copy(P(rx, ry)); g.rotation.y = h01(c, 21) * TAU;
        add(g, "cells");
      });
    } else {
      const pts = [];
      const cw = W / (w.run?.n_cells_x || 4), ch = H / 4;
      for (let k = 1; k < 4; k++) {
        pts.push(P(k * cw, 0, 0.03), P(k * cw, H, 0.03), P(0, k * ch, 0.03), P(W, k * ch, 0.03));
      }
      const lg = new THREE.BufferGeometry().setFromPoints(pts);
      add(new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ color: lineCol })), "cells");
    }
    for (const c of w.cells) {
      const [lx, ly] = labelAt(w, c);
      const g = new THREE.PlaneGeometry(3.2, 3.2);
      g.rotateX(-Math.PI / 2);
      const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ map: labelTexture(String(c.id), t.ink3, this.renderer), transparent: true, depthWrite: false, toneMapped: false }));
      m.position.copy(P(lx + 1.2, ly - 1.2, 0.05));
      add(m, "cells", { cast: false, receive: false });
    }
    // nest boxes
    this.boxes = new Array(w.nests.length);
    this.boxSlots = new Array(w.nests.length);
    this.boxFloors = [];
    const groups = new Map(); // side (or -1) -> nest ids
    w.nests.forEach((nb, id) => {
      const k = cal ? wallOf(nb.x, nb.y, W, H) : -1;
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(id);
    });
    const tray = cal ? trayGeometry(BOX_W, BOX_D, BOX_H, 0.2) : trayGeometry(GRID_BOX, GRID_BOX, GRID_BOX_H, 0.2);
    const slab = cal ? new THREE.BoxGeometry(BOX_W - 0.4, 0.2, BOX_D - 0.4) : new THREE.BoxGeometry(GRID_BOX - 0.4, 0.2, GRID_BOX - 0.4);
    slab.translate(0, 0.1, 0);
    for (const [k, ids] of groups) {
      const walls = new THREE.InstancedMesh(tray, mt.box, ids.length);
      const floors = new THREE.InstancedMesh(slab, mt.boxFloor, ids.length);
      floors.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(ids.length * 3).fill(1), 3);
      ids.forEach((id, j) => {
        const nb = w.nests[id];
        let M, b;
        if (cal) {
          const s = SIDES[k], q = wallPoint(k, nb.x, nb.y, W, H);
          const t3 = [s.t[0], -s.t[1]], o3 = [-s.n[0], s.n[1]], y = BOX_LEVEL[nb.level] ?? 8 * (nb.level + 1);
          const c = P(q[0], q[1], y), off = 0.25 + BOX_D / 2;
          M = basis(t3[0], t3[1], o3[0], o3[1], c.x + o3[0] * off, y, c.z + o3[1] * off);
          b = { sx: nb.x, sy: nb.y, cx: c.x + o3[0] * off, cz: c.z + o3[1] * off, y: y + 0.2, w: BOX_W, d: BOX_D,
            ax: t3[0], az: t3[1], bx: o3[0], bz: o3[1], yaw: Math.atan2(-s.n[1], -s.n[0]) };
        } else {
          const c = P(nb.x, nb.y);
          M = basis(1, 0, 0, 1, c.x, 0, c.z);
          b = { sx: nb.x, sy: nb.y, cx: c.x, cz: c.z, y: 0.2, w: GRID_BOX, d: GRID_BOX, ax: 1, az: 0, bx: 0, bz: 1, yaw: null };
        }
        walls.setMatrixAt(j, M); floors.setMatrixAt(j, M);
        this.boxes[id] = b;
        this.boxSlots[id] = { mesh: floors, j };
      });
      add(walls, "nests", {}, k); add(floors, "nests", {}, k);
      this.boxFloors.push(floors);
    }
    // Calhoun: the tunnels (one per four boxes), hoppers and water platforms on the wall
    this.hoppers = []; this.waters = [];
    if (cal) {
      const seen = new Set();
      for (const nb of w.nests) {
        const key = `${nb.x.toFixed(2)},${nb.y.toFixed(2)}`;
        if (seen.has(key)) continue;
        seen.add(key);
        const k = wallOf(nb.x, nb.y, W, H), q = wallPoint(k, nb.x, nb.y, W, H);
        const g = uvScale(new THREE.CylinderGeometry(TUNNEL_R, TUNNEL_R, TUNNEL_H, 18, 1, true), (TAU * TUNNEL_R) / MESH_PITCH, TUNNEL_H / MESH_PITCH);
        add(place(new THREE.Mesh(g, mt.wire), k, q, -(TUNNEL_R + 0.12), 0.5 + TUNNEL_H / 2), "nests", { cast: false, receive: false }, k);
      }
      for (const c of w.cells) {
        // hopper: a wire box of food, its face in the pen
        const [fx, fy] = c.food, k = wallOf(fx, fy, W, H), s = SIDES[k], q = wallPoint(k, fx, fy, W, H), m = mt;
        const n3 = [s.n[0], -s.n[1]], t3 = [s.t[0], -s.t[1]];
        const hop = new THREE.Group();
        hop.add(place(new THREE.Mesh(uvScale(new THREE.BoxGeometry(HOPPER_W, HOPPER_H, HOPPER_D), HOPPER_W / MESH_PITCH, HOPPER_H / MESH_PITCH), m.wire), k, q, -HOPPER_D / 2, HOPPER_Y - HOPPER_H / 2));
        hop.add(place(new THREE.Mesh(new THREE.BoxGeometry(HOPPER_W - 0.5, HOPPER_H * 0.72, HOPPER_D - 0.5), m.food), k, q, -HOPPER_D / 2, HOPPER_Y - HOPPER_H / 2 + 0.3));
        add(hop, "hoppers", {}, k);
        const face = P(q[0], q[1], HOPPER_Y);
        this.hoppers[c.id] = { sx: fx, sy: fy, side: k, fx: face.x + n3[0] * (HOPPER_D + 0.04), fy: HOPPER_Y, fz: face.z + n3[1] * (HOPPER_D + 0.04), tx: t3[0], tz: t3[1], nx: n3[0], nz: n3[1] };
        // water: a platform above the cell's tunnels, four bottles on the wall
        const [wx, wy] = c.water, kw = wallOf(wx, wy, W, H), sw = SIDES[kw], mw = mt;
        const us = w.nests.filter((nb) => nb.cell === c.id).map((nb) => along(kw, nb.x, nb.y, W, H));
        const u0 = Math.min(...us) - TUNNEL_R - 0.5, u1 = Math.max(...us) + TUNNEL_R + 0.5, len = u1 - u0;
        const a0 = wallXY(kw, u0, W, H), am = wallXY(kw, (u0 + u1) / 2, W, H);
        const plat = new THREE.Group();
        plat.add(place(new THREE.Mesh(new THREE.BoxGeometry(len, 0.5, PLATFORM_D), mw.shelf), kw, am, -PLATFORM_D / 2, PLATFORM_Y - 0.25));
        for (let b = 0; b < 4; b++) {
          const ab = wallXY(kw, u0 + ((b + 0.5) / 4) * len, W, H);
          plat.add(place(new THREE.Mesh(new THREE.CylinderGeometry(0.85, 0.85, 5.5, 16), mw.bottle), kw, ab, -1.0, PLATFORM_Y + 1.9 + 2.75));
          plat.add(place(new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.12, 1.3, 8), mw.spout), kw, ab, -1.0, PLATFORM_Y + 1.25));
        }
        add(plat, "hoppers", {}, kw);
        const n3w = [sw.n[0], -sw.n[1]], t3w = [sw.t[0], -sw.t[1]], A = P(a0[0], a0[1]);
        this.waters[c.id] = { sx: wx, sy: wy, side: kw, ax: A.x, az: A.z, y: PLATFORM_Y, len, tx: t3w[0], tz: t3w[1], nx: n3w[0], nz: n3w[1], yaw: Math.atan2(-sw.n[1], -sw.n[0]) };
      }
    } else {
      // the frozen colony's floor points: a small wire hopper and a bottle on a stand
      for (const c of w.cells) {
        const [fx, fy] = c.food, [wx, wy] = c.water, F = P(fx, fy), Wt = P(wx, wy);
        const hop = new THREE.Group();
        const hw = new THREE.Mesh(uvScale(new THREE.BoxGeometry(1.5, 4, 1.5), 1.5 / MESH_PITCH, 4 / MESH_PITCH), mt.wire);
        hw.position.set(F.x, 2, F.z);
        const food = new THREE.Mesh(new THREE.BoxGeometry(1.1, 3.2, 1.1), mt.food);
        food.position.set(F.x, 1.7, F.z);
        const bottle = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.62, 3.2, 16), mt.bottle);
        bottle.position.set(Wt.x, 2.0, Wt.z);
        const spout = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.11, 1.0, 8), mt.spout);
        spout.position.set(Wt.x, 0.5, Wt.z);
        hop.add(food, bottle, spout);
        add(hop, "hoppers");
        add(hw, "hoppers", { cast: false, receive: false });
        this.hoppers[c.id] = { sx: fx, sy: fy, side: -1 };
        this.waters[c.id] = { sx: wx, sy: wy, side: -1 };
      }
    }
    // cell density shading (and the hovered cell)
    this.cellMeshes = w.cells.map((c) => {
      const shape = new THREE.Shape(c.poly.map(([x, y]) => new THREE.Vector2(x - W / 2, y - H / 2)));
      const g = new THREE.ShapeGeometry(shape);
      g.rotateX(-Math.PI / 2); g.translate(0, 0.04, 0);
      const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: t.stress, transparent: true, opacity: 0, depthWrite: false, toneMapped: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4 }));
      m.visible = false;
      this.pen.add(m);
      return m;
    });
    // playground: dashed outline and its objects
    if (w.playground.enabled) {
      const [x0, y0, x1, y1] = w.playground.bounds;
      const lg = new THREE.BufferGeometry().setFromPoints([P(x0, y0, 0.06), P(x1, y0, 0.06), P(x1, y1, 0.06), P(x0, y1, 0.06), P(x0, y0, 0.06)]);
      const line = new THREE.Line(lg, new THREE.LineDashedMaterial({ color: mix(bedding, t.ink, 0.6), dashSize: 1.2, gapSize: 0.9 }));
      line.computeLineDistances();
      add(line, "playground");
      this._buildObjects();
    }
    // the outline of each wall side, per layer, for the cutaway
    this.outlineMat = new THREE.LineBasicMaterial({ color: t.ink3, transparent: true, opacity: 0.6, depthWrite: false });
    for (let k = 0; k < 4; k++) {
      for (const layer of [null, "nests", "hoppers"]) {
        const objs = this.pen.children.filter((o) => o.userData.vis && o.userData.vis.side === k && o.userData.vis.layer === layer);
        if (!objs.length) continue;
        const line = this._outline(objs);
        line.userData.vis = { layer, side: k, outline: true };
        this.pen.add(line);
      }
    }
    this.boxK = new Int32Array(w.nests.length);
    this.hopK = new Int32Array(w.cells.length);
    this.watK = new Int32Array(w.cells.length);
    this.layerKey = "";
  }

  _outline(objs) { // the edges of objects, in pen coordinates, as one set of lines
    const pts = [], v = new THREE.Vector3(), m = new THREE.Matrix4();
    for (const obj of objs) {
      obj.updateMatrixWorld(true);
      obj.traverse((c) => {
        if (!c.isMesh) return;
        const e = new THREE.EdgesGeometry(c.geometry, 25), a = e.attributes.position;
        const each = (M) => { for (let i = 0; i < a.count; i++) { v.fromBufferAttribute(a, i).applyMatrix4(M); pts.push(v.x, v.y, v.z); } };
        if (c.isInstancedMesh) for (let j = 0; j < c.count; j++) { c.getMatrixAt(j, m); each(m.premultiply(c.matrixWorld)); }
        else each(c.matrixWorld);
        e.dispose();
      });
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    return new THREE.LineSegments(g, this.outlineMat);
  }

  _buildObjects() {
    const t = this.tok, w = this.world;
    const ballMat = new THREE.MeshStandardMaterial({ map: ballTexture(t.paper2, t.ink2, this.renderer), roughness: 0.55 });
    const tunMat = new THREE.MeshStandardMaterial({ color: mix(t.slate, t.paper, 0.35), roughness: 0.7, side: THREE.DoubleSide });
    const rampMat = new THREE.MeshStandardMaterial({ color: mix(t.umber, t.paper, 0.35), roughness: 0.8 });
    this.objMeshes = w.objects.map((o) => {
      let m;
      if (o.kind === "ball") {
        m = new THREE.Mesh(new THREE.SphereGeometry(o.r, 28, 18), ballMat);
        m.userData.lift = o.r;
      } else if (o.kind === "tunnel") {
        const g = new THREE.CylinderGeometry(o.r * 0.85, o.r * 0.85, o.r * 2.5, 24, 1, true, 0, Math.PI);
        g.rotateZ(Math.PI / 2);
        m = new THREE.Mesh(g, tunMat);
        m.rotation.y = h01(o.id, 31) * Math.PI;
        m.userData.lift = 0;
      } else {
        const s = new THREE.Shape([new THREE.Vector2(-o.r, 0), new THREE.Vector2(o.r, 0), new THREE.Vector2(o.r, o.r * 0.64)]);
        const g = new THREE.ExtrudeGeometry(s, { depth: o.r * 1.44, bevelEnabled: false });
        g.translate(0, 0, -o.r * 0.72);
        m = new THREE.Mesh(g, rampMat);
        m.rotation.y = h01(o.id, 32) * TAU;
        m.userData.lift = 0;
      }
      m.castShadow = true; m.receiveShadow = true;
      m.userData.last = null;
      this.objs.add(m);
      return m;
    });
  }

  // ---------------------------------------------------------------- mice
  _makeMice(cap) {
    for (const m of [this.fur, this.skin, this.eyes]) if (m) { this.scene.remove(m); m.dispose(); }
    this.cap = cap;
    const geo = (this.mouseGeo ||= mouseGeometries());
    this.matFur ||= new THREE.MeshStandardMaterial({ roughness: 0.8 });
    this.matEye ||= new THREE.MeshStandardMaterial({ roughness: 0.25 });
    if (!this.matSkin) {
      this.matSkin = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.6 });
      this.matSkin.onBeforeCompile = (sh) => {
        sh.vertexShader = sh.vertexShader
          .replace("#include <common>", "#include <common>\nattribute vec2 aGait;\nattribute float aPart;\nattribute float aT;")
          .replace("#include <begin_vertex>", `#include <begin_vertex>
            if (aPart > 0.5 && aPart < 1.5) {
              transformed.z += sin(aGait.x * 0.5 - aT * 4.5) * (0.1 + 0.22 * aGait.y) * aT * aT;
            } else if (aPart > 1.5) {
              float ph = aGait.x + ((aPart < 2.5 || aPart > 4.5) ? 0.0 : 3.14159265);
              transformed.x += sin(ph) * 0.2 * aGait.y;
              transformed.y += max(0.0, cos(ph)) * 0.07 * aGait.y;
            }`);
      };
    }
    this.fur = new THREE.InstancedMesh(geo.fur, this.matFur, cap);
    this.skin = new THREE.InstancedMesh(geo.skin, this.matSkin, cap);
    this.eyes = new THREE.InstancedMesh(geo.eyes, this.matEye, cap);
    this.fur.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.skin.instanceMatrix = this.fur.instanceMatrix; // one set of matrices for the three parts
    this.eyes.instanceMatrix = this.fur.instanceMatrix;
    this.fur.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(cap * 3), 3).setUsage(THREE.DynamicDrawUsage);
    this.eyes.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(cap * 3), 3).setUsage(THREE.DynamicDrawUsage);
    this.gait = new THREE.InstancedBufferAttribute(new Float32Array(cap * 2), 2).setUsage(THREE.DynamicDrawUsage);
    geo.skin.setAttribute("aGait", this.gait);
    for (const m of [this.fur, this.skin, this.eyes]) { m.frustumCulled = false; m.count = 0; this.scene.add(m); }
    this.fur.castShadow = this.skin.castShadow = true;
    this.fur.receiveShadow = this.skin.receiveShadow = true;
    this.drawn = { n: 0, i: new Int32Array(cap), p: new Float32Array(cap * 3) };
    this.scale = new Float32Array(400);
    for (let a = 0; a < 400; a++) this.scale[a] = 1 - 0.63 * Math.exp(-a / 21); // about 0.37 at birth
  }

  _makeMarker() {
    const g = new THREE.RingGeometry(1.0, 1.07, 56);
    g.rotateX(-Math.PI / 2);
    this.marker = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ depthTest: false, transparent: true, toneMapped: false }));
    this.marker.renderOrder = 10;
    const sg = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 1, 0)]);
    this.stalk = new THREE.Line(sg, new THREE.LineBasicMaterial({ depthTest: false, transparent: true, toneMapped: false }));
    this.stalk.renderOrder = 10;
    this.marker.visible = this.stalk.visible = false;
    this.scene.add(this.marker, this.stalk);
  }

  // where each animal of a frame is drawn: on the floor, in its box, on a hopper or a platform
  _place(f) {
    let P = this.placed.get(f);
    if (P) return P;
    const n = f.n, W = this.W, H = this.H, w = this.world, cal = w.layout === "calhoun", nc = w.cells.length;
    P = { kind: new Uint8Array(n), x: new Float32Array(n), y: new Float32Array(n), z: new Float32Array(n), yaw: new Float32Array(n), side: new Int8Array(n).fill(-1) };
    const boxK = this.boxK.fill(0), hopK = this.hopK.fill(0), watK = this.watK.fill(0);
    for (let i = 0; i < n; i++) {
      const sx = f.x[i] / 100, sy = f.y[i] / 100, slot = f.slot[i];
      let kind = FLOOR, X = sx - W / 2, Y = 0, Z = H / 2 - sy, side = -1;
      let yaw = f.heading ? (f.heading[i] / 256) * TAU : h01(slot, 1) * TAU;
      const nest = f.nest[i], b = nest >= 0 ? this.boxes[nest] : null;
      if (b && Math.abs(sx - b.sx) < AT && Math.abs(sy - b.sy) < AT) {
        const k = boxK[nest]++, layer = (k / 4) | 0, q = k % 4;
        const u = ((q & 1) - 0.5) * b.w * 0.44 + (h01(slot, 2) - 0.5) * 0.3;
        const v = ((q >> 1) - 0.5) * b.d * 0.46 + (h01(slot, 3) - 0.5) * 0.4;
        X = b.cx + b.ax * u + b.bx * v; Z = b.cz + b.az * u + b.bz * v; Y = b.y + layer * 0.5;
        yaw = b.yaw == null // square box: a pinwheel, each body across its quarter
          ? Math.atan2(-v, u) + Math.PI / 2 + (h01(slot, 5) - 0.5) * 0.5
          : b.yaw + (h01(slot, 4) < 0.5 ? 0 : Math.PI) + (h01(slot, 5) - 0.5) * 0.7;
        kind = BOX;
      } else if (f.cell[i] < nc) {
        const c = f.cell[i];
        for (let o = 0; o < (cal ? 3 : 1); o++) {
          const cc = (c + NEAR[o] + nc) % nc, hp = this.hoppers[cc], wt = this.waters[cc];
          if (Math.abs(sx - hp.sx) < AT && Math.abs(sy - hp.sy) < AT) {
            const k = hopK[cc]++;
            if (cal) {
              const layer = (k / 12) | 0, q = k % 12, u = ((q % 3) - 1) * 1.8 + (h01(slot, 6) - 0.5) * 0.4;
              const v = (((q / 3) | 0) - 1.5) * 2.2 + (h01(slot, 7) - 0.5) * 0.4, off = 0.06 + layer * 0.9;
              X = hp.fx + hp.tx * u + hp.nx * off; Z = hp.fz + hp.tz * u + hp.nz * off; Y = hp.fy + v - 1.2;
              kind = CLING; side = hp.side;
            } else {
              const a = k * 2.39996 + h01(cc, 8) * TAU, r = 1.3 + 0.6 * Math.sqrt(k);
              X = hp.sx + Math.cos(a) * r - W / 2; Z = H / 2 - (hp.sy + Math.sin(a) * r); yaw = a + Math.PI;
            }
            break;
          }
          if (Math.abs(sx - wt.sx) < AT && Math.abs(sy - wt.sy) < AT) {
            const k = watK[cc]++;
            if (cal) {
              const per = 7, row = ((k / per) | 0) % 2, layer = (k / (2 * per)) | 0, u = (((k % per) + 0.5) / per) * wt.len;
              const depth = 1.3 + row * 1.4;
              X = wt.ax + wt.tx * u + wt.nx * depth; Z = wt.az + wt.tz * u + wt.nz * depth; Y = wt.y + layer * 0.55;
              yaw = wt.yaw + (h01(slot, 9) - 0.5) * 0.5;
              kind = SHELF; side = wt.side;
            } else {
              const a = k * 2.39996 + h01(cc, 10) * TAU, r = 1.2 + 0.6 * Math.sqrt(k);
              X = wt.sx + Math.cos(a) * r - W / 2; Z = H / 2 - (wt.sy + Math.sin(a) * r); yaw = a + Math.PI;
            }
            break;
          }
        }
      }
      P.kind[i] = kind; P.x[i] = X; P.y[i] = Y; P.z[i] = Z; P.yaw[i] = yaw; P.side[i] = side;
    }
    this.placed.set(f, P);
    return P;
  }

  _mice(st) {
    const ui = this.ui, fa = st.fa, n = fa ? fa.n : 0, D = this.drawn;
    ui.selIndex = -1;
    this.selAt = null;
    if (!n) { this.fur.count = this.skin.count = this.eyes.count = 0; D.n = 0; this.marker.visible = this.stalk.visible = false; return; }
    const PA = this._place(fa), fb = st.fb, a = st.alpha || 0, map = this.slotMap;
    let PB = null;
    if (fb && a > 0) { PB = this._place(fb); for (let j = 0; j < fb.n; j++) map[fb.slot[j]] = j; }
    const E = this.fur.instanceMatrix.array, FC = this.fur.instanceColor.array, EC = this.eyes.instanceColor.array;
    const G = this.gait.array, mode = this.colorBy, hidden = ui.hidden, turn = Math.min(1, a / 0.3);
    let m = 0;
    for (let i = 0; i < n; i++) {
      const role = fa.role[i];
      if (hidden.has(role)) continue;
      const slot = fa.slot[i], age = fa.age[i];
      let kind = PA.kind[i], x = PA.x[i], y = PA.y[i], z = PA.z[i], yaw = PA.yaw[i], side = PA.side[i];
      if (PB) {
        const j = map[slot];
        const dAge = j >= 0 ? fb.age[j] - age : -1;
        if (dAge >= 0 && dAge <= 2) { // the same animal in the next frame
          if (PB.kind[j] === kind) {
            const dx = PB.x[j] - x, dz = PB.z[j] - z;
            x += dx * a; y += (PB.y[j] - y) * a; z += dz * a;
            if (fa.heading) yaw = lerpAngle(yaw, PB.yaw[j], kind === FLOOR ? turn : a);
            else if (kind === FLOOR && dx * dx + dz * dz > 1e-4) yaw = Math.atan2(-dz, dx);
          } else if (a >= 0.5) {
            kind = PB.kind[j]; x = PB.x[j]; y = PB.y[j]; z = PB.z[j]; yaw = PB.yaw[j]; side = PB.side[j];
          }
        }
      }
      const s = this.scale[Math.min(399, age)], o = m * 16;
      if (kind === CLING) { // on the hopper face: nose up, back to the pen
        const sd = SIDES[side], nx = sd.n[0], nz = -sd.n[1];
        E[o] = 0; E[o + 1] = s; E[o + 2] = 0; E[o + 3] = 0;
        E[o + 4] = nx * s; E[o + 5] = 0; E[o + 6] = nz * s; E[o + 7] = 0;
        E[o + 8] = nz * s; E[o + 9] = 0; E[o + 10] = -nx * s; E[o + 11] = 0;
        D.p[m * 3] = x + nx * 0.6 * s; D.p[m * 3 + 1] = y; D.p[m * 3 + 2] = z + nz * 0.6 * s;
      } else {
        const c = Math.cos(yaw), sn = Math.sin(yaw);
        E[o] = c * s; E[o + 1] = 0; E[o + 2] = -sn * s; E[o + 3] = 0;
        E[o + 4] = 0; E[o + 5] = s; E[o + 6] = 0; E[o + 7] = 0;
        E[o + 8] = sn * s; E[o + 9] = 0; E[o + 10] = c * s; E[o + 11] = 0;
        D.p[m * 3] = x; D.p[m * 3 + 1] = y + 0.6 * s; D.p[m * 3 + 2] = z;
      }
      E[o + 12] = x; E[o + 13] = y; E[o + 14] = z; E[o + 15] = 1;
      let col;
      if (mode === "natural") col = this.cFur[Math.min(12, age)];
      else if (mode === "role") col = this.cRole[role];
      else if (mode === "sex") col = this.cSex[fa.flags[i] & 1];
      else if (mode === "action") col = this.cAction[ACTION_GROUP[fa.action[i]] ?? 0];
      else col = this.cStress[Math.min(7, Math.floor(((fa.stress[i] * 1.5) / 255) * 8))];
      FC[m * 3] = col.r; FC[m * 3 + 1] = col.g; FC[m * 3 + 2] = col.b;
      const ce = age >= 13 ? this.cEye : this.cEyeShut;
      EC[m * 3] = ce.r; EC[m * 3 + 1] = ce.g; EC[m * 3 + 2] = ce.b;
      // gait from the drawn displacement: still when the run is still
      const born = st.t - age;
      if (Math.abs(this.gborn[slot] - born) > 1.5) {
        this.gborn[slot] = born; this.gx[slot] = x; this.gz[slot] = z; this.gph[slot] = h01(slot, 11) * TAU; this.gamp[slot] = 0;
      }
      const dist = Math.hypot(x - this.gx[slot], z - this.gz[slot]);
      if (dist < 6) {
        this.gph[slot] = (this.gph[slot] + (dist / (0.95 * s)) * Math.PI) % (4 * Math.PI);
        this.gamp[slot] += ((dist > 0.003 ? 1 : 0) - this.gamp[slot]) * 0.3;
      } else this.gamp[slot] = 0;
      this.gx[slot] = x; this.gz[slot] = z;
      G[m * 2] = this.gph[slot]; G[m * 2 + 1] = kind === FLOOR ? this.gamp[slot] : 0;
      D.i[m] = i;
      if (ui.sel && slot === ui.sel.slot && Math.abs(born - ui.sel.born) < 2.5) {
        ui.selIndex = i;
        ui.selPos = [fa.x[i] / 100, fa.y[i] / 100];
        this.selAt = new THREE.Vector3(D.p[m * 3], D.p[m * 3 + 1], D.p[m * 3 + 2]);
        this.selScale = s; this.selFloor = y;
      }
      m++;
    }
    if (PB) for (let j = 0; j < fb.n; j++) map[fb.slot[j]] = -1;
    D.n = m;
    this.fur.count = this.skin.count = this.eyes.count = m;
    this.fur.instanceMatrix.needsUpdate = true;
    this.fur.instanceColor.needsUpdate = true;
    this.eyes.instanceColor.needsUpdate = true;
    this.gait.needsUpdate = true;
    const on = !!this.selAt;
    this.marker.visible = this.stalk.visible = on;
    if (on) {
      this.marker.position.set(this.selAt.x, this.selFloor + 0.05, this.selAt.z);
      this.marker.scale.setScalar(2.0 * this.selScale);
      this.stalk.position.set(this.selAt.x, this.selAt.y + 0.9 * this.selScale, this.selAt.z);
      this.stalk.scale.set(1, 5, 1);
    }
  }

  _cells(st) {
    const ui = this.ui, ma = st.ma, w = this.world, cap = w.cell_capacity;
    this.cellMeshes.forEach((mesh, c) => {
      let op = 0, col = this.cStressCell;
      if (ui.layers.density && ma) { const v = Math.min(1, (ma.cells[c] || 0) / cap); op = 0.55 * Math.pow(v, 1.6); }
      if (c === ui.hoverCell) { op = Math.max(op, 0.12); if (!ui.layers.density) col = this.cInk; }
      mesh.visible = op >= 0.02;
      mesh.material.opacity = op;
      mesh.material.color.copy(col);
    });
    const fa = st.fa;
    if (!fa || !ui.layers.nests) return;
    const cnt = (this._cnt ||= new Uint16Array(w.nests.length));
    cnt.fill(0);
    for (let i = 0; i < fa.n; i++) { const k = fa.nest[i]; if (k >= 0 && k < cnt.length) cnt[k]++; }
    const base = (this._boxBase ||= new THREE.Color()), c = (this._boxCol ||= new THREE.Color());
    base.set(mix(this.tok.paper2, this.tok.paper3, 0.5));
    for (let k = 0; k < cnt.length; k++) {
      const bs = this.boxSlots[k];
      if (!bs) continue;
      c.copy(base).lerp(this.cNest, cnt[k] ? 0.25 + 0.65 * Math.min(1, cnt[k] / (w.nests[k].cap || 15)) : 0);
      const arr = bs.mesh.instanceColor.array;
      arr[bs.j * 3] = c.r; arr[bs.j * 3 + 1] = c.g; arr[bs.j * 3 + 2] = c.b;
    }
    for (const mesh of this.boxFloors) mesh.instanceColor.needsUpdate = true;
  }

  _objects(st) {
    if (!this.objMeshes) return;
    const oa = st.ma?.obj, ob = st.mb?.obj, a = st.alpha || 0, W = this.W, H = this.H;
    this.world.objects.forEach((o, k) => {
      const m = this.objMeshes[k];
      let x = o.x, y = o.y;
      if (oa && oa[k]) { x = oa[k][0]; y = oa[k][1]; }
      if (ob && ob[k] && a > 0) { x += (ob[k][0] - x) * a; y += (ob[k][1] - y) * a; }
      const X = x - W / 2, Z = H / 2 - y, last = m.userData.last;
      if (o.kind === "ball" && last) { // roll without slipping: turn by the distance over the radius
        const dx = X - last[0], dz = Z - last[1], d = Math.hypot(dx, dz);
        if (d > 1e-5 && d < 8) {
          const q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(dz / d, 0, -dx / d), d / o.r);
          m.quaternion.premultiply(q);
        }
      }
      m.userData.last = [X, Z];
      m.position.set(X, m.userData.lift, Z);
    });
  }

  // ---------------------------------------------------------------- layers, cutaway, camera
  _layers() { // a layer shows when it is on; a wall side solid, or in outline when cut away
    const L = this.ui.layers;
    for (const o of this.pen.children) {
      const v = o.userData.vis;
      if (!v) continue;
      const cut = v.side >= 0 && !!this.ghosted[v.side];
      o.visible = (v.layer ? !!L[v.layer] : true) && (v.outline ? cut : !cut);
    }
    this.objs.visible = !!L.playground;
  }

  _cutaway() { // a wall with the camera behind it is drawn in outline
    const p = this.camera.position, W = this.W, H = this.H;
    const x = p.x + W / 2, y = H / 2 - p.z;
    const out = [y < 0, x > W, y > H, x < 0];
    if (out.every((o, k) => o === this.ghosted[k])) return;
    this.ghosted = out;
    this._layers();
    this.dirty = true;
  }

  presets() { // camera position and target per view; hero and hero_close: the hero figure
    const S = Math.max(this.W || 101, this.H || 101) / 101;
    return {
      overview: [[62 * S, 178 * S, 172 * S], [0, 6, 2 * S]],
      top: [[0, 245 * S, 0.01], [0, 0, 0]],
      floor: [[-6 * S, 3.2, 44 * S], [4 * S, 3.0, 0]],
      hero: [[88 * S, 138 * S, 138 * S], [8 * S, 2, 15 * S]],
      hero_close: [[16 * S, 26, 30 * S], [2 * S, 0, 6 * S]],
    };
  }

  // where a preset's target falls in the current view at the given aspect (image fractions)
  locate(name, aspect) {
    const t = new THREE.Vector3(...this.presets()[name][1]), a0 = this.camera.aspect;
    this.camera.aspect = aspect;
    this.camera.updateProjectionMatrix();
    this.camera.updateMatrixWorld();
    t.project(this.camera);
    this.camera.aspect = a0;
    this.camera.updateProjectionMatrix();
    return [(t.x + 1) / 2, (1 - t.y) / 2];
  }

  // the floor that preset `from` sees (aspect af), as a polygon of fractions of preset `to`'s
  // image (aspect at); the hero figure outlines the close-up with it
  footprint(from, af, to, at) {
    const cam = this.camera, pr = this.presets();
    const keep = [cam.position.clone(), cam.quaternion.clone(), cam.aspect];
    const set = (name, aspect) => {
      cam.position.set(...pr[name][0]);
      cam.lookAt(...pr[name][1]);
      cam.aspect = aspect;
      cam.updateProjectionMatrix();
      cam.updateMatrixWorld();
    };
    set(from, af);
    const ray = new THREE.Raycaster(), floor = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), pts = [];
    for (const [x, y] of [[-1, 1], [1, 1], [1, -1], [-1, -1]]) {
      ray.setFromCamera(new THREE.Vector2(x, y), cam);
      const p = new THREE.Vector3();
      if (ray.ray.intersectPlane(floor, p)) pts.push(p);
    }
    set(to, at);
    const out = pts.map((p) => { const v = p.project(cam); return [(v.x + 1) / 2, (1 - v.y) / 2]; });
    cam.position.copy(keep[0]);
    cam.quaternion.copy(keep[1]);
    cam.aspect = keep[2];
    cam.updateProjectionMatrix();
    cam.updateMatrixWorld();
    return out;
  }

  view(name, instant = false) {
    const presets = this.presets();
    if (name === "follow" && this.selAt) {
      const dir = this.camera.position.clone().sub(this.controls.target).normalize();
      const to = this.selAt.clone();
      presets.follow = [to.clone().add(dir.multiplyScalar(26)).toArray(), to.toArray()];
    }
    const pr = presets[name];
    if (!pr) return;
    const [p, t] = pr.map((v) => new THREE.Vector3(...v));
    if (name !== "follow" && this.ui.followSel) { this.ui.followSel = false; this.onFollow?.(); }
    if (instant) { this.camera.position.copy(p); this.controls.target.copy(t); this.controls.update(); this.tween = null; }
    else this.tween = { p0: this.camera.position.clone(), t0: this.controls.target.clone(), p, t, at: performance.now(), dur: 650 };
    this.dirty = true;
  }

  _stepTween() {
    const tw = this.tween, f = Math.min(1, (performance.now() - tw.at) / tw.dur), e = f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2;
    this.camera.position.lerpVectors(tw.p0, tw.p, e);
    this.controls.target.lerpVectors(tw.t0, tw.t, e);
    if (f >= 1) this.tween = null;
    this.dirty = true;
    return true;
  }

  _follow() {
    if (!this.ui.followSel) { this.wasFollowing = false; return; }
    if (!this.selAt) return;
    if (!this.wasFollowing) { // come close once, then keep the user's angle
      this.wasFollowing = true;
      if (this.camera.position.distanceTo(this.controls.target) > 60) { this.view("follow"); return; }
    }
    if (this.tween) return;
    const d = this.selAt.clone().sub(this.controls.target);
    if (d.lengthSq() < 1e-6) return;
    d.multiplyScalar(0.3);
    this.controls.target.add(d);
    this.camera.position.add(d);
    this.dirty = true;
  }

  // a PNG of the current view at w x h pixels, rendered off the screen's size
  snapshot(w, h) {
    const r = this.renderer, ratio = r.getPixelRatio();
    r.setPixelRatio(1);
    r.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    r.render(this.scene, this.camera);
    const done = new Promise((res) => this.c.toBlob(res, "image/png")); // copies the bitmap now
    r.setPixelRatio(ratio);
    this.w = 0; this.h = 0;
    this._size();
    this.dirty = true;
    return done;
  }

  // ---------------------------------------------------------------- frame
  draw(st) {
    this._size();
    if (!this.world) { this.renderer.render(this.scene, this.camera); return; }
    let moved = this.controls.update();
    if (this.tween) moved = this._stepTween() || moved;
    const ui = this.ui;
    const lk = ["cells", "nests", "hoppers", "playground", "density"].map((k) => (ui.layers[k] ? 1 : 0)).join("");
    if (lk !== this.layerKey) { this.layerKey = lk; this._layers(); this.sig = ""; this.dirty = true; }
    this._cutaway();
    const fa = st.fa, sel = ui.sel ? `${ui.sel.slot}:${ui.sel.born}` : "";
    const sig = [st.t, st.alpha, fa ? fa.n : -1, fa ? fa.slot[0] : -1, this.colorBy, [...ui.hidden].join(","), sel, ui.hoverCell, this.layerKey].join("|");
    if (sig !== this.sig) {
      this.sig = sig;
      this._mice(st); this._cells(st); this._objects(st);
      this.dirty = true;
    }
    this._follow();
    if (!this.dirty && !moved) return;
    this.dirty = false;
    this.renderer.render(this.scene, this.camera);
  }

  _size() {
    const r = this.c.getBoundingClientRect(), w = Math.max(1, Math.round(r.width)), h = Math.max(1, Math.round(r.height));
    if (w === this.w && h === this.h) return;
    this.w = w; this.h = h;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.dirty = true;
  }

  // ---------------------------------------------------------------- input
  _input() {
    const c = this.c;
    let down = null;
    c.addEventListener("pointerdown", (e) => { down = { x: e.offsetX, y: e.offsetY, b: e.button }; });
    c.addEventListener("pointerup", (e) => {
      if (down && down.b === 0 && Math.hypot(e.offsetX - down.x, e.offsetY - down.y) < 4) this._pick(e.offsetX, e.offsetY);
      down = null;
    });
    c.addEventListener("dblclick", () => this.view("overview"));
  }

  _pick(px, py) {
    const D = this.drawn, v = new THREE.Vector3();
    let best = -1, bd = 14 * 14;
    for (let k = 0; k < D.n; k++) {
      v.set(D.p[k * 3], D.p[k * 3 + 1], D.p[k * 3 + 2]).project(this.camera);
      if (v.z > 1) continue;
      const dx = ((v.x + 1) / 2) * this.w - px, dy = ((1 - v.y) / 2) * this.h - py, q = dx * dx + dy * dy;
      if (q < bd) { bd = q; best = D.i[k]; }
    }
    this.onSelect?.(best);
  }
}

// ------------------------------------------------------------------ pen geometry helpers
function r01(r) { return r(); }
function wallOf(x, y, W, H) { // the wall a point by the wall belongs to
  const d = [y, W - x, H - y, x];
  let k = 0;
  for (let j = 1; j < 4; j++) if (d[j] < d[k]) k = j;
  return k;
}
function along(k, x, y, W, H) { return [x, y, W - x, H - y][k]; } // inches along wall k (ccw)
function wallXY(k, u, W, H) { return [[u, 0], [W, u], [W - u, H], [0, H - u]][k]; }
function wallPoint(k, x, y, W, H) { return wallXY(k, along(k, x, y, W, H), W, H); }
function labelAt(w, c) {
  if (w.layout !== "calhoun") {
    const xs = c.poly.map((p) => p[0]), ys = c.poly.map((p) => p[1]);
    return [Math.min(...xs) + 0.9, Math.max(...ys) - 0.9];
  }
  const [a, b, m] = c.poly, mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
  return [mx + (m[0] - mx) * 0.22, my + (m[1] - my) * 0.22];
}
