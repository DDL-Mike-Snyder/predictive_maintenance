// Resolves 51-operator-console.md §2's own "BLOCKED, §23 UI-OQ-1" note.
// The double-submit token IS a real, named cookie -- `fathom_csrf`, set by
// `GET /session/callback` (platform/gateway/src/fathom_gateway/api/v1
// /session.py), deliberately NOT httponly so this exact read is possible.
// deps.py::verify_csrf compares this value against the X-Fathom-CSRF header
// api/client.ts echoes back on every non-GET request.
export function csrfHeader(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)fathom_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}
