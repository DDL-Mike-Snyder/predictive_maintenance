import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { client } from "../../api/client";

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
      // `proxy.py`'s route generator now copies each upstream operation's
      // own `path`/`query` `parameters` (and their referenced `$ref`
      // components) into the gateway's own generated openapi.json -- fixed
      // after this exact call site first hit the gap with a plain fetch()
      // workaround; the typed client works for real now.
      const { data, error, response } = await client.GET(
        "/api/v1/pdm/predictions/{prediction_id}",
        { params: { path: { prediction_id: id } } },
      );
      if (error) {
        const problem = error as { title?: string };
        throw new Error(problem.title ?? `request failed (${response.status})`);
      }
      return data;
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
