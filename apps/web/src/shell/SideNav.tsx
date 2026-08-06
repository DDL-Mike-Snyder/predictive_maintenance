import { NavLink } from "react-router-dom";

// 51-operator-console.md §4.2's exact eleven-item, four-group nav.
// [ESTABLISHED HERE, that section] `Telemetry`'s href is `/registry`
// directly (no route that bounces); `Failure Intelligence`/`Design
// Advisory` are ExternalLaunch items -- rendered here as inert (no
// apps/practitioner base URL exists in this vertical slice), visually
// distinguished per that section's own rule (`--ink-soft`, dashed
// border, no icon, never `aria-current`).
type NavEntry =
  | { kind: "route"; label: string; to: string; badge?: { tone: string; text: string } }
  | { kind: "external"; label: string };

const GROUPS: { label: string | null; items: NavEntry[] }[] = [
  { label: null, items: [{ kind: "route", label: "Fleet Status", to: "/fleet-status" }] },
  {
    label: "Asset & Condition",
    items: [
      { kind: "route", label: "Registry", to: "/registry" },
      { kind: "route", label: "Telemetry", to: "/registry" },
    ],
  },
  {
    label: "Maintenance",
    items: [
      { kind: "route", label: "Predictions", to: "/pdm" },
      { kind: "route", label: "Scheduling", to: "/maintenance" },
      { kind: "route", label: "Supply", to: "/supply" },
    ],
  },
  {
    label: "Analysis",
    items: [
      { kind: "route", label: "Post-Mission Review", to: "/pma" },
      { kind: "external", label: "Failure Intelligence" },
      { kind: "external", label: "Design Advisory" },
    ],
  },
  {
    label: "Cross-cutting",
    items: [
      {
        kind: "route",
        label: "Adjudication Queue",
        to: "/adjudication",
        badge: { tone: "warning", text: "7" },
      },
      { kind: "route", label: "Remediation Queue", to: "/audit/remediations" },
    ],
  },
];

export function SideNav() {
  return (
    <nav className="side" aria-label="Sub-applications">
      {GROUPS.map((group, i) => (
        <div key={group.label ?? `group-${i}`}>
          {group.label && <div className="group-label">{group.label}</div>}
          {group.items.map((item) =>
            item.kind === "external" ? (
              <span key={item.label} className="item external">
                {item.label}
              </span>
            ) : (
              <NavLink
                key={item.label}
                to={item.to}
                className={({ isActive }) => "item" + (isActive ? " active" : "")}
              >
                {item.label}
                {item.badge && (
                  <span className={`chip ${item.badge.tone}`} style={{ marginLeft: 6 }}>
                    {item.badge.text}
                  </span>
                )}
              </NavLink>
            ),
          )}
        </div>
      ))}
    </nav>
  );
}
