import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client.js";
import { formatApiError } from "../utils/apiError.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useCart } from "../context/CartContext.jsx";
import { formatINR } from "../utils/format.js";

export default function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const { isAuthenticated, isAdmin } = useAuth();
  const { addItem } = useCart();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .get("/products", { params: { search: search || undefined } })
      .then((res) => {
        if (!cancelled) setProducts(res.data);
      })
      .catch((err) => {
        if (!cancelled)
          setError(formatApiError(err, "Failed to load products"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [search]);

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Browse Inventory</h1>
          <p className="muted">All products currently available in stock.</p>
        </div>
        <input
          className="search"
          type="search"
          placeholder="Search by name, SKU, or category..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {error && <div className="alert error">{error}</div>}
      {loading ? (
        <div className="muted">Loading products...</div>
      ) : products.length === 0 ? (
        <div className="empty">No products match your search.</div>
      ) : (
        <div className="grid">
          {products.map((p) => (
            <article className="card product-card" key={p.id}>
              <Link to={`/products/${p.id}`} className="card-image-link">
                <div
                  className="card-image"
                  style={{
                    backgroundImage: p.image_url
                      ? `url(${p.image_url})`
                      : undefined,
                  }}
                />
              </Link>
              <div className="card-body">
                <div className="card-row">
                  <span className="chip">{p.category}</span>
                  <span
                    className={`chip ${p.quantity > 0 ? "chip-green" : "chip-red"}`}
                  >
                    {p.quantity > 0 ? `${p.quantity} in stock` : "Out of stock"}
                  </span>
                </div>
                <h3>
                  <Link to={`/products/${p.id}`}>{p.name}</Link>
                </h3>
                <p className="muted clamp">{p.description}</p>
                <div className="card-footer">
                  <strong className="price">{formatINR(p.price)}</strong>
                  {isAdmin ? (
                    <Link to="/admin/products" className="btn btn-ghost">
                      Manage
                    </Link>
                  ) : (
                    <button
                      className="btn btn-primary"
                      disabled={!isAuthenticated || p.quantity === 0}
                      onClick={() => addItem(p, 1)}
                      title={
                        !isAuthenticated ? "Login to add to cart" : "Add to cart"
                      }
                    >
                      Add
                    </button>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
