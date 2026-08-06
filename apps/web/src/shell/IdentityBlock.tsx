import { useQuery, useQueryClient } from "@tanstack/react-query";
import { client } from "../api/client";

// 51-operator-console.md §4.3 + §4.7. [SCOPE, this pass] `GET /session`'s
// REAL response shape (platform/gateway/src/fathom_gateway/api/v1
// /session.py::get_session_identity) is currently `{session_id,
// expires_at}` only -- its own docstring calls this a placeholder for
// 31-auth.md §3.1's real `fathom.identity` block (display_name, billet,
// authority_classes[], etc.), which needs decoding the access token's ABAC
// claims, not built yet. This component renders what the endpoint ACTUALLY
// returns today, not the wireframe's fuller (not-yet-real) fields -- doing
// otherwise would be exactly the "confident-sounding but unverified" trap
// this project's own conventions warn against.
export function IdentityBlock() {
  const queryClient = useQueryClient();
  const session = useQuery({
    queryKey: ["session"],
    queryFn: async () => {
      const { data, error, response } = await client.GET("/api/v1/gateway/session", {});
      if (error) {
        const err = new Error("session lookup failed") as Error & { status?: number };
        err.status = response.status;
        throw err;
      }
      // The real handler (api/v1/session.py::get_session_identity) returns
      // a plain dict with no Pydantic response_model, so the generated
      // type is an untyped `{}` -- this cast documents the real, narrow
      // shape rather than leaving `data` untyped.
      return data as { session_id: string; expires_at: string };
    },
  });

  async function signOut() {
    await client.POST("/api/v1/gateway/session/logout", {
      headers: { "Idempotency-Key": crypto.randomUUID() },
    });
    // §4.3: clear the entire query cache, navigate to `/`.
    await queryClient.clear();
    // Real bug, same class as client.ts's own -- a domain-absolute "/"
    // would drop this app's own base path (e.g. Domino's own
    // /apps-internal/<appId>/) the instant this is hosted anywhere but
    // the domain root.
    window.location.href = import.meta.env.BASE_URL;
  }

  if (session.isLoading) {
    return <span className="id" aria-busy="true">Loading…</span>;
  }

  const status = (session.error as { status?: number } | undefined)?.status;
  if (status === 404 || status === 401) {
    return (
      <a className="btn primary" href={`${import.meta.env.BASE_URL}api/v1/gateway/session/login`}>
        Sign in
      </a>
    );
  }
  if (session.error) {
    return (
      <span className="id" role="alert">
        <span className="chip critical">identity unavailable</span>
      </span>
    );
  }

  return (
    <span className="id">
      Session <span title={session.data?.session_id}>{session.data?.session_id?.slice(0, 8)}</span>
      <span className="chip neutral" style={{ marginLeft: 8 }}>
        demo session
      </span>
      <button type="button" className="btn ghost" style={{ marginLeft: 8 }} onClick={signOut}>
        Sign out
      </button>
    </span>
  );
}
