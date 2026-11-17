// Frames in the blob format of scripts/viewer_frames.py: a uint32 header length, the header
// JSON, zero bytes to a multiple of 4, then the payloads. Each payload holds n animals as
// uint16 slot, x, y (1/100 in), age (days); int16 nest; uint8 role, flags, stress, wounds,
// energy, action, cell.

export function parseBlob(buf) {
  const hlen = new DataView(buf).getUint32(0, true);
  const head = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, hlen)));
  const base = 4 + hlen + ((4 - ((4 + hlen) % 4)) % 4);
  return { head, buf, base };
}

function arrays(buf, at, n) {
  let p = at;
  const take = (Ctor, size) => {
    const a = new Ctor(buf, p, n);
    p += size * n;
    return a;
  };
  const slot = take(Uint16Array, 2);
  const x = take(Uint16Array, 2);
  const y = take(Uint16Array, 2);
  const age = take(Uint16Array, 2);
  const nest = take(Int16Array, 2);
  const role = take(Uint8Array, 1);
  const flags = take(Uint8Array, 1);
  const stress = take(Uint8Array, 1);
  const wounds = take(Uint8Array, 1);
  const energy = take(Uint8Array, 1);
  const action = take(Uint8Array, 1);
  const cell = take(Uint8Array, 1);
  return { n, slot, x, y, age, nest, role, flags, stress, wounds, energy, action, cell };
}

// All frames of one run, in time order: headers always kept, payloads while memory allows.
export class Store {
  constructor(world) {
    this.world = world;
    this.meta = [];
    this.t = [];
    this.src = []; // {buf, at} or null once dropped
    this.cache = new Map();
    this.bytes = 0;
    this.version = 0;
  }

  get length() { return this.meta.length; }
  get t0() { return this.t.length ? this.t[0] : 0; }
  get t1() { return this.t.length ? this.t[this.t.length - 1] : 0; }
  get lastIndex() { return this.meta.length ? this.meta[this.meta.length - 1].i : -1; }

  add({ head, buf, base }) {
    let added = 0;
    for (const m of head.frames) {
      const last = this.t.length ? this.t[this.t.length - 1] : -Infinity;
      if (m.t < last - 1e-9) continue;
      this.meta.push(m);
      this.t.push(m.t);
      this.src.push({ buf, at: base + m.off });
      added++;
    }
    if (added) {
      this.bytes += buf.byteLength;
      this.version++;
    }
    return added;
  }

  frame(i) {
    if (i < 0 || i >= this.meta.length) return null;
    let f = this.cache.get(i);
    if (f) return f;
    const s = this.src[i];
    if (!s) return null;
    f = arrays(s.buf, s.at, this.meta[i].n);
    if (this.cache.size > 48) this.cache.delete(this.cache.keys().next().value);
    this.cache.set(i, f);
    return f;
  }

  // largest i with t[i] <= t (0 before the first frame)
  indexAt(t) {
    const a = this.t;
    if (!a.length || t <= a[0]) return 0;
    let lo = 0, hi = a.length - 1;
    if (t >= a[hi]) return hi;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (a[mid] <= t) lo = mid; else hi = mid;
    }
    return lo;
  }

  // nearest frame at or before i whose payload is still held
  held(i) {
    for (let j = i; j >= 0; j--) if (this.src[j]) return j;
    for (let j = i + 1; j < this.src.length; j++) if (this.src[j]) return j;
    return -1;
  }

  // Live runs: past maxBytes, drop the oldest payload buffers, keeping a copy of the
  // whole-day frames so that the timeline stays browsable at a day's grain.
  prune(maxBytes) {
    if (this.bytes <= maxBytes) return;
    const seen = new Set();
    for (let i = 0; i < this.src.length && this.bytes > maxBytes * 0.8; i++) {
      const s = this.src[i];
      if (!s || seen.has(s.buf) || s.keep) continue;
      const buf = s.buf;
      seen.add(buf);
      for (let j = i; j < this.src.length; j++) {
        const sj = this.src[j];
        if (!sj || sj.buf !== buf) continue;
        const m = this.meta[j];
        if (Math.abs(m.t - Math.round(m.t)) < 1e-6 && !m.s) {
          this.src[j] = { buf: buf.slice(sj.at, sj.at + m.len), at: 0, keep: true };
        } else {
          this.src[j] = null;
        }
        this.cache.delete(j);
      }
      this.bytes -= buf.byteLength;
    }
  }
}
