import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

// [SCOPE, this pass] Not 51-operator-console.md §4.4's `IdentifierLookup`
// (that widget looks up a NIIN/installed-item/hull against a `registry`
// service that does not exist in this repo) and not sheet 04's Fleet-Risk
// Triage (§11 -- needs a composed view, also not built). This is a small,
// real, honestly-scoped analog: a direct lookup against the one PdM
// operation the gateway's pass-through proxy actually exposes today,
// `GET /api/v1/pdm/predictions/{prediction_id}` -- exercising the real
// session-cookie -> gateway -> PdM round trip end to end, not a composed
// view or a mock.
export function PredictionLookup() {
  const [predictionId, setPredictionId] = useState("");
  const lookup = useMutation({
    mutationFn: async (id: string) => {
      // NOT client.GET(): proxy.py's own pass-through route generator
      // (platform/gateway/src/fathom_gateway/proxy.py, [SCOPE] note in its
      // module docstring) doesn't declare `{prediction_id}` as an OpenAPI
      // Parameter, so the generated type has no path-param slot to fill --
      // a real, named gap in the proxy, not something to fake client-side.
      // A plain fetch against the real, literal URL is the honest
      // workaround until that's fixed.
      const response = await fetch(
        `/api/v1/pdm/predictions/${encodeURIComponent(id)}`,
        { credentials: "same-origin" },
      );
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.title ?? `request failed (${response.status})`);
      }
      return body;
    },
  });

  return (
    <section>
      <h2>Prediction lookup</h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          lookup.mutate(predictionId);
        }}
      >
        <label htmlFor="prediction-id">Prediction ID</label>
        <input
          id="prediction-id"
          value={predictionId}
          onChange={(e) => setPredictionId(e.target.value)}
          placeholder="UUID"
        />
        <button type="submit" disabled={lookup.isPending || !predictionId}>
          Look up
        </button>
      </form>
      {lookup.isError && (
        <p role="alert">{(lookup.error as Error).message}</p>
      )}
      {lookup.isSuccess && (
        <pre>{JSON.stringify(lookup.data, null, 2)}</pre>
      )}
    </section>
  );
}
