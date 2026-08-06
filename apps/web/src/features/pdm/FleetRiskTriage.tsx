import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { client } from "../../api/client";

// 51-operator-console.md §11 -- Sheet 04, Fleet-Risk Triage. Route `/pdm`.
//
// [SCOPE, this pass] Built against real backend additions made THIS pass
// (services/pdm's own GET /predictions list endpoint didn't exist before
// today -- see services/pdm/src/fathom_pdm/api/v1/predictions.py's own
// list_predictions handler). Honest simplifications, all named:
//   - No `GET /predictions/{id}/provenance` or `GET /pdm/attribution-policy`
//     -- contributing_factors are rendered directly from the list/get
//     response (added to both this pass) rather than gated on a stability-
//     floor policy fetch. §11.5's "does not render without a real
//     threshold" rule is therefore NOT enforced client-side in this pass.
//   - No `POST /pdm/what-if` -- doesn't exist in PdM at all. Box 4 renders
//     the spec's own already-sanctioned fallback (a placeholder naming why),
//     never an invented form.
//   - No `/pdm/installed-items/:id` sub-route -- the deep-dive is a
//     same-page selection, not a separate route, to avoid double-fetching
//     with no server-side single-item optimization to gain from it.
//   - No opaque cursor pagination (services/pdm's list_predictions has a
//     plain `limit`, no `cursor`/`changed_since` yet -- named in its own
//     docstring).
type PredictionRow = {
  prediction_id: string;
  asset_id: string;
  installed_item_id: string;
  niin: string;
  equipment_family: string;
  reference_class: "item" | "niin_fleet" | "equipment_family" | "class_estimate";
  p_failure: number | null;
  population_hazard_rate: number | null;
  calibration_population: number | null;
  confidence: number;
  sharpness: number;
  fallback_level: number;
  tier: number;
  horizon_days: number;
  rul: { p10: number; p50: number; p90: number; unit: string } | null;
  contributing_factors: {
    factor: string;
    contribution: number;
    attribution_method: string;
    stability: number;
    observation_ref: string;
  }[];
  model_version: string;
  computed_at: string;
  status: string;
};

type SortKey = "horizon_days" | "p_failure" | "computed_at";

function sortRows(rows: PredictionRow[], key: SortKey): PredictionRow[] {
  const copy = [...rows];
  if (key === "horizon_days") {
    // §11.2's default: soonest horizon first.
    return copy.sort((a, b) => a.horizon_days - b.horizon_days);
  }
  if (key === "computed_at") {
    return copy.sort((a, b) => b.computed_at.localeCompare(a.computed_at));
  }
  // §11.2's mandatory rule: p_failure is grouped by reference_class first,
  // never compared across classes (ui-no-cross-reference-class-sort).
  return copy.sort((a, b) => {
    if (a.reference_class !== b.reference_class) {
      return a.reference_class.localeCompare(b.reference_class);
    }
    return (b.p_failure ?? -1) - (a.p_failure ?? -1);
  });
}

// §11.4: the ONLY signal is the conjunction of p_failure===null and
// reference_class==="class_estimate" -- never a client-side n<50 check.
function UncalibratedCell({ row }: { row: PredictionRow }) {
  if (row.p_failure !== null) {
    return (
      <span>
        {row.p_failure.toFixed(2)} <small>({row.reference_class})</small>
      </span>
    );
  }
  if (row.reference_class === "class_estimate" && row.population_hazard_rate !== null) {
    return (
      <span className="chip chip--neutral">
        uncalibrated
        <br />
        pop. hazard {row.population_hazard_rate.toFixed(4)}, n={row.calibration_population}
      </span>
    );
  }
  return <span className="chip chip--neutral">no rate available</span>;
}

