import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api/client.js";
import { formatApiError } from "../utils/apiError.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useCart } from "../context/CartContext.jsx";
import { formatINR } from "../utils/format.js";

export default function ProductDetail() {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [qty, setQty] = useState(1);
  const [error, setError] = useState("");
  const { isAuthenticated, isAdmin } = useAuth();
  const { addItem } = useCart();

  useEffect(() => {
    setLoading(true);
    api
      .get(`/products/${id}`)
      .then((res) => setProduct(res.data))
      .catch((err) =>
        setError(formatApiError(err, "Failed to load product"))
      )
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="muted">Loading...</div>;
  if (error) return <div className="alert error">{error}</div>;
  if (!product) return null;

  return (
    <section className="detail">
      <Link to="/products" className="back">
        &larr; Back to products
      </Link>
      <div className="detail-grid">
        <div
          className="detail-image"
          style={{
            backgroundImage: product.image_url
              ? `url(${product.image_url})`
              : undefined,
          }}
        />
        <div>
          <span className="chip">{product.category}</span>
          <h1>{product.name}</h1>
          <p className="muted">SKU: {product.sku}</p>
          <p className="price-lg">{formatINR(product.price)}</p>
          <p>{product.description}</p>
          <p
            className={`chip ${product.quantity > 0 ? "chip-green" : "chip-red"}`}
          >
            {product.quantity > 0
              ? `${product.quantity} in stock`
              : "Out of stock"}
          </p>

          {isAdmin ? (
            <div className="qty-row">
              <Link to="/admin/products" className="btn btn-ghost">
                Manage in admin panel
              </Link>
            </div>
          ) : (
            <div className="qty-row">
              <label>
                Quantity
                <input
                  type="number"
                  min="1"
                  max={product.quantity || 1}
                  value={qty}
                  onChange={(e) =>
                    setQty(Math.max(1, parseInt(e.target.value || "1", 10)))
                  }
                />
              </label>
              <button
                className="btn btn-primary"
                disabled={!isAuthenticated || product.quantity === 0}
                onClick={() => addItem(product, qty)}
              >
                {isAuthenticated ? "Add to cart" : "Login to buy"}
              </button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
