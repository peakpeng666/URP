import type { RunRecord } from '../data/types';

/**
 * Efficient per-slot load state for rendering. It replays the SAME validated
 * arrays the kernel already checked at load (items + assignment), so every
 * rendered state corresponds to a real record; it is a fast renderer, not a
 * second source of truth. usedBins can be cross-checked against the kernel.
 */
export class ShelfModel {
  readonly slots: number;
  readonly capacity: number;
  readonly total: number;
  private items: Int32Array;
  private assignment: Int32Array;
  loads: Float32Array;
  counts: Int32Array;
  processed = 0;
  usedBins = 0;
  volume = 0;
  /** Highest bin index touched so far (bins open roughly in order). */
  maxBin = -1;

  constructor(run: RunRecord) {
    this.slots = run.remaining.length;
    this.capacity = run.capacity;
    this.total = run.items.length;
    this.items = Int32Array.from(run.items);
    this.assignment = Int32Array.from(run.assignment);
    this.loads = new Float32Array(this.slots);
    this.counts = new Int32Array(this.slots);
  }

  private applyForward(to: number) {
    for (let i = this.processed; i < to; i += 1) {
      const bin = this.assignment[i];
      if (this.counts[bin] === 0) this.usedBins += 1;
      this.counts[bin] += 1;
      this.loads[bin] += this.items[i];
      this.volume += this.items[i];
      if (bin > this.maxBin) this.maxBin = bin;
    }
    this.processed = to;
  }

  private rebuild(to: number) {
    this.loads.fill(0);
    this.counts.fill(0);
    this.processed = 0;
    this.usedBins = 0;
    this.volume = 0;
    this.maxBin = -1;
    this.applyForward(to);
  }

  seek(t: number) {
    const target = Math.max(0, Math.min(this.total, t | 0));
    if (target === this.processed) return;
    if (target > this.processed) this.applyForward(target);
    else this.rebuild(target);
  }

  /** The bin the item at step index (0-based) went into. */
  binAt(index: number): number {
    return this.assignment[index];
  }

  itemAt(index: number): number {
    return this.items[index];
  }
}
