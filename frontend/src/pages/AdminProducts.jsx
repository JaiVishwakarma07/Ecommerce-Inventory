import { useEffect, useState } from "react";
import api from "../api/client.js";
import { formatApiError } from "../utils/apiError.js";
import { formatINR } from "../utils/format.js";
import { productToForm, toProductWrite } from "../utils/productPayload.js";

const EMPTY_FORM = {
  name: "",
  sku: "",
  description: "",
  price: 0,
  quantity: 0,
  category: "general",
  image_url: "",
};

export default function AdminProducts() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // null = create new
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    setLoading(true);
    api
      .get("/products", { params: { limit: 100 } })
      .then((res) => setProducts(res.data))
      .catch((err) =>
        setError(formatApiError(err, "Failed to load products"))
      )
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  function startEdit(p) {
    setEditing(p.id);
    setForm(productToForm(p));
  }
  function startCreate() {
    setEditing("new");
    setForm(EMPTY_FORM);
  }
  function cancel() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setError("");
  }

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = toProductWrite(form);
      if (editing === "new") {
        await api.post("/products", payload);
      } else {
        await api.put(`/products/${editing}`, payload);
      }
      cancel();
      load();
    } catch (err) {
      setError(
        err instanceof Error && !err.response
          ? err.message
          : formatApiError(err, "Save failed")
      );
    } finally {
      setBusy(false);
    }
  }

  async function remove(p) {
    if (!confirm(`Delete '${p.name}'? This cannot be undone.`)) return;
    try {
      await api.delete(`/products/${p.id}`);
      load();
    } catch (err) {
      setError(formatApiError(err, "Delete failed"));
    }
  }

  return (
    <section>
      <div className="page-header">
        <h1>Manage products</h1>
        <button className="btn btn-primary" onClick={startCreate}>
          + New product
        </button>
      </div>

      {editing && (
        <form className="card form admin-form" onSubmit={save}>
          <h3>{editing === "new" ? "Create product" : `Edit product #${editing}`}</h3>
          <div className="form-grid">
            <label>
              Name
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </label>
            <label>
              SKU
              <input
                value={form.sku}
                onChange={(e) => setForm({ ...form, sku: e.target.value })}
                required
              />
            </label>
            <label>
              Price
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
                required
              />
            </label>
            <label>
              Quantity
              <input
                type="number"
                min="0"
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                required
              />
            </label>
            <label>
              Category
              <input
                value={form.category}
                onChange={(e) =>
                  setForm({ ...form, category: e.target.value })
                }
              />
            </label>
            <label>
              Image URL
              <input
                value={form.image_url}
                onChange={(e) =>
                  setForm({ ...form, image_url: e.target.value })
                }
              />
            </label>
            <label className="full">
              Description
              <textarea
                rows={3}
                value={form.description}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value })
                }
              />
            </label>
          </div>
          {error && <div className="alert error">{error}</div>}
          <div className="row gap">
            <button className="btn btn-primary" disabled={busy}>
              {busy ? "Saving..." : "Save"}
            </button>
            <button type="button" className="btn btn-ghost" onClick={cancel}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="muted">Loading...</div>
      ) : (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Name</th>
                <th>Category</th>
                <th>Price</th>
                <th>Stock</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id}>
                  <td>{p.sku}</td>
                  <td>{p.name}</td>
                  <td>{p.category}</td>
                  <td>{formatINR(p.price)}</td>
                  <td>{p.quantity}</td>
                  <td className="row gap">
                    <button
                      className="btn btn-ghost"
                      onClick={() => startEdit(p)}
                    >
                      Edit
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={() => remove(p)}
                    >
                      Delete
                    </button>
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
