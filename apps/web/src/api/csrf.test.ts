import { describe, expect, it, afterEach } from "vitest";
import { csrfHeader } from "./csrf";

// Real behavior, not a mock: sets document.cookie exactly the way the
// browser would after api/v1/session.py's own `session_callback` handler
// sets `fathom_csrf` (deps.py::verify_csrf's double-submit counterpart).
describe("csrfHeader", () => {
  afterEach(() => {
    document.cookie = "fathom_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  });

  it("returns null when no fathom_csrf cookie is set", () => {
    expect(csrfHeader()).toBeNull();
  });

  it("reads and decodes the fathom_csrf cookie's value", () => {
    document.cookie = "fathom_csrf=abc%2Fdef123";
    expect(csrfHeader()).toBe("abc/def123");
  });

  it("finds fathom_csrf among several cookies", () => {
    document.cookie = "other=1";
    document.cookie = "fathom_csrf=real-token";
    document.cookie = "another=2";
    expect(csrfHeader()).toBe("real-token");
  });
});
