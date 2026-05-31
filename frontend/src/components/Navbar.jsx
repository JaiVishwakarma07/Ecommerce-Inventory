import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useCart } from "../context/CartContext.jsx";

export default function Navbar() {
  const { user, isAuthenticated, isAdmin, logout } = useAuth();
  const { itemCount } = useCart();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header className="navbar">
      <div className="navbar-inner container">
        <Link to="/" className="brand">
          <span className="brand-mark">IM</span>
          <span>Inventory Manager</span>
        </Link>

        <nav className="nav-links">
          <NavLink to="/products">Products</NavLink>
          {isAuthenticated && !isAdmin && (
            <NavLink to="/orders">My Orders</NavLink>
          )}
          {isAdmin && (
            <>
              <NavLink to="/admin/insights">Insights</NavLink>
              <NavLink to="/admin/products">Manage Products</NavLink>
              <NavLink to="/admin/orders">All Orders</NavLink>
            </>
          )}
        </nav>

        <div className="nav-actions">
          {isAuthenticated && !isAdmin && (
            <Link to="/cart" className="cart-link" aria-label="Open cart">
              Cart
              {itemCount > 0 && <span className="badge">{itemCount}</span>}
            </Link>
          )}
          {isAuthenticated ? (
            <>
              <span className="hello">Hi, {user.full_name.split(" ")[0]}</span>
              <button className="btn btn-ghost" onClick={handleLogout}>
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn btn-ghost">
                Login
              </Link>
              <Link to="/register" className="btn btn-primary">
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
