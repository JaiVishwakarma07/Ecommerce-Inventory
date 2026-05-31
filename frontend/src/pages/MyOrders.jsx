import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client.js";
import { formatApiError } from "../utils/apiError.js";
import { formatINR } from "../utils/format.js";

const STATUS_CLASS = {
  pending: "chip-amber",
  processing: "chip-blue",
  shipped: "chip-blue",
  delivered: "chip-green",
  cancelled: "chip-red",
};

export default function MyOrders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/orders/me")
      .then((res) => setOrders(res.data))
      .catch((err) =>
        setError(formatApiError(err, "Failed to load orders"))
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="muted">Loading orders...</div>;
  if (error) return <div className="alert error">{error}</div>;

  return (
    <section>
      <h1>My orders</h1>
      {orders.length === 0 ? (
        <div className="empty">
          You haven't placed any orders yet.{" "}
          <Link to="/products">Start shopping</Link>.
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Order #</th>
                <th>Placed</th>
                <th>Items</th>
                <th>Total</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id}>
                  <td>#{o.id}</td>
                  <td>{new Date(o.created_at).toLocaleString()}</td>
                  <td>{o.items.reduce((s, i) => s + i.quantity, 0)}</td>
                  <td>{formatINR(o.total_amount)}</td>
                  <td>
                    <span className={`chip ${STATUS_CLASS[o.status] || ""}`}>
                      {o.status}
                    </span>
                  </td>
                  <td>
                    <Link to={`/orders/${o.id}`} className="btn btn-ghost">
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
