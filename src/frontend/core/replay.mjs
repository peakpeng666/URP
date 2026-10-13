/** Deterministic playback of recorded assignments; no policy is evaluated here. */
export class ReplayDataError extends Error {
  constructor(message, details = {}) {
    super(message);
    this.name = 'ReplayDataError';
    this.details = details;
  }
}

const EPSILON = 1e-9;
const same = (a, b) => Math.abs(a - b) <= EPSILON;
const copy = (value) => value == null ? value : structuredClone(value);
const isSequence = (value) => Array.isArray(value) || (ArrayBuffer.isView(value) && !(value instanceof DataView));

function integer(value, label, min, max) {
  if (!Number.isSafeInteger(value) || value < min || value > max) {
    throw new RangeError(`${label} must be an integer in [${min}, ${max}]`);
  }
  return value;
}

function sequence(data, key, length, predicate) {
  const input = data[key];
  if (!isSequence(input) || input.length !== length) {
    throw new ReplayDataError(`${key}: expected ${length} values`, { field: key });
  }
  const result = new Float64Array(length);
  for (let i = 0; i < length; i += 1) {
    if (!Number.isFinite(input[i]) || !predicate(input[i], i)) {
      throw new ReplayDataError(`${key}[${i}]: invalid value`, { field: key, index: i });
    }
    result[i] = input[i];
  }
  return result;
}

function cloneCheckpoint(value) {
  return { ...value, remaining: value.remaining.slice(), counts: value.counts.slice(), feasibleTree: value.feasibleTree?.slice() ?? null };
}

function frequencyAdd(tree, residual, delta) {
  for (let i = residual + 1; i < tree.length; i += i & -i) tree[i] += delta;
}

function frequencyLessThan(tree, size) {
  let result = 0;
  for (let i = size; i > 0; i -= i & -i) result += tree[i];
  return result;
}

function validateDecision(data, n) {
  const decision = data.decision;
  const fail = (field) => { throw new ReplayDataError(`Invalid SELECTOR decision: ${field}`, { field: `decision.${field}` }); };
  if (!decision || typeof decision !== 'object' || Array.isArray(decision)) fail('missing/object');
  const numeric = (values, predicate, count) => isSequence(values) && values.length > 0
    && (count === undefined || values.length === count) && Array.from(values).every((v) => Number.isFinite(v) && predicate(v));
  // Schema v1 identifies this frozen 5000-item experiment (31 features, k=5, 144 training rows).
  // Smaller isolated fixtures retain their own feature/k dimensions for kernel unit testing.
  const official = n === 5000;
  if (!numeric(decision.features, () => true, official ? 31 : undefined)) fail('features');
  if (!numeric(decision.neighbors, (v) => Number.isSafeInteger(v) && v >= 0 && v < 144, official ? 5 : undefined)) fail('neighbors');
  if (new Set(decision.neighbors).size !== decision.neighbors.length) fail('neighbors/duplicate');
  if (!numeric(decision.squared_distances, (v) => v >= 0, decision.neighbors.length)) fail('squared_distances');
  if (decision.squared_distances.some((value, index) => index > 0 && value < decision.squared_distances[index - 1])) fail('squared_distances/order');
  if (!numeric(decision.predicted_final_bins, (v) => v >= 1 && v <= n, 2)) fail('predicted_final_bins');
  if (decision.selected_index !== 0 && decision.selected_index !== 1) fail('selected_index');
  if (decision.predicted_final_bins[decision.selected_index] > decision.predicted_final_bins[1 - decision.selected_index] + EPSILON) fail('selected_index/not-minimum');
  const branches = ['BF', 'BF_then_EoH'];
  if (data.branch != null && data.branch !== branches[decision.selected_index]) fail('selected_index/branch');
  if (data.prefix_features != null && (!numeric(data.prefix_features, () => true, decision.features.length)
    || !decision.features.every((value, index) => same(value, data.prefix_features[index])))) fail('features/prefix_features');
  if (decision.feature_names != null && (!Array.isArray(decision.feature_names) || decision.feature_names.length !== decision.features.length
    || !decision.feature_names.every((name) => typeof name === 'string' && name.length > 0))) fail('feature_names');
  if (decision.neighbor_rows != null) {
    if (!Array.isArray(decision.neighbor_rows) || decision.neighbor_rows.length !== decision.neighbors.length) fail('neighbor_rows');
    const totals = [0, 0];
    decision.neighbor_rows.forEach((row, index) => {
      if (!row || row.index !== decision.neighbors[index]) fail(`neighbor_rows[${index}].index`);
      if (!Number.isFinite(row.squared_distance) || !same(row.squared_distance, decision.squared_distances[index])) fail(`neighbor_rows[${index}].squared_distance`);
      if (typeof row.instance_id !== 'string' || !row.instance_id.startsWith('train_')) fail(`neighbor_rows[${index}].instance_id`);
      if (!numeric(row.labels, (v) => Number.isSafeInteger(v) && v >= 1 && v <= n, 2)) fail(`neighbor_rows[${index}].labels`);
      totals[0] += row.labels[0]; totals[1] += row.labels[1];
    });
    for (let i = 0; i < 2; i += 1) if (!same(totals[i] / decision.neighbor_rows.length, decision.predicted_final_bins[i])) fail('neighbor_rows/predicted_final_bins');
  }
}

