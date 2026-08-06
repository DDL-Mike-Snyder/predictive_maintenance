import type { RouteObject } from "react-router-dom";
import { AppShell } from "./shell/AppShell";
import { NotBuilt } from "./shell/NotBuilt";
import { FleetRiskTriage } from "./features/pdm/FleetRiskTriage";

// 51-operator-console.md §3.1/§4.2's route tree. Every nav item in
// SideNav.tsx has a real route here -- most render `NotBuilt` (see that
// component's own docstring for why: this vertical slice only has a real
// backend for PdM). `/pdm` is Sheet 04, the one real screen.
export const routes: RouteObject[] = [
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <NotBuilt label="Persona Hub" /> },
      { path: "fleet-status", element: <NotBuilt label="Fleet Overview" /> },
      { path: "registry", element: <NotBuilt label="Asset Browser" /> },
      { path: "pdm", element: <FleetRiskTriage /> },
      { path: "maintenance", element: <NotBuilt label="Work Package Planner" /> },
      { path: "supply", element: <NotBuilt label="Supply" /> },
      { path: "pma", element: <NotBuilt label="Post-Mission Review" /> },
      { path: "adjudication", element: <NotBuilt label="Adjudication Queue" /> },
      { path: "audit/remediations", element: <NotBuilt label="Remediation Queue" /> },
    ],
  },
];
