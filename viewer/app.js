// Universe 25 viewer: control panel, pen view, transport and dashboard over one store of
// frames, from a recording (scripts/viewer_record.py) or a live run (scripts/viewer_serve.py).
import { parseBlob, Store } from "./codec.js";
import { ACTION_GROUP_NAMES, Pen, palette, tokens } from "./pen.js";
import { Dash } from "./dash.js";

const $ = (id) => document.getElementById(id);
const LIVE_KEEP_BYTES = 700 * 2 ** 20;
const S = {
  world: null, store: null, summary: null, src: "rec", name: "", t: 0, running: false,
  speed: 20, glide: true, span: 0, api: false, info: null, live: null, sel: null,
  lastNow: 0, lastUi: 0, lastDash: 0, lastCursor: 0, dashVersion: -1, derivedVersion: -1,
  peak: null, fine: [],
};

const pen = new Pen($("pen"), { onSelect: select, onView: scaleBar });
const dash = new Dash($("dash"), { onSeek: seek });

// ------------------------------------------------------------------ theme
function theme() {
  return document.documentElement.dataset.theme
    || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}
function syncTheme() {
  for (const b of document.querySelectorAll("[data-theme-set]")) b.setAttribute("aria-pressed", String(b.dataset.themeSet === theme()));
}
function setTheme(mode) {
  document.documentElement.dataset.theme = mode;
  try { localStorage.setItem("u25-theme", mode); } catch (e) { /* storage off */ }
  syncTheme();
  pen.retheme();
  if (S.world) { dash.build(S.world); roleChecks(); }
  legend();
  S.lastUi = 0;
}
for (const b of document.querySelectorAll("[data-theme-set]")) b.addEventListener("click", () => setTheme(b.dataset.themeSet));
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (!document.documentElement.dataset.theme) setTheme(theme()); });
syncTheme();

// ------------------------------------------------------------------ helpers
const nf = (v) => (v == null ? "–" : Math.round(v).toLocaleString("en-US"));
function clock(t) {
  const m = Math.round((t - Math.floor(t)) * 1440) % 1440;
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}
function dayText(t) { return Math.abs(t - Math.round(t)) < 1e-6 ? nf(t) : t.toFixed(2); }
function phaseAt(t) {
  const ph = S.world?.landmarks?.phases || [];
  return ph.find((p) => t >= p.from && (p.to == null || t < p.to))?.name || "";
}
function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function note(id, text, err = false) { const el = $(id); el.textContent = text; el.classList.toggle("err", err); }

// ------------------------------------------------------------------ opening a run
function openRun(world, store, { src, name, summary, span }) {
  S.world = world; S.store = store; S.src = src; S.name = name; S.summary = summary || null;
  S.span = span; S.sel = null; pen.sel = null; pen.followSel = false;
  S.dashVersion = -1; S.derivedVersion = -1;
  pen.setWorld(world);
  dash.span = span;
  dash.store = store;
  dash.build(world);
  roleChecks();
  cellRows();
  legend();
  sourceLabel();
  $("empty").hidden = true;
  for (const id of ["hudTL", "hudBL", "legend"]) $(id).hidden = false;
  $("followWrap").hidden = src !== "live";
  S.t = store.t0;
  S.lastUi = 0;
  inspector();
}

