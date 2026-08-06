import { Outlet, Link } from "react-router-dom";
import { IdentityBlock } from "./IdentityBlock";

// 51-operator-console.md §4.6. [SCOPE, this pass] Renders the real,
// buildable subset: SkipLink, the one <h1>, IdentityBlock, and <Outlet/>.
// Deliberately NOT built, named rather than silently dropped:
// ClassificationBanner/ClassificationFooter (need `X-Classification` off
// every response threaded through the query layer -- real work, not done
// here), IdentifierLookup (§4.4 -- its two working modes both hit a
// `registry` service that does not exist anywhere in this repo yet),
// NavBadge/proposals count (`GET /proposals/summary` doesn't exist),
// RateLimitNotice, and §4.7's "session 404 intercepts the WHOLE shell"
// rule (IdentityBlock renders its own login affordance in place; routes
// still render underneath, which is a real behavioral difference from
// what §4.7 specifies).
export function AppShell() {
  return (
    <>
      <a href="#main" className="skip-link">
        Skip to main content
      </a>
      <header>
        <h1>FATHOM</h1>
        <div className="topbar">
          <IdentityBlock />
        </div>
      </header>
      <div className="nav-shell">
        <nav aria-label="Sub-applications">
          <Link to="/pdm/predictions">Predictive Maintenance</Link>
        </nav>
        <main id="main">
          <Outlet />
        </main>
      </div>
    </>
  );
}
