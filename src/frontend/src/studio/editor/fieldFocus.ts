import type { FormField } from './validation';

/**
 * Scroll to and focus a fleet-parameter input in the inspector form, found by its rendered label text
 * (nth occurrence, so fleet class i maps to the i-th "车速" etc.). The form lives in panels/PlanPanels.tsx,
 * which owns its tab state; a `studio:focus-field` event is also dispatched so that panel can switch to its
 * fleet tab once it listens for it. Returns false when the field is not on screen (e.g. another tab is open).
 */
export function focusFormField(f: FormField, root: ParentNode = document): boolean {
  window.dispatchEvent(new CustomEvent('studio:focus-field', { detail: f }));
  const labels = [...root.querySelectorAll('label')].filter((l) => l.querySelector('span')?.textContent?.trim() === f.label);
  const input = labels[f.index]?.querySelector('input');
  if (!input) return false;
  input.scrollIntoView({ block: 'center', behavior: 'smooth' });
  input.focus({ preventScroll: true });
  input.select();
  return true;
}
