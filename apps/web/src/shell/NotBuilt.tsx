// A named, honest stand-in for every route this vertical slice doesn't
// build yet (registry, telemetry, scheduling, supply, pma, adjudication,
// audit/remediations -- see routes.tsx). Rendering a route at all (rather
// than omitting the nav item) is deliberate: 51-operator-console.md §4.2's
// full eleven-item nav is what gives an audience the real shape of the
// platform, even though only /pdm has a real screen behind it in this
// vertical slice.
export function NotBuilt({ label }: { label: string }) {
  return (
    <div className="box">
      <span className="box-label">{label}</span>
      <div className="box-content placeholder-fig">
        Not built in this vertical slice — only Predictive Maintenance has a real backend today.
      </div>
    </div>
  );
}