export class ReplayEngine {
  #data;
  #state;
  #checkpoints = new Map();
  #checkpointInterval;
  #indicesByBin;
  #prefixVolumes;
  #decision;
  #branch;
  #prefixFeatures;
  #metadata;
  #boundary;

  constructor(data, { checkpointInterval = 250 } = {}) {
    if (!data || typeof data !== 'object' || data.schema_version !== 1) {
      throw new ReplayDataError('Unsupported or missing schema_version; expected 1');
    }
    const n = data.items?.length;
    const slots = data.remaining?.length;
    if (!Number.isSafeInteger(n) || n < 1 || !Number.isSafeInteger(slots) || slots < 1) {
      throw new ReplayDataError('items and remaining must be nonempty arrays');
    }
    if (!Number.isFinite(data.capacity) || data.capacity <= 0) {
      throw new ReplayDataError('capacity must be a positive finite number');
    }
    for (const key of ['run_id', 'instance_id', 'policy']) {
      if (typeof data[key] !== 'string' || !data[key]) throw new ReplayDataError(`${key} must be a nonempty string`);
    }
    if (data.status !== undefined && data.status !== 'complete') throw new ReplayDataError('status must be complete when provided', { field: 'status' });
    if (data.steps !== undefined && data.steps !== n) throw new ReplayDataError('steps must match items.length when provided', { field: 'steps' });
    const capacity = data.capacity;
    this.#checkpointInterval = integer(checkpointInterval, 'checkpointInterval', 1, Number.MAX_SAFE_INTEGER);
    this.#boundary = data.selector_consumed_count ?? data.switch_after ?? 500;
    if (!Number.isSafeInteger(this.#boundary) || this.#boundary < 1 || this.#boundary > n) {
      throw new ReplayDataError('selector_consumed_count/switch_after must identify a valid processed-item boundary');
    }
    if (n === 5000 && this.#boundary !== 500) throw new ReplayDataError('Schema v1 experiment requires the selection boundary at processed=500', { field: 'selector_consumed_count/switch_after' });
    this.#data = {
      items: sequence(data, 'items', n, (v) => v > 0 && v <= capacity),
      assignment: sequence(data, 'assignment', n, (v) => Number.isSafeInteger(v) && v >= 0 && v < slots),
      pre_remaining: sequence(data, 'pre_remaining', n, (v) => v >= 0 && v <= capacity),
      post_remaining: sequence(data, 'post_remaining', n, (v) => v >= 0 && v <= capacity),
      feasible_counts: sequence(data, 'feasible_counts', n, (v) => Number.isSafeInteger(v) && v >= 1 && v <= slots),
      used_bins_after: sequence(data, 'used_bins_after', n, (v) => Number.isSafeInteger(v) && v >= 1 && v <= slots),
      remaining: sequence(data, 'remaining', slots, (v) => v >= 0 && v <= capacity),
    };
    if (this.#data.feasible_counts[0] !== slots) {
      throw new ReplayDataError('feasible_counts[0] must include every initially empty slot', { field: 'feasible_counts', index: 0 });
    }
    if (data.used_bins !== undefined && (!Number.isSafeInteger(data.used_bins) || data.used_bins !== this.#data.used_bins_after[n - 1])) {
      throw new ReplayDataError('used_bins must match the recorded final used_bins_after', { field: 'used_bins' });
    }
    this.#metadata = Object.freeze({
      schemaVersion: 1, runId: data.run_id, instanceId: data.instance_id,
      policy: data.policy, capacity, totalItems: n, slotCount: slots,
    });
    if (data.decision != null && (typeof data.decision !== 'object' || Array.isArray(data.decision))) {
      throw new ReplayDataError('decision must be an object or null');
    }
    if (data.policy === 'SELECTOR') validateDecision(data, n);
    // Only known-at-boundary fields are accepted. Future outcomes never enter the decision view.
    this.#decision = data.decision == null ? null : Object.fromEntries(
      ['features', 'neighbors', 'squared_distances', 'predicted_final_bins', 'selected_index', 'neighbor_rows', 'feature_names']
        .filter((key) => Object.hasOwn(data.decision, key)).map((key) => [key, copy(data.decision[key])]),
    );
    this.#branch = data.branch ?? null;
    this.#prefixFeatures = copy(data.prefix_features ?? null);
    this.#indicesByBin = Array.from({ length: slots }, () => []);
    this.#prefixVolumes = new Float64Array(n + 1);
    for (let i = 0; i < n; i += 1) {
      this.#indicesByBin[this.#data.assignment[i]].push(i);
      this.#prefixVolumes[i + 1] = this.#prefixVolumes[i] + this.#data.items[i];
    }
    this.#state = {
      processed: 0, usedBins: 0, volume: 0,
      remaining: new Float64Array(slots).fill(capacity), counts: new Uint32Array(slots),
      feasibleTree: Number.isSafeInteger(capacity) && capacity <= 10000
        && this.#data.items.every(Number.isInteger) && this.#data.post_remaining.every(Number.isInteger)
        ? new Int32Array(capacity + 2) : null,
    };
    if (this.#state.feasibleTree) frequencyAdd(this.#state.feasibleTree, capacity, slots);
    this.#checkpoints.set(0, cloneCheckpoint(this.#state));
  }

  get processed() { return this.#state.processed; }
  get totalItems() { return this.#metadata.totalItems; }
  get metadata() { return { ...this.#metadata }; }
  get checkpointCount() { return this.#checkpoints.size; }

  #apply(state, index) {
    const bin = this.#data.assignment[index];
    const size = this.#data.items[index];
    const before = state.remaining[bin];
    const after = before - size;
    const fail = (field) => { throw new ReplayDataError(`Trajectory mismatch at item ${index + 1}: ${field}`, { index, itemNumber: index + 1, bin, field }); };
    const feasible = state.feasibleTree
      ? this.#metadata.slotCount - frequencyLessThan(state.feasibleTree, size)
      : state.remaining.reduce((count, residual) => count + (residual >= size ? 1 : 0), 0);
    if (feasible !== this.#data.feasible_counts[index]) fail('feasible_counts');
    if (!same(before, this.#data.pre_remaining[index])) fail('pre_remaining');
    if (after < -EPSILON || !same(after, this.#data.post_remaining[index])) fail('post_remaining/capacity');
    const usedBins = state.usedBins + (state.counts[bin] === 0 ? 1 : 0);
    if (usedBins !== this.#data.used_bins_after[index]) fail('used_bins_after');
    if (state.feasibleTree) {
      frequencyAdd(state.feasibleTree, before, -1);
      frequencyAdd(state.feasibleTree, after, 1);
    }
    state.remaining[bin] = after;
    state.counts[bin] += 1;
    state.usedBins = usedBins;
    state.volume += size;
    state.processed = index + 1;
  }

  /** Seek to the count of already processed items (0 means no arrivals). */
  seek(processed) {
    integer(processed, 'processed', 0, this.totalItems);
    if (processed === this.processed) return this.getState();
    let source = this.#checkpoints.get(0);
    if (this.processed <= processed) source = this.#state;
    for (const [position, checkpoint] of this.#checkpoints) {
      if (position <= processed && position > source.processed) source = checkpoint;
    }
    const next = cloneCheckpoint(source);
    const pending = [];
    for (let i = next.processed; i < processed; i += 1) {
      this.#apply(next, i);
      if (next.processed % this.#checkpointInterval === 0 || next.processed === this.#boundary) {
        if (!this.#checkpoints.has(next.processed)) pending.push([next.processed, cloneCheckpoint(next)]);
      }
    }
    if (processed === this.totalItems) {
      let residualVolume = 0;
      for (let bin = 0; bin < this.#metadata.slotCount; bin += 1) {
        if (!same(next.remaining[bin], this.#data.remaining[bin])) {
          throw new ReplayDataError(`Final remaining mismatch at bin slot ${bin}`, { field: 'remaining', bin });
        }
        residualVolume += this.#metadata.capacity - next.remaining[bin];
      }
      if (!same(residualVolume, next.volume)) throw new ReplayDataError('Final volume conservation mismatch');
    }
    // A failed seek never commits a partial state or a partial checkpoint.
    for (const [position, checkpoint] of pending) this.#checkpoints.set(position, checkpoint);
    this.#state = next;
    return this.getState();
  }

  /** Signed steps clamp at either endpoint; seek itself rejects invalid positions. */
  step(delta = 1) {
    integer(delta, 'delta', -Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER);
    return this.seek(Math.max(0, Math.min(this.totalItems, this.processed + delta)));
  }

  reset() { return this.seek(0); }

  /** Bulk current-state copies for Canvas rendering; includes every real slot. */
  snapshot() {
    return {
      processed: this.processed,
      remaining: this.#state.remaining.slice(),
      counts: this.#state.counts.slice(),
    };
  }

  getState({ retrospective = false } = {}) {
    const { processed, usedBins, volume } = this.#state;
    const known = retrospective || processed >= this.#boundary;
    const current = processed === 0 ? null : this.#item(processed - 1);
    return {
      ...this.metadata, processed, usedBins, totalVolume: volume,
      unusedCapacity: usedBins * this.#metadata.capacity - volume,
      fillRatio: usedBins === 0 ? null : volume / (usedBins * this.#metadata.capacity),
      current, activeBin: current?.bin ?? null,
      atDecisionBoundary: processed === this.#boundary,
      decisionAvailable: known && this.#decision !== null,
      decisionBoundary: this.#boundary,
      selectedBranch: known ? this.#branch : null,
      phase: this.#metadata.policy === 'published_EoH' ? 'full-policy'
        : processed < this.#boundary ? 'prefix' : processed === this.#boundary ? 'decision' : 'continuation',
      finished: processed === this.totalItems,
      mode: retrospective ? 'retrospective' : 'observed',
    };
  }

  #item(index) {
    return {
      index, itemNumber: index + 1, size: this.#data.items[index], bin: this.#data.assignment[index],
      before: this.#data.pre_remaining[index], after: this.#data.post_remaining[index],
      feasibleSlots: this.#data.feasible_counts[index],
      // Counts include unused slots. This deliberately is not called feasible used bins.
      usedBinsAfter: this.#data.used_bins_after[index],
      openedBin: index === this.#indicesByBin[this.#data.assignment[index]][0],
    };
  }

  getBin(bin, { includeItems = true } = {}) {
    integer(bin, 'bin', 0, this.#metadata.slotCount - 1);
    const count = this.#state.counts[bin];
    const result = {
      bin, count, remaining: this.#state.remaining[bin],
      load: this.#metadata.capacity - this.#state.remaining[bin],
      used: count > 0, active: this.processed > 0 && this.#data.assignment[this.processed - 1] === bin,
    };
    if (includeItems) result.items = this.#indicesByBin[bin].slice(0, count).map((index) => ({ index, itemNumber: index + 1, size: this.#data.items[index] }));
    return result;
  }

  /** Stable slot order; offset is a row offset in the filtered list, not a bin ID. */
  getBins({ offset = 0, limit = 100, usedOnly = true, includeItems = false } = {}) {
    integer(offset, 'offset', 0, Number.MAX_SAFE_INTEGER);
    integer(limit, 'limit', 0, Number.MAX_SAFE_INTEGER);
    const bins = [];
    let matching = 0;
    for (let bin = 0; bin < this.#metadata.slotCount && bins.length < limit; bin += 1) {
      if (usedOnly && this.#state.counts[bin] === 0) continue;
      if (matching++ < offset) continue;
      bins.push(this.getBin(bin, { includeItems }));
    }
    return { bins, offset, limit, total: usedOnly ? this.#state.usedBins : this.#metadata.slotCount };
  }

  getItems({ start = 0, limit = 100, retrospective = false } = {}) {
    integer(start, 'start', 0, this.totalItems);
    integer(limit, 'limit', 0, Number.MAX_SAFE_INTEGER);
    const end = Math.min(retrospective ? this.totalItems : this.processed, start + limit);
    const result = [];
    for (let i = start; i < end; i += 1) result.push(this.#item(i));
    return result;
  }

  /** Each point is exact; point 0 is the empty initial state. No future points by default. */
  getCurve({ retrospective = false } = {}) {
    const end = retrospective ? this.totalItems : this.processed;
    const result = [{ processed: 0, usedBins: 0, totalVolume: 0 }];
    for (let i = 1; i <= end; i += 1) result.push({ processed: i, usedBins: this.#data.used_bins_after[i - 1], totalVolume: this.#prefixVolumes[i] });
    return result;
  }

  getDecision({ retrospective = false } = {}) {
    if (this.#decision === null) return { available: false, reason: 'not-recorded', requiredProcessed: this.#boundary };
    if (!retrospective && this.processed < this.#boundary) return { available: false, reason: 'not-yet-observed', requiredProcessed: this.#boundary };
    return { available: true, requiredProcessed: this.#boundary, branch: this.#branch, ...copy(this.#decision), prefix_features: copy(this.#prefixFeatures) };
  }

  getFinalResult({ retrospective = false } = {}) {
    if (!retrospective && this.processed < this.totalItems) return null;
    return { usedBins: this.#data.used_bins_after[this.totalItems - 1], totalVolume: this.#prefixVolumes[this.totalItems], totalItems: this.totalItems };
  }

  /** Internal comparison guard; checks the actual item sequence as well as its identifier. */
  hasSameStream(other) {
    return other instanceof ReplayEngine && this.#metadata.instanceId === other.#metadata.instanceId
      && this.#metadata.capacity === other.#metadata.capacity && this.totalItems === other.totalItems
      && this.#data.items.every((item, i) => item === other.#data.items[i]);
  }
}

/** Owns both engines so caller actions cannot silently desynchronize their time. */
export class ReplayComparison {
  #left;
  #right;

  constructor(leftData, rightData, options) {
    this.#left = new ReplayEngine(leftData, options);
    this.#right = new ReplayEngine(rightData, options);
    if (!this.#left.hasSameStream(this.#right)) throw new ReplayDataError('Comparison requires the same instance, capacity, and complete input sequence');
  }

  get processed() { return this.#left.processed; }
  get totalItems() { return this.#left.totalItems; }

  seek(processed) {
    const previous = this.processed;
    this.#left.seek(processed);
    try { this.#right.seek(processed); }
    catch (error) { this.#left.seek(previous); throw error; }
    return this.getState();
  }

  step(delta = 1) {
    integer(delta, 'delta', -Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER);
    return this.seek(Math.max(0, Math.min(this.totalItems, this.processed + delta)));
  }

  reset() { return this.seek(0); }

  #engine(side) {
    if (side !== 'left' && side !== 'right') throw new RangeError('side must be left or right');
    return side === 'left' ? this.#left : this.#right;
  }

  getState(options) {
    const left = this.#left.getState(options);
    const right = this.#right.getState(options);
    return { processed: this.processed, totalItems: this.totalItems, left, right, deltaUsedBins: left.usedBins - right.usedBins };
  }

  getBin(side, bin, options) { return this.#engine(side).getBin(bin, options); }
  snapshot(side) { return this.#engine(side).snapshot(); }
  getBins(side, options) { return this.#engine(side).getBins(options); }
  getItems(options) { return this.#left.getItems(options); }
  getCurve(side, options) { return this.#engine(side).getCurve(options); }
  getDecision(side, options) { return this.#engine(side).getDecision(options); }
  getFinalResult(side, options) { return this.#engine(side).getFinalResult(options); }
}
