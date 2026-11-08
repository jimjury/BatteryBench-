/* Browser / Node shared deterministic experiment logic. No network required. */
(function (root) {
  'use strict';
  function random(seed) {
    let state = (Number(seed) >>> 0) || 1;
    return function () {
      state += 0x6D2B79F5;
      let t = state;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function shuffle(items, seed) {
    const rng = random(seed), out = [...items];
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
  }
  function splitDemo(seed, testFraction, unit) {
    if (!['battery', 'cycle'].includes(unit)) throw Error('Unsupported split unit');
    if (!(testFraction > 0 && testFraction < 0.5)) throw Error('Invalid test fraction');
    const cells = Array.from({length: 8}, (_, i) => `CELL-${String(i + 1).padStart(2, '0')}`);
    const groups = unit === 'battery' ? cells : cells.flatMap(c => [1, 2, 3, 4].map(i => `${c}::${i}`));
    const order = shuffle(groups, seed), n = groups.length;
    const ntest = Math.max(1, Math.round(n * testFraction)), nval = Math.max(1, Math.round(n * .125));
    const assignment = {};
    order.forEach((key, i) => { assignment[key] = i < ntest ? 'test' : i < ntest + nval ? 'val' : 'train'; });
    const tiles = cells.map(id => ({
      id,
      parts: unit === 'battery' ? [assignment[id]] : [1, 2, 3, 4].map(i => assignment[`${id}::${i}`])
    }));
    const overlap = unit === 'cycle' && tiles.some(t => new Set(t.parts).size > 1);
    const counts = Object.fromEntries(['train', 'val', 'test'].map(k => [k, order.filter(v => assignment[v] === k).length]));
    return {tiles, overlap, counts, totalGroups: groups.length, unit};
  }
  function generateSignal(n = 240) {
    return Array.from({length: n}, (_, i) => {
      const soc = 1 - i / (n - 1), pulse = Math.sin(i * .14) * .045;
      const v = 3.04 + 1.12 * soc - .022 * (1.3 + pulse) + .016 * Math.sin(i * .33);
      return {index: i, v, current: -1.3 - pulse, temp: 25 + i * .003, soc};
    });
  }
  function prepareSignal({step = 1, window = 64, norm = 'raw'} = {}) {
    if (!Number.isInteger(step) || step < 1 || !Number.isInteger(window) || window < 1) throw Error('Invalid signal parameters');
    if (!['raw', 'minmax', 'standard'].includes(norm)) throw Error('Invalid normalization');
    const raw = generateSignal(), selected = raw.filter((_, i) => i % step === 0);
    // Demonstration training-only fit uses initial 70% as its training slice.
    const train = selected.slice(0, Math.max(1, Math.floor(selected.length * .7))).map(r => r.v);
    const min = Math.min(...train), max = Math.max(...train);
    const mean = train.reduce((a, b) => a + b, 0) / train.length;
    const std = Math.sqrt(train.reduce((a, b) => a + (b - mean) ** 2, 0) / train.length) || 1;
    const processed = selected.map(r => ({...r, plotted: norm === 'minmax' ? (r.v - min) / (max - min || 1) : norm === 'standard' ? (r.v - mean) / std : r.v}));
    return {raw, processed, trainingFitCount:train.length, rawRange:[Math.min(...raw.map(r=>r.v)),Math.max(...raw.map(r=>r.v))], outputRange:[Math.min(...processed.map(r=>r.plotted)),Math.max(...processed.map(r=>r.plotted))], count: processed.length, windows: Math.max(0, processed.length - window),
      shape: `[${window}, 3]`};
  }
  const MODELS = ['mean', 'ridge', 'mlp', 'cnn', 'gru', 'bilstm', 'transformer', 'rdb_attn_bilstm'];
  function experimentConfig({task = 'soc', model = 'ridge', window = 64, seed = 42, normalization = 'minmax', splitUnit = 'battery', testFraction = .25} = {}) {
    if (!['soc', 'soh', 'rul'].includes(task)) throw Error('Unsupported task');
    if (!MODELS.includes(model)) throw Error('Unsupported model');
    if (!['standard','minmax','none'].includes(normalization)) throw Error('Unsupported normalization');
    const w = Number(window), s = Number(seed), f = Number(testFraction);
    if (!Number.isInteger(w) || w < 1 || w > 512) throw Error('Window must be an integer from 1 to 512');
    if (!Number.isInteger(s) || s < 0 || s > 99999) throw Error('Seed out of range');
    if (!['battery', 'cycle'].includes(splitUnit) || (task !== 'soc' && splitUnit !== 'battery')) throw Error('SOH/RUL require battery-level split');
    if (!(f > 0 && f < .8)) throw Error('Invalid test fraction');
    return {
      task, model,
      data: {path: 'data/your_dataset.csv', phase: 'discharge', discharge_sign: 'negative', decimation_step: 1, max_gap_sec: 10, synthetic: false},
      features: {window: w, normalization},
      split: {unit: splitUnit, seed: s, val_fraction: .125, test_fraction: f},
      train: {alpha: 1.0, epochs: 12, lr: .001, hidden: 48, batch_size: 128, shuffle: false}
    };
  }
  function validReport(data) {
    if (!data || data.schema_version !== '1.0') return false;
    if (!['soc', 'soh', 'rul'].includes(data.task) || !MODELS.includes(data.model)) return false;
    if (!data.metrics || !data.by_cell || !data.split || !data.features) return false;
    return ['train', 'val', 'test'].every(k => {
      const m = data.metrics[k];
      return m && Number.isInteger(m.n) && m.n >= 0 && ['rmse', 'mae'].every(p => Number.isFinite(m[p]) && m[p] >= 0);
    });
  }
  function pretty(v, digits=4) { return Number.isFinite(v) ? Number(v).toFixed(digits) : '—'; }
  const exported = {random, shuffle, splitDemo, generateSignal, prepareSignal, experimentConfig, validReport, pretty, MODELS};
  if (typeof module !== 'undefined' && module.exports) module.exports = exported;
  root.CellCore = exported;
})(typeof window !== 'undefined' ? window : globalThis);
