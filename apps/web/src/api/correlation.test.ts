import { describe, expect, it } from "vitest";
import { correlationId } from "./correlation";

describe("correlationId", () => {
  it("returns a stable, real UUID for the lifetime of the module", () => {
    const first = correlationId();
    const second = correlationId();
    expect(first).toBe(second);
    expect(first).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
  });
});
