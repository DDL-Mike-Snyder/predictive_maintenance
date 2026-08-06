import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { client } from "../../api/client";

// 51-operator-console.md §11 -- Sheet 04, Fleet-Risk Triage. Route `/pdm`.
// Markup/classes match docs/design/operator-console-wireframes.html's own
// Sheet 04 (`.sheet` > `.titleblock` + `.sheet-body` > `.box`/`.row.wrap
// -mobile` > `.col.box`), not a generic layout.
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
    return <span className="num">{row.p_failure.toFixed(2)}</span>;
  }
  if (row.reference_class === "class_estimate" && row.population_hazard_rate !== null) {
    return (
      <span className="chip neutral" style={{ whiteSpace: "normal" }}>
        uncalibrated
        <br />
        pop. hazard {row.population_hazard_rate.toFixed(4)}, n={row.calibration_population}
      </span>
    );
  }
  return <span className="chip neutral">no rate available</span>;
}

function referenceClassChipTone(row: PredictionRow): string {
  return row.fallback_level > 0 ? "warning" : "neutral";
}

function DeepDive({ row }: { row: PredictionRow }) {
  return (
    <div className="col box">
      <span className="box-label">Item deep-dive — {row.installed_item_id.slice(0, 8)}</span>
      <div className="box-content">
        {row.rul ? (
          <div className="table-scroll">
            <table className="wf">
              <caption>RUL distribution ({row.rul.unit})</caption>
              <tbody>
                <tr>
                  <th>p10</th>
                  <td className="num">{row.rul.p10}</td>
                </tr>
                <tr>
                  <th>p50</th>
                  <td className="num">{row.rul.p50}</td>
                </tr>
                <tr>
                  <th>p90</th>
                  <td className="num">{row.rul.p90}</td>
                </tr>
              </tbody>
            </table>
          </div>
        ) : (
          <p className="placeholder-fig">
            no residual-life distribution at reference class {row.reference_class}
          </p>
        )}
      </div>

      <div className="box-content" style={{ marginTop: 8 }}>
        {row.contributing_factors.length > 0 ? (
          <div className="table-scroll">
            <table className="wf">
              <caption>Contributing factor (association, not cause)</caption>
              <thead>
                <tr>
                  <th>Factor</th>
                  <th>Attribution method</th>
                  <th className="num">Stability</th>
                </tr>
              </thead>
              <tbody>
                {row.contributing_factors.map((f) => (
                  <tr key={f.factor}>
                    <td>{f.factor}</td>
                    <td>{f.attribution_method}</td>
                    <td className="num">{f.stability.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="sheet-note">—</p>
        )}
      </div>
    </div>
  );
}

function WhatIf({ row }: { row: PredictionRow }) {
  return (
    <div className="col box">
      <span className="box-label">
        What-if scenario
        <span className="chip accent" style={{ marginLeft: 6 }}>
          interactive · no latency guarantee
        </span>
      </span>
      <div className="box-content placeholder-fig">
        {row.reference_class === "item"
          ? "POST /api/v1/pdm/what-if is not built in this vertical slice (22-pdm.md §10 names the operation; no request-body schema exists yet)."
          : `What-if is unavailable — this row is not item-conditional (reference class ${row.reference_class}).`}
      </div>
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

  return (
    <section className="sheet">
      <div className="titleblock">
        <div className="tb-left">
          <span className="sheet-no">SHEET 04 / PREDICTIVE MAINTENANCE</span>
          <h2>Fleet-Risk Triage</h2>
          <span className="persona">Maintainer, Planner — ranked prediction review</span>
        </div>
        <div className="tb-right">
          Doc 03 §7.1
          <br />
          Doc 06 §3
        </div>
      </div>

      <div className="sheet-body">
        {query.isLoading && <p aria-busy="true">Loading…</p>}
        {query.isError && <p role="alert">Couldn't load predictions</p>}

        {query.data && (
          <>
            <div className="box">
              <span className="box-label">Triage — active predictions</span>
              <div className="box-content">
                <div className="row" style={{ alignItems: "center", marginBottom: 8 }}>
                  <div>
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
                  </div>
                  <p style={{ fontSize: "var(--fs-200)", color: "var(--ink-soft)", margin: 0 }}>
                    Showing {sorted.length} predictions on this page — not a fleet ranking.
                  </p>
                </div>

                <div className="table-scroll">
                  <table className="wf">
                    <thead>
                      <tr>
                        <th>NIIN</th>
                        <th>Installed item</th>
                        <th>Tier</th>
                        <th>Reference class</th>
                        <th>P(failure) / rate</th>
                        <th className="num">Horizon</th>
                        <th>Top factor</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sorted.map((row) => (
                        <tr
                          key={row.prediction_id}
                          onClick={() => setSelectedId(row.prediction_id)}
                          aria-selected={row.prediction_id === selectedId}
                          style={{
                            cursor: "pointer",
                            background:
                              row.prediction_id === selectedId ? "var(--paper-2)" : undefined,
                          }}
                        >
                          <td>{row.niin}</td>
                          <td>{row.installed_item_id.slice(0, 8)}</td>
                          <td>{row.tier}</td>
                          <td>
                            <span className={`chip ${referenceClassChipTone(row)}`}>
                              {row.reference_class}
                            </span>
                          </td>
                          <td>
                            <UncalibratedCell row={row} />
                          </td>
                          <td className="num">{row.horizon_days}d</td>
                          <td>{row.contributing_factors[0]?.factor ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <p className="sheet-note" style={{ marginTop: 8 }}>
                A null <code>p_failure</code> (calibration population &lt; 50) renders as
                "uncalibrated," never as zero risk — doc 03 §7.1.
              </p>
            </div>

            {selected ? (
              <div className="row wrap-mobile">
                <DeepDive row={selected} />
                <WhatIf row={selected} />
              </div>
            ) : (
              <p className="sheet-note">Select a row above to open its deep-dive.</p>
            )}
          </>
        )}
      </div>
    </section>
  );
}
