"""Document 09-monorepo-and-conventions.md §4.7. `fathom_gateway.main`
executes `app = create_app()` at MODULE level (09 §4.6's own template), so
merely IMPORTING it -- which any test file that imports `fathom_gateway
.main` will do -- requires these to already be set. Pytest imports
conftest.py before collecting sibling test files, so setting them here
(module level, not inside a fixture) is what makes that import succeed;
individual tests override with their own real `Settings()` where it
matters (see tests/integration/test_passthrough_proxy_e2e.py's own
`_gateway_settings()`). Mirrors services/pdm/tests/conftest.py's own
identical rationale.
"""

from __future__ import annotations

import os

os.environ.setdefault("FATHOM_DATABASE__URL", "sqlite+aiosqlite://")
os.environ.setdefault("FATHOM_OIDC__ISSUER", "https://test-issuer/realms/fathom")
os.environ.setdefault("FATHOM_OIDC__CLIENT_ID", "gateway")
os.environ.setdefault("FATHOM_OIDC__CLIENT_SECRET", "test-secret")
os.environ.setdefault(
    "FATHOM_OIDC__REDIRECT_URI", "https://gateway.test/api/v1/gateway/session/callback"
)
os.environ.setdefault("FATHOM_SESSION__COOKIE_SIGNING_KEY", "test-signing-key")
os.environ.setdefault("FATHOM_PDM__BASE_URL", "http://test-pdm")
os.environ.setdefault("FATHOM_PDM__OPENAPI_PATH", "../../services/pdm/openapi.json")