async function loadRecording(name) {
  stopPolling();
  note("recNote", `Loading ${name}…`);
  try {
    const r = await fetch(`rec/${encodeURIComponent(name)}.u25`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    openBlob(await r.arrayBuffer(), name);
  } catch (e) {
    note("recNote", `Could not load ${name}: ${e.message}`, true);
  }
}

function openBlob(buf, name) {
  const parsed = parseBlob(buf);
  const { world, summary } = parsed.head;
  if (!world) throw new Error("not a recording (no world in the header)");
  const store = new Store(world);
  store.add(parsed);
  openRun(world, store, { src: "rec", name, summary, span: store.t1 });
  setSpeed(store.t1 > 60 ? 20 : 0.1666667);
  S.running = false;
  runIcon();
  const mb = (buf.byteLength / 2 ** 20).toFixed(1);
  note("recNote", `${name}: ${nf(store.length)} frames, days ${dayText(store.t0)}–${dayText(store.t1)}, ${mb} MB.`);
}

function sourceLabel() {
  const r = S.world.run;
  const bits = [S.src === "live" ? `live · ${r.preset || ""}` : S.name, r.arm_label, `seed ${r.seed}`,
    `${nf(r.days)} d`, `${r.ticks_per_day} ticks/d`, `K ${r.free_substeps}`];
  if (r.ball_physics) bits.push("ball physics");
  if (S.world.layout === "calhoun") bits.push("Calhoun layout");
  $("sourceLabel").textContent = bits.filter(Boolean).join(" · ");
  $("roEngine").textContent = `${r.backend} · ${r.device}`;
}

// ------------------------------------------------------------------ live runs
function liveParams() {
  return {
    preset: $("lvPreset").value, seed: Number($("lvSeed").value) || 7000,
    days: Number($("lvDays").value) || 1600, backend: $("lvBackend").value,
    playground: $("lvPlayground").value, free_substeps: Number($("lvK").value),
    ball_physics: $("lvPhys").checked, sample: $("lvSample").value, rate: S.speed,
  };
}

async function startLive() {
  const p = liveParams();
  if (p.ball_physics && p.free_substeps < 2) { note("lvNote", "Ball physics runs in the free-time sub-steps: set K = 12.", true); return; }
  if (p.sample === "sub" && !p.ball_physics) { note("lvNote", "Sub-step frames need ball physics (K = 12).", true); return; }
  stopPolling();
  $("lvStart").disabled = true;
  note("lvNote", p.backend === "warp" ? "Starting; Warp compiles its kernels on first use…" : "Starting…");
  try {
    const r = await fetch("api/live", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p) });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
    const store = new Store(j.world);
    S.live = { status: j.status, follow: true, timer: null, busy: false };
    openRun(j.world, store, { src: "live", name: "live", span: j.world.run.days });
    S.running = true;
    runIcon();
    $("follow").checked = true;
    poll();
  } catch (e) {
    note("lvNote", `Could not start: ${e.message}`, true);
  } finally {
    $("lvStart").disabled = false;
    liveButtons();
  }
}

function stopPolling() {
  if (S.live?.timer) clearTimeout(S.live.timer);
  if (S.live) S.live.timer = null;
  if (S.src === "live") S.live = null;
}

