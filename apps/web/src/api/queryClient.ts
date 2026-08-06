import { QueryClient } from "@tanstack/react-query";

// [SCOPE, this pass] 51-operator-console.md §3.4's full freshness table is
// keyed to composed-view fragments this pass doesn't build (no `views`
// endpoint exists on the gateway yet -- deferred alongside proposals/rate
// limiting, see platform/gateway's own CLAUDE.md entry). A single
// reasonable default stands in; do not treat this as §3.4's real policy.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: false,
    },
  },
});
