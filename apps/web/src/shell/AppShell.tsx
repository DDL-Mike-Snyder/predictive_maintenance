import { Outlet } from "react-router-dom";
import { IdentityBlock } from "./IdentityBlock";
import { SideNav } from "./SideNav";

// 51-operator-console.md §4.1/§4.6 -- Sheet 00, the App Shell. Structure
// matches docs/design/operator-console-wireframes.html's own Sheet 00
// markup class-for-class (.classbar, .topbar, .nav-shell .side/.main).
//
// [SCOPE, this pass] Renders the full eleven-item nav (SideNav.tsx) so an
// audience sees the platform's real shape, even though only `/pdm` has a
// real screen behind it. Deliberately NOT built, named rather than
// silently dropped: `ClassificationBanner` is rendered here as WF's own
// STATIC literal text ("Unclassified — demonstration data — internal
// working draft") -- a real one derives its label from the most recently
// completed request's `X-Classification` header (§4.6 rule 2), which
// needs the response-header threading this pass doesn't build.
// `IdentifierLookup` (§4.4, a registry-backed identifier search) and
// `RateLimitNotice` (§4.7) are omitted entirely, not stubbed.
export function AppShell() {
  return (
    <div className="wrap">
      <a href="#main" className="skip-link">
        Skip to main content
      </a>
      <header className="masthead">
        <span className="classbar">
          <span className="dot" />
          Unclassified — demonstration data — internal working draft
        </span>
        <h1>FATHOM</h1>
      </header>

      <div className="topbar">
        <span className="word">FATHOM</span>
        <IdentityBlock />
      </div>
      <div className="nav-shell">
        <SideNav />
        <main id="main" className="main">
          <Outlet />
        </main>
      </div>

      <footer className="foot">
        Classification: UNCLASSIFIED // Simulated data — not an authoritative record. Doc 03 §7.3.
      </footer>
    </div>
  );
}