async function poll() {
  const L = S.live;
  if (!L || S.src !== "live") return;
  let delay = 600;
  try {
    const r = await fetch(`api/live/frames?after=${S.store.lastIndex}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const parsed = parseBlob(await r.arrayBuffer());
    if (S.live !== L) return;
    L.status = parsed.head.status;
    const got = parsed.head.frames.length;
    if (got) { S.store.add(parsed); S.store.prune(LIVE_KEEP_BYTES); }
    const st = L.status.state;
    delay = got >= 600 ? 0 : st === "running" ? 120 : 600;
    if ((st === "finished" || st === "stopped" || st === "error") && !got) {
      liveButtons();
      if (st === "error") note("lvNote", `Run failed: ${L.status.error}`, true);
      else note("lvNote", `Run ${st} at day ${dayText(L.status.day)} with ${nf(L.status.n)} alive.`);
      return;
    }
  } catch (e) {
    note("lvNote", `Lost the server: ${e.message}`, true);
    delay = 2000;
  }
  liveButtons();
  if (S.live === L) L.timer = setTimeout(poll, delay);
}

async function control(body) {
  if (!S.api) return;
  try {
    const r = await fetch("api/live/control", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const j = await r.json();
    if (S.live && j.status) S.live.status = j.status;
  } catch (e) { /* the next poll reports it */ }
  liveButtons();
}

function liveButtons() {
  const st = S.src === "live" ? S.live?.status?.state : null;
  const active = st === "running" || st === "paused" || st === "starting";
  $("lvPause").disabled = !active;
  $("lvStop").disabled = !active;
  $("lvPause").textContent = st === "paused" ? "Resume" : "Pause";
  if (active) {
    const s = S.live.status;
    note("lvNote", `${st} · day ${dayText(s.day)} · ${nf(s.n)} alive · ${s.ticks_per_s} ticks/s · ${nf(s.frames)} frames`);
  }
}

$("lvStart").addEventListener("click", startLive);
$("lvPause").addEventListener("click", () => control({ op: S.live?.status?.state === "paused" ? "resume" : "pause" }));
$("lvStop").addEventListener("click", () => control({ op: "stop" }));
$("lvK").addEventListener("change", () => { if ($("lvK").value === "1") $("lvPhys").checked = false; });
$("lvBackend").addEventListener("change", () => {
  note("lvNote", $("lvBackend").value === "warp"
    ? "Warp runs the tick on the GPU, but its mortality and cell kernels are not at parity with NumPy (HANDOFF), so it is not the calibrated colony."
    : "NumPy is the calibrated, deterministic reference path.");
});
$("lvPhys").addEventListener("change", () => { if ($("lvPhys").checked) $("lvK").value = "12"; });

// ------------------------------------------------------------------ source tabs
function showSource(which) {
  for (const b of document.querySelectorAll("#sourceSeg button")) b.setAttribute("aria-pressed", String(b.dataset.src === which));
  $("recPanel").hidden = which !== "rec";
  $("livePanel").hidden = which !== "live";
}
for (const b of document.querySelectorAll("#sourceSeg button")) b.addEventListener("click", () => { if (!b.disabled) showSource(b.dataset.src); });
$("recLoad").addEventListener("click", () => { if ($("recSelect").value) loadRecording($("recSelect").value); });

// ------------------------------------------------------------------ transport
function setSpeed(v) {
  const sel = $("speed");
  let best = sel.options[0], bd = Infinity;
  for (const o of sel.options) { const d = Math.abs(Number(o.value) - v); if (d < bd) { bd = d; best = o; } }
  sel.value = best.value;
  S.speed = Number(best.value);
}
$("speed").addEventListener("change", () => {
  S.speed = Number($("speed").value);
  if (S.src === "live") control({ rate: S.speed });
});
$("interp").addEventListener("change", () => { S.glide = $("interp").checked; });
$("follow").addEventListener("change", () => { if (S.live) S.live.follow = $("follow").checked; });

function runIcon() {
  $("tRunIcon").innerHTML = S.running ? '<rect x="2" y="1" width="3" height="10"/><rect x="7" y="1" width="3" height="10"/>' : '<path d="M2 1v10l9-5z"/>';
  $("tRun").setAttribute("aria-label", S.running ? "Pause" : "Run");
}
function toggleRun() {
  if (!S.store) return;
  if (!S.running && S.src === "rec" && S.t >= S.store.t1 - 1e-9) S.t = S.store.t0;
  S.running = !S.running;
  runIcon();
}
function seek(day) {
  if (!S.store || !S.store.length) return;
  S.t = Math.min(S.store.t1, Math.max(S.store.t0, day));
  if (S.live) { S.live.follow = S.t >= S.store.t1 - 1e-6; $("follow").checked = S.live.follow; }
  pen.clearTrails();
  S.lastUi = 0;
}
function step(k) {
  if (!S.store) return;
  S.running = false; runIcon();
  const i = S.store.indexAt(S.t + 1e-9);
  const j = Math.min(S.store.length - 1, Math.max(0, i + k));
  seek(S.store.t[j]);
}
$("tRun").addEventListener("click", toggleRun);
$("tBack").addEventListener("click", () => step(-1));
$("tFwd").addEventListener("click", () => step(1));
$("tStart").addEventListener("click", () => seek(S.store ? S.store.t0 : 0));
$("tEnd").addEventListener("click", () => { if (S.store) { seek(S.store.t1); if (S.live) { S.live.follow = true; $("follow").checked = true; } } });
$("dashToggle").addEventListener("click", () => { $("app").classList.toggle("dash-off"); requestAnimationFrame(() => dash.resize()); });

document.addEventListener("keydown", (e) => {
  if (e.target.closest("input, select, textarea")) return;
  if (e.key === " ") { e.preventDefault(); toggleRun(); }
  else if (e.key === "ArrowLeft") step(-1);
  else if (e.key === "ArrowRight") step(1);
  else if (e.key === "Home") $("tStart").click();
  else if (e.key === "End") $("tEnd").click();
  else if (e.key === "[" || e.key === "]") {
    const sel = $("speed"), k = sel.selectedIndex + (e.key === "]" ? 1 : -1);
    if (k >= 0 && k < sel.options.length) { sel.selectedIndex = k; sel.dispatchEvent(new Event("change")); }
  } else if (e.key === "Escape") select(-1);
  else if (e.key === "f" && S.sel) { pen.followSel = !pen.followSel; S.lastUi = 0; }
});

// timeline
const tl = $("timeline");
function tlGeom() {
  const r = tl.getBoundingClientRect();
  const t0 = 0, t1 = Math.max(S.span || 0, S.store ? S.store.t1 : 1, 1);
  return { w: r.width, h: r.height, pad: 6, t0, t1 };
}
function tlDay(px) { const g = tlGeom(); return g.t0 + ((px - g.pad) / (g.w - 2 * g.pad)) * (g.t1 - g.t0); }
tl.addEventListener("pointerdown", (e) => { tl.setPointerCapture(e.pointerId); seek(tlDay(e.offsetX)); });
tl.addEventListener("pointermove", (e) => { if (e.buttons & 1) seek(tlDay(e.offsetX)); });

function drawTimeline() {
  const g = tlGeom(), dpr = window.devicePixelRatio || 1;
  tl.width = Math.round(g.w * dpr); tl.height = Math.round(g.h * dpr);
  const ctx = tl.getContext("2d"), t = pen.tok;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, g.w, g.h);
  if (!S.store) return;
  const X = (d) => g.pad + ((d - g.t0) / (g.t1 - g.t0 || 1)) * (g.w - 2 * g.pad);
  const mid = Math.round(g.h * 0.55);
  ctx.font = '9.5px "IBM Plex Mono", monospace';
  ctx.textBaseline = "top";
  (S.world.landmarks?.phases || []).forEach((p, i) => {
    const a = X(p.from), b = X(Math.min(p.to ?? g.t1, g.t1));
    if (b <= a) return;
    ctx.fillStyle = i % 2 ? t.paper : t.paper3;
    ctx.fillRect(a, mid - 4, b - a, 8);
    ctx.fillStyle = t.ink3;
    if (b - a > 16) ctx.fillText(p.name, a + 2, 2);
  });
  ctx.fillStyle = t.ink3;
  ctx.fillRect(X(S.store.t0), mid - 1, X(S.store.t1) - X(S.store.t0), 2);
  ctx.fillStyle = t.ink;
  for (const [a, b] of S.fine) ctx.fillRect(X(a), mid - 3, Math.max(2, X(b) - X(a)), 6);
  ctx.strokeStyle = t.ink3; ctx.lineWidth = 1;
  for (const [, d] of S.world.landmarks?.events || []) {
    if (d > g.t1) continue;
    ctx.beginPath(); ctx.moveTo(Math.round(X(d)) + 0.5, mid + 6); ctx.lineTo(Math.round(X(d)) + 0.5, mid + 11); ctx.stroke();
  }
  const x = Math.round(X(S.t)) + 0.5;
  ctx.strokeStyle = t.stress; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(x, 1); ctx.lineTo(x, g.h - 1); ctx.stroke();
  ctx.fillStyle = t.stress;
  ctx.beginPath(); ctx.moveTo(x - 4, 1); ctx.lineTo(x + 4, 1); ctx.lineTo(x, 6); ctx.fill();
}

// ------------------------------------------------------------------ panels
function roleChecks() {
  const box = $("roleChecks"), pal = palette(tokens());
  box.innerHTML = S.world.roles.map((name, r) => `<label class="check"><input type="checkbox" data-role="${r}" ${pen.hidden.has(r) ? "" : "checked"}><span class="sw${r === 6 ? " ring" : ""}" style="background:${pal.role[r]}"></span>${esc(name)}<span class="count" id="rc${r}">–</span></label>`).join("");
  for (const cb of box.querySelectorAll("input")) {
    cb.addEventListener("change", () => {
      const r = Number(cb.dataset.role);
      if (cb.checked) pen.hidden.delete(r); else pen.hidden.add(r);
    });
  }
}

for (const cb of document.querySelectorAll("[data-layer]")) {
  cb.addEventListener("change", () => { pen.layers[cb.dataset.layer] = cb.checked; pen.layerKey = ""; pen.clearTrails(); });
}
for (const b of document.querySelectorAll("#colorSeg button")) {
  b.addEventListener("click", () => {
    pen.colorBy = b.dataset.color;
    for (const o of document.querySelectorAll("#colorSeg button")) o.setAttribute("aria-pressed", String(o === b));
    legend();
  });
}

function legend() {
  const el = $("legend");
  if (!S.world) return;
  const tok = tokens(), pal = palette(tok);
  const dot = (c, label, cls = "") => `<span><b class="${cls}" style="background:${c}"></b>${esc(label)}</span>`;
  let items = [];
  if (pen.colorBy === "role") items = S.world.roles.map((n, r) => dot(pal.role[r], n, r === 6 ? "ring" : ""));
  else if (pen.colorBy === "sex") items = [dot(pal.sex[0], "female"), dot(pal.sex[1], "male")];
  else if (pen.colorBy === "action") items = ACTION_GROUP_NAMES.map((n, k) => dot(pal.action[k], n));
  else items = [dot(pal.stress[0], "stress 0"), dot(pal.stress[3], "0.5"), dot(pal.stress[7], "1.0 +")];
  items.push(dot(tok.ochre, "food", "sq"), dot(tok.slate, "water"), dot(tok.nest, "nest box", "sq"));
  el.innerHTML = items.join("");
}

function cellRows() {
  const body = $("cellTable").querySelector("tbody");
  body.innerHTML = S.world.cells.map((c) => `<tr data-cell="${c.id}"><td>${c.id}</td><td class="n" id="cn${c.id}">–</td><td class="bar"><i id="cb${c.id}"></i></td><td class="n" id="cs${c.id}">–</td></tr>`).join("");
  for (const tr of body.querySelectorAll("tr")) {
    tr.addEventListener("pointerenter", () => { pen.hoverCell = Number(tr.dataset.cell); });
    tr.addEventListener("pointerleave", () => { pen.hoverCell = -1; });
  }
}

function select(i) {
  const st = S.store;
  if (!st || i == null || i < 0) { S.sel = null; pen.sel = null; pen.followSel = false; inspector(); return; }
  const fa = st.frame(st.held(st.indexAt(S.t)));
  if (!fa || i >= fa.n) return;
  S.sel = { slot: fa.slot[i], born: S.t - fa.age[i] };
  pen.sel = S.sel;
  S.lastUi = 0;
}

$("inspector").addEventListener("click", (e) => {
  if (e.target.id === "selFollow") { pen.followSel = !pen.followSel; S.lastUi = 0; }
  if (e.target.id === "selClear") select(-1);
});

function inspector(fa) {
  const box = $("inspector");
  if (!S.sel) {
    box.innerHTML = '<p class="hint">Click a mouse in the pen to follow it. F follows, Esc clears.</p>';
    $("inspAside").textContent = "";
    return;
  }
  const i = pen.selIndex;
  $("inspAside").textContent = `slot ${S.sel.slot}`;
  if (!fa || i == null || i < 0 || i >= fa.n || fa.slot[i] !== S.sel.slot) {
    box.innerHTML = `<p class="hint">Not in this frame: not yet born, dead, or its slot now holds another animal (born near day ${nf(S.sel.born)}).</p><div class="row"><button class="btn" id="selClear">Clear</button></div>`;
    return;
  }
  const w = S.world, stress = (fa.stress[i] * 1.5) / 255, energy = fa.energy[i] / 255, wounds = (fa.wounds[i] * 1.5) / 255;
  const nest = fa.nest[i], cell = fa.cell[i];
  const meter = (v, cls = "") => `<span class="meter ${cls}"><i style="width:${Math.round(Math.min(1, v) * 100)}%"></i></span>`;
  const rows = [
    ["role", w.roles[fa.role[i]]],
    ["sex", fa.flags[i] & 1 ? "male" : "female"],
    ["age", `${nf(fa.age[i])} d · born day ${nf(S.t - fa.age[i])}`],
    ["stress", `${stress.toFixed(2)}${meter(stress, "stress")}`],
    ["energy", `${energy.toFixed(2)}${meter(energy)}`],
    ["wounds", wounds.toFixed(2)],
    ["decision", w.actions[fa.action[i]] || "–"],
    ["cell", cell === 255 ? "–" : String(cell)],
    ["nest box", nest < 0 ? "none" : `${nest}${w.nests[nest]?.level ? ` · level ${w.nests[nest].level}` : ""}`],
    ["playground", fa.flags[i] & 2 ? "inside" : "outside"],
    ["gestating", fa.flags[i] & 4 ? "yes" : "no"],
  ];
  box.innerHTML = `<dl class="kv">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl><div class="row"><button class="btn" id="selFollow">${pen.followSel ? "Stop following" : "Follow"}</button><button class="btn" id="selClear">Clear</button></div>`;
}

function derived() {
  const st = S.store;
  if (S.derivedVersion === st.version) return;
  S.derivedVersion = st.version;
  const L = st.length, pk = new Float64Array(L), pd = new Float64Array(L);
  let best = -1, bestDay = 0;
  for (let i = 0; i < L; i++) { if (st.meta[i].n > best) { best = st.meta[i].n; bestDay = st.t[i]; } pk[i] = best; pd[i] = bestDay; }
  S.peak = { n: pk, day: pd };
  const fine = [];
  for (let i = 0; i + 1 < L; i++) {
    if (st.t[i + 1] - st.t[i] < 0.5) {
      const last = fine[fine.length - 1];
      if (last && last[1] >= st.t[i] - 1e-9) last[1] = st.t[i + 1]; else fine.push([st.t[i], st.t[i + 1]]);
    }
  }
  S.fine = fine;
}

function colony(i, m) {
  const pct = (a, b) => (b ? ((100 * a) / b).toFixed(1) : "0.0");
  const rows = [
    ["births", nf(m.b)], ["deaths", nf(m.d)], ["conceptions", nf(m.c)],
    ["peak so far", `${nf(S.peak.n[i])} · day ${nf(S.peak.day[i])}`],
    ["withdrawn", `${nf(m.roles[6])} · ${pct(m.roles[6], m.n)} %`],
    ["in playground", `${nf(m.pg)} · ${pct(m.pg, m.n)} %`],
    ["nest boxes used", `${nf(m.nests)} / ${S.world.nests.length}`],
    ["mean stress", m.ms.toFixed(3)],
    ["mean wounds", m.mw.toFixed(3)],
  ];
  if (S.summary && S.src === "rec") rows.push(["recorded in", `${nf(S.summary.wall_seconds)} s, ${S.summary.backend}`]);
  $("colony").innerHTML = rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
}

function cells(fa, m) {
  const nc = S.world.cells.length, cap = S.world.cell_capacity;
  const sum = new Float64Array(nc);
  for (let k = 0; k < fa.n; k++) { const c = fa.cell[k]; if (c < nc) sum[c] += fa.stress[k]; }
  for (let c = 0; c < nc; c++) {
    const n = m.cells[c] || 0, v = n / cap;
    $(`cn${c}`).textContent = nf(n);
    const bar = $(`cb${c}`);
    bar.style.width = `${Math.min(100, v * 100)}%`;
    bar.classList.toggle("over", v > 1);
    $(`cs${c}`).textContent = n ? ((sum[c] * 1.5) / 255 / n).toFixed(2) : "–";
  }
  for (const tr of $("cellTable").querySelectorAll("tr[data-cell]")) tr.classList.toggle("on", Number(tr.dataset.cell) === pen.hoverCell);
}

function hud(i, m) {
  const st = S.store;
  $("roDay").textContent = dayText(S.t);
  $("roClock").textContent = clock(S.t);
  $("roN").textContent = nf(m.n);
  $("roFrame").textContent = `${nf(i + 1)} / ${nf(st.length)}`;
  if (S.src === "live" && S.live?.status) $("roRate").textContent = `${S.live.status.ticks_per_s} ticks/s`;
  else $("roRate").textContent = S.summary ? `${nf((S.summary.days_simulated * S.world.run.ticks_per_day) / Math.max(1, S.summary.wall_seconds))} ticks/s` : "–";
  const ph = phaseAt(S.t);
  const sub = m.s ? ` · sub-step ${m.s}` : "";
  $("hudTL").innerHTML = `<div class="big">Day ${dayText(S.t)} · ${clock(S.t)}</div><div>${nf(m.n)} alive${sub}</div>${ph ? `<div class="phase">Calhoun phase ${ph} (record days)</div>` : ""}`;
  for (let r = 0; r < 7; r++) { const el = $(`rc${r}`); if (el) el.textContent = nf(m.roles[r]); }
  $("rolesTotal").textContent = nf(m.n);
  $("tLabel").textContent = `${dayText(S.t)} / ${nf(Math.max(S.span, st.t1))} d`;
}

function scaleBar() {
  if (!S.world) return;
  const s = pen.s;
  const L = [1, 2, 5, 10, 20, 50].find((v) => v * s >= 50) || 50;
  $("scaleBar").style.width = `${Math.round(L * s)}px`;
  $("scaleText").textContent = `${L} in`;
}

// ------------------------------------------------------------------ main loop
function render() {
  const st = S.store;
  if (!st || !st.length) { pen.draw({}); return; }
  const ia = st.held(st.indexAt(S.t));
  if (ia < 0) return;
  const fa = st.frame(ia), ma = st.meta[ia];
  let fb = null, mb = null, alpha = 0;
  if (S.glide && ia + 1 < st.length && st.src[ia + 1]) {
    const ta = st.t[ia], tb = st.t[ia + 1];
    if (tb > ta && tb - ta <= 0.26 && S.t > ta) { fb = st.frame(ia + 1); mb = st.meta[ia + 1]; alpha = Math.min(1, (S.t - ta) / (tb - ta)); }
  }
  pen.draw({ fa, fb, ma, mb, alpha, t: S.t });
  const now = performance.now();
  if (st.version !== S.dashVersion && now - S.lastDash > (S.src === "live" ? 700 : 0)) {
    S.dashVersion = st.version; S.lastDash = now;
    dash.span = S.span;
    dash.update(st);
  }
  if (now - S.lastCursor > 60) { S.lastCursor = now; dash.setTime(S.t); }
  if (now - S.lastUi > 120) {
    S.lastUi = now;
    derived();
    hud(ia, ma);
    colony(ia, ma);
    cells(fa, ma);
    inspector(fa);
    drawTimeline();
    scaleBar();
  }
}

function loop(now) {
  const dt = S.lastNow ? Math.min(0.1, (now - S.lastNow) / 1000) : 0;
  S.lastNow = now;
  const st = S.store;
  if (st && st.length && S.running) {
    const end = st.t1;
    const following = S.src === "live" && S.live?.follow;
    if (S.speed <= 0) S.t = following ? end : Math.min(end, S.t + dt * 60);
    else S.t = Math.min(end, S.t + dt * S.speed);
    if (S.t >= end - 1e-9) {
      S.t = end;
      if (S.src === "rec") { S.running = false; runIcon(); }
      else if (S.live && !S.live.follow) { S.live.follow = true; $("follow").checked = true; }
    }
  }
  render();
  requestAnimationFrame(loop);
}

// ------------------------------------------------------------------ files and start-up
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", async (e) => {
  e.preventDefault();
  const f = e.dataTransfer?.files?.[0];
  if (!f) return;
  try { stopPolling(); openBlob(await f.arrayBuffer(), f.name.replace(/\.u25$/, "")); showSource("rec"); }
  catch (err) { note("recNote", `Could not read ${f.name}: ${err.message}`, true); }
});
window.addEventListener("resize", () => { S.lastUi = 0; });

window.u25 = { S, pen, dash, seek, select, setTheme }; // for the console

async function init() {
  try {
    const r = await fetch("api/info");
    if (r.ok) { S.info = await r.json(); S.api = true; }
  } catch (e) { /* static hosting: recordings by file only */ }
  const recSel = $("recSelect");
  const recs = S.info?.recordings || [];
  recSel.innerHTML = recs.length
    ? recs.map((r) => `<option value="${esc(r.name)}">${esc(r.name)} · ${(r.bytes / 2 ** 20).toFixed(1)} MB</option>`).join("")
    : '<option value="">no recordings found</option>';
  if (S.api) {
    $("lvPreset").innerHTML = Object.entries(S.info.presets).map(([k, p]) => `<option value="${k}">${esc(p.label)}</option>`).join("");
  } else {
    $("liveTab").disabled = true;
    $("liveTab").title = "Live runs need scripts/viewer_serve.py";
    note("recNote", "Opened without the local server: drop a .u25 recording on the window. Live runs need scripts/viewer_serve.py.");
  }
  const want = new URLSearchParams(location.search).get("rec");
  const pick = recs.find((r) => r.name === want) || recs.find((r) => r.name === "ref_7000") || recs[0];
  if (pick) { recSel.value = pick.name; loadRecording(pick.name); }
  requestAnimationFrame(loop);
}
init();
