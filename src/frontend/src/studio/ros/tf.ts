import { Matrix4, Quaternion, Vector3 } from 'three';

interface Vec { x: number; y: number; z: number }
interface Quat { x: number; y: number; z: number; w: number }
export interface TransformStamped {
  header: { frame_id: string };
  child_frame_id: string;
  transform: { translation: Vec; rotation: Quat };
}

const strip = (f: string) => f.replace(/^\//, '');
const ONE = new Vector3(1, 1, 1);

/** Latest-only TF tree (tf2 semantics: each transform is the child's pose in its parent). */
export class TfBuffer {
  private frames = new Map<string, { parent: string; m: Matrix4 }>();
  version = 0;

  update(transforms: TransformStamped[]) {
    for (const t of transforms) {
      const { translation: p, rotation: q } = t.transform;
      const m = new Matrix4().compose(new Vector3(p.x, p.y, p.z), new Quaternion(q.x, q.y, q.z, q.w), ONE);
      this.frames.set(strip(t.child_frame_id), { parent: strip(t.header.frame_id), m });
    }
    this.version++;
  }

  has(frame: string) {
    return this.frames.has(strip(frame));
  }

  /** root ← frame, or null when the chain does not reach the root. */
  lookup(frame: string, root = 'map'): Matrix4 | null {
    const m = new Matrix4();
    let f = strip(frame);
    for (let guard = 0; f !== root && guard < 64; guard++) {
      const e = this.frames.get(f);
      if (!e) return null;
      m.premultiply(e.m);
      f = e.parent;
    }
    return f === root ? m : null;
  }
}
