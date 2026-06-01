import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client.js";
import { formatApiError } from "../utils/apiError.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useCart } from "../context/CartContext.jsx";
import { formatINR } from "../utils/format.js";

function ProductCard({ product, isAdmin, isAuthenticated, addItem }) {
  return (
    <article className="card product-card">
      <Link to={`/products/${product.id}`} className="card-image-link">
        <div
          className="card-image"
          style={{
            backgroundImage: product.image_url
              ? `url(${product.image_url})`
              : undefined,
          }}
        />
      </Link>
      <div className="card-body">
        <div className="card-row">
          <span className="chip">{product.category}</span>
          <span
            className={`chip ${product.quantity > 0 ? "chip-green" : "chip-red"}`}
          >
            {product.quantity > 0 ? `${product.quantity} in stock` : "Out of stock"}
          </span>
        </div>
        <h3>
          <Link to={`/products/${product.id}`}>{product.name}</Link>
        </h3>
        <p className="muted clamp">{product.description}</p>
        <div className="card-footer">
          <strong className="price">{formatINR(product.price)}</strong>
          {isAdmin ? (
            <Link to="/admin/products" className="btn btn-ghost">
              Manage
            </Link>
          ) : (
            <button
              className="btn btn-primary"
              disabled={!isAuthenticated || product.quantity === 0}
              onClick={() => addItem(product, 1)}
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
  );
}

export default function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [aiQuery, setAiQuery] = useState("");
  const [aiAnswer, setAiAnswer] = useState("");
  const [aiProducts, setAiProducts] = useState([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  const { isAuthenticated, isAdmin, isCustomer } = useAuth();
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

  async function submitAiQuery(event) {
    event.preventDefault();
    const trimmed = aiQuery.trim();
    if (!trimmed) return;
    setAiLoading(true);
    setAiError("");
    setAiAnswer("");
    setAiProducts([]);
    try {
      const { data } = await api.post("/assistant/query", { query: trimmed });
      setAiAnswer(data.answer);
      setAiProducts(data.products || []);
    } catch (err) {
      setAiError(formatApiError(err, "Assistant temporarily unavailable"));
    } finally {
      setAiLoading(false);
    }
  }

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

      {isCustomer && (
        <form className="assistant-bar" onSubmit={submitAiQuery}>
          <input
            className="search"
            type="text"
            placeholder='Ask AI — e.g. "laptop under 10000"'
            value={aiQuery}
            onChange={(e) => setAiQuery(e.target.value)}
            maxLength={500}
          />
          <button className="btn btn-primary" type="submit" disabled={aiLoading}>
            {aiLoading ? "Searching..." : "Ask AI"}
          </button>
        </form>
      )}
      {aiError && <div className="alert error">{aiError}</div>}
      {aiAnswer && <p className="assistant-answer">{aiAnswer}</p>}
      {aiProducts.length > 0 && (
        <div className="grid">
          {aiProducts.map((p) => (
            <ProductCard
              key={`ai-${p.id}`}
              product={p}
              isAdmin={isAdmin}
              isAuthenticated={isAuthenticated}
              addItem={addItem}
            />
          ))}
        </div>
      )}

      {error && <div className="alert error">{error}</div>}
      {loading ? (
        <div className="muted">Loading products...</div>
      ) : products.length === 0 ? (
        <div className="empty">No products match your search.</div>
      ) : (
        <div className="grid">
          {products.map((p) => (
            <ProductCard
              key={p.id}
              product={p}
              isAdmin={isAdmin}
              isAuthenticated={isAuthenticated}
              addItem={addItem}
            />
          ))}
        </div>
      )}
    </section>
  );
}
