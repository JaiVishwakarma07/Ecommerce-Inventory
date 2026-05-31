import { useEffect, useState } from "react";
import api from "../api/client.js";
import { formatApiError } from "../utils/apiError.js";
import { formatINR } from "../utils/format.js";

const STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled"];

export default function AdminOrders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    api
      .get("/orders", {
        params: { status: filter || undefined, limit: 100 },
      })
      .then((res) => setOrders(res.data))
      .catch((err) =>
        setError(formatApiError(err, "Failed to load orders"))
      )
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, [filter]); // eslint-disable-line react-hooks/exhaustive-deps

  async function changeStatus(orderId, status) {
    try {
      await api.patch(`/orders/${orderId}/status`, { status });
      load();
    } catch (err) {
      setError(formatApiError(err, "Update failed"));
    }
  }

  return (
    <section>
      <div className="page-header">
        <h1>All orders</h1>
        <select
          className="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="alert error">{error}</div>}
      {loading ? (
        <div className="muted">Loading...</div>
      ) : orders.length === 0 ? (
        <div className="empty">No orders found.</div>
      ) : (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Order #</th>
                <th>User</th>
                <th>Placed</th>
                <th>Items</th>
                <th>Total</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id}>
                  <td>#{o.id}</td>
                  <td>user #{o.user_id}</td>
                  <td>{new Date(o.created_at).toLocaleString()}</td>
                  <td>{o.items.reduce((s, i) => s + i.quantity, 0)}</td>
                  <td>{formatINR(o.total_amount)}</td>
                  <td>
                    <select
                      value={o.status}
                      onChange={(e) => changeStatus(o.id, e.target.value)}
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
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
