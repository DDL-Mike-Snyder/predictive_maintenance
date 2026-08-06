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
    window.location.href = "/";
  }

  if (session.isLoading) {
    return <div className="identity-block" aria-busy="true">Loading…</div>;
  }

  const status = (session.error as { status?: number } | undefined)?.status;
  if (status === 404 || status === 401) {
    return (
      <a className="identity-block__login" href="/api/v1/gateway/session/login">
        Sign in
      </a>
    );
  }
  if (session.error) {
    return <div className="identity-block__error" role="alert">Couldn't load identity</div>;
  }

  return (
    <div className="identity-block">
      <span title={session.data?.session_id}>Session {session.data?.session_id?.slice(0, 8)}</span>
      <button type="button" onClick={signOut}>
        Sign out
      </button>
    </div>
  );
}
