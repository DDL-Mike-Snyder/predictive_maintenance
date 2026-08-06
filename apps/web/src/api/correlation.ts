// 09-monorepo-and-conventions.md §8.1 / 51-operator-console.md §2: "one
// X-Correlation-Id per user action." A per-module-load id is this pass's
// honest approximation -- true per-action correlation (a fresh id per
// button click, threaded through any resulting mutation) needs the
// outcomes.ts/mutation-tracking machinery this pass does not build (no
// composed-view or mutation surface exists yet to track).
const id = crypto.randomUUID();

export function correlationId(): string {
  return id;
}
