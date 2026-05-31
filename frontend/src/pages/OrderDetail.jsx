import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api/client.js";
import { formatApiError } from "../utils/apiError.js";
import { formatINR } from "../utils/format.js";

export default function OrderDetail() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get(`/orders/${id}`)
      .then((res) => setOrder(res.data))
      .catch((err) =>
        setError(
          formatApiError(
            err,
            err.response?.status === 403
              ? "You do not have access to this order."
              : "Failed to load order"
          )
        )
      )
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="muted">Loading order...</div>;
  if (error) return <div className="alert error">{error}</div>;
  if (!order) return null;

  return (
    <section>
      <Link to="/orders" className="back">
        &larr; Back to my orders
      </Link>
      <h1>Order #{order.id}</h1>
      <div className="card detail-card">
        <div className="row">
          <span className="muted">Placed</span>
          <span>{new Date(order.created_at).toLocaleString()}</span>
        </div>
        <div className="row">
          <span className="muted">Status</span>
          <span className="chip">{order.status}</span>
        </div>
        <div className="row">
          <span className="muted">Shipping address</span>
          <span>{order.shipping_address}</span>
        </div>
        <hr />
        <h3>Items</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Qty</th>
              <th>Unit</th>
              <th>Subtotal</th>
            </tr>
          </thead>
          <tbody>
            {order.items.map((it) => (
              <tr key={it.id}>
                <td>{it.product_name}</td>
                <td>{it.quantity}</td>
                <td>{formatINR(it.unit_price)}</td>
                <td>{formatINR(it.unit_price * it.quantity)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3} className="text-right">
                <strong>Total</strong>
              </td>
              <td>
                <strong>{formatINR(order.total_amount)}</strong>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}
