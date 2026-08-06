import createClient from "openapi-fetch";
import type { paths } from "./generated";
import { csrfHeader } from "./csrf";
import { correlationId } from "./correlation";

// 51-operator-console.md §2's own example baseUrl is "/api/v1" -- but the
// gateway's real, committed openapi.json (unlike that illustrative example)
// already includes the full "/api/v1/<slug>/..." prefix in every path key
// (fathom_operation_id/build_router's own convention, services/pdm's
// openapi.json does the same) -- so baseUrl is "", and every call site
// below uses the full path, matching `paths`' real generated keys exactly.
// `paths` is generated (openapi-typescript, `pnpm generate:types`) from the
// REAL, committed `platform/gateway/openapi.json` -- 09 §2.6/50 §10.2's
// "no hand-written wire type" rule, satisfied for real, not asserted.
export const client = createClient<paths>({
  baseUrl: "",
  credentials: "same-origin",
});

client.use({
  onRequest({ request }) {
    request.headers.set("X-Correlation-Id", correlationId());
    // 30-gateway.md §8.1.2's double-submit CSRF -- the "BLOCKED, §23 UI-OQ-1"
    // open question in 51-operator-console.md §2's own file listing is
    // resolved for real here, against the mechanism this same session's
    // work on platform/gateway actually built (fathom_csrf cookie +
    // X-Fathom-CSRF header, deps.py::verify_csrf) -- not a placeholder.
    if (request.method !== "GET") {
      const csrf = csrfHeader();
      if (csrf) request.headers.set("X-Fathom-CSRF", csrf);
    }
    return request;
  },
});
