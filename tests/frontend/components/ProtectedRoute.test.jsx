import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProtectedRoute from "../../../frontend/src/components/ProtectedRoute.jsx";
import { useAuth } from "../../../frontend/src/context/AuthContext.jsx";

vi.mock("../../../frontend/src/context/AuthContext.jsx", () => ({
  useAuth: vi.fn(),
}));

function renderProtectedRoute(props = {}) {
  return render(
    <MemoryRouter initialEntries={["/protected"]}>
      <Routes>
        <Route
          path="/protected"
          element={
            <ProtectedRoute {...props}>
              <div>Secret content</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div>Login page</div>} />
        <Route path="/" element={<div>Home page</div>} />
        <Route path="/admin/products" element={<div>Admin products</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReset();
  });

  it("shows loading while auth is bootstrapping", () => {
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      isAdmin: false,
      bootstrapping: true,
    });

    renderProtectedRoute();
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("redirects unauthenticated users to login", () => {
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      isAdmin: false,
      bootstrapping: false,
    });

    renderProtectedRoute();
    expect(screen.getByText("Login page")).toBeInTheDocument();
  });

  it("renders children for authenticated users", () => {
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: true,
      isAdmin: false,
      bootstrapping: false,
    });

    renderProtectedRoute();
    expect(screen.getByText("Secret content")).toBeInTheDocument();
  });

  it("redirects non-admin users away from admin-only routes", () => {
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: true,
      isAdmin: false,
      bootstrapping: false,
    });

    renderProtectedRoute({ adminOnly: true });
    expect(screen.getByText("Home page")).toBeInTheDocument();
  });

  it("redirects admins away from customer-only routes", () => {
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: true,
      isAdmin: true,
      bootstrapping: false,
    });

    renderProtectedRoute({ customerOnly: true });
    expect(screen.getByText("Admin products")).toBeInTheDocument();
  });
});
