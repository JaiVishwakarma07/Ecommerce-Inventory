import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/client.js";
import { useCart } from "../context/CartContext.jsx";
import { formatApiError } from "../utils/apiError.js";
import { formatINR } from "../utils/format.js";
import { validateCartStock } from "../utils/validateCartStock.js";

export default function Cart() {
  const { items, total, updateQuantity, removeItem, clearCart } = useCart();
  const [address, setAddress] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function handleCheckout(e) {
    e.preventDefault();
    if (items.length === 0) return;
    setSubmitting(true);
    setError("");
    try {
      const trimmedAddress = address.trim();
      if (!trimmedAddress) {
        setError("Enter a shipping address.");
        return;
      }

      const { data: products } = await api.get("/products", {
        params: { limit: 100 },
      });
      const stockCheck = validateCartStock(items, products);
      if (!stockCheck.ok) {
        setError(stockCheck.issues.join(" "));
        return;
      }

      const payload = {
        shipping_address: trimmedAddress,
        items: items.map((i) => ({
          product_id: i.product_id,
          quantity: i.quantity,
        })),
      };
      const { data } = await api.post("/orders", payload);
      clearCart();
      navigate(`/orders/${data.id}`);
    } catch (err) {
      setError(formatApiError(err, "Could not place order"));
    } finally {
      setSubmitting(false);
    }
  }

  if (items.length === 0) {
    return (
      <section>
        <h1>Your cart</h1>
        <div className="empty">
          Your cart is empty. <Link to="/products">Browse products</Link>.
        </div>
      </section>
    );
  }

  return (
    <section>
      <h1>Your cart</h1>
      <div className="cart-grid">
        <div className="cart-list">
          {items.map((i) => (
            <div className="cart-item" key={i.product_id}>
              <div
                className="cart-thumb"
                style={{
                  backgroundImage: i.image_url ? `url(${i.image_url})` : undefined,
                }}
              />
              <div className="cart-info">
                <strong>{i.name}</strong>
                <div className="muted">{formatINR(i.price)} each</div>
              </div>
              <input
                type="number"
                min="1"
                value={i.quantity}
                onChange={(e) =>
                  updateQuantity(
                    i.product_id,
                    Math.max(1, parseInt(e.target.value || "1", 10))
                  )
                }
                className="qty-input"
              />
              <div className="cart-line-total">
                {formatINR(i.price * i.quantity)}
              </div>
              <button
                className="btn btn-ghost"
                onClick={() => removeItem(i.product_id)}
              >
                Remove
              </button>
            </div>
          ))}
        </div>

        <aside className="cart-summary card">
          <h2>Order summary</h2>
          <div className="row">
            <span>Subtotal</span>
            <strong>{formatINR(total)}</strong>
          </div>
          <div className="row muted">
            <span>Shipping</span>
            <span>Calculated at checkout</span>
          </div>
          <hr />
          <form onSubmit={handleCheckout} className="form">
            <label>
              Shipping address
              <textarea
                rows={3}
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                required
                placeholder="Street, City, Postal code, Country"
              />
            </label>
            {error && <div className="alert error">{error}</div>}
            <button className="btn btn-primary btn-block" disabled={submitting}>
              {submitting ? "Placing order..." : "Place order"}
            </button>
          </form>
        </aside>
      </div>
    </section>
  );
}