function DeepDive({ row }: { row: PredictionRow }) {
  return (
    <div className="col box">
      <h3>Item deep-dive — {row.installed_item_id.slice(0, 8)}</h3>
      {row.rul ? (
        <table>
          <caption>RUL distribution ({row.rul.unit})</caption>
          <tbody>
            <tr>
              <th>p10</th>
              <td>{row.rul.p10}</td>
            </tr>
            <tr>
              <th>p50</th>
              <td>{row.rul.p50}</td>
            </tr>
            <tr>
              <th>p90</th>
              <td>{row.rul.p90}</td>
            </tr>
          </tbody>
        </table>
      ) : (
        <p>no residual-life distribution at reference class {row.reference_class}</p>
      )}

      {row.contributing_factors.length > 0 ? (
        <table>
          <caption>Contributing factor (association, not cause)</caption>
          <thead>
            <tr>
              <th>Factor</th>
              <th>Attribution method</th>
              <th>Stability</th>
            </tr>
          </thead>
          <tbody>
            {row.contributing_factors.map((f) => (
              <tr key={f.factor}>
                <td>{f.factor}</td>
                <td>{f.attribution_method}</td>
                <td>{f.stability.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>—</p>
      )}

      <section className="col box">
        <h3>What-if scenario</h3>
        <span className="chip chip--neutral">interactive · no latency guarantee</span>
        {row.reference_class === "item" ? (
          <p>
            <em>
              POST /api/v1/pdm/what-if is not built in this vertical slice (22-pdm.md §10 names the
              operation; no request-body schema exists yet). This box intentionally has no form.
            </em>
          </p>
        ) : (
          <p>What-if is unavailable — this row is not item-conditional (reference class {row.reference_class}).</p>
        )}
      </section>
    </div>
  );
}

export function FleetRiskTriage() {
  const [sortKey, setSortKey] = useState<SortKey>("horizon_days");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["pdm", "predictions"],
    queryFn: async () => {
      const { data, error, response } = await client.GET("/api/v1/pdm/predictions", {});
      if (error) throw new Error(`request failed (${response.status})`);
      return (data as { predictions: PredictionRow[] }).predictions;
    },
  });

  const sorted = useMemo(() => sortRows(query.data ?? [], sortKey), [query.data, sortKey]);
  const selected = sorted.find((r) => r.prediction_id === selectedId) ?? null;

  if (query.isLoading) return <p aria-busy="true">Loading…</p>;
  if (query.isError) return <p role="alert">Couldn't load predictions</p>;

  return (
    <section>
      <div className="box">
        <h2>Triage — active predictions</h2>
        <p className="sheet-note">
          A null p_failure (calibration population &lt; 50) renders as "uncalibrated," never as zero
          risk — doc 03 §7.1.
        </p>
        <label htmlFor="sort-key">Sort by</label>
        <select
          id="sort-key"
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as SortKey)}
        >
          <option value="horizon_days">Horizon (soonest first)</option>
          <option value="p_failure">P(failure), within reference class</option>
          <option value="computed_at">Most recently computed</option>
        </select>
        <caption>Showing {sorted.length} predictions on this page — not a fleet ranking.</caption>

        <table>
          <thead>
            <tr>
              <th>NIIN</th>
              <th>Installed item</th>
              <th>Tier</th>
              <th>Reference class</th>
              <th>P(failure) / rate</th>
              <th>Horizon</th>
              <th>Top factor</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <tr
                key={row.prediction_id}
                onClick={() => setSelectedId(row.prediction_id)}
                aria-selected={row.prediction_id === selectedId}
                style={{ cursor: "pointer" }}
              >
                <td>{row.niin}</td>
                <td>{row.installed_item_id.slice(0, 8)}</td>
                <td>{row.tier}</td>
                <td className="chip chip--neutral">{row.reference_class}</td>
                <td>
                  <UncalibratedCell row={row} />
                </td>
                <td>{row.horizon_days}d</td>
                <td>{row.contributing_factors[0]?.factor ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && <DeepDive row={selected} />}
    </section>
  );
}
