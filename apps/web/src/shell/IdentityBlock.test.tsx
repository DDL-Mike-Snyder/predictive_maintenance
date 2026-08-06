import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IdentityBlock } from "./IdentityBlock";
import { client } from "../api/client";

// Mocks the wire boundary only (`client.GET`/`client.POST`) -- everything
// above that (react-query, the component's own state machine for
// loading/login/authenticated) is real. Covers 51-operator-console.md
// §4.7's shell states for the subset this pass actually implements:
// loading, `404` -> sign-in affordance, and a successful session.
vi.mock("../api/client", () => ({
  client: { GET: vi.fn(), POST: vi.fn() },
}));

function renderWithQueryClient() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <IdentityBlock />
    </QueryClientProvider>,
  );
}

describe("IdentityBlock", () => {
  beforeEach(() => {
    vi.mocked(client.GET).mockReset();
    vi.mocked(client.POST).mockReset();
  });

  it("shows a sign-in affordance when the session lookup 404s (no session)", async () => {
    vi.mocked(client.GET).mockResolvedValue({
      data: undefined,
      error: { type: "urn:fathom:problem:gateway:no-session" } as unknown as never,
      response: { status: 404 } as Response,
    });

    renderWithQueryClient();

    const signIn = await screen.findByRole("link", { name: /sign in/i });
    expect(signIn).toHaveAttribute("href", "/api/v1/gateway/session/login");
  });

  it("renders the real session id and a sign-out control on success", async () => {
    vi.mocked(client.GET).mockResolvedValue({
      data: { session_id: "abcdef12-3456-7890-abcd-ef1234567890", expires_at: "2026-08-06T00:00:00Z" },
      error: undefined,
      response: { status: 200 } as Response,
    });

    renderWithQueryClient();

    await waitFor(() => expect(screen.getByText(/abcdef12/)).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument();
  });

  it("renders an inline error for a non-404 session failure, per §4.7", async () => {
    vi.mocked(client.GET).mockResolvedValue({
      data: undefined,
      error: { type: "urn:fathom:problem:common:internal-error" } as unknown as never,
      response: { status: 500 } as Response,
    });

    renderWithQueryClient();

    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't load identity/i);
  });
});
