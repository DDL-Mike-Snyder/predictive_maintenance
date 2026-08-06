import type { RouteObject } from "react-router-dom";
import { AppShell } from "./shell/AppShell";
import { FleetRiskTriage } from "./features/pdm/FleetRiskTriage";
import { PredictionLookup } from "./features/pdm/PredictionLookup";

// 51-operator-console.md §3.1's route tree, narrowed to what's real in
// this pass -- see AppShell.tsx, FleetRiskTriage.tsx, and
// PredictionLookup.tsx's own docstrings for exactly what's omitted and why
// (sheets 01, 01B, 02, 03, 05-11, the Persona Hub, registry-backed
// IdentifierLookup -- all depend on services/composed views that don't
// exist yet in this repo). `/pdm` is sheet 04's real route.
export const routes: RouteObject[] = [
  {
    path: "/",
    element: <AppShell />,
    children: [
      { path: "pdm", element: <FleetRiskTriage /> },
      { path: "pdm/predictions", element: <PredictionLookup /> },
    ],
  },
];
