import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function ProtectedRoute({
  children,
  adminOnly = false,
  customerOnly = false,
}) {
  const { isAuthenticated, isAdmin, bootstrapping } = useAuth();
  const location = useLocation();

  if (bootstrapping) {
    return <div className="muted">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (adminOnly && !isAdmin) {
    return <Navigate to="/" replace />;
  }
  if (customerOnly && isAdmin) {
    return <Navigate to="/admin/products" replace />;
  }
  return children;
}
